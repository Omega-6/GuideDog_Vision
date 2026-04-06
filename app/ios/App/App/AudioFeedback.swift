import AVFoundation

// MARK: - RiskLevel Enum
enum RiskLevel: Equatable {
    case safe
    case caution
    case danger
}

// MARK: - RiskSolver Struct
struct RiskSolver {
    // Entry thresholds
    static let dangerThreshold: Float  = 1.0  // < 1.0m → danger  (~3.3 ft, 0.8s reaction at 1.2m/s)
    static let cautionThreshold: Float = 2.0  // < 2.0m → caution (~6.6 ft, 1.7s reaction)

    // Hysteresis exit thresholds — must move THIS far away before risk level drops
    // Prevents oscillation when LiDAR readings bounce at a threshold boundary
    static let dangerExit: Float  = 1.3   // exit danger when center > 1.3m
    static let cautionExit: Float = 2.4   // exit caution when center > 2.4m

    static func analyze(distance: Float?) -> RiskLevel {
        guard let distance = distance, distance > 0 else { return .safe }
        if distance < dangerThreshold  { return .danger  }
        if distance < cautionThreshold { return .caution }
        return .safe
    }

    /// Hysteresis-aware analysis: only escalates freely, de-escalates conservatively.
    static func analyze(distance: Float?, current: RiskLevel) -> RiskLevel {
        guard let d = distance, d > 0 else { return .safe }
        // Escalate immediately
        if d < dangerThreshold  { return .danger  }
        if d < cautionThreshold { return .caution }
        // De-escalate only past hysteresis exit thresholds
        switch current {
        case .danger:  return d < dangerExit  ? .danger  : (d < cautionExit ? .caution : .safe)
        case .caution: return d < cautionExit ? .caution : .safe
        case .safe:    return .safe
        }
    }

    static func metersToFeet(_ meters: Float?) -> String {
        guard let meters = meters, meters > 0 else {
            return "Unknown"
        }

        let feet = meters * 3.28084

        if feet < 1 {
            let inches = feet * 12
            return String(format: "%.0f inches", inches)
        } else if feet < 100 {
            return String(format: "%.1f ft", feet)
        } else {
            return String(format: "%.0f ft", feet)
        }
    }
}

// MARK: - SpeechController
//
// Priority levels (higher = more urgent):
//   danger(3)    — "Stop!" alerts from depth/detection
//   caution(2)   — "Obstacle ahead" warnings
//   detection(1) — object labels ("door ahead")
//   info(0)      — AI scene descriptions, status messages
//
// Rules:
//  • Lower priority never interrupts currently-speaking higher priority
//  • Each priority has its own repeat cooldown (danger=2s, caution=4s, detection=6s, info=10s)
//  • Same text at same priority won't repeat within its cooldown
class SpeechController: NSObject, AVSpeechSynthesizerDelegate {
    private let synthesizer = AVSpeechSynthesizer()

    private enum Priority: Int, Comparable {
        case info = 0, detection = 1, caution = 2, danger = 3, user = 4
        static func < (a: Priority, b: Priority) -> Bool { a.rawValue < b.rawValue }

        var cooldown: TimeInterval {
            switch self {
            case .user:      return 0.5   // user-initiated — almost no cooldown
            case .danger:    return 2.0
            case .caution:   return 4.0
            case .detection: return 6.0
            case .info:      return 10.0
            }
        }
    }

    private var lastText: String?
    private var lastTime: Date?
    private var currentPriority: Priority = .info
    private let lock = NSLock()

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    // urgency mapping (matches NavigationEngine call sites):
    //   urgency 0   → info
    //   urgency 1–2 → detection
    //   urgency 3–4 → caution
    //   urgency 5+  → danger
    func speak(_ text: String, urgency: Double = 3.0) {
        let priority: Priority
        switch urgency {
        case 0...0.5:    priority = .info       // background cloud AI
        case 1...2:      priority = .detection  // segmenter, low-confidence objects
        case 3...4:      priority = .caution    // object detection, distance bands
        case 5...6:      priority = .danger     // critical distance, wall close
        default:         priority = .user       // user-initiated (scan, help, voice commands)
        }

        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.lock.lock()
            defer { self.lock.unlock() }

            let now = Date()

            // Never interrupt a higher-priority utterance
            if self.synthesizer.isSpeaking && priority < self.currentPriority { return }

            // Cooldown: skip if same text was spoken recently
            if let lt = self.lastText, let ltime = self.lastTime,
               lt == text, now.timeIntervalSince(ltime) < priority.cooldown { return }

            // Global cooldown only for info (background) — everything else speaks freely
            if priority == .info,
               let ltime = self.lastTime,
               now.timeIntervalSince(ltime) < priority.cooldown { return }

            // Danger and user always stop whatever is playing
            if priority >= .danger { self.synthesizer.stopSpeaking(at: .word) }

            let utterance = AVSpeechUtterance(string: text)
            utterance.rate = priority == .danger ? 0.58 : 0.52
            utterance.volume = 1.0
            utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
            if priority == .danger { utterance.pitchMultiplier = 0.85 }

            self.synthesizer.speak(utterance)
            self.lastText = text
            self.lastTime = now
            self.currentPriority = priority
        }
    }

    var isSpeaking: Bool { synthesizer.isSpeaking }

    /// Cancel current speech if it's lower priority than the given urgency threshold.
    /// Used to cancel stale detection speech when new detections arrive.
    func cancelIfLowerThan(urgency: Double) {
        let threshold: Priority
        switch urgency {
        case 0...0.5: threshold = .info
        case 1...2:   threshold = .detection
        case 3...4:   threshold = .caution
        case 5...6:   threshold = .danger
        default:      threshold = .user
        }
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            if self.synthesizer.isSpeaking && self.currentPriority < threshold {
                self.synthesizer.stopSpeaking(at: .word)
                self.currentPriority = .info
            }
        }
    }

    func stop() {
        DispatchQueue.main.async { [weak self] in
            self?.synthesizer.stopSpeaking(at: .immediate)
            self?.currentPriority = .info
        }
    }

    // Reset priority tracking when utterance finishes
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                            didFinish utterance: AVSpeechUtterance) {
        lock.lock()
        currentPriority = .info
        lock.unlock()
    }
}

// MARK: - SpatialAudioController
class SpatialAudioController {
    private let engine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private var isEngineStarted = false
    private let lock = NSLock()
    private var lastBeepTime: Date?
    private let beepCooldown: TimeInterval = 1.0  // max 1 beep per second

    // Shared reference to SpeechController so beeps can pause during speech
    weak var speechController: SpeechController?

    init() {
        // Subscribe to engine configuration change (audio route changes, interruptions)
        // so we can reset and reconnect nodes instead of crashing
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleEngineConfigChange),
            name: .AVAudioEngineConfigurationChange,
            object: engine
        )
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleAudioSessionInterruption),
            name: AVAudioSession.interruptionNotification,
            object: nil
        )
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    @objc private func handleEngineConfigChange(_ notification: Notification) {
        // Audio route changed (e.g. headphones connected/disconnected) —
        // nodes and format are now invalid; tear down so ensureEngine() rebuilds clean.
        lock.lock()
        isEngineStarted = false
        lock.unlock()
        print("SpatialAudio: engine config changed — will rebuild on next beep")
    }

    @objc private func handleAudioSessionInterruption(_ notification: Notification) {
        guard let info = notification.userInfo,
              let typeValue = info[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: typeValue) else { return }
        if type == .ended {
            lock.lock()
            isEngineStarted = false
            lock.unlock()
        }
    }

    private func ensureEngine() {
        lock.lock()
        defer { lock.unlock() }

        guard !isEngineStarted else { return }

        // Full teardown before rebuilding to avoid stale node graph
        if engine.isRunning { engine.stop() }

        if !engine.attachedNodes.contains(playerNode) {
            engine.attach(playerNode)
        }

        // Always reconnect — format may have changed after config change
        let stereoFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)
        engine.connect(playerNode, to: engine.mainMixerNode, format: stereoFormat)

        do {
            try engine.start()
            playerNode.volume = 1.0
            isEngineStarted = true
        } catch {
            print("SpatialAudio: engine start failed: \(error)")
        }
    }

    private func restartEngineIfNeeded() {
        // Only called after ensureEngine() — if still not running, mark dirty for next call
        if !engine.isRunning {
            lock.lock()
            isEngineStarted = false
            lock.unlock()
            do {
                try engine.start()
            } catch {
                print("SpatialAudio: engine restart failed: \(error)")
            }
        }
    }

    func updateFromDepth(
        leftDist: Float?,
        centerDist: Float?,
        rightDist: Float?,
        leftRisk: RiskLevel,
        centerRisk: RiskLevel,
        rightRisk: RiskLevel
    ) {
        // Don't beep while speech is playing — competing audio causes cognitive overload
        // for blind users who must process both simultaneously
        if let sc = speechController, sc.isSpeaking { return }

        // Check cooldown
        if let lastTime = lastBeepTime,
           Date().timeIntervalSince(lastTime) < beepCooldown {
            return
        }

        // Determine most urgent zone (danger > caution > safe)
        let urgencyMap: [(RiskLevel, Float?)] = [
            (leftRisk, leftDist),
            (centerRisk, centerDist),
            (rightRisk, rightDist)
        ]

        let panMap: [Int: Float] = [0: -1.0, 1: 0.0, 2: 1.0]  // left, center, right

        var mostUrgentIndex = 0
        var highestRiskLevel: Int = -1

        for (index, (risk, _)) in urgencyMap.enumerated() {
            let riskValue: Int
            switch risk {
            case .danger:
                riskValue = 2
            case .caution:
                riskValue = 1
            case .safe:
                riskValue = 0
            }

            if riskValue > highestRiskLevel {
                highestRiskLevel = riskValue
                mostUrgentIndex = index
            }
        }

        // Only beep for DANGER — caution is handled by speech
        guard highestRiskLevel >= 2 else { return }

        let (riskLevel, _) = urgencyMap[mostUrgentIndex]
        let pan = panMap[mostUrgentIndex] ?? 0.0

        let (frequency, duration, baseVolume): (Float, Float, Float) = {
            switch riskLevel {
            case .danger:
                return (880, 0.08, 0.5)
            case .caution, .safe:
                return (0, 0, 0)
            }
        }()

        guard frequency > 0 else { return }

        playBeep(frequency: frequency, duration: duration, volume: baseVolume, pan: pan)
        lastBeepTime = Date()
    }

    private func playBeep(frequency: Float, duration: Float, volume: Float, pan: Float) {
        ensureEngine()
        restartEngineIfNeeded()
        guard engine.isRunning else { return }

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }

            let sampleRate = Float(self.engine.outputNode.outputFormat(forBus: 0).sampleRate)
            // Guard: sampleRate=0 means audio session is interrupted — skip to avoid crash
            guard sampleRate > 0 else { return }
            let frameCount = AVAudioFrameCount(sampleRate * duration)
            guard frameCount > 0 else { return }

            // Create sine wave with envelope
            guard let audioBuffer = AVAudioPCMBuffer(pcmFormat: AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: Double(sampleRate), channels: 1, interleaved: false)!, frameCapacity: frameCount) else {
                return
            }

            audioBuffer.frameLength = frameCount

            guard let floatChannelData = audioBuffer.floatChannelData else { return }
            let channelData = floatChannelData[0]

            for frame in 0..<Int(frameCount) {
                let time = Float(frame) / sampleRate
                let angle = 2.0 * Float.pi * frequency * time
                let sineWave = sin(angle)

                // Envelope: fade out at the end to prevent clicks
                let fadeOutStart = duration * 0.8
                let fadeOutDuration = duration * 0.2
                let envelopeValue: Float

                if time < fadeOutStart {
                    envelopeValue = 1.0
                } else {
                    let fadeOutProgress = (time - fadeOutStart) / fadeOutDuration
                    envelopeValue = max(0.0, 1.0 - fadeOutProgress)
                }

                channelData[frame] = sineWave * envelopeValue * volume
            }

            // Apply stereo panning
            let leftVolume = volume * min(1.0, 1.0 - pan)
            let rightVolume = volume * min(1.0, 1.0 + pan)

            guard let stereoCopy = AVAudioPCMBuffer(pcmFormat: AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: Double(sampleRate), channels: 2, interleaved: false)!, frameCapacity: frameCount) else {
                return
            }

            stereoCopy.frameLength = frameCount

            guard let stereoData = stereoCopy.floatChannelData else { return }

            for frame in 0..<Int(frameCount) {
                stereoData[0][frame] = channelData[frame] * leftVolume   // Left channel
                stereoData[1][frame] = channelData[frame] * rightVolume  // Right channel
            }

            // Schedule and play
            DispatchQueue.main.async {
                guard self.engine.isRunning else { return }

                self.playerNode.scheduleBuffer(stereoCopy) {
                    // Completion handler
                }

                if !self.playerNode.isPlaying {
                    self.playerNode.play()
                }
            }
        }
    }

    func stopAll() {
        DispatchQueue.main.async { [weak self] in
            self?.playerNode.stop()
        }
    }
}
