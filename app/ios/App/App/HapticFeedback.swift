import UIKit

// MARK: - HapticController
class HapticController {
    private var pulseTimer: Timer?
    private var currentRiskLevel: RiskLevel = .safe
    private var feedbackGeneratorLight: UIImpactFeedbackGenerator?
    private var feedbackGeneratorHeavy: UIImpactFeedbackGenerator?

    init() {
        prepareFeedbackGenerators()
    }

    private func prepareFeedbackGenerators() {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.feedbackGeneratorLight = UIImpactFeedbackGenerator(style: .light)
            self.feedbackGeneratorHeavy = UIImpactFeedbackGenerator(style: .heavy)
            self.feedbackGeneratorLight?.prepare()
            self.feedbackGeneratorHeavy?.prepare()
        }
    }

    /// Updates haptic feedback based on risk level and distance
    /// Only changes pulsing timer if risk level has changed
    /// - Parameters:
    ///   - risk: The current risk level (safe, caution, or danger)
    ///   - distance: The distance in meters
    func updateFeedback(risk: RiskLevel, distance: Float) {
        // Only update if risk level has changed
        guard risk != currentRiskLevel else { return }

        currentRiskLevel = risk

        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }

            // Stop existing timer
            self.pulseTimer?.invalidate()
            self.pulseTimer = nil

            switch risk {
            case .safe:
                // No pulsing for safe
                break

            case .caution:
                // Light pulse every 0.5 seconds
                self.pulseTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
                    self?.feedbackGeneratorLight?.impactOccurred()
                }

            case .danger:
                // Heavy pulse every 0.1 seconds
                self.pulseTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
                    self?.feedbackGeneratorHeavy?.impactOccurred()
                }
            }
        }
    }

    /// Stops all haptic feedback and resets to safe state
    func stop() {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }

            self.pulseTimer?.invalidate()
            self.pulseTimer = nil
            self.currentRiskLevel = .safe
        }
    }

    deinit {
        pulseTimer?.invalidate()
        pulseTimer = nil
    }
}
