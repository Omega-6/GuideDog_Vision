# Web User Interface

## Overview

Designed for blind users. Visual elements exist primarily for sighted helpers and for debugging. Primary output channels are speech and audio, not visual display. The visual interface is kept simple, high contrast, and large enough to be useful for users with low vision.

---

## Homepage (mode select)

The homepage is the first screen users see. It uses system humanist sans (`-apple-system`, `SF Pro Text`, `system-ui`) instead of the older monospace, so it reads conversationally instead of code adjacent.

Hero copy: **"Eyes and ears, when you need them."** with a blue accent on "when you need them."

Two big mode cards:

- **See** (primary, blue glow): the obstacle detection guide
- **Hear** (secondary, neutral): sound detection and live captions

Tapping anywhere on the homepage starts See mode. The Hear button has its own touch handler with `stopPropagation` so its tap doesn't fall through. A blind user lands on the page and can just tap.

On page load (where the browser allows), a welcome message plays: "Welcome to GuideDog. Press anywhere on the page for obstacle detection, or the second button for sounds and captions." It's cancelled the moment the user picks a mode.

---

## Alert box (See mode)

Central visual element, positioned in the middle of the screen within the `alert-area` container. Max width 350px, 25px padding, 20px border radius.

### States

**Safe:**
- Background: `rgba(0, 255, 136, 0.2)`
- Border: 3px solid `#0f8`
- Icon: "OK"
- Text: "Path Clear"
- Detail: "Walking is safe"
- No animation

**Warning:**
- Background: `rgba(255, 170, 0, 0.3)`
- Border: 3px solid `#fa0`
- Pulse: scales between 1.0x and 1.05x every 1 second
- Icon, text, and detail are set dynamically based on the detected hazard

**Danger:**
- Background: `rgba(255, 68, 68, 0.4)`
- Border: 4px solid `#f44` (thicker than other states)
- Shake: translates horizontally between -5px and +5px every 0.3 seconds
- Icon, text, and detail are set dynamically

### No CSS transition

The alert box has `transition: none`. State changes are instant. When a wall appears 2 feet ahead, the alert must go from green to red immediately. A 300 ms CSS transition would delay the visual feedback and create a disconnect between the audio alert (which fires instantly) and the visual state.

---

## Status badge

Top left of the status bar. Displays "SAFE", "CAUTION", or "DANGER" with matching backgrounds:
- Safe: `#0f8` background, black text
- Warning: `#fa0` background, black text, pulse
- Danger: `#f44` background, white text, pulse (0.3 s cycle)

`updateUI` sets the class and text every cycle. The fast hazard loop updates both the badge and the alert box in the same function call, so they're always in sync.

---

## AI badge

Top right of the status bar. Shows the current AI and depth model status:

- "AI Active" (default, after COCO-SSD loads)
- "Starting depth sensor..." (during depth init)
- "Loading depth model..." (while Transformers.js downloads)
- "Downloading depth model..." (during weight download)
- "AI + Depth Active" (Transformers.js depth loaded)
- "AI + LiDAR Active" (WebXR LiDAR active, rare on web)
- "Audio Unavailable" (Web Audio API failed)

---

## Gesture hint

Below the alert box, a hint line reads "Double-tap to scan. Hold to speak." Persistent reminder, not interactive.

When voice recognition is active, the mic button text changes to "Listening..." to show the system is waiting.

---

## Control buttons

Control bar at the bottom of the screen, three buttons:
- **"What's Around"** (left): triggers `describeArea()`
- **"Speak"** (center, blue): triggers `startListening()` for voice recognition
- **"Is It Safe"** (right): triggers `checkSafety()`

The mic button has a blue background (`#48f`) that changes to red with a pulse when listening. Large touch target (18px vertical padding, full flex width).

All buttons call `unlockAudio()` on click so iOS audio works regardless of which element the user taps first.

---

## Direction indicators

Three circles below the alert box: Left (L), Ahead (F), Right (R). Each 70px diameter with a 3px border.

Default: 50 percent opacity, white border, dark background.

When a detection occurs in a direction, the corresponding indicator becomes active (full opacity, amber border and background). If the detection is at danger level, the indicator turns red and pulses.

The indicators flash briefly (1 second) when the user asks about a specific direction through `speakDirection`.

---

## Camera preview

The video element fills the screen (`width: 100%, height: 100%, object-fit: cover`) and sits behind the overlay at 30 percent opacity. Faint camera preview for sighted helpers while keeping the overlay text readable. Low opacity keeps alert colors (green, amber, red) clearly visible against the darkened camera feed.

The video element has `autoplay`, `playsinline`, and `muted` attributes. `playsinline` is required for iOS, which otherwise opens video in fullscreen.

---

## Privacy screen

Shown every launch. Full screen overlay (`position: fixed, inset: 0`) with a near opaque black background (`rgba(0,0,0,0.98)`).

### Content

- Title: "Privacy & Permissions"
- Info items explaining camera usage, cloud AI, and data handling
- Silent mode reminder card (the single most common support question was "Why isn't it talking?" and the answer was usually silent mode)
- An "I Understand - Continue" button
- A hint: "Tap to hear aloud. Tap again to continue"

### Two tap flow

**First tap anywhere:**
1. Calls `unlockAudio()` to enable iOS speech
2. Cancels any current speech
3. Speaks: "Welcome to GuideDog. This app uses your camera and cloud AI to help you navigate. All detection runs on your device. No data is stored. Tap again to continue."
4. The `privacyRead` flag is set to true

**Second tap:**
1. Cancels the speech (if still playing)
2. Hides the privacy screen (`display: none`)
3. Calls `showHelp()` to display the features screen

Ensures blind users hear the privacy information. First tap unlocks audio and reads it aloud. Second tap confirms the user has heard it.

---

## Features screen (help)

Appears after the privacy screen. Scrollable full screen overlay with a near opaque black background.

### Content

Four help items:
1. **AUTOMATIC PROTECTION** - "App constantly scans and warns you about obstacles, stairs, walls, doors automatically. You don't need to do anything!"
2. **Voice Commands** - lists available commands
3. **Gesture Controls** - "Tap TOP = describe area, Tap BOTTOM = detailed scan, Swipe LEFT/RIGHT = check sides"
4. **Alert Sounds** - "Beeps indicate direction of obstacle, Fast beeps = DANGER, Vibration = obstacle in your path"

A "START - TAP HERE OR SAY 'START'" button at the bottom calls `hideHelp()`. The screen also has tap anywhere to start, with the back button and colorblind toggle exempted so those keep working as buttons.

When `showHelp()` is called, it speaks: "GuideDog automatically warns you about obstacles, stairs, walls, and doors. You don't need to do anything. Tap the button to start."

When `hideHelp()` is called, it cancels speech, unlocks audio, sets `state.isRunning = true`, and starts both loops.

---

## Version tag

Bottom right corner. 10px font, 30 percent white opacity, `pointer-events: none` so it never intercepts taps. Positioned with `fixed` and respects the safe area inset on devices with home indicators.

---

## Viewport and interaction

The viewport meta tag does not include `maximum-scale=1` in the current implementation, but `touch-action: manipulation` is effectively in place through `* { -webkit-tap-highlight-color: transparent; user-select: none; }`. Text selection is disabled globally to prevent accidental selections during gesture use.

`html` and `body` have `overflow: hidden` and `height: 100%` to prevent scrolling the main app. The help screen has its own `overflow-y: auto` for scrolling its content independently.

---

## Debug info

A hidden debug line sits below the alert box. Monospace 10px gray:

- Detection timing (ms per COCO-SSD inference)
- Number of detected objects
- Depth model status (LiDAR, model, or loading)
- Current depth center value
- Calibration status
- Depth hazard indicator
- Threat transition (raw to smoothed)

Updated every protectionLoop cycle. Development use only.
