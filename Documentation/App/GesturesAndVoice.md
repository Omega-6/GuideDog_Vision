# Gestures and Voice Commands

## Gestures

Gestures are the primary interaction for blind users. All gesture listeners attach to `document.body` rather than to specific UI elements. The reason: overlays (privacy, help) use z indexes that would intercept touch events if gestures were attached to a lower z index element. Attaching to `document.body` means gestures work regardless of which overlay is visible.

### Hold to speak

A press lasting 600 ms or longer activates the speech recognizer (`SFSpeechRecognizer`). The 600 ms threshold distinguishes a deliberate hold from a tap or accidental touch.

When the user starts holding:

1. A timer starts. If the touch lasts 600 ms, the ViewController receives a `voiceCommand` message with `"toggle"` and starts the VoiceCommandController.
2. The speech recognizer processes audio from the mic.
3. Partial recognition results are checked against the known command list. If a known command shows up in a partial, it executes immediately. Reduces perceived latency because the user doesn't wait for finalization.
4. Unknown phrases (not matching any known pattern) wait for the final result. Stops the engine from acting on a partial transcript that might still resolve to a command.

When the user releases:

1. If the recognizer is still running, it continues for up to 3 seconds to get a final result.
2. After the timeout (or after the final result arrives), the VoiceCommandController cleans up the audio engine and recognition task.

### Double tap to scan

Two taps within 400 ms trigger a cloud AI scan. The app sends a `scanRequest` to the ViewController, which calls `triggerManualScan()` on the NavigationEngine. The engine says "Scanning now," then sends the current camera frame to the cloud AI race.

### Swipe left and right

Horizontal swipes check the corresponding side. A left swipe calls `speakDirection("left")`, which reads the smoothed LiDAR distance for the left zone and speaks the distance in feet plus the risk level. A right swipe does the same for the right zone.

## VoiceCommandController

Manages on device speech recognition using Apple's Speech framework.

### Audio engine lifecycle

The controller creates a fresh `AVAudioEngine` for each listening session rather than reusing one across sessions. This avoids conflicts with the SpatialAudioController, which also owns an AVAudioEngine. Two engines can coexist as long as they aren't both trying to use the input node simultaneously. Creating and destroying for each session ensures clean state and avoids stale audio route references.

### Authorization

Before starting a session, the controller checks `SFSpeechRecognizer.authorizationStatus()`. If `.notDetermined`, it requests authorization and starts listening only after authorization is granted. If `.authorized`, it proceeds immediately. If `.denied` or `.restricted`, it logs the failure and does not attempt to listen.

`requiresOnDeviceRecognition` is `false`. On device offers better privacy and lower latency, but the on device speech model may not be downloaded on the user's device. Setting this to `false` allows the recognizer to use server based recognition as a fallback so voice commands always work.

### Command parsing

The controller parses the transcript by checking for keyword presence:

| Keywords | Command |
|---|---|
| "around", "describe", "surroundings" | whatsAround |
| "safe", "clear" | isSafe |
| "left" | checkLeft |
| "right" | checkRight |
| "stop", "pause" | stop |
| "resume", "start", "go" | resume |
| "help" | help |
| "scan" | scan |
| (none of the above) | unknown |

Keyword matching is case insensitive (the transcript is lowercased before parsing) and uses `contains`, so "is it safe to walk" matches isSafe because the transcript contains "safe."

### Cooldown

A 2 second cooldown prevents the same transcript from being processed multiple times. Handles the case where the recognizer produces multiple partial results that all match the same command.

### Execution

When a command is recognized, the controller dispatches it to the NavigationEngine via the `VoiceCommandDelegate` protocol. The NavigationEngine handles each:

- **whatsAround:** Speaks a local description (LiDAR distances + latest detections), then triggers a cloud AI scan.
- **isSafe:** Evaluates risk level of all three zones and speaks a safety summary ("Path is clear" or "Careful, something directly ahead").
- **checkLeft / checkRight:** Speaks distance and risk level for the requested side.
- **stop:** Pauses the ARSession and all feedback. Speaks "Paused. Say resume to continue."
- **resume:** Restarts the ARSession and all feedback. Speaks "Resuming navigation."
- **help:** Speaks the full list of controls at the highest priority so detection alerts don't interrupt.
- **scan:** Speaks "Scanning now" and triggers a cloud AI scan with a short delay so the announcement plays before the frame goes up.
- **unknown:** Speaks "Sorry, I didn't catch that. Say help for commands."
