# Speech, Spatial Audio, and Haptics

## What Makes This System Non Trivial

GuideDog Vision uses three audio channels (speech, spatial beeps, vibration) plus a fourth via the haptic engine. They have to coexist without interrupting each other or overwhelming the user. Several design decisions go beyond just calling `AVSpeechSynthesizer.speak()`:

- **Five priority tiers with explicit cooldowns.** Lower priority speech never interrupts higher priority speech. Each tier has its own cooldown so the same alert does not repeat too quickly.
- **`stopSpeaking(at: .word)` instead of `.immediate`.** When a higher priority alert needs to interrupt, the synthesizer stops at the next word boundary instead of cutting mid syllable. The result sounds less jarring and is easier to parse.
- **NSLock thread safety.** All synthesis state (current priority, last spoken text, last spoken time) is protected by an NSLock so the detection queue and main queue can both touch it safely.
- **1 second SpatialAudioController delay.** AVAudioEngine and AVSpeechSynthesizer conflict if both initialize at the same time. The synthesizer can lose its audio output entirely. The fix is to delay AVAudioEngine creation until after the synthesizer has spoken its first utterance.
- **Speech pause before spatial beeps.** A blind user processes audio sequentially. Playing a beep over speech makes both harder to parse. The spatial audio controller checks `speechController.isSpeaking` and skips the beep if speech is currently playing.
- **AVAudioEngineConfigurationChange listener.** When the audio route changes (headphones connect or disconnect), the engine gets marked dirty and rebuilt on the next beep. Without this the spatial audio would silently break after every route change.
- **Bluetooth aware speaker fallback.** The audio session is configured for `.playAndRecord`, which by default routes output to the earpiece (too quiet for navigation). The app overrides the route to the speaker only when no Bluetooth audio device is connected, so AirPods routing is never disrupted.
- **Pre initialized haptic generators.** UIImpactFeedbackGenerator instances are created at startup, not at alert time, to avoid the latency of allocating the haptic engine when an alert needs to fire.

## SpeechController

The SpeechController manages all spoken output through AVSpeechSynthesizer. It implements a priority system that prevents low-importance announcements from interrupting urgent safety alerts.

### Priority Tiers

The controller defines five priority levels. Each maps to a range of urgency values used by the rest of the engine:

| Priority   | Urgency Range | Cooldown | Use Cases |
|-----------|--------------|----------|-----------|
| User      | 7.0 and above | 0.5s    | Voice command responses, manual scan results, help text, user-initiated speech from JS |
| Danger    | 5.0 to 6.0   | 2.0s    | Critical distance alerts ("Stop!"), wall nearby, fast-approaching objects |
| Caution   | 3.0 to 4.0   | 4.0s    | Object detections at moderate distance, distance band entries |
| Detection | 1.0 to 2.0   | 6.0s    | DeepLabV3 segmentation results, low-confidence objects |
| Info      | 0.0 to 0.5   | 10.0s   | Background cloud AI scene descriptions, status messages |

### Interruption Rules

- A lower-priority utterance never interrupts a currently-speaking higher-priority utterance. If a detection-level announcement is queued while a danger-level alert is playing, the detection announcement is silently dropped.
- Danger and user priorities always stop the currently playing speech using `stopSpeaking(at: .word)`. The `.word` boundary (rather than `.immediate`) prevents the synthesizer from cutting off mid-syllable, which sounds jarring and can be difficult for the user to parse.
- Each priority tier has its own cooldown. The same text at the same priority will not repeat within the cooldown window. This prevents rapid-fire repetition of "Stop!" when the user is standing still next to an obstacle.
- The info tier has a global cooldown. Even different text at info priority will not play if any info-priority speech played within the last 10 seconds. This keeps background cloud AI descriptions from flooding the audio channel.

### Voice Characteristics

- Danger-priority speech plays at rate 0.58 with pitch multiplier 0.85. The slightly faster rate and lower pitch create a sense of urgency distinct from normal announcements.
- All other speech plays at rate 0.52 with default pitch.
- Volume is always 1.0.
- The voice is set to `en-US` via `AVSpeechSynthesisVoice(language: "en-US")`.

### Thread Safety

The SpeechController uses an NSLock to protect its internal state. All synthesis calls are dispatched to the main thread because AVSpeechSynthesizer requires main-thread access. The lock protects the `lastText`, `lastTime`, and `currentPriority` properties from concurrent reads and writes across the detection queue and main queue.

The controller conforms to `AVSpeechSynthesizerDelegate` and resets `currentPriority` to `.info` when an utterance finishes. This ensures that the priority lock is released after each utterance completes, allowing lower-priority announcements to play again.

## SpatialAudioController

The SpatialAudioController generates directional beeps that indicate which side a danger-level obstacle is on. It uses AVAudioEngine to synthesize and pan sine wave tones in real time.

### Beep Characteristics

- Frequency: 880 Hz (A5, a clear and attention-getting pitch).
- Duration: 0.08 seconds (short enough to be a beep, not a tone).
- Maximum rate: 1 beep per second. A `lastBeepTime` timestamp enforces this cooldown.

### Stereo Panning

The beep is panned based on which zone has the highest risk level:

- Left zone danger: pan = -1.0 (full left channel).
- Center zone danger: pan = 0.0 (centered).
- Right zone danger: pan = +1.0 (full right channel).

Panning is implemented by scaling the left and right channel amplitudes of a stereo PCM buffer. The formula is: left volume = base volume * min(1.0, 1.0 - pan), right volume = base volume * min(1.0, 1.0 + pan).

### Danger-Only Design

The spatial audio system only fires beeps for danger-level risk. Caution-level beeps were disabled during testing because they fired constantly in indoor environments. Any room with a wall within 2 meters on at least one side (which is nearly every room) would trigger continuous caution beeps, making the feature useless. Restricting beeps to danger-level threats means they only sound when the user is about to collide with something.

### Speech Pause

Before playing a beep, the controller checks `speechController.isSpeaking`. If speech is currently playing, the beep is skipped. Blind users must process audio information sequentially. Overlapping beeps and speech creates cognitive overload and makes both harder to understand.

### Engine Management

The SpatialAudioController creates its own AVAudioEngine instance. The engine is started lazily on the first beep request (`ensureEngine()`). The controller listens for `AVAudioEngineConfigurationChange` notifications (triggered by audio route changes such as connecting or disconnecting headphones) and marks the engine as dirty so it will be rebuilt on the next beep. It also listens for `AVAudioSession.interruptionNotification` to handle phone calls and other audio interruptions.

The controller is created 1.0 second after engine start. This delay prevents a conflict between AVAudioEngine and AVSpeechSynthesizer that occurs when both initialize at the same time. The conflict manifests as the speech synthesizer producing no audio output, which is a critical failure for a blind user.

## HapticController

The HapticController provides tactile feedback through the iPhone's Taptic Engine using UIImpactFeedbackGenerator.

### Feedback Patterns

| Risk Level | Generator Style | Pulse Interval |
|-----------|----------------|----------------|
| Safe      | None           | No pulses      |
| Caution   | Light          | 0.5 seconds    |
| Danger    | Heavy          | 0.1 seconds    |

The controller uses two pre-initialized feedback generators (light and heavy) to avoid the latency of creating a generator at alert time. When the risk level changes, the controller invalidates the existing pulse timer and creates a new repeating timer at the appropriate interval.

The controller only updates when the risk level changes. If the risk level remains at caution across multiple depth frames, the existing 0.5-second pulse timer continues running without interruption.

### Purpose

Haptic feedback provides an immediate, non-auditory signal of danger. A blind user wearing headphones receives haptic pulses even if audio is momentarily unavailable. The increasing pulse rate (from 0.5s at caution to 0.1s at danger) creates an intuitive sense of escalating urgency without requiring any audio output.

## AVAudioSession Configuration

The AVAudioSession is configured in two places (ViewController for pre-engine welcome speech, and NavigationEngine for ongoing operation) with the same settings:

- **Category:** `.playAndRecord`. This enables simultaneous speech output and microphone input for voice commands.
- **Mode:** `.spokenAudio`. Optimized for speech synthesis, providing appropriate audio processing.
- **Options:**
  - `.allowBluetoothA2DP`: Routes audio to Bluetooth headphones (AirPods, etc.) when connected.
  - `.allowBluetooth`: Enables HFP Bluetooth for hearing aids.
  - `.mixWithOthers`: Allows GuideDog audio to play alongside other app audio.
  - `.duckOthers`: Lowers the volume of other apps' audio when GuideDog speaks.

### Speaker Fallback

After configuring the audio session, the app checks the current audio route for Bluetooth outputs (A2DP, HFP, or BLE). If no Bluetooth device is connected, the app calls `overrideOutputAudioPort(.speaker)` to route audio through the phone's built-in speaker. Without this override, the `.playAndRecord` category defaults to the earpiece, which is too quiet for navigation use. The override is only applied when Bluetooth is absent so that Bluetooth routing is not disrupted.
