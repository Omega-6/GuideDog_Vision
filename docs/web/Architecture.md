# PWA Architecture

## What Makes This Architecture Non Trivial

Running real time computer vision in a web browser, on a phone, in iOS Safari, with two ML models loaded at once, has serious memory and timing constraints. Several decisions in the architecture come from working around those constraints:

- **Dual loop system.** A fast loop (50ms / 20fps) handles cheap operations (pixel wall check, UI updates, speech) and a slow loop (200ms / 5fps) handles expensive operations (object detection, depth model, cloud AI). The split is justified by walking speed math: at 1.4 m/s a person covers 7 cm in 50 ms but 28 cm in 200 ms. The user needs 50 ms response for walls, but ML inference cannot run that fast.
- **Single owner for UI updates.** The fast loop is the sole writer to the DOM. The slow loop only writes to the shared state object. An earlier version had both loops calling `updateUI` and the alert box flickered between states within a single animation frame. Restricting all UI writes to one loop eliminates the race.
- **Camera before model load order.** The camera initializes before any model loads, so the pixel variance wall check has video frames to process from the very first cycle. Loading models first would leave the user unprotected for the 3 to 5 seconds it takes to download COCO-SSD.
- **Single file deployment.** All HTML, CSS, and JavaScript live in one `index.html` file. No build tools, no bundler, no framework. One file loads in one request and has no dependency resolution issues. This is unusual for a project with this much functionality, but it eliminates an entire class of deployment failures.
- **COCO-SSD via script tag, not ES module.** MediaPipe uses ES module imports that crash iOS Safari during WebAssembly initialization. COCO-SSD loads via a traditional `<script>` tag and avoids the crash.
- **Transformers.js v2, not v3.** Transformers.js v3 uses ONNX Runtime Web, which on iOS Safari combined with TensorFlow.js exceeds the per tab memory budget on 4 GB iPhones. Version 2 has a lighter inference engine that coexists with TensorFlow.js inside the same tab.

## Single File Structure

The entire PWA website is contained in a single `index.html` file. All HTML, CSS, and JavaScript live in this one file. There are no build tools, no bundler, no framework. The supporting files are `manifest.json` (PWA metadata) and `sw.js` (service worker for offline caching). This structure was chosen for simplicity, reliability, and ease of deployment. A single file loads in one request and has no dependency resolution issues.

## External Scripts

Two external libraries are loaded via CDN:

1. **TensorFlow.js** (`@tensorflow/tfjs@4.22.0`) and **COCO-SSD** (`@tensorflow-models/coco-ssd@2.2.3`) are loaded as traditional `<script>` tags with SRI integrity hashes. These provide the object detection runtime. Script tags were chosen over ES modules because COCO-SSD loads reliably via script tag on all browsers, including iOS Safari.

2. **Transformers.js v2** (`@xenova/transformers@2.17.2`) is loaded as an ES module via a `<script type="module">` block. It provides the Depth-Anything model runtime. The module loads asynchronously and dispatches a `tx-ready` custom event when ready, or `tx-failed` if it cannot load. A fallback CDN (`esm.sh`) is attempted if the primary CDN (`jsdelivr`) fails.

## Dual Loop System

The core of the architecture is two independent loops running at different frequencies. This separation is the most important architectural decision in the codebase.

### protectionLoop (200ms cycle, 5fps)

This loop handles all heavy computation:

- Runs COCO-SSD object detection on the video feed
- Updates depth calibration from detected objects
- Fires async depth model scans (every 400ms)
- Fires async cloud AI scans (every 5 seconds)
- Sets state data: `state.localDetections`, `state._mainThreat`, `state.currentObstacle`, `state.depthHazard`, `state.aiHazard`

This loop never touches the UI directly. It never calls `updateUI`, `speakAlert`, `playAlertSound`, or `vibrateAlert`. It only writes to the shared state object.

### fastHazardLoop (50ms cycle, 20fps)

This loop handles all output:

- Runs the fast wall check (pixel variance, under 5ms)
- Reads cached depth values from `state.depthHistory`
- Reads active hazards from `state.depthHazard` and `state.aiHazard`
- Reads COCO-SSD results from `state._mainThreat` and `state.currentObstacle`
- Calls `updateUI` to set alert box colors, text, and badge state
- Calls `speakAlert`, `playAlertSound`, and `vibrateAlert` for audio output

This loop is the sole owner of all UI updates and all speech output. No other code path modifies the UI during normal operation.

### Why Two Loops

Running COCO-SSD inference at 50ms intervals would be too computationally expensive. The model needs approximately 100 to 200 milliseconds per frame on mobile devices. Running it every 50ms would cause frame drops, battery drain, and potential crashes on lower-end devices.

At the same time, the UI needs to respond at 20fps to feel responsive. A wall that appears in the camera feed should trigger a visual and audio alert within 50ms, not 200ms. The fast wall check (pixel variance) can detect uniform surfaces in under 5ms, making it suitable for the 50ms cycle.

The separation also eliminates race conditions. In earlier versions, both loops called `updateUI`, which caused the status badge color and alert box color to fall out of sync. With a single owner of all UI updates, the display is always consistent.

## State Object

The `state` object is the central data store. Both loops read from and write to it. Key fields include:

- `state.video` - the HTML video element
- `state.model` - the loaded COCO-SSD model instance
- `state.isRunning` - whether the protection loops are active
- `state.isPaused` - whether the user has paused alerts
- `state.localDetections` - array of current COCO-SSD detections
- `state.aiResult` - most recent cloud AI response text
- `state.aiHazard` - parsed hazard from cloud AI with expiry timestamp
- `state.depthHazard` - parsed hazard from depth model with expiry timestamp
- `state.depthPipeline` - the loaded Transformers.js depth estimation pipeline
- `state.depthHistory` - rolling window of depth readings (center, left, right)
- `state.depthCalibration` - mapping between raw depth values and real meters
- `state.currentStatus` - current threat level (safe, warning, danger)
- `state.currentObstacle` - the most dangerous detected obstacle
- `state._mainThreat` - threat level from the protection loop for the fast loop to read

## Startup Flow

The startup sequence is ordered deliberately:

1. **Camera starts first.** The video feed must be running before any detection can occur. The fast wall check needs pixels from the first frame. Loading models first would delay wall detection by 3 to 5 seconds, leaving the user unprotected.

2. **COCO-SSD loads.** This is the primary object detection model. It loads synchronously (awaited) because the protection loop depends on it.

3. **Loading screen hides.** The loading overlay is removed once the camera and COCO-SSD are ready.

4. **Depth model loads in background.** `initDepthModel()` is called without `await`. It first attempts WebXR LiDAR (which would only work on supported devices in AR mode), then falls back to downloading the Transformers.js Depth-Anything model. This download can take several seconds and happens in the background while the user interacts with the privacy and help screens.

5. **Privacy screen shown.** The privacy notice is displayed every launch. The first tap unlocks audio and speaks the welcome message. The second tap dismisses it and shows the features screen.

6. **Features screen shown.** This describes the gestures and voice commands. Tapping the start button calls `hideHelp()`, which sets `state.isRunning = true` and starts both `protectionLoop()` and `fastHazardLoop()`.

## Visibility Handling

When the browser tab goes to the background (`document.hidden` becomes true), the app stops running. Any active WebXR session is ended. When the tab returns to the foreground, the loops restart automatically if the model and camera are already initialized. This prevents unnecessary battery drain and avoids errors from trying to run ML inference on a backgrounded tab.

## Service Worker

The service worker (`sw.js`) is registered on load. It provides basic caching for the app shell, enabling the PWA to load from cache on subsequent visits. The cloud AI features still require a network connection, but the interface itself can render offline.
