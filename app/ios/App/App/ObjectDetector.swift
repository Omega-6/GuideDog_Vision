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

    // Latest results
    private(set) var detectedObjects: [DetectedObject] = []

    // Throttle
    private var isProcessing = false

    init() {
        // Load model in background to avoid blocking UI
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.loadModel()
        }
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
                try handler.perform([request])
            } catch {
                print("❌ OBJECT DETECTOR: \(error.localizedDescription)")
            }
        }
    }

    // MARK: - Process Results

    private func handleResults(request: VNRequest, error: Error?) {
        guard let results = request.results as? [VNRecognizedObjectObservation] else { return }

        // Filter out low-confidence noise
        let minConfidence: Float = 0.7

        let objects = results
            .filter { ($0.labels.first?.confidence ?? 0) >= minConfidence }
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
