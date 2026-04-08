# GuideDog Vision: Detection System

## Overview

The PWA uses four detection layers that run concurrently. Each layer has different strengths, speeds, and failure modes. Together, they provide redundant coverage so that no single point of failure leaves the user unprotected.

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

### Distance Estimation via Known-Object Triangulation

When COCO-SSD detects an object with a known real-world height, the system estimates distance using camera geometry:

```
distance = (realHeight * imageHeight) / (2 * bboxHeight * tan(FOV/2))
```

Where:
- `realHeight` is the known physical height of the object in meters
- `imageHeight` is the video frame height in pixels
- `bboxHeight` is the bounding box height in pixels
- `FOV` is the camera's vertical field of view

**Known Heights Table (meters):**

| Object | Height | Object | Height |
|--------|--------|--------|--------|
| person | 1.7 | car | 1.5 |
| chair | 0.9 | couch | 0.85 |
| bus | 3.0 | truck | 3.0 |
| motorcycle | 1.1 | bicycle | 1.0 |
| refrigerator | 1.7 | stop sign | 2.1 |
| parking meter | 1.2 | bench | 0.85 |
| bed | 0.6 | dining table | 0.75 |
| fire hydrant | 0.6 | backpack | 0.5 |
| potted plant | 0.5 | dog | 0.5 |
| cat | 0.3 | horse | 1.6 |
| suitcase | 0.7 | sports ball | 0.22 |
| skateboard | 0.1 | toilet | 0.4 |

The camera FOV is assumed to be 55 degrees, which is typical for most phone rear cameras. This is converted to radians internally. The `getCameraFOV()` function returns this value.

Distance results are clamped between 0.3 meters and 8.0 meters. Objects closer than 0.3 meters are likely camera artifacts. Objects beyond 8 meters are too far to matter for pedestrian navigation.

### Fallback for Unknown Objects

When an object does not have a known height (not in the table above), the system falls back to a bounding box size ratio table:

| Bbox size ratio | Estimated distance |
|-----------------|-------------------|
| > 60% of frame | 0.5m |
| > 45% of frame | 1.0m |
| > 30% of frame | 1.5m |
| > 20% of frame | 2.0m |
| > 10% of frame | 3.0m |
| smaller | 4.0m |

This is a rough approximation. The triangulation method is significantly more accurate when available.

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

The model produces relative depth values, not absolute distances. A value of 200 means "closer than something at 100" but does not directly indicate meters. The system extracts three regions from the depth map:

- **Center strip:** 30% to 70% of frame width, 15% to 85% of frame height
- **Left strip:** less than 22% of frame width
- **Right strip:** greater than 78% of frame width

Average depth values for each region are stored in `state.depthHistory` as a rolling window of the last 6 readings.

### computeDepthHazard Logic

The function checks several conditions in order:

**1. Approach Rate (works without calibration)**

If depth values have been rising consistently across 4 or more frames, something is getting closer. Each consecutive frame must show an increase of at least 1 unit, and the average rate must exceed a threshold:
- Average rate > 15 per frame: DANGER ("Approaching fast")
- Average rate > 8 per frame: WARNING ("Something getting closer")

**2. Calibrated Distance (when available)**

If auto-calibration has been performed (see below), raw depth values are converted to meters:
- Less than 1.0 meter: DANGER
- Less than 1.8 meters: DANGER
- Less than 3.0 meters: WARNING

**3. Uncalibrated Fallback (raw values)**

When no calibration exists, raw center values are compared against empirical thresholds:
- Center value > 110: DANGER ("Wall/obstacle, close ahead")
- Center value > 85: WARNING ("Obstacle ahead")

Additionally, center deviation from the scene average is checked:
- Center ratio minus side average > 0.35: DANGER ("Obstacle directly ahead")
- Center ratio minus side average > 0.20: WARNING ("Obstacle in path")

### Auto-Calibration from COCO-SSD

When COCO-SSD detects a known-size object in the "ahead" position with at least 0.7 confidence, and the triangulated distance is between 0.5 and 5.0 meters, the system records a calibration point mapping the current center depth value to the estimated real distance.

Calibration uses exponential moving average (alpha = 0.3) to blend new readings with the existing calibration, preventing single-frame outliers from corrupting the mapping.

The conversion formula uses the inverse relationship between depth value and distance:
```
distance = (calibration_depth * calibration_meters) / current_depth
```

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

### BlindGuideNav (Future)

A custom 55-class object detection model called BlindGuideNav exists in the project's model directory. It was trained specifically for navigation-relevant objects. It currently exists as a PyTorch model and requires ONNX conversion before it can run in the browser via Transformers.js or ONNX Runtime Web. Once converted, it would replace COCO-SSD and provide significantly better coverage of navigation-specific objects.

---

## Temporal Smoothing

To prevent flickering between states, the system uses temporal smoothing with asymmetric behavior:

- **Escalation is instant.** If any single frame detects a danger or warning, the system immediately escalates to that level. There is no delay or confirmation required for threats.
- **De-escalation requires confirmation.** The system requires 2 consecutive safe readings (`SAFE_CONFIRM_COUNT = 2`) before returning to the safe state. This prevents a single missed detection from briefly showing "Path Clear" when an obstacle is still present.

The `_threatHistory` array stores the last 5 raw threat readings. Only the most recent `SAFE_CONFIRM_COUNT` readings are checked for de-escalation. If all of them are safe, the system transitions to safe. Otherwise, it holds the previous threat level.
