# Web Gestures and Voice Commands

## Overview

The website provides two input methods: touch gestures and voice commands. Both are designed for blind users who can't see the screen. Gestures work without visual targeting. Voice commands accept natural phrasing.


## Touch gestures

### Event attachment

Gesture listeners attach to the `alertArea` element. Touch events are tracked with `touchstart` recording start position and timestamp, and `touchend` computing delta and duration.

The gesture system excludes `.help` and `.loading` elements, which have their own click handlers and higher z index. Taps on those overlays are handled separately.

### Hold (long press)

A touch held for more than 1500 ms triggers `showHelp()`, which displays the help screen and speaks the feature list. Discovery mechanism for users who forget the available commands.

Voice recognition starts through the on screen microphone button rather than through a hold gesture. Tapping the mic button calls `startListening()` (see Voice Commands below).

### Tap to scan

The screen is divided into vertical zones. A tap in the top zone (Y less than 40 percent of screen height) calls `describeArea()`, which sends a detailed cloud AI request and speaks a full description. A tap in the bottom zone (Y greater than 60 percent) calls `triggerAIScan()`, which sends a detailed cloud AI request focused on hazards. The system says "Scanning surroundings..." and speaks the response. The middle zone has no action, which prevents accidental triggers when the user is just resting a finger on the screen.

### Swipe left/right

A horizontal touch movement greater than 60 pixels (with horizontal distance exceeding vertical) triggers `speakDirection` for that side. Swiping right calls `speakDirection('right')`. Swiping left calls `speakDirection('left')`.

`speakDirection` checks `state.localDetections` for objects in the requested direction. If found, it speaks the object name and distance (converted to feet). If nothing's there, "Nothing detected on your [direction]." The corresponding direction indicator briefly highlights for 1 second.

---

## Voice commands

### Setup

`initSpeechRecognition` creates a `SpeechRecognition` instance (or `webkitSpeechRecognition` on Safari). Configuration:
- `continuous: false` (recognizes a single phrase, then stops)
- `interimResults: false` (waits for the final result)
- `lang: 'en-US'`

Lifecycle through four callbacks:
- `onstart`: sets `state.isListening = true`, updates the mic button to "Listening..."
- `onresult`: extracts transcript, lowercases it, passes to `handleVoiceCommand`
- `onend`: resets `state.isListening = false`, updates the mic button
- `onerror`: resets state. If the error is `no-speech`, speaks "No speech heard. Tap microphone and try again."

### Starting recognition

`startListening` is called when the user taps the mic button. It cancels current speech (so the mic doesn't pick up the phone's own speaker), then starts recognition with a short vibration confirmation (50 ms buzz).

If recognition is already active, tapping toggles it off through `stopListening`.

If `start()` throws (can happen if the previous session hasn't fully ended), the function stops the current session and retries after 100 ms.

### Matching

`handleVoiceCommand` matches transcribed text against keywords using `String.includes()`. Flexible phrasing. The user can say "what's around me" or "tell me what's around" and both match.

Order matters:

| Keywords | Action | Function |
|---|---|---|
| "start", "begin" | Hide help screen if visible | `hideHelp()` |
| "stop", "pause", "quiet" | Pause all alerts | sets `state.isPaused = true` |
| "resume", "continue" | Resume alerts | sets `state.isPaused = false` |
| "around", "describe", "what" | Describe surroundings | `describeArea()` |
| "safe", "clear", "walk" | Check if path is safe | `checkSafety()` |
| "left" | Report what's on the left | `speakDirection('left')` |
| "right" | Report what's on the right | `speakDirection('right')` |
| "scan", "stair", "door" | Trigger detailed AI scan | `triggerAIScan()` |
| "help" | Show help screen | `showHelp()` |

If nothing matches, the system hints: "Say: what is around, is it safe, left, right, or scan."

Each recognized command triggers a short vibration (30 ms) to confirm the command was heard.

### Order matters

"start" is checked before "around" because a user saying "start describing" on the help screen should dismiss the help screen, not trigger a description. "stop" is checked before "safe" because "stop, is it safe" should pause alerts, not check safety.

---

## Mic button

`updateMicButton` toggles the visual state of the mic button (`btnMic`). When listening, the button gets the `listening` class (red background with pulse animation) and its text becomes "Listening...". When not listening, it returns to blue with "Speak" text.

The gesture hint below the alert box reads "Double-tap to scan. Hold to speak" as a persistent reminder.

---

## User action functions

### describeArea

Speaks "Scanning surroundings...", sends a detailed AI request, speaks the full response. If the AI is unavailable, falls back to listing up to 3 high confidence COCO-SSD detections with positions. If nothing detected, "Area appears clear."

### checkSafety

Speaks "Checking safety...", sends a detailed AI request, speaks the response. If the AI is unavailable, checks `state.localDetections` for objects in the walking path. Reports the nearest in path obstacle with its distance in feet. If no obstacles in path, "Path appears clear."

### triggerAIScan

Speaks "Scanning surroundings...", sends a detailed AI request, speaks the response. If the AI returns nothing, "Scan complete. No additional hazards detected." Identical to `describeArea` except for the fallback message.

### speakDirection

Checks `state.localDetections` for objects matching the requested direction. Speaks the first detected object's name and distance. If nothing's there, "Nothing detected on your [direction]." Briefly highlights the corresponding direction indicator for 1 second.
