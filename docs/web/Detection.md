# Detection System

## Overview

The PWA uses five detection layers that run concurrently. Each layer has different strengths, speeds, and failure modes. Together, they provide redundant coverage so that no single point of failure leaves the user unprotected.

## What Makes This Pipeline Non Trivial

The website is running real time computer vision in a web browser, on a phone, with no LiDAR. Several techniques in this pipeline go beyond just calling a model and waiting for results:

- **Pixel variance wall check.** Pure JavaScript, no ML, runs in under 5 milliseconds. Detects flat surfaces by computing brightness variance and edge density across a 64 by 48 sample of the center frame. This is the safety net that protects the user during the 3 to 5 seconds it takes the COCO-SSD model to download.
- **Asymmetric temporal smoothing.** Escalation is instant (a single frame can trigger danger), but de escalation requires 2 consecutive safe readings before the system relaxes. Being too cautious is fine, being too late is dangerous.
- **Camera triangulation with a curated heights table.** The system uses real pinhole camera math to estimate distance from bounding box height, with a hand built table of 24 known object heights. See [Distance](Distance.md) for the full pipeline.
- **Auto calibration of relative depth.** The Depth-Anything model only outputs unitless 0 to 255 values. The system bootstraps absolute distance measurements from those relative values by using triangulated detections as ground truth anchors. See [Distance](Distance.md).
- **Two ML detectors sharing one runtime.** COCO-SSD (TensorFlow.js) and BlindGuideNav (ONNX Runtime Web) run on the same camera frames in the same protection loop. Their results merge into a single deduplicated list before the announcement system picks which object to speak.
- **Center vs sides depth deviation.** Catches narrow obstacles (poles, signs, railings) that fill the center but not the periphery. A pure absolute threshold would miss these.

Each technique is described in the layer sections below.

---

## Layer 1: COCO-SSD (Object Detection)

**Runtime:** TensorFlow.js, loaded via `<script>` tag
**Cycle:** Every 200ms in the protectionLoop
**Model:** COCO-SSD v2.2.3, pretrained on the COCO dataset (80 classes)

### Filtered Object Set

Of the 80 COCO classes, the system filters to 19 objects relevant to pedestrian navigation:

- **Critical (vehicles):** car, bus, truck, motorcycle, bicycle
- **Obstacles:** person, chair, bench, couch, bed, dining table, refrigerator, potted plant, backpack, fire hydrant, stop sign, parking meter, laptop, tv

Detections below 0.7 confidence are discarded entirely. This threshold (`CONFIG.HIGH_CONFIDENCE`) was chosen to eliminate false positives that would cause unnecessary alerts. A false "person ahead" alert while walking in an empty hallway erodes user trust quickly.

### Distance Estimation

The full distance pipeline (known object triangulation, auto calibration of relative depth, approach rate detection, and center vs sides analysis) is documented in [Distance](Distance.md). In brief: detected objects with known real world heights are converted to absolute distances through pinhole camera geometry, and those distances are used to calibrate the depth model so that distances to unknown objects can also be estimated.

### Position Classification

Each detection is classified by horizontal position based on the bounding box center:
- **Left:** center X < 35% of frame width
- **Right:** center X > 65% of frame width
- **Ahead:** everything else

An object is considered "in path" if its center X is between 25% and 75% of the frame width AND its center Y is below 30% from the top (meaning it is not floating in the sky).

### Danger Classification

Objects are classified by category:
- **Critical:** vehicles (car, bus, truck, motorcycle, bicycle)
- **Obstacle:** all other tracked objects
- **Low:** anything else

Distance zones determine the alert level:
- **Danger zone:** less than 1.0 meter
- **Warning zone:** less than 2.0 meters
- **Awareness zone:** less than 4.0 meters

---

## Layer 2: Depth-Anything (Relative Depth Estimation)

**Runtime:** Transformers.js v2 (`@xenova/transformers@2.17.2`), loaded as ES module
**Model:** `Xenova/depth-anything-small-hf`, quantized
**Cycle:** Every 400ms, fired from protectionLoop
**Input:** 256x256 JPEG from video feed
**Output:** Depth map with values 0 to 255 (higher = closer)

### How It Works

The model produces a depth map with values from 0 to 255. Higher values mean closer. Three regions are sampled (center, left strip, right strip) and the average values for each region are stored in `state.depthHistory` as a rolling window of the last 6 readings.

The relative depth values are turned into absolute distances and into actionable threat levels through the auto calibration and approach rate logic. See [Distance](Distance.md) for the full pipeline (calibration formula, approach rate detection, center versus sides deviation analysis).

---

## Layer 3: Fast Wall Check (Pixel Variance)

**Runtime:** Pure JavaScript, no ML
**Cycle:** Every 50ms in fastHazardLoop
**Input:** 64x48 canvas grabbed from the video feed
**Execution time:** Under 5 milliseconds

### How It Works

A wall or flat surface close to the camera fills the frame with uniform color and few edges. Open space has texture variation, color gradients, and visible edges between objects.

The algorithm:

1. Grabs a 64x48 frame from the video (reuses a persistent canvas to avoid allocation)
2. Samples the center strip: middle 50% width (pixels 16 to 48), middle 60% height (pixels 10 to 38)
3. Computes brightness for each pixel using the luminance formula: `R * 0.299 + G * 0.587 + B * 0.114`
4. Computes brightness variance across all sampled pixels
5. Counts edges: adjacent pixels with brightness difference greater than 30
6. Computes edge ratio: edge count divided by total sampled pixels

### Thresholds

| Variance | Edge Ratio | Result |
|----------|------------|--------|
| < 150 | < 6% | DANGER (wall detected) |
| < 350 | < 10% | WARNING (obstacle ahead) |
| above both | above both | No detection |

Typical values observed in testing:
- Wall at arm's length: variance 50 to 200, edge ratio under 0.05
- Open room: variance 500 to 2000+, edge ratio above 0.15
- Cluttered desk: variance 300 to 800, edge ratio 0.08 to 0.15

This method is not ML inference. It is simple statistical analysis of pixel data. It runs in constant time regardless of scene complexity and cannot be slowed by model loading or GPU contention.

---

## Layer 4: Cloud AI Guide

**Runtime:** Cloudflare Worker proxying to Anthropic and OpenAI APIs
**Cycle:** Every 5 seconds in protectionLoop
**Input:** JPEG frame (960px max width, 0.75 quality) plus COCO-SSD detection context
**Output:** Natural language description, parsed into structured hazard data

### Guide Mode

The website sends `mode='guide'` to the Cloudflare Worker, which triggers the `SYSTEM_PROMPT_GUIDE` prompt. This prompt instructs the AI to act as a sighted guide companion walking beside a blind person. The AI describes what is ahead, identifies obstacles, stairs (only if clearly visible), doors, floor conditions, general surroundings, and which direction is clear. Responses are limited to under 15 words.

### COCO-SSD Context

The request includes up to 5 high-confidence COCO-SSD detections formatted as `"person 6ft ahead, chair 3ft left"`. This context tells the AI what the local model already found, so the AI can focus on things the local model missed (stairs, floor conditions, signage, narrow passages).

### Racing Providers

The system sends the request to both Anthropic and OpenAI simultaneously via `Promise.any()`. The first response to arrive is used. This reduces latency and provides automatic failover if one provider is down.

### Hazard Parsing

The `parseAIResult` function searches the AI response text for hazard keywords:

| Pattern | Level | Key |
|---------|-------|-----|
| stair, step down, drop-off, ledge | DANGER | stairs |
| car/vehicle/truck approaching | DANGER | vehicle |
| wall, dead end, blocked, barrier | WARNING | wall |
| step up, curb, raised, bump | WARNING | step_up |
| wet, slippery, puddle, spill | WARNING | wet |
| narrow, tight gap, low ceiling | WARNING | narrow |
| door, doorway, entrance, exit | INFO | door |
| hazard, caution, obstacle | WARNING | hazard |
| path clear, no hazard, safe | CLEAR | (clears AI hazard) |

Results are spoken directly via `speakAlert` at priority 2 (warning) or priority 3 (danger). AI hazards persist with a time-to-live of 4 seconds for danger and 3 seconds for warnings.

### Backoff on Errors

When the Cloudflare Worker returns an error or the request fails, the system applies exponential backoff: 10 seconds, 20 seconds, 40 seconds, up to a maximum of 60 seconds. The backoff counter resets on any successful response. This prevents hammering a broken endpoint and wasting battery on failed network requests.

---

## Layer 5: BlindGuideNav Custom Model

**Runtime:** ONNX Runtime Web with the WebAssembly backend
**Model:** `BlindGuideNav.onnx`, a custom 55 class navigation focused detector exported from PyTorch
**Cycle:** Interleaved with COCO-SSD in the protectionLoop (200ms cycle)
**Inference time:** Roughly 80 to 150 ms per frame on a modern phone browser

### Why This Layer Exists

COCO-SSD is excellent at people, vehicles, and indoor furniture, but it does not know what a curb ramp is. The COCO dataset it was trained on does not contain navigation specific labels. BlindGuideNav fills this gap by providing detections for features that matter most to a blind walker: stairs (going up and going down as separate classes), curbs, crosswalks, doors (open and closed), railings, wet floors, traffic signals, and overhead obstacles. See [BlindGuideNav](../models/BlindGuideNav.md) for the full class list, the architecture, and the training details.

### Integration

The model loads through ONNX Runtime Web alongside COCO-SSD. Both detectors run inside the protection loop on the same camera frame. Their outputs merge into a single deduplicated list of detections before the announcement system picks which object to speak. The downstream announcement logic does not know or care which model produced a given detection. It only needs the class label, position, and distance estimate.

```javascript
const session = await ort.InferenceSession.create('models/BlindGuideNav.onnx', {
    executionProviders: ['wasm'],
    graphOptimizationLevel: 'all'
});
```

### Why ONNX Instead of TensorFlow.js

ONNX Runtime Web uses a single shared WebAssembly module that all loaded ONNX models run through. TensorFlow.js loads its own runtime in addition to the COCO-SSD model. Adding a TensorFlow.js conversion of BlindGuideNav on top of the existing COCO-SSD load would double the runtime memory cost. Routing BlindGuideNav through ONNX Runtime Web shares the runtime across both formats and keeps the per tab memory budget under iOS Safari's limit.

---

## Temporal Smoothing

To prevent flickering between states, the system uses temporal smoothing with asymmetric behavior:

- **Escalation is instant.** If any single frame detects a danger or warning, the system immediately escalates to that level. There is no delay or confirmation required for threats.
- **De-escalation requires confirmation.** The system requires 2 consecutive safe readings (`SAFE_CONFIRM_COUNT = 2`) before returning to the safe state. This prevents a single missed detection from briefly showing "Path Clear" when an obstacle is still present.

The `_threatHistory` array stores the last 5 raw threat readings. Only the most recent `SAFE_CONFIRM_COUNT` readings are checked for de-escalation. If all of them are safe, the system transitions to safe. Otherwise, it holds the previous threat level.
