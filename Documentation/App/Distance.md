# Distance and Alert Bands

## Why this is more than "read the depth value"

Most LiDAR navigation apps just sample the depth map at the bounding box of a detected object and call it the distance. This app doesn't, because the camera image and the LiDAR depth map don't share a 1 to 1 pixel correspondence. They have different resolutions, slightly different fields of view, and projecting between them involves interpolation that drifts at the edges of the frame. During testing, sampling the depth map at an object's bounding box would sometimes return the distance to the wall behind the object instead of the object itself.

So the engine uses three independent distance signals and cross checks them:

1. Pinhole camera triangulation from the bounding box size and the known real world height of the object.
2. LiDAR zone distances computed by statistical aggregation over thirds of the frame, with different statistics for the center (closest in path) and the sides (representative).
3. A cross check that averages the two when they agree and prefers triangulation when they don't.

A separate progressive band system sits on top of all this to keep the user from being told "stop" repeatedly when LiDAR readings oscillate near a threshold.

## Progressive distance bands

The engine uses a 4 band progressive system that fires once when you enter each band. Continuous announcements become white noise. One announcement per band makes each one mean something.

### Bands

| Band | Entry | Speech |
|---|---|---|
| Approaching | < 3.0 m | "Something ahead" at urgency 3.0. Fires once on entry. |
| Caution | < 2.0 m | "Heads up" at urgency 4.0. Fires once on entry. |
| Danger | < 1.0 m | "Stop, something close" at urgency 5.0. Fires once on entry. |
| Critical | < 0.4 m | "Stop" at urgency 5.0. Fires on entry, repeats every 3 seconds while you remain inside. |

Bands escalate in one direction. If you walk from safe toward a wall, you hear "Something ahead" then "Heads up" then "Stop, something close" then "Stop." Each fires once at its threshold except critical.

When wall inference identifies a featureless wall, the band escalation uses "Wall ahead" instead of "Heads up" or "Something ahead." Same band logic, different wording.

### Hysteresis

LiDAR readings are noisy. A reading at 1.01 m might bounce to 0.99 m and back. Without hysteresis, the app would enter and exit the danger band repeatedly, producing a stream of "Stop, something close" announcements.

So each band has a different exit threshold:

| Band | Entry | Exit |
|---|---|---|
| Critical | 0.4 m | 0.6 m |
| Danger | 1.0 m | 1.1 m |
| Caution | 2.0 m | 2.2 m |
| Approaching | 3.0 m | 3.3 m |

You enter danger at 1.0 m. The band doesn't clear until you pass 1.1 m. The gap absorbs LiDAR fluctuation. The RiskSolver applies the same hysteresis pattern to the risk levels used by haptics and spatial audio.

### Scan suppression

When a cloud AI scan is active, the `isScanActive` flag suppresses distance band speech for 5 seconds so "Heads up" doesn't interrupt the scene description. Haptics and spatial audio continue because they use different output channels.

## Size based triangulation

For objects detected by YOLOv8n or BlindGuideNav, the engine estimates distance through the pinhole camera model:

```
distance = (realHeight * focalLength) / bboxPixelHeight
```

### Camera intrinsics

Most phone navigation apps hardcode a single FOV value (usually 55 or 60 degrees) for every device. That's convenient but wrong. Different iPhone models have different lenses with different fields of view, and even within one model the active lens can switch (wide vs ultrawide vs telephoto) depending on what ARKit picks.

The engine reads the real focal length from `ARFrame.camera.intrinsics` on every frame. That's the actual vertical focal length in pixels for the current camera configuration. The formula is then exact for the specific lens and sensor combination of each iPhone, instead of approximate for an imaginary average phone.

### Known heights

The engine maintains a table of known real world heights:

| Object | Height (m) |
|---|---|
| Person | 1.7 |
| Car | 1.5 |
| Bus | 3.0 |
| Truck | 3.0 |
| Motorcycle | 1.1 |
| Bicycle | 1.0 |
| Chair | 0.9 |
| Bench | 0.85 |
| Couch | 0.85 |
| Bed | 0.6 |
| Dining Table | 0.75 |
| Refrigerator | 1.7 |
| Fire Hydrant | 0.6 |
| Stop Sign | 2.1 |
| Parking Meter | 1.2 |
| Potted Plant | 0.5 |
| Backpack | 0.5 |
| Laptop | 0.3 |
| TV | 0.5 |

Objects not in this table fall back to zone based LiDAR distance.

### Bounding box conversion

The bounding box from Vision is normalized 0.0 to 1.0. The engine converts it to pixels by multiplying by the camera image resolution height. A minimum bbox height of 10 pixels is enforced. Below that, the bbox is too small for a reliable estimate.

The distance is clamped to 0.3 to 15.0 m to prevent extreme outliers from tiny or huge bboxes.

## Cross check with LiDAR

When both size based and LiDAR zone distances are available, the engine cross checks them:

If they agree within 1.0 m, the engine averages them. That gives the most accurate estimate by combining per object geometry with direct depth measurement.

If they disagree by more than 1.0 m, the engine trusts the size based estimate. Size triangulation measures the specific object. LiDAR zone is an average over a third of the frame. The zone might include a wall 4 m away while the object is 1.5 m away, which makes the zone average misleading.

## Zone based LiDAR fallback

When size triangulation isn't available (the class has no known height), the engine falls back to the LiDAR zone for the object's direction:

- Objects on the left third use the left zone distance.
- Center objects use the center zone distance.
- Right objects use the right zone distance.

If LiDAR is unavailable (no hardware, or tracking state isn't normal and the wall inference isn't firing), the fallback distance is 5.0 m (safe).

On non LiDAR iPhones, Depth-Anything fills the gap. The same band system fires, but speech drops the "feet" suffix because Depth-Anything distances are estimates, not direct measurements.

### Zone processing

Each zone is processed from the depth map as described in [Detection](Detection.md). The statistical measure matters:

- **Center: 20th percentile.** The center is the walking path. Biasing toward the closest obstacle in that zone tells you what you're about to walk into.
- **Left and right: median.** Sides need a representative distance. The 20th percentile would be too aggressive (might pick up the user's own arm or the edge of the phone).

All three zones are smoothed with EMA at alpha 0.4 and have a minimum threshold of 0.03 m to reject sensor noise.
