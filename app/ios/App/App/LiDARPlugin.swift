import Capacitor
import ARKit
import Foundation

@objc(LiDARPlugin)
public class LiDARPlugin: CAPPlugin, ARSessionDelegate {

    private var arSession: ARSession?
    private var isRunning = false
    private var lastNotifyTime: TimeInterval = 0
    private let notifyInterval: TimeInterval = 0.1  // max 10 events/sec to JS

    @objc func isAvailable(_ call: CAPPluginCall) {
        let available = ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth)
        call.resolve(["available": available])
    }

    @objc func start(_ call: CAPPluginCall) {
        guard ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) else {
            call.reject("LiDAR not available on this device")
            return
        }

        DispatchQueue.main.async {
            let config = ARWorldTrackingConfiguration()
            config.frameSemantics = .sceneDepth

            self.arSession = ARSession()
            self.arSession?.delegate = self
            self.arSession?.run(config)
            self.isRunning = true
            call.resolve(["started": true])
        }
    }

    @objc func stop(_ call: CAPPluginCall) {
        DispatchQueue.main.async {
            self.arSession?.pause()
            self.arSession = nil
            self.isRunning = false
            call.resolve()
        }
    }

    // ARSessionDelegate — fires for every AR frame (~60fps)
    public func session(_ session: ARSession, didUpdate frame: ARFrame) {
        guard isRunning else { return }

        let now = Date().timeIntervalSince1970
        guard now - lastNotifyTime >= notifyInterval else { return }
        lastNotifyTime = now

        guard let depthMap = frame.sceneDepth?.depthMap else { return }

        let width  = CVPixelBufferGetWidth(depthMap)
        let height = CVPixelBufferGetHeight(depthMap)

        CVPixelBufferLockBaseAddress(depthMap, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(depthMap, .readOnly) }

        guard let base = CVPixelBufferGetBaseAddress(depthMap) else { return }
        let floatBuffer = base.assumingMemoryBound(to: Float32.self)

        // Sample three vertical strips: left (0–22%), center (30–70%), right (78–100%)
        var cSum: Float = 0; var cN = 0
        var lSum: Float = 0; var lN = 0
        var rSum: Float = 0; var rN = 0

        let yStart = Int(Double(height) * 0.2)
        let yEnd   = Int(Double(height) * 0.8)

        for y in yStart..<yEnd {
            for x in 0..<width {
                let d = floatBuffer[y * width + x]
                guard d.isFinite && d > 0 else { continue }
                let fx = Double(x) / Double(width)
                if fx > 0.30 && fx < 0.70      { cSum += d; cN += 1 }
                else if fx < 0.22              { lSum += d; lN += 1 }
                else if fx > 0.78              { rSum += d; rN += 1 }
            }
        }

        let c = cN > 0 ? Double(cSum) / Double(cN) : 5.0
        let l = lN > 0 ? Double(lSum) / Double(lN) : 5.0
        let r = rN > 0 ? Double(rSum) / Double(rN) : 5.0

        notifyListeners("depthReading", data: [
            "c": c,
            "l": l,
            "r": r,
            "timestamp": now
        ])
    }

    public func session(_ session: ARSession, didFailWithError error: Error) {
        notifyListeners("depthError", data: ["message": error.localizedDescription])
        isRunning = false
    }
}
