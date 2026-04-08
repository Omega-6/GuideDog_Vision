# GuideDog Vision: User Interface

## Overview

The PWA interface is designed for blind users. Visual elements exist primarily for sighted helpers who may be assisting the user, and for development and debugging purposes. The primary output channels are speech and audio, not visual display. That said, the visual interface is kept simple, high-contrast, and large enough to be useful for users with low vision.

---

## Alert Box

The alert box is the central visual element, positioned in the middle of the screen within the `alert-area` container. It has a maximum width of 350px, 25px padding, and 20px border radius.

### States

**Safe:**
- Background: `rgba(0, 255, 136, 0.2)` (translucent green)
- Border: 3px solid `#0f8` (bright green)
- Icon: "OK"
- Text: "Path Clear"
- Detail: "Walking is safe"
- No animation

**Warning:**
- Background: `rgba(255, 170, 0, 0.3)` (translucent amber)
- Border: 3px solid `#fa0` (bright amber)
- Pulse animation: scales between 1.0x and 1.05x every 1 second
- Icon, text, and detail are set dynamically based on the detected hazard

**Danger:**
- Background: `rgba(255, 68, 68, 0.4)` (translucent red)
- Border: 4px solid `#f44` (bright red, thicker than other states)
- Shake animation: translates horizontally between -5px and +5px every 0.3 seconds
- Icon, text, and detail are set dynamically

### No CSS Transition

The alert box has `transition: none` set explicitly. State changes are instant. There is no fade or slide between safe, warning, and danger states. This is intentional. When a wall appears 2 feet ahead, the alert must change from green to red immediately. A 300ms CSS transition would delay the visual feedback, creating a disconnect between the audio alert (which fires instantly) and the visual state.

---

## Status Badge

The status badge is in the top-left of the status bar. It displays "SAFE", "CAUTION", or "DANGER" with corresponding background colors:
- Safe: `#0f8` background, black text
- Warning: `#fa0` background, black text, pulse animation
- Danger: `#f44` background, white text, pulse animation (0.3s cycle)

In the current implementation, the badge is visible. The `updateUI` function sets its class and text every cycle. The fast hazard loop updates both the badge and the alert box in the same function call, ensuring they are always in sync.

---

## AI Badge

The AI badge sits in the top-right of the status bar. It is a small indicator showing the current AI and depth model status:
- "AI Active" (default, after COCO-SSD loads)
- "Starting depth sensor..." (during depth initialization)
- "Loading depth model..." (while Transformers.js downloads the model)
- "Downloading depth model..." (during model weight download)
- "AI + Depth Active" (Transformers.js depth model loaded)
- "AI + LiDAR Active" (WebXR LiDAR active, rare on web)
- "Audio Unavailable" (Web Audio API failed to initialize)

---

## Gesture Hint

Below the alert box, a hint line reads "Double-tap to scan. Hold to speak." This text serves as a persistent reminder of available interactions. It is not interactive itself.

When voice recognition is active, the microphone button text changes to "Listening..." to indicate the system is waiting for a voice command.

---

## Control Buttons

The control bar at the bottom of the screen contains three buttons:
- **"What's Around"** (left): Triggers `describeArea()`
- **"Speak"** (center, blue): Triggers `startListening()` for voice recognition
- **"Is It Safe"** (right): Triggers `checkSafety()`

The microphone button has a distinct blue background (`#48f`) that changes to red with a pulse animation when listening. Each button has a large touch target (18px vertical padding, full flex width) to make them easy to tap without precise targeting.

All buttons call `unlockAudio()` on click to ensure iOS audio works regardless of which element the user taps first.

---

## Direction Indicators

Three circular direction indicators sit below the alert box in a row: Left (L), Ahead (F), Right (R). Each is 70px diameter with a 3px border.

Default state: 50% opacity, white border, dark background.

When a detection occurs in a specific direction, the corresponding indicator becomes active (full opacity, amber border and background). If the detection is at danger level, the indicator turns red with a pulse animation.

The indicators flash briefly (1 second) when the user asks about a specific direction via `speakDirection`.

---

## Camera Preview

The video element fills the entire screen (`width: 100%, height: 100%, object-fit: cover`) and sits behind the overlay at 30% opacity. This provides a faint camera preview for sighted helpers while keeping the overlay text readable. The low opacity ensures the alert colors (green, amber, red) are clearly visible against the darkened camera feed.

The video element has `autoplay`, `playsinline`, and `muted` attributes. The `playsinline` attribute is required for iOS, which otherwise opens video in fullscreen mode.

---

## Privacy Screen

The privacy screen is shown every time the app launches. It is a full-screen overlay (`position: fixed, inset: 0`) with a near-opaque black background (`rgba(0,0,0,0.98)`).

### Content

- Title: "Privacy & Permissions"
- Two info items explaining camera usage, cloud AI, and data handling
- A "I Understand - Continue" button
- A hint: "Tap to hear aloud. Tap again to continue"

### Two-Tap Flow

**First tap anywhere on the privacy screen:**
1. Calls `unlockAudio()` to enable iOS speech
2. Cancels any current speech
3. Speaks: "Welcome to GuideDog. This app uses your camera and cloud AI to help you navigate. All detection runs on your device. No data is stored. Tap again to continue."
4. The `privacyRead` flag is set to true

**Second tap:**
1. Cancels the speech (in case it is still playing)
2. Hides the privacy screen (`display: none`)
3. Calls `showHelp()` to display the features screen

This two-tap flow ensures blind users hear the privacy information. The first tap unlocks audio and reads the information aloud. The second tap confirms the user has heard it and wants to proceed.

---

## Features Screen (Help)

The features screen appears after the privacy screen is dismissed. It is a scrollable full-screen overlay with a near-opaque black background.

### Content

Four help items:
1. **AUTOMATIC PROTECTION** - "App constantly scans and warns you about obstacles, stairs, walls, doors automatically. You don't need to do anything!"
2. **Voice Commands** - Lists available commands: "What's around", "Is it safe", "Left"/"Right", "Stop"/"Resume"
3. **Gesture Controls** - "Tap TOP = describe area, Tap BOTTOM = detailed scan, Swipe LEFT/RIGHT = check sides"
4. **Alert Sounds** - "Beeps indicate direction of obstacle, Fast beeps = DANGER, Vibration = obstacle in your path"

A "START - TAP HERE OR SAY 'START'" button at the bottom calls `hideHelp()`.

When `showHelp()` is called, it speaks the feature summary: "GuideDog automatically warns you about obstacles, stairs, walls, and doors. You don't need to do anything. Tap the button to start."

When `hideHelp()` is called, it cancels speech, unlocks audio, sets `state.isRunning = true`, and starts both `protectionLoop()` and `fastHazardLoop()`.

---

## Version Tag

A small version tag sits in the bottom-right corner: "build 25c-v2". It uses 10px font, 30% white opacity, and `pointer-events: none` so it never intercepts taps. It is positioned with `fixed` positioning and respects the safe area inset on devices with home indicators.

---

## Viewport and Interaction Restrictions

The viewport meta tag does not include `maximum-scale=1` in the current implementation, but `touch-action: manipulation` is implied through the CSS rule `* { -webkit-tap-highlight-color: transparent; user-select: none; }`. Text selection is disabled globally via `user-select: none` to prevent accidental text selections during gesture use.

The `html` and `body` elements have `overflow: hidden` and `height: 100%` to prevent any scrolling of the main app. The help screen has its own `overflow-y: auto` for scrolling its content independently.

---

## Debug Info

A hidden debug line sits below the alert box. It displays in monospace 10px gray text:
- Detection timing (milliseconds per COCO-SSD inference)
- Number of detected objects
- Depth model status (LiDAR, model, or loading)
- Current depth center value
- Calibration status
- Depth hazard indicator
- Threat transition (raw threat to smoothed threat)

This information is updated every protectionLoop cycle and is intended for development use only.
