# Gestures and Voice Commands

## Gesture System

Gestures are the primary interaction method for blind users. All gesture listeners are attached to `document.body` rather than to specific UI elements like the alert area. This decision was made because overlays (privacy screen, help screen) use z-index values that would intercept touch events if gestures were attached to a lower-z-index element. By attaching to `document.body`, gestures work regardless of which overlay is currently visible.

### Hold to Speak (Press and Hold)

A press lasting 600 milliseconds or longer activates the speech recognizer (SFSpeechRecognizer). The 600ms threshold was chosen to distinguish a deliberate hold from a tap or accidental touch.

When the user begins holding:

1. A timer starts. If the touch lasts 600ms, the ViewController receives a `voiceCommand` message with `"toggle"` and starts the VoiceCommandController.
2. The speech recognizer processes audio from the microphone.
3. Partial recognition results are checked against the known command list. If a known command is recognized from a partial result, it executes immediately. This reduces perceived latency because the user does not need to wait for the recognizer to finalize.
4. Unknown commands (phrases that do not match any known pattern) wait for the final result. This prevents the engine from acting on a partial transcript that might still resolve to a known command.

When the user releases:

1. If the recognizer is still running, it continues for up to 3 seconds to allow the speech recognizer to produce a final result.
2. After the timeout (or after the final result arrives), the VoiceCommandController cleans up the audio engine and recognition task.

### Double Tap to Scan

Two taps within a 400-millisecond window trigger a cloud AI scene scan. The app sends a `scanRequest` message to the ViewController, which calls `triggerManualScan()` on the NavigationEngine. The engine speaks "Scanning now," then sends the current camera frame to the cloud AI race (Claude Haiku 4.5 vs GPT-4.1-mini).

### Swipe Left and Right

Horizontal swipes check the corresponding side. A swipe to the left calls `speakDirection("left")`, which reads the smoothed LiDAR distance for the left zone and speaks the distance in feet along with the risk level. A swipe to the right does the same for the right zone.

## VoiceCommandController

The VoiceCommandController manages on-device speech recognition using Apple's Speech framework.

### Audio Engine Lifecycle

A critical design decision is that the controller creates a fresh `AVAudioEngine` instance for each listening session. It does not reuse the engine across sessions. This avoids conflicts with the SpatialAudioController, which also owns an AVAudioEngine. Two AVAudioEngine instances can coexist as long as they are not both trying to use the input node simultaneously. By creating and destroying the engine for each voice command session, the controller ensures clean state and avoids stale audio route references.

### Authorization

Before starting a listening session, the controller checks `SFSpeechRecognizer.authorizationStatus()` synchronously. If the status is `.notDetermined`, it requests authorization and begins listening only after authorization is granted. If the status is `.authorized`, it proceeds immediately. If the status is `.denied` or `.restricted`, it logs the failure and does not attempt to listen.

The `requiresOnDeviceRecognition` property is set to `false`. While on-device recognition offers better privacy and lower latency, the on-device speech model may not be downloaded on the user's device. Setting this to `false` allows the recognizer to use server-based recognition as a fallback, ensuring that voice commands always work.

### Command Parsing

The controller parses the transcript by checking for keyword presence:

| Keywords                          | Command      |
|----------------------------------|-------------|
| "around", "describe", "surroundings" | whatsAround |
| "safe", "clear"                  | isSafe      |
| "left"                           | checkLeft   |
| "right"                          | checkRight  |
| "stop", "pause"                  | stop        |
| "resume", "start", "go"         | resume      |
| "help"                           | help        |
| "scan"                           | scan        |
| (none of the above)              | unknown     |

Keyword matching is case-insensitive (the transcript is lowercased before parsing). The matching uses `contains` rather than exact equality, so "is it safe to walk" matches the isSafe command because the transcript contains "safe."

### Command Cooldown

A 2-second cooldown prevents the same transcript from being processed multiple times. This handles the case where the recognizer produces multiple partial results that all match the same command.

### Command Execution

When a command is recognized, the controller dispatches it to the NavigationEngine via the `VoiceCommandDelegate` protocol. The NavigationEngine handles each command:

- **whatsAround:** Speaks a local description (LiDAR distances plus latest detections), then triggers a cloud AI scan.
- **isSafe:** Evaluates the risk level of all three zones and speaks a safety summary ("Path is clear" or "Careful, something directly ahead").
- **checkLeft / checkRight:** Speaks the distance and risk level for the requested side.
- **stop:** Pauses the ARSession and all feedback. Speaks "Paused. Say resume to continue."
- **resume:** Restarts the ARSession and all feedback. Speaks "Resuming navigation."
- **help:** Speaks a full list of available controls and commands at the highest priority so it is not interrupted by detection alerts.
- **scan:** Speaks "Scanning now" and triggers a cloud AI scan with a short delay to let the announcement play before sending the camera frame.
- **unknown:** Speaks "Sorry, I didn't catch that. Say help for commands."
