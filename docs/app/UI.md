# User Interface

## Design Philosophy

The visual UI serves two purposes. For blind users, it is largely irrelevant. All critical information is delivered through speech, haptics, and spatial audio. For sighted helpers (orientation and mobility instructors, family members, developers), the UI provides a visual representation of the app's current state. The design prioritizes high-contrast colors and large text so that a sighted helper can glance at the screen and immediately understand the situation.

## Alert Box

The alert box is centered on screen within the alert area. It displays the current safety status with three visual states:

### Safe State
- Background: dark green (rgba 0, 40, 20, 0.8).
- Border: 3px solid #0f8 (bright green).
- Icon: "OK" text.
- Text: "Path Clear" with subtext "Walking is safe."
- No animation.

### Warning State
- Background: dark amber (rgba 50, 30, 0, 0.85).
- Border: 3px solid #fa0 (bright amber).
- Animation: pulse (scale 1.0 to 1.05 over 1 second, repeating).
- Text updates to show the current distance in feet.

### Danger State
- Background: dark red (rgba 60, 10, 10, 0.9).
- Border: 4px solid #f44 (bright red).
- Animation: shake (horizontal displacement of 5 pixels over 0.3 seconds, repeating).
- Text updates to "STOP!" with the distance.

State transitions are immediate. There is no CSS transition on the background color or border color. When the risk level changes, the alert box class switches instantly. The `transition: all 0.3s` in the base `.alert-box` class applies only to the scale/transform animations, not to color changes. This ensures the user (or helper) sees the state change without a gradual fade that could mask a sudden danger.

## Status Bar

The status bar sits at the top of the screen with a dark semi-transparent background.

### Status Badge
The status badge (showing "SAFE", "WARNING", or "DANGER") is hidden by default (`display: none`). It was part of an earlier design and is preserved in the markup but not shown in the current build.

### AI Badge
The AI badge appears in the top left area. It initially shows "AI Active" and updates to "AI + LiDAR Active" when the first LiDAR depth reading arrives (triggered by `__onLiDARDepth`). This gives the user and helper a quick visual confirmation that LiDAR is functioning.

### Camera Toggle
The CAM button is positioned in the top right. It is a 44x44 point button (meeting Apple's minimum touch target size) with a camera icon and "CAM" label. Tapping it sends a `cameraToggle` message to Swift. When enabled, native camera frames are sent as base64 JPEG strings via `__onNativeFrame` and displayed in the background. The camera preview is off by default to save battery and processing resources.

## Gesture Hint

Below the alert box, a small text hint reads "Hold to speak. Double-tap to scan." This is styled at 12px in a low-opacity white (rgba 255, 255, 255, 0.4). It provides a visual reminder of the primary gestures without being visually dominant.

## Onboarding Screens

### Privacy Screen

The privacy screen is shown every time the app launches. It is a full-screen overlay at z-index 50 that covers the entire interface.

The screen lists four items:
1. **Camera and LiDAR.** Explains that the app needs camera access and that all detection runs on device.
2. **Microphone and Speech.** Explains that the microphone is used for voice commands and that speech recognition runs on device.
3. **Cloud AI (Optional).** Explains that scan photos may be sent to cloud AI, with no images stored after analysis.
4. **No Account Required.** States that no personal data is collected.

The first tap on this screen serves a critical technical purpose: it unlocks the audio context. iOS requires a user gesture before the app can play audio. The first tap triggers the standalone AVSpeechSynthesizer to speak the welcome message and privacy summary. The second tap (or tap on "I Understand") transitions to the features screen.

### Features Screen

The features screen describes the five main capabilities:
1. Automatic protection (LiDAR and AI monitoring).
2. Gestures (hold, double tap, swipe).
3. Voice commands (what's around, is it safe, left, right, stop, resume, scan).
4. Distance alerts (live distance in feet, "Stop" for close obstacles).
5. Camera preview (CAM button for sighted helpers).

A "START GUIDEDOG" button and "Tap anywhere to start" text are shown. Tapping anywhere dismisses this screen and sends the `engineStart` message to Swift, which begins the permission request and engine startup flow.

## Screen and Interaction Settings

### Screen Wake Lock
The app sets `UIApplication.shared.isIdleTimerDisabled = true` when the engine starts. This prevents the screen from dimming or locking during use. A blind user cannot easily re-unlock the phone if the screen turns off during navigation.

### Zoom Prevention
The viewport meta tag sets `maximum-scale=1.0` and `user-scalable=no`. The CSS applies `touch-action: manipulation` globally. Together, these prevent pinch-to-zoom and double-tap-to-zoom, which would interfere with the app's gesture recognition (particularly the double-tap-to-scan gesture).

### Text Selection Prevention
The CSS applies `user-select: none`, `-webkit-user-select: none`, and `-webkit-touch-callout: none` globally. This prevents the user from accidentally selecting text or triggering the iOS copy/paste callout, which would interfere with touch gestures.

## Version Tag

A small version tag ("build 19") is positioned at the bottom right of the screen at 10px font size and low opacity. It is marked `pointer-events: none` so it does not intercept touch events. It provides a quick visual reference for debugging and testing.
