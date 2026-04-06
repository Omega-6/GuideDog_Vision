import ARKit

// MARK: - MeshHit

struct MeshHit {
    let classification: ARMeshClassification
    let distance: Float
    let direction: String  // "left" | "center" | "right"

    var label: String { classification.label }

    /// True for surfaces a walking user needs to know about
    var isNavigationRelevant: Bool {
        switch classification {
        case .wall, .door, .window, .seat, .table: return true
        default: return false
        }
    }
}

// MARK: - MeshClassifier
//
// Adapted from GuideVision — works with ARFrame directly (no ARView/RealityKit required).
// Scans ARMeshAnchors in the current frame and returns hits sorted by distance.

class MeshClassifier {

    // Throttle: only run every N frames (call sites decide)
    private(set) var latestHits: [MeshHit] = []

    // MARK: - Public API

    /// Call from ARSession delegate, background thread OK.
    func classify(frame: ARFrame) {
        let cameraTransform = frame.camera.transform

        let camPos = SIMD3<Float>(cameraTransform.columns.3.x,
                                   cameraTransform.columns.3.y,
                                   cameraTransform.columns.3.z)
        // Camera faces –Z in camera space; transform that to world space
        let forwardDir = normalize(-SIMD3<Float>(cameraTransform.columns.2.x,
                                                  cameraTransform.columns.2.y,
                                                  cameraTransform.columns.2.z))
        let rightDir   =  normalize(SIMD3<Float>(cameraTransform.columns.0.x,
                                                  cameraTransform.columns.0.y,
                                                  cameraTransform.columns.0.z))

        var hits: [MeshHit] = []

        for anchor in frame.anchors {
            guard let mesh = anchor as? ARMeshAnchor,
                  let classData = mesh.geometry.classification else { continue }

            let anchorPos = SIMD3<Float>(mesh.transform.columns.3.x,
                                          mesh.transform.columns.3.y,
                                          mesh.transform.columns.3.z)

            let toAnchor = anchorPos - camPos
            let distance = length(toAnchor)
            guard distance > 0.1, distance < 4.0 else { continue }

            // Only consider anchors broadly in front of the user (within ~60° cone)
            let dotFwd = dot(normalize(toAnchor), forwardDir)
            guard dotFwd > 0.5 else { continue }

            // Determine lateral direction
            let dotRight = dot(normalize(toAnchor), rightDir)
            let direction: String
            if dotRight < -0.3      { direction = "left"   }
            else if dotRight > 0.3  { direction = "right"  }
            else                    { direction = "center" }

            // Sample up to 200 faces to find dominant classification
            let faceCount = mesh.geometry.faces.count
            let sampleCount = min(faceCount, 200)
            let buf = classData.buffer.contents().assumingMemoryBound(to: UInt8.self)
            var counts = [Int: Int]()
            let step = max(1, faceCount / sampleCount)
            for i in stride(from: 0, to: faceCount, by: step) {
                let id = Int(buf[i])
                counts[id, default: 0] += 1
            }

            guard let (dominantId, _) = counts.max(by: { $0.value < $1.value }),
                  let cls = ARMeshClassification(rawValue: dominantId),
                  cls != .none else { continue }

            hits.append(MeshHit(classification: cls, distance: distance, direction: direction))
        }

        // Deduplicate: keep only closest hit per (classification, direction) pair
        var seen = Set<String>()
        latestHits = hits
            .sorted { $0.distance < $1.distance }
            .filter { seen.insert("\($0.classification.rawValue)-\($0.direction)").inserted }
    }

    /// Returns the closest navigation-relevant hit in the center zone, if any.
    var centerHit: MeshHit? {
        latestHits.first { $0.direction == "center" && $0.isNavigationRelevant }
    }
}

// MARK: - ARMeshClassification label

extension ARMeshClassification {
    var label: String {
        switch self {
        case .ceiling: return "Ceiling"
        case .door:    return "Door"
        case .floor:   return "Floor"
        case .seat:    return "Seat"
        case .table:   return "Table"
        case .wall:    return "Wall"
        case .window:  return "Window"
        case .none:    return "None"
        @unknown default: return "Unknown"
        }
    }
}
