import Vision
import CoreML
import ARKit

// MARK: - Detected Object Model

struct DetectedObject {
    let label: String
    let confidence: Float
    let boundingBox: CGRect   // Normalized (0...1) from Vision
}

// MARK: - Object Detector (Vision + CoreML)

class ObjectDetector {

    private var vnModel: VNCoreMLModel?
    private var request: VNCoreMLRequest?

    // Apple's first-party human-rectangle detector, used as a corroborator
    // for YOLOv8n's `person` class. Person is by far the most common false
    // positive (mannequins, posters, large coats, tall narrow shapes). When
    // YOLO says "person" but VNDetectHumanRectanglesRequest sees no human
    // rectangle in roughly the same region, the detection is dropped.
    private var humanRequest: VNDetectHumanRectanglesRequest?
    private var latestHumanBoxes: [CGRect] = []

    // Latest results
    private(set) var detectedObjects: [DetectedObject] = []

    // Throttle
    private var isProcessing = false

    init() {
        // Load model in background to avoid blocking UI
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.loadModel()
        }

        // Configure Apple's human detector synchronously — no model file
        // needed, it ships with the Vision framework.
        let req = VNDetectHumanRectanglesRequest { [weak self] request, _ in
            let humans = (request.results as? [VNHumanObservation]) ?? []
            self?.latestHumanBoxes = humans.map { $0.boundingBox }
        }
        // Default detects upper bodies only; switching to full body matches
        // what YOLO sees (whole-person bounding boxes).
        if #available(iOS 15.0, *) {
            req.upperBodyOnly = false
        }
        humanRequest = req
    }

    // MARK: - Model Loading

    /// Load ANY CoreML object detection model.
    ///
    /// HOW TO USE:
    /// 1. Download a model from https://developer.apple.com/machine-learning/models/
    ///    - Recommended: YOLOv3 (fast) or YOLOv3Tiny (fastest, less accurate)
    /// 2. Drag the .mlmodel file into your Xcode project
    /// 3. Xcode auto-generates a Swift class with the same name (e.g. YOLOv3.swift)
    /// 4. Replace the model loading line below with YOUR model class:
    ///
    ///    let mlModel = try YOLOv3(configuration: .init()).model
    ///    — or —
    ///    let mlModel = try YOLOv3Tiny(configuration: .init()).model
    ///
    private func loadModel() {
        do {
            // Look for YOLOv8n specifically (not DeepLabV3 or other models)
            let preferredNames = ["YOLOv8n", "yolov8n", "YOLOv3Tiny"]
            var modelURL: URL?

            for name in preferredNames {
                if let url = Bundle.main.url(forResource: name, withExtension: "mlmodelc") {
                    modelURL = url
                    break
                }
            }

            guard let foundURL = modelURL else {
                print("❌ OBJECT DETECTOR: No YOLO .mlmodelc found in bundle.")
                print("   Looked for: \(preferredNames.joined(separator: ", "))")
                return
            }

            let mlModel = try MLModel(contentsOf: foundURL)
            vnModel = try VNCoreMLModel(for: mlModel)

            // Build the request
            request = VNCoreMLRequest(model: vnModel!) { [weak self] request, error in
                self?.handleResults(request: request, error: error)
            }

            // Crop the input to match the model's expected aspect ratio
            request?.imageCropAndScaleOption = .scaleFill

            print("✅ OBJECT DETECTOR: Model loaded from \(foundURL.lastPathComponent)")

        } catch {
            print("❌ OBJECT DETECTOR: Failed to load model — \(error.localizedDescription)")
        }
    }

    // MARK: - Run Detection on an AR Frame

    /// Call this from the ARSession delegate on a background thread.
    /// Pass the ARFrame's capturedImage (CVPixelBuffer from the camera).
    func detect(pixelBuffer: CVPixelBuffer) {
        guard let request = request, !isProcessing else { return }

        isProcessing = true

        // Vision needs the correct orientation for the rear camera
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .right, options: [:])

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            defer { self?.isProcessing = false }

            do {
                // Order matters — humanRequest's completion fires before
                // YOLO's, so by the time handleResults() runs, the human
                // boxes for this frame are already cached in
                // latestHumanBoxes and the person-validator can use them.
                var requests: [VNRequest] = []
                if let h = self?.humanRequest { requests.append(h) }
                requests.append(request)
                try handler.perform(requests)
            } catch {
                print("❌ OBJECT DETECTOR: \(error.localizedDescription)")
            }
        }
    }

    // MARK: - Process Results

    private func handleResults(request: VNRequest, error: Error?) {
        guard let results = request.results as? [VNRecognizedObjectObservation] else { return }

        // Filter out low-confidence noise. Default 0.75 (raised from 0.7
        // when detection rate doubled). Per-class overrides tighten the
        // gate further for classes that YOLO routinely hallucinates:
        //   refrigerator — pattern-matches onto any tall rectangular
        //     vertical surface (fridges, doors, large posters, lockers).
        //   tv — false-fires on monitors, mirrors, paintings.
        //   chair — pattern-matches onto the back of any seating, table
        //     legs, generic four-legged silhouettes.
        //   bed — fires on couches, large tables, ottomans, low flat
        //     horizontal surfaces.
        let defaultMin: Float = 0.75
        let perClassMin: [String: Float] = [
            "refrigerator": 0.88,
            "tv": 0.90,
            "chair": 0.90,
            "bed": 0.85,
            "dining table": 0.85,
        ]

        let humans = self.latestHumanBoxes

        let objects = results
            .filter { obs in
                let label = obs.labels.first?.identifier.lowercased() ?? ""
                let conf  = obs.labels.first?.confidence ?? 0
                let minC  = perClassMin[label] ?? defaultMin
                return conf >= minC
            }
            .filter { obs in
                // Person validator: when YOLO says "person", require
                // Apple's VNDetectHumanRectanglesRequest to also see a
                // human in roughly the same region (IoU ≥ 0.2). Other
                // classes pass through unchanged.
                let label = obs.labels.first?.identifier.lowercased() ?? ""
                guard label == "person" else { return true }
                let yoloBox = obs.boundingBox
                return humans.contains { Self.iou($0, yoloBox) >= 0.2 }
            }
            .prefix(5) // Keep top 5 at most
            .map { observation -> DetectedObject in
                let topLabel = observation.labels.first!
                return DetectedObject(
                    label: topLabel.identifier,
                    confidence: topLabel.confidence,
                    boundingBox: observation.boundingBox
                )
            }

        detectedObjects = Array(objects)
    }

    // Intersection-over-union for two normalised bounding boxes. Used to
    // confirm YOLO's "person" detection lines up with Apple's first-party
    // human-rectangle output. Threshold of 0.2 is intentionally loose —
    // we want to confirm overlap, not require pixel-perfect alignment.
    private static func iou(_ a: CGRect, _ b: CGRect) -> CGFloat {
        let inter = a.intersection(b)
        guard !inter.isNull, inter.width > 0, inter.height > 0 else { return 0 }
        let interArea = inter.width * inter.height
        let unionArea = a.width * a.height + b.width * b.height - interArea
        return unionArea > 0 ? interArea / unionArea : 0
    }

    // MARK: - Helpers

    /// Returns the single most prominent object (highest confidence).
    var topObject: DetectedObject? {
        detectedObjects.max(by: { $0.confidence < $1.confidence })
    }

    /// Returns true if the model loaded successfully.
    var isReady: Bool {
        vnModel != nil
    }
}
