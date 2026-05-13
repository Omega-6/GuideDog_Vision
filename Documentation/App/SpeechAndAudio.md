# Speech, Spatial Audio, and Haptics

## Technical Complexities

Three audio channels (speech, spatial beeps, vibration) plus a fourth through the haptic engine. They have to coexist without interrupting each other or overwhelming the user.

Five priority tiers with explicit cooldowns. Lower priority speech never interrupts higher priority speech. Each tier has its own cooldown so the same alert doesn't repeat too quickly.

`stopSpeaking(at: .word)` instead of `.immediate`. When a higher priority alert needs to interrupt, the synthesizer stops at the next word boundary instead of mid syllable. Sounds less jarring and is easier to parse.

NSLock thread safety. All synthesis state (current priority, last spoken text, last spoken time) is protected by an NSLock so the detection queue and main queue can both touch it safely.

1 second SpatialAudioController delay. AVAudioEngine and AVSpeechSynthesizer conflict if both initialize at the same time. The synthesizer can lose its audio output entirely. The fix is to delay AVAudioEngine creation until after the synthesizer has spoken its first utterance.

Speech pause before spatial beeps. A blind user processes audio sequentially. Playing a beep over speech makes both harder to parse. The spatial audio controller checks `speechController.isSpeaking` and skips the beep if speech is currently playing.

AVAudioEngineConfigurationChange listener. When the audio route changes (headphones connect or disconnect), the engine gets marked dirty and rebuilt on the next beep. Without this, spatial audio would silently break after every route change.

Bluetooth aware speaker fallback. The audio session is configured for `.playAndRecord`, which by default routes output to the earpiece (too quiet for navigation). The app overrides to the speaker only when no Bluetooth audio device is connected, so AirPods routing is never disrupted.

Pre initialized haptic generators. `UIImpactFeedbackGenerator` instances are created at startup, not at alert time, to avoid the latency of allocating the haptic engine when an alert needs to fire.

## SpeechController

Manages all spoken output through `AVSpeechSynthesizer`. Priority system prevents low importance announcements from interrupting urgent safety alerts.

### Priority tiers

Five levels. Each maps to a range of urgency values used by the rest of the engine:

| Priority | Urgency Range | Cooldown | Use cases |
|---|---|---|---|
| User | 7.0+ | 0.5 s | Voice command responses, manual scan results, help text, JS speech |
| Danger | 5.0 to 6.0 | 2.0 s | Critical distance alerts ("Stop!"), wall nearby, fast approaching objects |
| Caution | 3.0 to 4.0 | 4.0 s | Object detections at moderate distance, distance band entries |
| Detection | 1.0 to 2.0 | 6.0 s | DeepLabV3 segmentation results, low confidence objects |
| Info | 0.0 to 0.5 | 10.0 s | Background cloud AI descriptions, status messages |

### Interruption rules

A lower priority utterance never interrupts a higher priority one. If a detection level announcement is queued while danger is playing, the detection one is silently dropped.

Danger and user priorities stop the currently playing speech using `stopSpeaking(at: .word)`. The `.word` boundary (not `.immediate`) keeps the synthesizer from cutting off mid syllable.

Each priority has its own cooldown. Same text at the same priority will not repeat within the cooldown window. Stops rapid fire repetition of "Stop!" when the user is standing next to an obstacle.

The info tier has a global cooldown. Even different info text won't play if any info speech played in the last 10 seconds. Keeps background cloud AI descriptions from flooding the audio channel.

### Voice characteristics

- Danger speech plays at rate 0.58 with pitch multiplier 0.85. Slightly faster, slightly lower pitch creates urgency.
- All other speech plays at rate 0.52 with default pitch.
- Volume is always 1.0.
- Voice is `en-US` via `AVSpeechSynthesisVoice(language: "en-US")`.

### Thread safety

The SpeechController uses an `NSLock` to protect internal state. All synthesis calls dispatch to the main thread because `AVSpeechSynthesizer` requires it. The lock protects `lastText`, `lastTime`, and `currentPriority` from concurrent reads and writes across the detection queue and main queue.

The controller conforms to `AVSpeechSynthesizerDelegate` and resets `currentPriority` to `.info` when an utterance finishes. The priority lock releases after each utterance so lower priority announcements can play again.

## SpatialAudioController

Generates directional beeps that indicate which side a danger level obstacle is on. Uses `AVAudioEngine` to synthesize and pan sine wave tones in real time.

### Beep characteristics

- Frequency: 880 Hz (A5, clear and attention getting)
- Duration: 0.08 seconds
- Max rate: 1 beep per second, enforced by `lastBeepTime`

### Stereo panning

Beep is panned by which zone has the highest risk:

- Left zone danger: pan = -1.0
- Center zone danger: pan = 0.0
- Right zone danger: pan = +1.0

Implemented by scaling left and right channel amplitudes of a stereo PCM buffer: `left = base * min(1.0, 1.0 - pan)`, `right = base * min(1.0, 1.0 + pan)`.

### Danger only

Spatial audio only fires for danger level risk. Caution beeps were disabled during testing because they fired constantly indoors. Any room with a wall within 2 m on one side (basically every room) would trigger continuous beeps. Restricting to danger only means they only sound when the user is about to collide with something.

### Speech pause

Before playing a beep, the controller checks `speechController.isSpeaking`. If speech is currently playing, the beep is skipped. Blind users process audio sequentially. Overlapping beeps and speech creates cognitive overload.

### Engine management

The controller creates its own `AVAudioEngine`. The engine is started lazily on first beep (`ensureEngine()`). The controller listens for `AVAudioEngineConfigurationChange` (triggered by route changes like connecting or disconnecting headphones) and marks the engine dirty so it rebuilds on the next beep. It also listens for `AVAudioSession.interruptionNotification` for phone calls.

The controller is created 1.0 second after engine start. This delay prevents the AVAudioEngine vs AVSpeechSynthesizer conflict that occurs when both initialize simultaneously. The conflict manifests as the speech synthesizer producing no audio output, which is a critical failure for a blind user.

## HapticController

Tactile feedback through the iPhone's Taptic Engine using `UIImpactFeedbackGenerator`.

### Patterns

| Risk level | Generator | Pulse interval |
|---|---|---|
| Safe | none | no pulses |
| Caution | light | 0.5 s |
| Danger | heavy | 0.1 s |

Two pre initialized feedback generators (light and heavy) avoid the latency of creating a generator at alert time. When the risk level changes, the existing pulse timer is invalidated and a new repeating timer fires at the appropriate interval.

The controller only updates on risk level change. If the risk stays at caution across multiple depth frames, the existing 0.5 s timer keeps running without interruption.

### Why haptics

Haptic feedback provides an immediate non auditory signal of danger. A blind user wearing headphones still feels haptic pulses if audio is momentarily unavailable. The increasing pulse rate (0.5 s at caution, 0.1 s at danger) gives an intuitive escalation without requiring audio.

## AVAudioSession

Configured in two places (ViewController for pre engine welcome speech, NavigationEngine for ongoing operation) with the same settings:

- **Category:** `.playAndRecord`. Speech output plus mic input for voice commands.
- **Mode:** `.spokenAudio`. Optimized for speech.
- **Options:**
  - `.allowBluetoothA2DP`: routes to Bluetooth headphones when connected
  - `.allowBluetooth`: HFP Bluetooth for hearing aids
  - `.mixWithOthers`: GuideDog audio plays alongside other apps
  - `.duckOthers`: lowers volume of other apps when GuideDog speaks

### Speaker fallback

After configuring the session, the app checks the current audio route for Bluetooth outputs (A2DP, HFP, BLE). If no Bluetooth device is connected, the app calls `overrideOutputAudioPort(.speaker)` to route to the phone's speaker. Without this override, `.playAndRecord` defaults to the earpiece. The override only applies when Bluetooth is absent so AirPods routing isn't disrupted.
