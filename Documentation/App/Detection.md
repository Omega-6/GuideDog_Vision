# Detection

## Overview

The app runs six detection layers at once, each at a different frame rate and each targeting a different aspect of the environment. LiDAR provides raw distance. YOLOv8n recognizes 80 COCO classes. BlindGuideNav (the custom model built for this project) recognizes 55 navigation specific classes that COCO trained models miss (curbs, crosswalks, stairs, doors, railings, wet floors). ARKit mesh classifies architectural surfaces. DeepLabV3 catches large objects everything else missed. The wall inference layer fires when zone depths are uniform and no center object detection has hit recently.

The point of stacking these is that they fail in different ways. Any single method has blind spots. LiDAR sees distance but doesn't know what an object is. Object detectors know what something is but cannot measure how far it is without help. Mesh classification handles architectural features but misses movable objects. Layering them means very few scenarios where every layer misses the same hazard.

All detection runs on device. No frames are sent to a server for detection. Cloud AI is used only for on demand scene descriptions.

## Pipeline tricks

A few things in this pipeline are worth calling out specifically.

Different statistics for different zones. The center uses the 20th percentile of depth samples (biases toward the closest thing in the user's walking path). Left and right use the median (representative distance for the side).

Top 25 percent and bottom 35 percent of the depth map are excluded. Sky and floor would otherwise pull distance estimates the wrong way.

3 frame consecutive streak filter. Eliminates ghost detections that show up for one frame and disappear, without adding meaningful latency for real objects.

`isDetecting` and `isSegmenting` flags prevent CoreML requests piling up on the Apple Neural Engine, which would otherwise stall the camera pipeline.

60 degree forward cone for mesh classification. Computed from the dot product of the camera forward vector and the direction to each mesh anchor. Stops the app from announcing walls behind the user. The mesh range was extended to 6 meters (it was 4) so walls get caught earlier.

DeepLabV3 dedup against YOLO. If YOLO already announced a class, the segmenter suppresses it. DeepLabV3 is the backup catcher, not a duplicate announcer.

Tier gating with cross tier wait windows. Lower priority detections (a chair) wait several seconds after a higher priority detection (a person) so the user is not interrupted while navigating around the more urgent one.

Approach speed detection. A fast path that bypasses the streak filter for objects approaching at more than 0.8 m/s within 2.5 meters. Vehicles and cyclists need this because waiting 3 frames would be too slow.

VNDetectHumanRectanglesRequest cross check. Every YOLO "person" detection has to also match an Apple human rectangle in the same area. If they don't agree, the detection is dropped. This kills the phantom person announcements from posters, mannequins, and pictures.

## Layer 1: LiDAR Depth

**Rate:** every 4 frames (~7.5 fps)

**Prerequisite:** Device must have LiDAR. ARSession tracking state is normally `.normal`, but depth still processes during `.limited(.insufficientFeatures)` so featureless walls don't break the system. The engine skips depth processing for the first second or two after launch while SLAM is still settling.

**Process:**

1. Lock the depth map pixel buffer for read access.
2. Split into three vertical columns: left, center, right thirds.
3. Scan the middle 60 percent of the frame vertically (rows 25 percent to 65 percent). Top is sky or ceiling, bottom is floor.
4. Sample every 6th pixel in both X and Y.
5. Discard readings below 0.03 m (sensor noise floor) or above 5.0 m (beyond useful range).
6. Center zone: 20th percentile. Biases toward the closest obstacle in the walking path.
7. Left and right zones: median. Representative without being thrown by single bad readings.
8. Smooth each zone with an exponential moving average at alpha 0.4. New reading counts 40 percent, previous smoothed value retains 60 percent. Tracks real changes within a few frames but rejects single frame spikes.
9. Feed the smoothed values into the RiskSolver, which uses hysteresis to prevent flickering near a band boundary.
10. Evaluate progressive distance bands ([Distance](Distance.md)) and fire alerts on band entry.
11. Send distances to JavaScript via `__onLiDARDepth` and to the haptic and spatial audio controllers.

## Layer 2: YOLOv8n

**Rate:** every 10 frames (~3 fps)

**Model:** YOLOv8n compiled to CoreML (`.mlmodelc`). Runs through `VNCoreMLRequest`, which dispatches to the Apple Neural Engine on supported hardware.

**Confidence threshold:** 0.75 default. Class specific overrides where the class is prone to false positives: refrigerator 0.88, tv 0.90, chair 0.90, bed 0.85, dining table 0.85.

**Ghost filter:** 3 consecutive cycles required before announcement. Phantom detections rarely survive that long. The cost is about a second of delay for a new object, which is fine for stationary obstacles. Fast moving threats bypass the filter through approach speed detection.

**ANE guard:** `isDetecting` boolean prevents a new Vision request from being submitted while a previous one is still running.

**Person validation:** Every YOLO "person" detection runs through `VNDetectHumanRectanglesRequest` in the same frame. If Apple's human detector doesn't agree that there's a human in the same region, the detection is dropped. This eliminates the most common false positive (posters, photos, mannequins).

**Per detection processing:**

1. Filter to the relevant object set (tier 1, 2, 3 classes).
2. Determine direction (left, center, right) from the bounding box center X. Below 0.33 is left, above 0.67 is right, between is ahead.
3. Estimate distance with size based triangulation ([Distance](Distance.md)).
4. Sort by tier first, then by distance.
5. Track across frames for approach speed detection.
6. Pick one object to announce.

## Layer 3: ARKit Mesh Classification

**Rate:** every 15 frames (~2 fps)

**Prerequisite:** Device has LiDAR and supports `sceneReconstruction(.meshWithClassification)`.

**Range:** 6 meters (extended from the previous 4 m so walls get caught earlier).

**Process:**

MeshClassifier reads all `ARMeshAnchor` objects from the current AR frame. For each anchor:

1. Compute distance and direction from the camera to the anchor position.
2. Filter to a forward facing 60 degree cone (dot product of camera forward vector with anchor direction > 0.5).
3. Determine lateral direction using the dot product with the camera right vector. Below -0.3 is left, above 0.3 is right, between is center.
4. Sample up to 200 mesh faces to find the dominant surface classification.
5. Classify as one of: wall, door, window, seat, table, floor, ceiling, none.

A `closestWall` accessor surfaces the nearest wall regardless of direction zone, which powers the "Wall nearby" announcements.

**Dedup:** Keep only the closest hit for each unique (classification, direction) pair. Stops the app from saying "wall ahead, wall ahead, wall ahead" when multiple mesh anchors on the same wall are all in view.

**Announcement rules:**

- Walls at caution distance with feet, danger distance with "Wall nearby."
- Doors always (navigation opportunity).
- Windows only when closer than 1.0 m ("Glass ahead"), because glass doors and walls are collision hazards.
- Seats and tables at caution distance.

## Layer 4: DeepLabV3 Segmentation

**Rate:** every 60 frames (~0.5 fps)

**Model:** DeepLabV3 compiled to CoreML. Segments the frame into 21 PASCAL VOC classes (background, person, car, chair, dining table, sofa, TV, etc.).

**Process:**

1. Run through Vision framework with `VNCoreMLRequest`.
2. Parse the output segmentation map.
3. Sample every 8th pixel.
4. Count class votes for left, center, right zones.
5. Compute frame coverage for each detected class.

**Filter:** Only objects covering more than 15 percent of the frame are announced. Small slivers at the edges are ignored.

**YOLO dedup:** If YOLO already announced the same class, DeepLabV3 stays silent. It's the backup catcher.

**Priority:** One announcement per pass, at detection priority (urgency 2.0).

## Layer 5: BlindGuideNav

**Rate:** every 20 frames (~1.5 fps), interleaved with YOLO

**Model:** custom 55 class CoreML model. Trained on navigation specific classes including curb ramps, crosswalks, traffic signals, stairs (up and down as separate classes), escalators, doors (open and closed), railings, wet floors, and overhead obstacles. Full class list and training notes in [BlindGuideNav](../CustomModel/BlindGuideNav.md).

**Why it exists:** YOLOv8n is great at people, vehicles, and indoor furniture, but the COCO dataset it was trained on doesn't have navigation labels. BlindGuideNav fills that. Both detectors run together and their results merge into one deduplicated list before announcement picks what to speak.

**Process:**

1. Run through Vision with `VNCoreMLRequest`, same as YOLO.
2. Apply per class confidence thresholds (0.5 to 0.7) and non maximum suppression.
3. Translate detections into the same internal object format YOLO uses.
4. Merge with the YOLO list. Where both detectors find the same object in the same place, the higher confidence one wins.
5. Pass the merged list to the announcement system.

The downstream tier system doesn't care which model produced a given detection. It only needs the class label, position, and distance.

## Wall inference

The hardest indoor failure mode is a blank painted wall. ARKit's mesh classifier needs visual features to track. A flat wall in good lighting has very few, so the tracking state drops to `.limited(.insufficientFeatures)` and the mesh classifier stops returning useful data.

The wall inference layer handles this. When the left, center, and right depth zones all read similar distances (depth map is uniform) AND no object detection has hit in the center recently, the band escalation speech says "Wall ahead" instead of "Heads up" or "Something ahead."

The `announceWallHit()` path has three tiers by distance:
- Under 3 m: "Wall ahead"
- Under 2 m: "Wall, X feet"
- Under 1 m: "Wall nearby"

Depth processing now keeps running during `.limited(.insufficientFeatures)`, which is the change that lets this inference actually fire when ARKit's tracking degrades.

## Announcement system

All detections feed into a unified system that enforces several rules to prevent speech overload.

### Tiers

- **Tier 1 (highest):** person, car, truck, bus, motorcycle, bicycle. Moving hazards, immediate attention.
- **Tier 2:** chair, bench, dining table, couch. Static indoor obstacles.
- **Tier 3:** fire hydrant, stop sign, parking meter, refrigerator, potted plant, bed, backpack, laptop, TV. Context objects, less urgent.

### One announcement per cycle

The engine picks exactly one object to announce per cycle. The reason is staleness. If you queue three announcements, by the time the third one plays the user has walked past those objects. Picking one keeps every announcement current. The next cycle (about 0.67 seconds later) can pick a different object.

### Tier gating

Lower tier objects are suppressed when a tier 1 object was announced recently. Tier 2 waits 3 seconds after the last tier 1 announcement. Tier 3 waits 5 seconds. Stops a chair announcement from interrupting while you're navigating around a person.

### Repetition cooldowns

The same object in the same direction does not re announce unless distance has changed significantly or enough time has passed. For tier 1: 0.3 m distance change within 1.5 seconds, or 4 seconds elapsed. For lower tiers: 1.0 m distance change within 4 seconds, or 15 seconds elapsed.

### Approach speed

The engine tracks each detected object's position and distance across frames. If a tier 1 object is approaching at more than 0.8 m/s and is within 2.5 m, the engine immediately announces "[Object] approaching fast" at danger priority. This handles cars and cyclists where waiting for the streak filter would be too slow.
