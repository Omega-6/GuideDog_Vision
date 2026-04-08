# Distance Estimation and Alert Bands

## Why This Approach Is Non Trivial

Most navigation apps that use LiDAR just read the depth value at the bounding box of the detected object and call it the distance. GuideDog Vision does not do that. The reason is coordinate space alignment: the camera image and the LiDAR depth map do not share a 1 to 1 pixel correspondence. They have different resolutions, slightly different fields of view, and the projection between them involves interpolation that introduces errors at the edges of the frame. During testing, sampling the depth map at the bounding box of an object would sometimes return the distance to the wall behind the object instead of to the object itself.

To avoid this, the engine uses three independent distance signals that get cross checked:

1. **Pinhole camera triangulation** from the size of the detected bounding box and the known real world height of the object.
2. **LiDAR zone distances** computed by statistical aggregation over thirds of the frame, with separate aggregation methods for the center (closest in path) and the sides (representative).
3. **A cross check rule** that averages the two when they agree and prefers triangulation when they disagree.

A separate progressive band system on top of all this prevents the user from being told "stop" repeatedly when LiDAR readings oscillate near a threshold.

## Progressive Distance Band System

GuideDog Vision uses a 4-band progressive alert system that fires once when the user enters each band. This design avoids continuous announcements (which become white noise) while ensuring the user is warned at each stage of approach.

### Band Definitions

| Band        | Entry Threshold | Behavior |
|------------|----------------|----------|
| Approaching | Less than 3.0m | Speech: "Something ahead" at urgency 3.0. Fires once on entry. |
| Caution     | Less than 2.0m | Speech: "Heads up" at urgency 4.0. Fires once on entry. |
| Danger      | Less than 1.0m | Speech: "Stop, something close" at urgency 5.0. Fires once on entry. |
| Critical    | Less than 0.4m | Speech: "Stop" at urgency 5.0. Fires on entry, then repeats every 3 seconds as long as the user remains in the critical zone. |

The bands escalate in a single direction. If the user walks from safe (beyond 3.0m) toward a wall, they will hear "Something ahead," then "Heads up," then "Stop, something close," then "Stop" in sequence. Each announcement fires exactly once at its threshold (except critical, which repeats).

### Band Reset and Hysteresis

LiDAR depth readings are not perfectly stable. A reading at 1.01 meters might bounce to 0.99 meters and back on successive frames. Without hysteresis, this would cause the app to enter and exit the danger band repeatedly, producing a stream of "Stop, something close" announcements.

To prevent this oscillation, the exit threshold for each band is higher than the entry threshold:

| Band     | Entry Threshold | Exit Threshold |
|---------|----------------|----------------|
| Critical | 0.4m           | 0.6m           |
| Danger   | 1.0m           | 1.3m           |
| Caution  | 2.0m           | 2.4m           |
| Approaching | 3.0m        | 3.3m           |

The user enters the danger band when the center distance drops below 1.0m. But the band does not clear until the distance rises above 1.3m. This 0.3m hysteresis window absorbs normal LiDAR fluctuation and prevents repeated alerts at boundary distances.

The RiskSolver implements the same hysteresis pattern for the risk levels used by haptics and spatial audio. The risk level escalates immediately when a threshold is crossed, but de-escalates only when the distance passes the exit threshold.

### Scan Suppression

When a cloud AI scan is active (triggered by the user or by a scene change), the `isScanActive` flag suppresses distance band speech for 5 seconds. This prevents "Heads up" from interrupting the AI scene description. Haptics and spatial audio continue during scans because they use a different output channel.

## Size-Based Triangulation

For objects detected by YOLOv8n, the engine estimates distance using the pinhole camera model:

```
distance = (realHeight * focalLength) / bboxPixelHeight
```

### Camera Intrinsics

**Why this matters.** Most phone navigation apps hardcode a single FOV value (commonly 55 or 60 degrees) and use it for every device. This is convenient but incorrect. Different iPhone models have different rear camera lenses with different fields of view, and even within a single model the active lens can switch (wide vs ultrawide vs telephoto) depending on what ARKit selects. A hardcoded FOV introduces a systematic distance error that varies by device.

GuideDog Vision reads the real focal length from `ARFrame.camera.intrinsics` on every frame. This is the actual vertical focal length in pixels for the current camera configuration. The triangulation formula then becomes exact for the specific lens and sensor combination of each iPhone, instead of being approximate for some imaginary average phone.

### Known Heights Table

The engine maintains a table of known real-world heights for YOLO classes:

| Object       | Height (meters) |
|-------------|----------------|
| Person       | 1.7            |
| Car          | 1.5            |
| Bus          | 3.0            |
| Truck        | 3.0            |
| Motorcycle   | 1.1            |
| Bicycle      | 1.0            |
| Chair        | 0.9            |
| Bench        | 0.85           |
| Couch        | 0.85           |
| Bed          | 0.6            |
| Dining Table | 0.75           |
| Refrigerator | 1.7            |
| Fire Hydrant | 0.6            |
| Stop Sign    | 2.1            |
| Parking Meter| 1.2            |
| Potted Plant | 0.5            |
| Backpack     | 0.5            |
| Laptop       | 0.3            |
| TV           | 0.5            |

Objects not in this table do not receive size-based distance estimates and fall back to zone-based LiDAR distance.

### Bounding Box Conversion

The bounding box from Vision is normalized to 0.0 through 1.0. The engine converts the bounding box height to pixels by multiplying by the camera image resolution height. A minimum bounding box height of 10 pixels is enforced. Below that, the bounding box is too small for a reliable estimate.

The resulting distance is clamped to 0.3 through 15.0 meters to prevent extreme outlier values from a tiny bounding box or a very large one.

## Cross-Checking with LiDAR

When both size-based and LiDAR zone distances are available, the engine cross-checks them:

1. If both agree within 1.0 meter, the engine averages them. This produces the most accurate estimate by combining per-object geometry with direct depth measurement.
2. If they disagree by more than 1.0 meter, the engine trusts the size-based estimate. The reasoning is that size-based triangulation measures the specific object, while LiDAR zone distance is an average over a third of the frame. The zone might include a wall 4 meters away while the object is 1.5 meters away, making the zone average misleading for that specific object.

## Zone-Based LiDAR Fallback

When size-based triangulation is not available (because the object class has no known height entry), the engine falls back to the LiDAR zone distance for the appropriate direction:

- Objects on the left third of the frame use the left zone distance.
- Objects in the center use the center zone distance.
- Objects on the right use the right zone distance.

If LiDAR is not available at all (no LiDAR hardware, or tracking state is not normal), the fallback distance is 5.0 meters (safe).

### Zone Processing

Each zone is processed from the depth map as described in DETECTION.md. The key distinction is the statistical measure used:

- **Center zone: 20th percentile.** The center represents the user's walking path. The 20th percentile biases toward the closest obstacle in that zone, which is the one the user is most likely to walk into.
- **Left and right zones: Median.** The sides use the median to provide a representative distance. The 20th percentile would be too aggressive for sides, where the closest reading might be the user's own arm or the edge of the phone.

All three zones are smoothed with EMA (alpha 0.4) and have a minimum threshold of 0.03 meters to reject sensor noise.
