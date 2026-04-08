# Detection System

## Overview

GuideDog Vision runs six detection layers simultaneously, each operating at a different frame rate and targeting a different aspect of the environment. The layers are designed to be complementary. LiDAR provides raw distance. YOLOv8n identifies common objects from the COCO dataset. BlindGuideNav identifies navigation specific features that COCO trained models miss (curbs, crosswalks, stairs, doors, railings, wet floors). ARKit mesh classifies architectural surfaces. DeepLabV3 catches large objects that the others miss. Together, these layers provide overlapping coverage so that obstacles are rarely missed entirely.

**Why this many layers.** Any single detection method has blind spots. LiDAR sees distance but does not know what an object is. Object detectors know what something is but cannot measure how far away it is without help. Mesh classification identifies architectural features (walls, doors) but does not detect movable objects. By stacking multiple methods that fail in different ways, the overall system has fewer scenarios where every layer simultaneously misses a hazard.

All detection runs on the device. No camera frames are sent to a server for detection. Cloud AI is used only for on demand scene descriptions, not for continuous detection.

## What Makes This Pipeline Non Trivial

The detection pipeline includes several engineering decisions that go beyond simply running models on frames:

- **20th percentile in the center, median on the sides.** Different statistical measures for different zones because the user cares about the closest thing in front of them but the average distance on the sides.
- **Top 25 percent and bottom 35 percent of the depth map are excluded.** Sky and floor would otherwise pull distance estimates in the wrong direction.
- **2 frame consecutive streak filter.** Eliminates ghost detections that show up for one frame and disappear, without adding meaningful latency for real objects.
- **`isDetecting` and `isSegmenting` ANE guards.** Prevent CoreML requests from piling up on the Apple Neural Engine, which would otherwise stall the camera pipeline.
- **60 degree forward cone for mesh classification.** Computed from the dot product of the camera forward vector and the direction to each mesh anchor. Stops the app from announcing walls that are behind the user.
- **DeepLabV3 deduplication against YOLO.** The segmentation layer suppresses any class that YOLO already announced. DeepLabV3 acts as a backup catcher, not a duplicate announcer.
- **Tier gating with cross tier wait windows.** Lower priority detections (a chair) wait several seconds after a higher priority detection (a person) so the user is not interrupted while navigating around the more urgent obstacle.
- **Approach speed detection.** A separate fast path that bypasses the normal streak filter for objects approaching at more than 0.8 m/s within 2.5 meters. This handles vehicles and cyclists where waiting two frames would be too slow.

Each of these is described in more detail in the layer sections below.

## Layer 1: LiDAR Depth Processing

**Rate:** Every 4 frames (~7.5 fps)

**Prerequisite:** Device must have LiDAR. ARSession tracking state must be `.normal`. The engine skips depth processing during SLAM initialization because depth readings are unreliable before the tracking system has stabilized.

**Process:**

1. Lock the depth map pixel buffer for read access.
2. Split the depth map into three vertical columns: left third, center third, right third.
3. Scan the middle 60% of the frame vertically (rows from 25% to 65% of the image height). The top 25% is excluded because it typically contains sky or ceiling. The bottom 35% is excluded because it contains floor readings that would pull distance values artificially low.
4. Sample every 6th pixel in both X and Y (stride of 6) to reduce computation.
5. Discard any reading below 0.03 meters (sensor noise floor) or above 5.0 meters (beyond useful range).
6. For the center zone, compute the 20th percentile of all valid samples. This biases toward the closest obstacle in the center, which is what the user will walk into.
7. For the left and right zones, compute the median. The median avoids floor and edge noise and gives a representative distance for each side.
8. Apply exponential moving average (EMA) smoothing with alpha = 0.4 to each zone. This smooths LiDAR noise while still responding quickly to genuine distance changes.
9. Feed the smoothed values into the RiskSolver for hysteresis-aware risk level determination.
10. Evaluate the progressive distance band system (see DISTANCE.md) and fire alerts if a new band is entered.
11. Send the smoothed distances to the JavaScript layer via `__onLiDARDepth` and to the haptic and spatial audio controllers.

## Layer 2: YOLOv8n Object Detection

**Rate:** Every 20 frames (~1.5 fps)

**Model:** YOLOv8n, compiled to CoreML format (`.mlmodelc`). Runs through Apple's Vision framework using `VNCoreMLRequest`, which automatically dispatches inference to the Apple Neural Engine on supported hardware.

**Confidence Threshold:** 0.7 minimum. This value was chosen after testing showed that 0.5 produced too many false positives, particularly shadows being classified as objects and posters being classified as people. At 0.7, the model reliably identifies real objects while filtering out visual noise.

**Ghost Detection Filter:** A 2-frame consecutive streak filter eliminates phantom detections. For each detected object class, the engine tracks how many consecutive frames it has appeared. Only objects that have been detected in at least 2 consecutive cycles pass through to the announcement system. Ghost detections (reflections, momentary misclassifications) typically appear for a single frame and then disappear, so this filter catches them without adding meaningful latency.

**ANE Guard:** An `isDetecting` boolean prevents a new Vision request from being submitted while a previous one is still running. Without this guard, queued CoreML requests pile up on the Apple Neural Engine, causing a pipeline stall that freezes the camera feed.

**Object Processing:**

1. Filter results to the relevant object set (tier 1, 2, and 3 classes).
2. Determine direction (left, center, right) based on the bounding box center X coordinate. Below 0.33 is left, above 0.67 is right, and everything between is ahead.
3. Estimate distance using size-based triangulation (see DISTANCE.md).
4. Sort by tier (tier 1 first) then by distance (closest first).
5. Track objects across frames for approach speed detection.
6. Select the single most important object to announce (see Smart Announcements below).

## Layer 3: ARKit Mesh Classification

**Rate:** Every 15 frames (~2 fps)

**Prerequisite:** Device must have LiDAR and support `sceneReconstruction(.meshWithClassification)`.

**Process:**

The MeshClassifier reads all `ARMeshAnchor` objects from the current AR frame. For each anchor:

1. Compute the distance and direction from the camera to the anchor position.
2. Filter to a forward-facing 60-degree cone. The dot product of the camera forward vector and the direction to the anchor must be greater than 0.5. This prevents the app from announcing walls behind the user.
3. Determine lateral direction using the dot product with the camera right vector. Below -0.3 is left, above 0.3 is right, and between is center.
4. Sample up to 200 faces from the mesh geometry to find the dominant surface classification.
5. Classify the anchor as one of: wall, door, window, seat, table, floor, ceiling, or none.

**Deduplication:** After collecting all hits, the classifier deduplicates by keeping only the closest hit for each unique (classification, direction) pair. This prevents the app from announcing "wall ahead, wall ahead, wall ahead" when multiple mesh anchors on the same wall are all visible.

**Announcement Rules:**

- Walls are announced at caution distance with distance in feet, and at danger distance with "Wall nearby."
- Doors are always announced (they represent navigation opportunities).
- Windows are announced only when closer than 1.0 meter ("Glass ahead"), because glass doors and glass walls are collision hazards.
- Seats and tables are announced at caution distance.

## Layer 4: DeepLabV3 Semantic Segmentation

**Rate:** Every 60 frames (~0.5 fps)

**Model:** DeepLabV3, compiled to CoreML format. This model segments the entire camera frame into 21 PASCAL VOC classes: background, aeroplane, bicycle, bird, boat, bottle, bus, car, cat, chair, cow, dining table, dog, horse, motorbike, person, potted plant, sheep, sofa, train, and TV monitor.

**Process:**

1. Run the model through Vision framework with `VNCoreMLRequest`.
2. Parse the output segmentation map. The output may be 3D or 4D depending on CoreML's handling of the batch dimension.
3. Sample every 8th pixel in both X and Y for speed.
4. Count class votes for left, center, and right zones.
5. Compute frame coverage for each detected class.

**Announcement Filter:** Only objects with more than 15% frame coverage are announced. This threshold ensures that only large, scene-dominating objects are reported. Small slivers of a class at the edge of the frame are ignored.

**YOLO Deduplication:** Before announcing, the segmenter checks whether YOLOv8n has already detected the same object class. If YOLO already announced "car ahead," DeepLabV3 will not repeat it. DeepLabV3 serves as a backup for objects that YOLO missed, not a duplicate announcement source.

**Announcement Priority:** One announcement per segmentation pass, spoken at detection priority (urgency 2.0).

## Layer 5: BlindGuideNav Custom Model

**Rate:** Every 20 frames (~1.5 fps), interleaved with YOLOv8n

**Model:** A custom CoreML model trained on 55 navigation specific classes. These classes are focused on objects and surfaces commonly encountered during pedestrian navigation, including curb ramps, crosswalks, traffic signals, stairs (with separate up and down classes), escalators, doors (open and closed), railings, wet floors, and overhead obstacles. See [BlindGuideNav](../models/BlindGuideNav.md) for the full class list and the architecture details.

**Why this layer exists.** YOLOv8n is excellent at people, vehicles, and indoor furniture, but it does not know what a curb ramp is. The COCO dataset it was trained on does not contain navigation specific labels. BlindGuideNav fills this gap by providing detections for the features that matter most to a blind walker. Both detectors run together and their results merge into a single deduplicated list before the announcement system picks which object to speak.

**Process:**

1. Run the model through Vision framework with `VNCoreMLRequest`, the same way YOLOv8n is dispatched.
2. Apply confidence threshold (0.5 to 0.7 depending on class) and non maximum suppression.
3. Translate detections into the same internal object format used by YOLOv8n results.
4. Merge with the YOLOv8n detection list. Where both detectors find the same object in the same location, the higher confidence detection wins.
5. Pass the merged list to the smart announcement system described below.

**Why merge instead of dedicate to specific cases.** Running the two detectors as a unified pipeline keeps the announcement logic simple. The downstream tier system (described below) does not need to know which model produced a given detection. It only needs the class label, position, and distance. Whether a "curb" detection came from BlindGuideNav and a "person" detection came from YOLOv8n is invisible to the rest of the engine.

## Smart Announcement System

All detection results feed into a unified announcement system that enforces several rules to prevent speech overload.

### Tier Priority

Objects are grouped into three tiers by navigation importance:

- **Tier 1 (highest priority):** person, car, truck, bus, motorcycle, bicycle. These are moving hazards that require immediate attention.
- **Tier 2:** chair, bench, dining table, couch. These are static obstacles commonly encountered indoors.
- **Tier 3:** fire hydrant, stop sign, parking meter, refrigerator, potted plant, bed, backpack, laptop, TV. These are useful context objects but less urgent.

### One Announcement Per Cycle

The engine selects exactly one object to announce per detection cycle. This is a deliberate design choice. When multiple objects are detected simultaneously and each generates a speech utterance, the utterances queue up in the speech synthesizer. By the time the second or third utterance plays, the user may have walked past those objects, making the announcements stale and confusing.

Instead, the engine picks the single highest-priority, closest object and announces only that one. On the next detection cycle (about 0.67 seconds later), it can pick a different object if the situation has changed.

### Tier Gating

Lower-tier objects are suppressed when a tier 1 object was announced recently. Tier 2 objects wait 3 seconds after the last tier 1 announcement. Tier 3 objects wait 5 seconds. This prevents a chair announcement from interrupting while the user is navigating around a person.

### Repetition Cooldowns

The same object in the same direction is not re-announced unless the distance has changed significantly or enough time has passed. For tier 1 objects, re-announcement requires either a 0.3-meter distance change within 1.5 seconds, or 4 seconds of elapsed time. For lower tiers, the thresholds are 1.0-meter distance change within 4 seconds, or 15 seconds of elapsed time.

### Approach Speed Detection

The engine tracks the position and distance of each detected object across frames. If a tier 1 object is approaching at more than 0.8 meters per second and is within 2.5 meters, the engine immediately announces "[Object] approaching fast" at danger priority. This handles the scenario of a car or cyclist moving toward the user.
