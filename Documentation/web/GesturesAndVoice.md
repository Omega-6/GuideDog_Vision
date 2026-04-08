# GuideDog Vision: Gestures and Voice Commands

## Overview

The PWA provides two input methods: touch gestures and voice commands. Both are designed for blind users who cannot see the screen. Gestures work without visual targeting. Voice commands use natural language that does not require memorization of exact phrases.

---

## Touch Gestures

### Event Attachment

In the current implementation, gesture listeners are attached to the `alertArea` element. Touch events are tracked with `touchstart` recording the start position and timestamp, and `touchend` computing the delta and duration.

The gesture system excludes interactions with `.help` and `.loading` elements, which have their own click handlers and higher z-index values. Taps on these overlay elements are handled separately.

### Hold (Long Press)

A touch held for more than 1500 milliseconds triggers `showHelp()`, which displays the help screen and speaks the feature list aloud. This provides a discovery mechanism for users who forget the available commands.

Voice recognition is started through the on screen microphone button rather than through a hold gesture. Tapping the microphone button calls `startListening()`, which is described in the Voice Commands section below.

### Tap to Scan

The website divides the screen into vertical zones for tap actions. A tap in the top zone (Y less than 40 percent of screen height) calls `describeArea()`, which sends a detailed cloud AI request and speaks a full description of the surroundings. A tap in the bottom zone (Y greater than 60 percent of screen height) calls `triggerAIScan()`, which sends a detailed cloud AI request focused on hazards. The system says "Scanning surroundings..." and then speaks the AI's response. The middle zone has no action, which prevents accidental triggers when the user is just resting a finger on the screen.

### Swipe Left/Right

A horizontal touch movement greater than 60 pixels (with horizontal distance exceeding vertical distance) triggers `speakDirection` for the corresponding side. Swiping right calls `speakDirection('right')`. Swiping left calls `speakDirection('left')`.

The `speakDirection` function checks `state.localDetections` for objects in the requested direction. If an object is found, it speaks the object name and distance (converted to feet). If nothing is detected, it says "Nothing detected on your [direction]". The corresponding direction indicator element briefly highlights for 1 second.

---

## Voice Commands

### Speech Recognition Setup

The `initSpeechRecognition` function creates a `SpeechRecognition` instance (or `webkitSpeechRecognition` on Safari). Configuration:
- `continuous: false` - recognizes a single phrase, then stops
- `interimResults: false` - waits for the final result
- `lang: 'en-US'`

The recognition lifecycle is managed through four callbacks:
- `onstart`: Sets `state.isListening = true`, updates the microphone button to "Listening..."
- `onresult`: Extracts the transcript, converts to lowercase, passes to `handleVoiceCommand`
- `onend`: Resets `state.isListening = false`, updates the microphone button
- `onerror`: Resets state. If the error is `no-speech`, speaks "No speech heard. Tap microphone and try again."

### Starting Recognition

The `startListening` function is called when the user taps the microphone button. It cancels any current speech (so the microphone does not pick up the phone's own speaker), then starts recognition with a short vibration confirmation (50ms buzz).

If recognition is already active, tapping the microphone button toggles it off via `stopListening`.

If `start()` throws (which can happen if the previous session has not fully ended), the function stops the current session and retries after 100 milliseconds.

### Command Matching

The `handleVoiceCommand` function matches the transcribed text against keywords using `String.includes()`. This allows flexible phrasing. The user can say "what's around me" or "tell me what's around" and both will match the "around" keyword.

Commands are checked in the following order:

| Keywords | Action | Function |
|----------|--------|----------|
| "start", "begin" | Hide help screen if visible | `hideHelp()` |
| "stop", "pause", "quiet" | Pause all automated alerts | Sets `state.isPaused = true` |
| "resume", "continue" | Resume automated alerts | Sets `state.isPaused = false` |
| "around", "describe", "what" | Describe the full surroundings | `describeArea()` |
| "safe", "clear", "walk" | Check if path is safe to walk | `checkSafety()` |
| "left" | Report what is on the left | `speakDirection('left')` |
| "right" | Report what is on the right | `speakDirection('right')` |
| "scan", "stair", "door" | Trigger detailed AI scan | `triggerAIScan()` |
| "help" | Show help screen | `showHelp()` |

If no keyword matches, the system speaks a hint: "Say: what is around, is it safe, left, right, or scan."

Each recognized command triggers a short vibration (30ms) to confirm that the command was heard and processed.

### Order of Matching

The order matters. "start" is checked before "around" because a user saying "start describing" on the help screen should dismiss the help screen, not trigger a description. "stop" is checked before "safe" because "stop, is it safe" should pause alerts, not check safety.

---

## Microphone Button

The `updateMicButton` function toggles the visual state of the microphone button (`btnMic`). When listening, the button gets the `listening` class (red background with pulse animation) and its text changes to "Listening...". When not listening, it returns to the default blue background with "Speak" text.

The gesture hint text below the alert box reads "Double-tap to scan. Hold to speak" and serves as a persistent reminder of available interactions.

---

## User Action Functions

### describeArea

Speaks "Scanning surroundings...", sends a detailed AI request, and speaks the full response. If the AI is unavailable, falls back to listing up to 3 high-confidence COCO-SSD detections with their positions. If nothing is detected, says "Area appears clear."

### checkSafety

Speaks "Checking safety...", sends a detailed AI request, and speaks the response. If the AI is unavailable, checks `state.localDetections` for objects in the walking path. Reports the nearest in-path obstacle with its distance in feet. If no obstacles are in the path, says "Path appears clear."

### triggerAIScan

Speaks "Scanning surroundings...", sends a detailed AI request, and speaks the response. If the AI returns nothing, says "Scan complete. No additional hazards detected." This function is identical to `describeArea` except for the fallback message.

### speakDirection

Checks `state.localDetections` for objects matching the requested direction ("left" or "right"). Speaks the first detected object's name and distance. If nothing is detected in that direction, says "Nothing detected on your [direction]." Briefly highlights the corresponding direction indicator element for 1 second.
