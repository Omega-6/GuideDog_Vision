import Capacitor
import AVFoundation

/// Configures AVAudioSession so sound plays even in silent mode and
/// doesn't require a user gesture (unlike the Web Audio API on iOS Safari).
@objc(AudioPlugin)
public class AudioPlugin: CAPPlugin {

    @objc func activate(_ call: CAPPluginCall) {
        do {
            let session = AVAudioSession.sharedInstance()
            // .playback = plays in silent mode; .mixWithOthers = doesn't kill music
            try session.setCategory(.playback, options: [.mixWithOthers, .duckOthers])
            try session.setActive(true)
            call.resolve(["activated": true])
        } catch {
            call.reject("AVAudioSession error: \(error.localizedDescription)")
        }
    }
}
