# User Interface

## Design philosophy

The visual UI serves two purposes. For blind users, it's largely irrelevant. All critical information reaches you through speech, haptics, and spatial audio. For sighted helpers (orientation and mobility instructors, family, developers), the UI shows the current state of the app. The design uses high contrast colors and large text so a sighted helper can glance at the screen and immediately understand the situation.

## Alert box

Centered on screen within the alert area. Three visual states.

### Safe

- Background: dark green (rgba 0, 40, 20, 0.8)
- Border: 3px solid #0f8 (bright green)
- Icon: "OK"
- Text: "Path Clear" with subtext "Walking is safe."
- No animation

### Warning

- Background: dark amber (rgba 50, 30, 0, 0.85)
- Border: 3px solid #fa0 (bright amber)
- Animation: pulse (scale 1.0 to 1.05 over 1 s, repeating)
- Text: current distance in feet

### Danger

- Background: dark red (rgba 60, 10, 10, 0.9)
- Border: 4px solid #f44 (bright red)
- Animation: shake (5 px horizontal over 0.3 s, repeating)
- Text: "STOP!" with the distance

State transitions are immediate. No CSS transition on background or border color. When the risk level changes, the alert box class switches instantly. The `transition: all 0.3s` on `.alert-box` applies only to scale/transform animations, not to color changes. The user (or helper) sees the state change without a gradual fade that could mask a sudden danger.

### AI badge

Top left. Initially shows "AI Active." Updates to "AI + LiDAR Active" when the first LiDAR depth reading arrives (triggered by `__onLiDARDepth`). Gives the user and helper a quick visual confirmation that LiDAR is working.

### Camera toggle

CAM button, top right. 44x44 points (Apple's minimum touch target size) with a camera icon and "CAM" label. Tapping it sends a `cameraToggle` message to Swift. When enabled, native camera frames go to JS as base64 JPEG via `__onNativeFrame` and display in the background. Camera preview is off by default to save battery.

## Gesture hint

Below the alert box, a small text hint reads "Hold to speak. Double-tap to scan." Styled at 12px in low opacity white (rgba 255, 255, 255, 0.4). Visual reminder without being visually dominant.

## Help item: silent mode reminder

The privacy screen has a help item card reminding users about silent mode. The single most common support question was "Why isn't it talking?" and the usual answer was "Your phone is on silent." The banner makes this obvious.

## Onboarding screens

### Privacy screen

Shown every launch. Full screen overlay at z index 50.

Lists four items:
1. Camera and LiDAR. App needs camera access. All detection runs on device.
2. Microphone and Speech. Mic is used for voice commands. Speech recognition runs on device.
3. Cloud AI (optional). Scan photos may be sent to cloud AI. No images stored.
4. No account required.

The first tap unlocks the audio context. iOS requires a user gesture before the app can play audio. The first tap triggers the standalone AVSpeechSynthesizer to speak the welcome message and privacy summary. The second tap (or tap on "I Understand") transitions to the features screen.

### Features screen

Describes the five main capabilities:

1. Automatic protection (LiDAR and AI monitoring)
2. Gestures (hold, double tap, swipe)
3. Voice commands ("what's around", "is it safe", "left", "right", "stop", "resume", "scan")
4. Distance alerts (live distance in feet, "Stop" for close obstacles)
5. Camera preview (CAM button for sighted helpers)

A "START GUIDEDOG" button and "Tap anywhere to start" text are shown. Tapping anywhere dismisses this screen and sends `engineStart` to Swift, which begins the permission flow and engine startup.

## Startup speech

When the user taps START, the app says "Loading. One moment." right away so blind users know something is happening. Once the first real depth callback arrives, it says "GuideDog active." That confirms the engine is actually running, not still initializing.

## Screen and interaction settings

### Screen wake lock

The app sets `UIApplication.shared.isIdleTimerDisabled = true` when the engine starts. Prevents the screen from dimming or locking during use. A blind user cannot easily re unlock the phone if the screen turns off during navigation.

### Zoom prevention

The viewport meta tag sets `maximum-scale=1.0` and `user-scalable=no`. CSS applies `touch-action: manipulation` globally. Prevents pinch to zoom and double tap to zoom, which would interfere with gesture recognition (particularly the double tap scan).

### Text selection prevention

CSS applies `user-select: none`, `-webkit-user-select: none`, and `-webkit-touch-callout: none` globally. Prevents accidental text selections or iOS copy/paste callouts during gesture use.

## Version tag

Small version tag at the bottom right at 10px font, low opacity. Marked `pointer-events: none` so it doesn't intercept touches. Useful for testing and bug reports.

Current build: 1.4(2).
