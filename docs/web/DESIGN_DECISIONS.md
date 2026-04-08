# GuideDog Vision: Design Decisions

This document explains the reasoning behind each major design decision in the PWA. Many of these decisions were made after encountering specific bugs, crashes, or user complaints. Each section describes the decision, the alternatives that were considered, and why the chosen approach was selected.

---

## Why COCO-SSD Over MediaPipe

**Decision:** Use COCO-SSD via TensorFlow.js loaded as a `<script>` tag, rather than MediaPipe's object detection solution.

**What happened:** MediaPipe's JavaScript API uses ES module imports. When loaded on iOS Safari, the ES module import crashed the browser tab. The crash occurred during the module initialization phase, not during inference. The root cause appears to be related to how iOS Safari handles certain WebAssembly module imports within ES module scope.

**Why COCO-SSD works:** COCO-SSD loads via a traditional `<script>` tag. The `cocoSsd` global is available after the script loads. This approach does not trigger the ES module parsing issues on iOS Safari. TensorFlow.js handles its own WebAssembly backend initialization internally, and this path has been tested extensively across browsers.

**Trade-off:** COCO-SSD only detects 80 COCO classes, while MediaPipe offers more flexible detection options. For this use case, the 19 relevant COCO classes provide adequate coverage for the most common navigation obstacles.

---

## Why Transformers.js v2 Over v3

**Decision:** Use `@xenova/transformers@2.17.2` (v2), not `@huggingface/transformers@3` (v3).

**What happened:** Transformers.js v3 uses ONNX Runtime Web as its inference backend. When loaded alongside TensorFlow.js, both runtimes initialize simultaneously. On iOS Safari, this combination exceeded the per-tab memory limit. The browser killed the tab without warning during model initialization.

The failure was consistent on iPhones with 4GB of RAM and intermittent on iPhones with 6GB. Desktop browsers and Android Chrome handled both runtimes without issue because they allocate more memory per tab.

**Why v2 works:** Transformers.js v2 uses its own lightweight inference engine that does not conflict with TensorFlow.js. Both can coexist in the same tab without exceeding iOS Safari's memory budget. The v2 inference engine is slower than ONNX Runtime, but the depth model only runs every 400ms, so the speed difference is acceptable.

**Trade-off:** v2 is no longer actively maintained. The `@xenova/transformers` package is the community fork, while `@huggingface/transformers` is the official package. Future model releases may only support v3. If iOS Safari increases its per-tab memory limit, switching to v3 would be worth revisiting.

---

## Why Cloud AI Every 5 Seconds

**Decision:** Send a camera frame to the cloud AI every 5 seconds, not faster or slower.

**Why it exists at all:** The PWA has no LiDAR. COCO-SSD detects 19 object classes but cannot detect stairs, floor conditions, walls (as semantic concepts), narrow passages, or doors. The depth model provides relative depth but cannot identify what a surface is. The cloud AI fills these gaps by acting as a sighted guide companion who describes what they see.

**Why 5 seconds:** This interval was chosen by balancing three factors:

1. **Token cost.** Each request sends an image to both Anthropic and OpenAI. At 1 request per 5 seconds, a 30-minute walk generates approximately 360 API calls. Running every 2 seconds would triple the cost. Running every 10 seconds would miss obstacles at normal walking speed.

2. **Walking speed.** A person walks at roughly 1.4 meters per second. In 5 seconds, they cover about 7 meters. Most indoor hallways have obstacles spaced further apart than 7 meters. For dense environments, the local detection models (COCO-SSD, depth, wall check) provide continuous coverage between AI scans.

3. **Response latency.** Cloud AI responses take 1 to 3 seconds to return. A 5-second interval ensures the previous response has arrived before the next request fires. The `state.aiScanInProgress` flag prevents overlapping requests.

---

## Why Guide Mode Prompt vs App Prompt

**Decision:** The website uses a different AI prompt ("guide mode") than the native app ("app mode").

**Why they differ:** The native iOS app has LiDAR for spatial awareness and YOLOv8 for object detection. It already knows where walls are and how far away objects are. The app uses the AI as a safety backstop: confirm hazards, catch edge cases, prioritize stairs. The prompt is terse and safety-focused.

The PWA has no LiDAR. It cannot measure absolute distances reliably. It needs the AI to provide environmental context: "hallway ahead, door on your left, floor slopes down." This is navigation guidance, not hazard detection. The guide mode prompt instructs the AI to describe the surroundings as a sighted companion would, including which direction is clear for walking.

**Same worker, different behavior:** Both prompts are served by the same Cloudflare Worker. The `mode` parameter in the request body selects which system prompt to use. This keeps infrastructure simple while allowing the two clients to have different AI behaviors.

---

## Why Zero Cooldowns on speakAlert

**Decision:** All priority tiers in `speakAlert` have zero-millisecond cooldowns.

**What happened:** Previous versions used cooldowns of 2 to 3 seconds per alert key. The intent was to prevent the same alert from repeating too quickly. In practice, users reported missing important warnings. A wall would appear, the system would speak "Wall ahead", and then the cooldown would prevent any further wall alerts for 2 to 3 seconds. If the user continued walking during that time, they would not hear another warning until the cooldown expired.

The problem was worse for escalating situations. If the system said "Slow" at the warning level, and the obstacle transitioned to danger within the cooldown window, the danger alert was silently dropped. The user heard "Slow" but never heard "Stop."

**Why zero works:** The temporal smoothing system in the detection layer already prevents rapid state changes. A danger alert does not fire repeatedly because the state remains at "danger" and the fast hazard loop only speaks on state changes (`threat !== _lastFastThreat`). The speech system does not need its own deduplication because the detection system handles it upstream.

---

## Why fastHazardLoop Owns All UI

**Decision:** The `fastHazardLoop` (50ms cycle) is the sole owner of all UI updates and speech output. The `protectionLoop` (200ms cycle) only writes to the state object.

**What happened:** In earlier versions, both loops called `updateUI`. The protectionLoop would set the alert box to green ("Path Clear"), and 20ms later the fastHazardLoop would set it to red ("Wall detected"). The badge and box colors flickered between states. On some cycles, the badge showed "SAFE" while the box was red, because the protectionLoop updated the badge but the fastHazardLoop updated the box in the same animation frame.

**Why single ownership works:** When only one code path modifies the DOM, the display is always internally consistent. The badge, box, icon, text, and detail are all set in a single `updateUI` call within the fast loop. No other code path can interleave and create a mismatch.

The protectionLoop writes its results to `state._mainThreat` and `state.currentObstacle`. The fast loop reads these values on its next cycle (at most 50ms later). This 50ms delay is imperceptible to the user but eliminates all race conditions.

---

## Why Camera Loads Before COCO-SSD Model

**Decision:** The startup sequence loads the camera first, then loads the COCO-SSD model.

**Why this order matters:** The fast wall check (pixel variance analysis) needs video pixels from the very first frame. It runs every 50ms in the fast hazard loop and requires `state.video.videoWidth > 0`. If the COCO-SSD model loaded first, the camera would not have pixels available for 3 to 5 seconds (the time it takes to download and initialize the model). During those seconds, the user could walk into a wall with no warning.

By loading the camera first, the wall check begins working as soon as the protection loops start (after the user dismisses the privacy and help screens). The COCO-SSD model loads next and is typically ready within 1 to 3 seconds. The depth model loads in the background and may take longer, but the wall check and COCO-SSD provide adequate coverage during the gap.

---

## Why Privacy Screen Shown Every Launch

**Decision:** The privacy screen is displayed every time the app opens, not just on the first run.

**Why not first-run-only:** The target users are blind. They cannot read the screen. The privacy screen's primary purpose is not visual. It is an audio reminder. The first tap triggers a spoken welcome message that explains what the app does, how it uses the camera, and that no data is stored. The second tap confirms the user heard the information and wants to proceed.

If the privacy screen were only shown on the first run, returning users would never hear the instructions again. They would go directly to the scanning interface without any audio orientation. A user who has not used the app in weeks might forget the available gestures and voice commands.

The privacy screen also serves as the iOS audio unlock point. The first tap is guaranteed to be a user gesture, which satisfies iOS Safari's requirement for enabling speech synthesis. Without this screen, the app would need to find another guaranteed-gesture moment to unlock audio.

---

## Why Dual Loop Instead of Single Loop

**Decision:** Use two independent loops (protectionLoop at 200ms, fastHazardLoop at 50ms) rather than a single loop.

**Why not a single fast loop:** Running COCO-SSD object detection every 50ms would be too computationally expensive. The model requires 100 to 200 milliseconds per inference on mobile devices. Running it every 50ms would create a backlog of inference requests, cause frame drops, drain the battery, and potentially crash the browser tab on lower-end devices.

**Why not a single slow loop:** A single 200ms loop would update the UI at 5fps. The wall check (pixel variance) can detect a wall in under 5ms. If the wall check only ran every 200ms, the user could walk 0.28 meters (about 11 inches) between checks at normal walking speed. The 50ms cycle (20fps) reduces this to 0.07 meters (about 3 inches), providing much faster response to sudden obstacles.

**The dual loop solution:** The slow loop handles expensive operations (COCO-SSD, depth model, cloud AI). The fast loop handles cheap operations (wall check, cached depth values, UI updates, speech). This gives the user 20fps responsiveness for the most common hazard (walls and flat surfaces) while running the expensive detection models at a sustainable 5fps rate.

---

## Why No Buttons (Gesture-Only Consideration)

**Decision:** The interface prioritizes gesture and voice interaction, with buttons serving as a secondary option.

**The argument for removing buttons:** Blind users cannot see button labels. They must explore the screen by touch to find buttons, which is slow and unreliable. Gestures (hold, double-tap, swipe) are discoverable through the help screen audio and work anywhere on the screen without visual targeting. A gesture-only interface would be cleaner and avoid the confusion of buttons that the user cannot see.

**The current state:** The PWA still includes three buttons (What's Around, Speak, Is It Safe) in the control bar. These serve two purposes: they provide a familiar interaction model for users who are accustomed to button-based apps, and they give sighted helpers an easy way to trigger actions on behalf of the user. The gesture system works in parallel with the buttons.

The help screen teaches both gestures and voice commands, so users who prefer the gesture-only approach can ignore the buttons entirely.

---

## Why iOS Audio Unlock With Primer Utterance

**Decision:** On the first user gesture, speak a silent primer utterance (empty string, zero volume, maximum rate) to unlock iOS Safari's speech synthesis engine.

**What the problem is:** iOS Safari blocks `speechSynthesis.speak()` until a user gesture (touchstart or click) occurs. If the app tries to speak before any gesture, the utterance is silently discarded. No error is thrown. The speech simply never plays.

**Why a primer utterance:** Simply calling `speechSynthesis.speak()` during a gesture is not enough if the gesture handler also needs to do other work before speaking the real content. The primer utterance (spoken during the first gesture) "unlocks" the engine. After the primer, all subsequent calls to `speechSynthesis.speak()` work regardless of whether they occur during a gesture or in an asynchronous callback.

**Why empty and silent:** The primer utterance uses an empty string with volume 0 and rate 10 (maximum). The user hears nothing. The utterance exists solely to satisfy the browser's security policy. Using a non-empty string at audible volume would produce an unwanted sound on the first tap.

**Why document-level listeners:** The primer fires from `touchstart` and `click` listeners on the `document` object. Earlier versions attached these to specific UI elements, but overlays (privacy screen, help screen) intercepted the touches before they reached those elements. Using document-level listeners ensures the primer fires on any touch, anywhere on the page, regardless of which overlay is currently displayed.
