import Foundation
import AVFoundation
import CoreVideo
import UIKit

/// "AI Race" — sends camera frame to both Claude and ChatGPT via Cloudflare Worker,
/// speaks whichever response arrives first for real-time scene description.
public class AISceneDescriber {

    // MARK: - Configuration

    /// Cloudflare Worker URL — proxies to Claude & OpenAI (API keys stored as Worker secrets)
    private static let workerURL = "https://guidedog.kpremks.workers.dev"

    /// Timeout for each API call (seconds)
    private static let requestTimeout: TimeInterval = 5.0

    /// Minimum interval between scene descriptions to avoid spamming (seconds)
    private static let cooldownInterval: TimeInterval = 5.0

    /// JPEG compression quality for camera frames (0.0-1.0, lower = smaller payload)
    private static let jpegQuality: CGFloat = 0.3

    // MARK: - State

    private var lastDescriptionTime: Date = .distantPast
    private var isDescribing = false
    private let session: URLSession

    // MARK: - Callbacks

    /// Called when a scene description is ready to be spoken
    public var onDescription: ((String, String) -> Void)?  // (description, provider)

    /// Called when an error occurs
    public var onError: ((String) -> Void)?

    // MARK: - Init

    public init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = Self.requestTimeout
        config.timeoutIntervalForResource = Self.requestTimeout + 5
        self.session = URLSession(configuration: config)
    }

    // MARK: - Public API

    /// Describe the current scene by racing Claude vs ChatGPT
    /// - Parameter pixelBuffer: Camera frame from ARSession
    public func describeScene(pixelBuffer: CVPixelBuffer) {
        let now = Date()
        guard now.timeIntervalSince(lastDescriptionTime) >= Self.cooldownInterval else { return }
        guard !isDescribing else { return }

        isDescribing = true
        lastDescriptionTime = now

        // Encode image OFF main thread to prevent AR freeze
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }

            guard let base64Image = self.pixelBufferToBase64(pixelBuffer) else {
                DispatchQueue.main.async {
                    self.isDescribing = false
                    self.onError?("Failed to capture camera frame")
                }
                return
            }

            print("AISceneDescriber: Starting AI Race (image size: \(base64Image.count) chars)")
            self.raceProviders(base64Image: base64Image)
        }
    }

    /// Check if the describer is ready (not in cooldown or already running)
    public var isReady: Bool {
        let now = Date()
        return !isDescribing && now.timeIntervalSince(lastDescriptionTime) >= Self.cooldownInterval
    }

    // MARK: - Race Logic

    private func raceProviders(base64Image: String) {
        let group = DispatchGroup()
        var firstResult: (description: String, provider: String)?
        var errors: [String] = []
        let lock = NSLock()
        var finished = false

        // Launch both requests simultaneously
        for provider in ["anthropic", "openai"] {
            group.enter()

            callWorker(base64Image: base64Image, provider: provider) { result in
                lock.lock()
                defer {
                    lock.unlock()
                    group.leave()
                }

                switch result {
                case .success(let description):
                    if !finished {
                        finished = true
                        firstResult = (description, provider)
                        print("AISceneDescriber: \(provider) won the race!")
                    } else {
                        print("AISceneDescriber: \(provider) also returned (not used)")
                    }

                case .failure(let error):
                    errors.append("\(provider): \(error.localizedDescription)")
                    print("AISceneDescriber: \(provider) failed — \(error.localizedDescription)")
                }
            }
        }

        // When both complete (or timeout), deliver result
        group.notify(queue: .main) { [weak self] in
            guard let self = self else { return }
            self.isDescribing = false

            if let result = firstResult {
                self.onDescription?(result.description, result.provider)
            } else {
                let errorMsg = errors.isEmpty ? "Both APIs timed out" : errors.joined(separator: "; ")
                self.onError?("Scene description failed: \(errorMsg)")
            }
        }
    }

    // MARK: - Worker API Call

    private func callWorker(base64Image: String, provider: String, completion: @escaping (Result<String, Error>) -> Void) {
        guard let url = URL(string: Self.workerURL) else {
            completion(.failure(NSError(domain: "AISceneDescriber", code: -1,
                                       userInfo: [NSLocalizedDescriptionKey: "Invalid worker URL"])))
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "image": base64Image,
            "provider": provider
        ]

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        } catch {
            completion(.failure(error))
            return
        }

        let task = session.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data else {
                completion(.failure(NSError(domain: "AISceneDescriber", code: -2,
                                           userInfo: [NSLocalizedDescriptionKey: "No data received"])))
                return
            }

            do {
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    if let result = json["result"] as? String {
                        completion(.success(result))
                    } else if let error = json["error"] as? String {
                        completion(.failure(NSError(domain: "AISceneDescriber", code: -3,
                                                   userInfo: [NSLocalizedDescriptionKey: error])))
                    } else {
                        completion(.failure(NSError(domain: "AISceneDescriber", code: -4,
                                                   userInfo: [NSLocalizedDescriptionKey: "Unexpected response format"])))
                    }
                }
            } catch {
                completion(.failure(error))
            }
        }

        task.resume()
    }

    // MARK: - Image Conversion

    private func pixelBufferToBase64(_ pixelBuffer: CVPixelBuffer) -> String? {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let context = CIContext()

        // Get the full extent of the image
        let extent = ciImage.extent

        guard let cgImage = context.createCGImage(ciImage, from: extent) else {
            print("AISceneDescriber: Failed to create CGImage")
            return nil
        }

        let uiImage = UIImage(cgImage: cgImage)

        // Resize to reduce payload — 384px is enough for scene understanding
        let resized = resizeImage(uiImage, maxDimension: 384)

        guard let jpegData = resized.jpegData(compressionQuality: Self.jpegQuality) else {
            print("AISceneDescriber: Failed to create JPEG data")
            return nil
        }

        print("AISceneDescriber: Image compressed to \(jpegData.count / 1024) KB")
        return jpegData.base64EncodedString()
    }

    private func resizeImage(_ image: UIImage, maxDimension: CGFloat) -> UIImage {
        let size = image.size
        let ratio = min(maxDimension / size.width, maxDimension / size.height)

        // Don't upscale
        guard ratio < 1.0 else { return image }

        let newSize = CGSize(width: size.width * ratio, height: size.height * ratio)
        let renderer = UIGraphicsImageRenderer(size: newSize)
        return renderer.image { _ in
            image.draw(in: CGRect(origin: .zero, size: newSize))
        }
    }
}
