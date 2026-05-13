# Web Detection

## Overview

The website runs five detection layers concurrently. Each has different strengths, speeds, and failure modes. Stacking them means no single point of failure leaves the user unprotected.

## Pipeline tricks

A few things in this pipeline are worth calling out specifically.

The pixel variance wall check is pure JavaScript, no ML, under 5 ms. It detects flat surfaces by computing brightness variance and edge density across a 64 by 48 sample of the center frame. This is the safety net during the 3 to 5 seconds it takes COCO-SSD to download.

Asymmetric temporal smoothing. Escalation is instant (a single frame can trigger danger). De escalation requires 2 consecutive safe readings before relaxing. Being too cautious is fine. Being too late is dangerous.

Camera triangulation with a curated heights table. The system uses real pinhole camera math to estimate distance from bounding box height, with a hand built table of 24 known object heights. See [Distance](Distance.md).

Auto calibration of relative depth. Depth-Anything outputs unitless 0 to 255 values. The system bootstraps absolute distances by using triangulated detections as ground truth anchors. See [Distance](Distance.md).

Two ML detectors sharing one runtime. COCO-SSD (TensorFlow.js) and BlindGuideNav (ONNX Runtime Web) run on the same camera frames in the same protection loop. Their results merge into one deduplicated list before announcement.

Center vs sides depth deviation catches narrow obstacles (poles, signs, railings) that fill the center but not the periphery. A pure absolute threshold would miss these.

---

## Layer 1: COCO-SSD

**Runtime:** TensorFlow.js loaded via `<script>` tag
**Cycle:** every 200 ms in the protectionLoop
**Model:** COCO-SSD v2.2.3, pretrained on COCO (80 classes)

### Filtered object set

Of the 80 COCO classes, the system uses 19 navigation relevant ones:

- **Critical (vehicles):** car, bus, truck, motorcycle, bicycle
- **Obstacles:** person, chair, bench, couch, bed, dining table, refrigerator, potted plant, backpack, fire hydrant, stop sign, parking meter, laptop, tv

Detections below 0.7 confidence (`CONFIG.HIGH_CONFIDENCE`) are dropped. A false "person ahead" alert in an empty hallway erodes user trust fast.

### Distance

The full distance pipeline (known size triangulation, auto calibration of relative depth, approach rate detection, center vs sides analysis) is documented in [Distance](Distance.md). Short version: detected objects with known real world heights are converted to absolute distances through pinhole camera geometry, and those distances calibrate the depth model so unknown objects get distance estimates too.

### Position

Each detection is classified horizontally:
- **Left:** center X < 35 percent
- **Right:** center X > 65 percent
- **Ahead:** in between

An object is "in path" if its center X is between 25 and 75 percent AND its center Y is below 30 percent from the top (so not floating in the sky).

### Danger class

- **Critical:** vehicles
- **Obstacle:** other tracked objects
- **Low:** everything else

Distance zones:
- **Danger:** under 1.0 m
- **Warning:** under 2.0 m
- **Awareness:** under 4.0 m

---

## Layer 2: Depth-Anything

**Runtime:** Transformers.js v2 (`@xenova/transformers@2.17.2`), loaded as ES module
**Model:** `Xenova/depth-anything-small-hf`, quantized
**Cycle:** every 400 ms from protectionLoop
**Input:** 256x256 JPEG from video feed
**Output:** depth map with values 0 to 255 (higher = closer)

Three regions get sampled (center, left strip, right strip). Average values for each are stored in `state.depthHistory` as a rolling 6 frame window.

Relative depth values turn into absolute distances and into actionable threat levels through auto calibration and approach rate logic. Full pipeline in [Distance](Distance.md).

---

## Layer 3: Fast wall check (pixel variance)

**Runtime:** pure JavaScript
**Cycle:** every 50 ms in fastHazardLoop
**Input:** 64x48 canvas grabbed from the video feed
**Execution time:** under 5 ms

A wall close to the camera fills the frame with uniform color and few edges. Open space has texture variation, color gradients, and visible edges between objects.

The algorithm:

1. Grab a 64x48 frame from the video (reuse a persistent canvas to avoid allocation).
2. Sample the center strip: middle 50 percent width (pixels 16 to 48), middle 60 percent height (pixels 10 to 38).
3. Compute brightness per pixel: `R * 0.299 + G * 0.587 + B * 0.114`.
4. Compute brightness variance across all sampled pixels.
5. Count edges: adjacent pixels with brightness difference > 30.
6. Compute edge ratio: edge count divided by total sampled pixels.

### Thresholds

| Variance | Edge ratio | Result |
|----------|------------|--------|
| < 150 | < 6% | DANGER (wall detected) |
| < 350 | < 10% | WARNING (obstacle ahead) |
| above both | above both | no detection |

Typical values in testing:
- Wall at arm's length: variance 50 to 200, edge ratio under 0.05
- Open room: variance 500 to 2000+, edge ratio above 0.15
- Cluttered desk: variance 300 to 800, edge ratio 0.08 to 0.15

This isn't ML inference. It's statistics on pixel data. Runs in constant time regardless of scene complexity. Can't be slowed by model loading or GPU contention.

---

## Layer 4: Cloud AI Guide

**Runtime:** Cloudflare Worker at `guidedog.kpremks.workers.dev` proxying to Anthropic and OpenAI
**Cycle:** every 5 seconds in protectionLoop
**Input:** JPEG frame (960px max width, 0.75 quality) plus COCO-SSD detection context
**Output:** natural language description, parsed into structured hazard data

### Guide mode

The website sends `mode='guide'`, which triggers the `SYSTEM_PROMPT_GUIDE`. This prompt instructs the AI to act as a sighted guide companion walking beside a blind person. The AI describes what is ahead, obstacles, stairs (only if clearly visible), doors, floor conditions, surroundings, and which direction is clear. Responses are limited to under 15 words.

### COCO-SSD context

The request includes up to 5 high confidence COCO-SSD detections formatted like `"person 6ft ahead, chair 3ft left"`. This tells the AI what the local model already found, so the AI focuses on things the local model missed (stairs, floor conditions, signage, narrow passages).

### Racing providers

Both Anthropic and OpenAI receive the same request via `Promise.any()`. First response wins. Reduces latency and provides automatic failover if one provider is slow.

### Hazard parsing

`parseAIResult` searches the AI response for hazard keywords:

| Pattern | Level | Key |
|---------|-------|-----|
| stair, step down, drop off, ledge | DANGER | stairs |
| car/vehicle/truck approaching | DANGER | vehicle |
| wall, dead end, blocked, barrier | WARNING | wall |
| step up, curb, raised, bump | WARNING | step_up |
| wet, slippery, puddle, spill | WARNING | wet |
| narrow, tight gap, low ceiling | WARNING | narrow |
| door, doorway, entrance, exit | INFO | door |
| hazard, caution, obstacle | WARNING | hazard |
| path clear, no hazard, safe | CLEAR | (clears AI hazard) |

Results are spoken through `speakAlert` at priority 2 (warning) or 3 (danger). AI hazards persist with a TTL of 4 seconds for danger, 3 seconds for warnings.

### Backoff

When the Worker errors or the request fails, exponential backoff kicks in: 10 s, 20 s, 40 s, up to 60 s max. The counter resets on any successful response. Prevents hammering a broken endpoint.

---

## Layer 5: BlindGuideNav

**Runtime:** ONNX Runtime Web with WebAssembly backend
**Model:** `BlindGuideNav.onnx`, custom 55 class navigation focused detector exported from PyTorch
**Cycle:** interleaved with COCO-SSD in protectionLoop (200 ms)
**Inference time:** 80 to 150 ms per frame on a modern phone browser

### Why it exists

COCO-SSD is great at people, vehicles, and indoor furniture, but it doesn't know what a curb ramp is. COCO doesn't have navigation labels. BlindGuideNav fills that gap with stairs (up and down as separate classes), curbs, crosswalks, doors (open and closed), railings, wet floors, traffic signals, and overhead obstacles. Class list and training in [BlindGuideNav](../CustomModel/BlindGuideNav.md).

### Integration

The model loads through ONNX Runtime Web alongside COCO-SSD. Both run on the same camera frame. Their outputs merge into one deduplicated list before announcement picks what to speak. The downstream logic doesn't care which model produced a detection. It only needs class label, position, and distance.

```javascript
const session = await ort.InferenceSession.create('models/BlindGuideNav.onnx', {
    executionProviders: ['wasm'],
    graphOptimizationLevel: 'all'
});
```

### Why ONNX, not TensorFlow.js

ONNX Runtime Web uses one shared WebAssembly module for all loaded ONNX models. TensorFlow.js loads its own runtime in addition to the COCO-SSD model. Adding a TF.js conversion of BlindGuideNav on top of COCO-SSD would double the runtime memory cost. ONNX shares the runtime and keeps the per tab memory budget under iOS Safari's limit.

---

## Temporal smoothing

Temporal smoothing means using more than one frame's information before deciding what to show. Without it, every frame's detection result would flash on screen, and any single bad frame would cause visible flicker.

The smoothing is asymmetric:

- **Escalation is instant.** Any single frame at danger or warning level immediately escalates. No confirmation needed. Being slow to warn is more dangerous than being too cautious.
- **De escalation needs confirmation.** Two consecutive safe readings required before returning to safe. Prevents a single missed detection from briefly showing "Path Clear" while an obstacle is still present.

The `_threatHistory` array stores the last 5 raw threat readings. Only the most recent `SAFE_CONFIRM_COUNT` readings are checked for de escalation. If all of them are safe, the system transitions to safe. Otherwise, the previous threat level holds.
