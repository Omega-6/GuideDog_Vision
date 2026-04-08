# Architecture

## What Makes This Architecture Non Trivial

GuideDog Vision is a Capacitor app, which is unusual for a real time computer vision application. Most apps in this category are pure native (SwiftUI or UIKit). The Capacitor architecture introduces a JavaScript bridge that, if used carelessly, would add latency to safety critical operations. Several decisions keep that bridge out of the hot path:

- **JavaScript only renders the display surface.** All sensor processing, model inference, audio output, and haptic feedback runs in Swift. The JavaScript layer receives status updates and renders them. It never makes detection decisions.
- **Synchronous engine startup.** The `start()` method is intentionally not `async`. An earlier async version had a race condition where `isRunning` was set to `true` before the ARSession had actually started, causing detection layers to run against empty frame data and fail silently.
- **Six layer dispatch at deliberately different rates.** Each detection layer runs at a different frame interval (4 / 15 / 20 / 60) chosen to match how fast its information becomes stale.
- **Dedicated background DispatchQueue.** Depth processing and mesh classification run on a serial queue at `.userInitiated` quality of service so they never block the main thread or AR frame delivery.
- **`isDetecting` and `isSegmenting` ANE guards.** Boolean flags prevent CoreML requests from piling up on the Apple Neural Engine, which would otherwise cause pipeline stalls and frozen camera output.
- **Staggered initialization.** SpeechController, HapticController, and SpatialAudioController are created at deliberate offsets (immediate, 0.1s, 1.0s) to avoid an AVFoundation conflict that would otherwise leave the speech synthesizer with no audio output.

## Overview

GuideDog Vision is a native iOS app built on Capacitor 8.3. Capacitor wraps a WKWebView inside a native Swift application, allowing the UI to be written in HTML, CSS, and JavaScript while the detection, speech, and sensor logic runs in native Swift with full access to Apple frameworks.

The app uses Swift Package Manager (SPM) for dependency management. There is no CocoaPods or Carthage dependency chain. Capacitor itself is integrated through SPM.

## Bridge Architecture

### CAPBridgeViewController Subclass

The entry point is `ViewController.swift`, which subclasses `CAPBridgeViewController`. This is the standard Capacitor pattern for adding native behavior to the web container. The ViewController owns the NavigationEngine and the VoiceCommandController, and it manages the bridge between Swift and JavaScript.

### Swift-to-JavaScript Communication

The ViewController registers five WKScriptMessageHandler message names during `viewDidLoad`:

| Message Name   | Direction      | Purpose |
|---------------|----------------|---------|
| `speak`       | JS to Swift    | Speak text through native AVSpeechSynthesizer. A whitespace-only string cancels current speech. |
| `scanRequest` | JS to Swift    | Trigger a manual AI scene scan. |
| `cameraToggle`| JS to Swift    | Turn the camera preview on or off (sends a boolean). |
| `voiceCommand`| JS to Swift    | Start or stop the speech recognizer. |
| `engineStart` | JS to Swift    | Signal that the user has dismissed the privacy and help screens. Starts the NavigationEngine. |

For Swift-to-JavaScript communication, the ViewController calls `evaluateJavaScript` on the WKWebView with function calls on the `window` object:

| JS Function        | Direction      | Purpose |
|-------------------|----------------|---------|
| `__onLiDARDepth`  | Swift to JS    | Sends center, left, and right depth values (meters) after each depth processing cycle. |
| `__onNativeReady` | Swift to JS    | Sent once after engine start. Passes a boolean indicating whether the device has LiDAR. |
| `__onDetection`   | Swift to JS    | Sends object label and direction when YOLO confirms a detection. |
| `__onNativeFrame` | Swift to JS    | Sends a base64-encoded JPEG camera frame for the preview overlay (only when camera toggle is on). |

This bridge design keeps the web layer as a display surface. All sensor processing, model inference, and audio output happens in Swift. The JavaScript layer handles UI rendering, gesture detection, and user onboarding screens.

## NavigationEngine

`NavigationEngine` is the core class. It manages the ARSession, all detection models, speech output, haptic feedback, and spatial audio. It conforms to `ARSessionDelegate` and `VoiceCommandDelegate`.

### Initialization and Startup

The engine is created when the user taps through the privacy and help screens. The ViewController sends the `engineStart` message to Swift, which requests camera, microphone, and speech recognition permissions (if not already granted), then calls `startEngine()`.

The `start()` method is intentionally synchronous. An earlier async version caused a race condition where `isRunning` was set to `true` before the ARSession had started, causing the detection layers to run against empty frame data. The synchronous version ensures the ARSession is configured and running before any detection code executes.

The start sequence is:

1. Disable the idle timer (`isIdleTimerDisabled = true`) so the screen stays awake.
2. Configure the AVAudioSession for `playAndRecord` with `spokenAudio` mode.
3. Create the SpeechController and speak "Starting."
4. After a 0.1-second delay (to let the UI render and the welcome speech play), create the HapticController.
5. After a 1.0-second delay, create the SpatialAudioController. This delay is intentional. AVAudioEngine conflicts with AVSpeechSynthesizer if both initialize at the same time.
6. Create and configure the ARSession with world tracking, scene depth (if LiDAR is available), and mesh classification with classification.
7. Run the ARSession.

### ARSession Delegate and Frame Dispatch

The `session(_:didUpdate:)` delegate method is called at the AR frame rate (typically 30 fps on modern iPhones). A frame counter tracks which frame the engine is on. Each detection layer runs at a different interval to balance accuracy against computational cost:

| Layer | Name | Interval | Effective Rate | Thread |
|-------|------|----------|---------------|--------|
| 1 | LiDAR Depth | Every 4 frames | ~7.5 fps | detectionQueue (background) |
| 2 | YOLOv8n Object Detection | Every 20 frames | ~1.5 fps | Global async queue |
| 3 | BlindGuideNav Custom Detection | Every 20 frames | ~1.5 fps | Global async queue |
| 4 | ARKit Mesh Classification | Every 15 frames | ~2 fps | detectionQueue (background) |
| 5 | DeepLabV3 Segmentation | Every 60 frames | ~0.5 fps | Global async queue |
| 6 | Camera Frame (preview) | Every 3 frames | ~10 fps | Main thread callback |

**Why these specific intervals.** The intervals were chosen to balance computational cost against the rate at which information becomes stale. LiDAR runs the most often because depth changes fastest as the user walks (a person at 1.4 m/s covers 18 cm between LiDAR cycles). Object detectors (YOLO and BlindGuideNav) run slower because their results take longer to compute and because object identity does not change frame to frame in the same way distance does. Mesh classification runs slower still because architectural surfaces change only when the user enters a new area. Segmentation runs slowest because its job is to catch large objects the other layers missed, which is a low frequency event by design.

### Background Processing

Depth processing and mesh classification run on a dedicated serial `DispatchQueue` named `com.blindguide.detection` with `.userInitiated` quality of service. This prevents these operations from blocking AR frame delivery on the main thread.

YOLOv8n and DeepLabV3 use `isDetecting` and `isSegmenting` boolean guards to prevent concurrent CoreML requests from piling up on the Apple Neural Engine. Without these guards, queued requests cause ANE overload, which stalls the camera pipeline and freezes the display.

### Audio Session Configuration

The AVAudioSession is configured with:

- Category: `.playAndRecord` (enables both speech output and microphone input for voice commands).
- Mode: `.spokenAudio` (optimized for speech synthesis).
- Options: `.allowBluetoothA2DP`, `.mixWithOthers`, `.duckOthers`.
- If no Bluetooth device is connected, the output is routed to the speaker using `overrideOutputAudioPort(.speaker)`.

This configuration ensures that the app works with AirPods and other Bluetooth audio devices while still falling back to the phone speaker when no Bluetooth is available.

## File Structure

| File | Responsibility |
|------|---------------|
| `ViewController.swift` | CAPBridgeViewController subclass. WKScriptMessageHandler bridge. Owns engine and voice controller. |
| `NavigationEngine.swift` | ARSession management, frame dispatch, depth processing, detection orchestration, distance bands, voice command handling. |
| `ObjectDetector.swift` | YOLOv8n CoreML model loading and Vision framework inference. |
| `MeshClassifier.swift` | ARMeshAnchor classification (wall, door, window, seat, table). |
| `SceneSegmenter.swift` | DeepLabV3 semantic segmentation with PASCAL VOC classes. |
| `AISceneDescriber.swift` | Cloud AI race between Claude and GPT via Cloudflare Worker. |
| `AudioFeedback.swift` | SpeechController (priority speech), SpatialAudioController (directional beeps), RiskSolver (hysteresis logic). |
| `HapticFeedback.swift` | HapticController (UIImpactFeedbackGenerator pulse timers). |
| `VoiceCommands.swift` | VoiceCommandController (SFSpeechRecognizer, command parsing). |
| `index.html` | Web UI: onboarding screens, alert box, gesture handling, camera preview. |
