# Design Decisions

This document explains the reasoning behind each major technical decision in GuideDog Vision. Every choice involves a tradeoff. The goal here is to make those tradeoffs explicit so that future contributors understand not just what the code does, but why it does it that way.

## Why Capacitor Over Pure Native

GuideDog Vision uses Capacitor 8.3 to wrap a WKWebView inside a native Swift application. The detection engine, speech, haptics, and all sensor processing run in native Swift. The UI runs in the web layer.

The alternative was to build the entire app in SwiftUI or UIKit. The reasons for choosing Capacitor:

**Web UI flexibility.** The onboarding screens, alert box, status indicators, and gesture handlers are all HTML and CSS. Updating the layout, colors, animations, or onboarding flow does not require recompilation. During development, this allowed rapid iteration on the visual design without waiting for Xcode build cycles.

**Cross-platform potential.** The same HTML, CSS, and JavaScript can run on Android inside a Capacitor Android project. The native detection code would need to be rewritten in Kotlin, but the UI layer transfers directly. For a pure native app, both the UI and the detection layer would need to be rewritten.

**Familiar tooling.** Web technologies have a lower barrier to entry for UI work. Contributors who know HTML and CSS can modify the interface without learning SwiftUI or UIKit layout systems.

The tradeoff is added complexity in the bridge layer. Every piece of data that crosses between Swift and JavaScript must be serialized and deserialized. The WKScriptMessageHandler and evaluateJavaScript calls add a small amount of latency compared to direct native UI updates. For GuideDog, this latency is acceptable because the web layer only handles display. All latency-sensitive operations (detection, speech, haptics) run entirely in Swift.

## Why YOLOv8n Over COCO-SSD on Native

The web version of GuideDog uses COCO-SSD (TensorFlow.js) for object detection. The native version uses YOLOv8n compiled to CoreML format.

**Apple Neural Engine acceleration.** CoreML models run on the Apple Neural Engine (ANE), a dedicated hardware accelerator present in A11 and later chips. The ANE runs inference significantly faster and with less power consumption than the CPU or GPU. COCO-SSD running through TensorFlow.js in the web layer cannot access the ANE and runs on the CPU via WebAssembly or on the GPU via WebGL, both of which are slower.

**Higher accuracy at comparable speed.** YOLOv8n (the "nano" variant) provides better detection accuracy than COCO-SSD while maintaining real-time inference speeds on the ANE. The smaller COCO-SSD model was originally chosen for web compatibility, but that constraint does not apply in the native layer.

**Vision framework integration.** Running YOLOv8n through Apple's Vision framework (`VNCoreMLRequest`) handles image preprocessing, orientation correction, and result parsing automatically. This reduces custom code and potential bugs compared to manually feeding tensors to a TensorFlow model.

## Why 0.7 Confidence Threshold

The YOLOv8n detector filters results to a minimum confidence of 0.7 (70%).

During testing at 0.5 (50%), the detector produced frequent false positives. Shadows on the ground were classified as objects. Posters and photographs were classified as people. Reflective surfaces generated phantom detections. Each false positive triggered a spoken announcement, which eroded user trust in the system. A blind user who hears "Person ahead" and finds nothing there will eventually start ignoring the app's alerts, which defeats the purpose of the safety system.

At 0.7, the false positive rate dropped dramatically. Real objects (actual people, actual chairs, actual cars) are consistently detected above 0.7 confidence. The tradeoff is that some legitimate detections at longer distances (where the object is small and less distinct in the image) may fall below 0.7 and be missed. This is acceptable because the LiDAR depth system provides distance warnings regardless of object identification. The user will still hear "Something ahead" from the distance band system even if the YOLO detector does not reach 0.7 confidence.

## Why 2-Frame Consecutive Streak Filter

Even at 0.7 confidence, occasional ghost detections appear for a single frame and then disappear. These are often caused by a momentary camera shake, a lighting change between frames, or a partial occlusion that resolves on the next frame.

The 2-frame streak filter requires an object to be detected in at least 2 consecutive YOLOv8n cycles (about 1.3 seconds apart at 1.5 fps) before it is announced. Ghost detections almost never persist across two consecutive frames. Real objects that are physically present in the scene almost always do.

The tradeoff is a one-cycle delay (approximately 0.67 seconds) before a new object is first announced. For stationary obstacles, this delay is negligible. For fast-moving objects (cars approaching), the approach speed detection system provides an independent fast path that does not wait for the streak filter.

## Why 1 Announcement Per Cycle

When multiple objects are detected simultaneously, the engine selects exactly one to announce. It does not queue multiple announcements.

The problem with multiple announcements is staleness. AVSpeechSynthesizer queues utterances and plays them sequentially. If the engine detects three objects and queues three announcements, the second and third announcements play 2 to 4 seconds after the detections occurred. In that time, the user has continued walking. The objects may be behind the user by the time the announcements play. A blind user hearing "chair on left" when the chair is already behind them is confusing and potentially dangerous if it causes them to turn or stop unnecessarily.

By announcing only the single most important object (highest tier, closest distance), the engine ensures that every announcement is current. On the next detection cycle, it can select a different object if needed. The rapid cycle rate (every 0.67 seconds at 1.5 fps) means that important secondary objects will be announced within one or two cycles.

## Why Hysteresis on Distance Bands

LiDAR depth readings oscillate. A wall that is 1.0 meters away might read as 0.98m on one frame and 1.02m on the next. Without hysteresis, the app would enter the danger band (below 1.0m), exit it (above 1.0m), enter it again, and so on, producing repeated "Stop, something close" announcements.

Hysteresis adds a gap between the entry and exit thresholds. The user enters danger at 1.0m but does not exit until 1.3m. This 0.3m gap absorbs the normal oscillation range of LiDAR readings. The user hears one clean announcement when they approach an obstacle, and silence until they either get closer (triggering the critical band) or clearly move away (past 1.3m).

The same logic applies to caution (enter at 2.0m, exit at 2.4m) and approaching (enter at 3.0m, exit at 3.3m). The exit thresholds were determined empirically during testing by observing the range of oscillation at each distance.

## Why Beeps are Danger-Only

An earlier version of the app played spatial audio beeps for both caution and danger levels. During indoor testing, caution beeps fired continuously. In a typical hallway, there is always a wall within 2 meters on at least one side. In a room, both side walls and the far wall may all be within caution range. The result was constant beeping that the user could not escape, which made the feature actively harmful rather than helpful.

Restricting beeps to danger-level threats (below 1.0 meter) means they only sound when the user is genuinely about to collide with something. In a normal room, the user can walk down the center of a hallway without hearing beeps, because the walls on either side are typically more than 1 meter away. When they approach a wall or obstacle closely enough to be at risk, the beep sounds with directional panning to indicate which side the danger is on.

Caution-level feedback is still provided through haptic pulses (light, every 0.5 seconds) and speech ("Heads up"). These channels are less intrusive than audio beeps and do not create the same constant-noise problem.

## Why Size-Based Triangulation Over Per-Pixel Depth Sampling

The ideal approach for measuring the distance to a detected object would be to sample the LiDAR depth map at the exact pixel coordinates of the object's bounding box. The engine does include a `sampleDepthAt(box:)` method that does this, but the primary distance estimation uses size-based triangulation (pinhole camera model) instead.

The reason is coordinate space alignment. The camera image and the LiDAR depth map do not share a 1:1 pixel correspondence. The depth map has a different resolution and field of view than the camera image. While ARKit provides methods to project between these coordinate spaces, the projection involves interpolation and can introduce errors, especially at the edges of the frame. During testing, per-pixel sampling at bounding box coordinates sometimes returned distances from the background (a wall behind the object) rather than from the object itself, because the depth map pixel did not align precisely with the object's surface.

Size-based triangulation avoids this problem entirely. It uses only the camera image (bounding box height) and the camera intrinsics (focal length), both of which are in the same coordinate space. The distance estimate is less precise than a perfect LiDAR sample would be, but it is consistently accurate and never returns a distance from the wrong surface.

The zone-based LiDAR fallback (left/center/right thirds) provides a complementary depth signal that is cross-checked with the size-based estimate. When both agree, the average is highly accurate. When they disagree, the size-based estimate is trusted because it measures the specific object rather than an average over a zone.

## Why start() is Synchronous

An earlier version of the NavigationEngine's `start()` method was `async`. It awaited the ARSession configuration and run call. The problem was a race condition: `isRunning` was set to `true` before the `await` completed. The detection layers checked `isRunning` and began processing, but the ARSession had not yet started, so there were no frames to process. This caused silent failures where the detection system appeared to be running but was not producing any results.

The synchronous version sets `isRunning = true` and then immediately configures and runs the ARSession on the main thread. The detection layers will not receive any `session(_:didUpdate:)` callbacks until the ARSession has actually started delivering frames, so there is no race condition. The heavy initialization (HapticController, SpatialAudioController) is deferred with `asyncAfter` to avoid blocking the main thread, but the ARSession itself starts synchronously.

## Why Cloud AI on Scene Change, Not on a Timer

An earlier approach used a timer that triggered a cloud AI scan every 30 seconds. This had two problems:

**Wasted API tokens.** If the user is standing still or walking down a long, featureless hallway, the scene does not change. Scanning every 30 seconds produces the same description repeatedly, consuming API quota without providing new information.

**Missed scene changes.** If the user walks quickly through a doorway into a new room, the timer might not fire until 25 seconds later, long after the user has already navigated the transition.

The scene-change trigger solves both problems. It monitors the ARKit mesh classification for the center zone. When the dominant classification changes (for example, from "Wall" to "Door"), it indicates that the user has entered a new area. The cloud AI scan fires immediately, providing a description of the new environment when it is most useful. If the scene does not change, no scan fires, and no API tokens are spent.

The 20-second minimum interval between automatic scans prevents rapid-fire requests when the mesh classification oscillates (for example, at the threshold between a wall and a door).

## Why SpatialAudioController is Delayed 1 Second After Engine Start

The SpatialAudioController is created 1.0 second after the NavigationEngine's `start()` method runs, rather than immediately.

The reason is a conflict between AVAudioEngine and AVSpeechSynthesizer. When both are initialized at the same time, the speech synthesizer can lose its audio output. The synthesizer appears to be speaking (isSpeaking returns true, the delegate callbacks fire), but no audio is produced. This is a critical failure for a blind user.

The root cause appears to be that AVAudioEngine reconfigures the audio session's rendering pipeline during initialization, and if AVSpeechSynthesizer attempts to speak during that reconfiguration, its audio route is lost. By delaying the SpatialAudioController creation by 1 second, the engine ensures that the initial "Starting" speech has already begun playing through the synthesizer before AVAudioEngine is initialized. Once the synthesizer has an active audio route, the AVAudioEngine initialization does not disrupt it.

This timing-based workaround is not ideal, but the underlying AVFoundation behavior is not well documented. The 1-second delay has been reliable across all tested device and iOS version combinations.
