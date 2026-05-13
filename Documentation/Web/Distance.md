# Web Distance

## The problem

The iOS app has LiDAR. It measures distance in centimeters, in real time, without any inference. The website doesn't get any of that. Browsers can't access LiDAR even on iPhones that have the hardware. The only inputs available are the camera image and a depth model that produces relative depth values, not meters.

This forces the web side to do real distance math. The website cannot just read a sensor. It has to reconstruct distance from geometry and from the rate of change of pixel values. Four techniques work together to fill the gap.

## Layer 1: Known object triangulation

When COCO-SSD or BlindGuideNav detects an object whose real world height is in the table (a person, a car, a chair), the website estimates distance through the pinhole camera model. The pinhole camera model is the standard way computer vision describes how the 3D world projects onto a 2D image. Treats the lens as a single point that light passes through, which makes the geometry simple: the bigger an object looks in the image relative to its real world size, the closer it is. Same principle that lets a sighted person tell a car is far away when it looks small.

The formula:

```
distance = (realHeight * imageHeight) / (2 * bboxHeight * tan(FOV / 2))
```

Where:
- `realHeight` is the known physical height in meters
- `imageHeight` is the video frame height in pixels
- `bboxHeight` is the detected bounding box height in pixels
- `FOV` is the camera's vertical field of view (assumed 55 degrees, typical for phone rear cameras)

The FOV is converted to radians internally. `getCameraFOV()` returns the assumed value.

### Known heights table

24 common COCO classes have known heights:

| Object | Height (m) | Object | Height (m) |
|---|---|---|---|
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

### Clamping

Distance results clamp between 0.3 m and 8.0 m. Anything under 0.3 m is almost certainly a camera artifact (a finger over the lens, a label on furniture). Anything beyond 8 m is too far to matter for pedestrian navigation.

### Unknown objects

If an object is detected but not in the height table, the website falls back to a coarser bbox ratio table:

| Bbox area as fraction of frame | Estimated distance |
|---|---|
| > 60% | 0.5 m |
| > 45% | 1.0 m |
| > 30% | 1.5 m |
| > 20% | 2.0 m |
| > 10% | 3.0 m |
| smaller | 4.0 m |

Much less accurate than triangulation but it gives a usable estimate when there's no other information.

## Layer 2: Auto calibration of relative depth

Depth-Anything outputs a depth map where every pixel has a value 0 to 255. Higher = closer. The catch is these values are relative, not absolute. A center pixel value of 200 means "closer than something at 100" but doesn't directly correspond to meters.

This is where triangulation becomes the calibration source. The website turns the relative depth model into an absolute distance model by using known object detections as ground truth.

### How it works

When COCO-SSD or BlindGuideNav detects a known size object that meets three conditions:

1. The object is in the "ahead" position (center of the frame)
2. Detection confidence is at least 0.7
3. The triangulated distance is between 0.5 and 5.0 meters

The website records a calibration pair: the current center depth value paired with the triangulated real distance. Subsequent depth readings use this pair to convert raw values to meters.

The conversion formula uses the inverse relationship between depth value and distance:

```
distance = (calibration_depth * calibration_meters) / current_depth
```

### Why this matters

The depth model alone only knows pixel A is closer than pixel B. The bounding box detector alone only knows distances to objects whose real size is in the table. Neither can measure the distance to a wall (not in the height table) or to an unknown object. By combining the two, the website measures absolute distance to anything the depth model can see, even objects it has never seen before. The known size objects act as living rulers that the depth model uses to learn what its raw values mean in this scene.

### Smoothing the calibration

A single calibration update shouldn't throw off the entire mapping. If a person walks past partly out of frame and the triangulation is slightly off, that one bad reading shouldn't poison future estimates.

So calibration uses EMA with alpha 0.3. The new calibration value contributes 30 percent, the existing calibration retains 70 percent. Outliers get smoothed out. A consistent shift (user walks into a new room with different lighting) eventually wins out, but one bad frame cannot derail the system.

## Layer 3: Approach rate detection

Even before any calibration has happened, the depth model produces useful information about the rate of change. If the center depth value has been climbing for several frames, something is getting closer regardless of what the actual distance is in meters.

### How it works

The website tracks the center depth value across the last 6 frames in a rolling window (`state.depthHistory`). On each cycle, it checks for a monotonic rise:

- Values must increase from one frame to the next for at least 4 consecutive frames
- The average frame to frame rate of increase is computed

If the rise is detected:

| Average rate | Result |
|---|---|
| > 15 per frame | DANGER ("Approaching fast") |
| > 8 per frame | WARNING ("Something getting closer") |

### Why this matters

This layer is the safety net for the first seconds after the website opens. The depth model has loaded but no calibration data exists yet. Triangulation can't help because the user might be looking at a wall (not a known object). Approach rate detection works regardless. It only requires that the depth values trend upward.

It also handles fast moving hazards that other layers would miss. A car approaching at 5 m/s would only trigger triangulation when the bounding box gets large enough, which might be too late. Approach rate fires the moment the depth signal starts climbing, often a full second earlier.

## Layer 4: Center vs sides deviation

The depth map gets sampled in three regions:

- **Center strip:** 30 to 70 percent of frame width, 15 to 85 percent of frame height
- **Left strip:** less than 22 percent of frame width
- **Right strip:** greater than 78 percent of frame width

The center is the walking path. The sides are the periphery. Most rooms have walls or furniture at moderate distance on the sides, which the user doesn't need to be warned about because they aren't in the path.

The useful question is whether the center is significantly closer than the sides. If yes, there's something in the path that isn't just the natural background:

| Center minus side average | Result |
|---|---|
| > 0.35 (normalized) | DANGER ("Obstacle directly ahead") |
| > 0.20 (normalized) | WARNING ("Obstacle in path") |

This catches narrow obstacles like poles, signs, and railings that fill the center but don't extend to the periphery. A pure center distance threshold would miss these because the absolute value might still be high but the side comparison shows the obstacle is genuinely in the path.

## How the layers combine

The four techniques run concurrently and produce overlapping signals. The protection loop merges them into one threat assessment:

- **Triangulation** is the highest accuracy source when it has a known object detection to work from. Anchors the absolute distance.
- **Auto calibrated depth** extends triangulation to the rest of the scene, including walls and unknown objects.
- **Approach rate** is the calibration free safety net. Works in the first few seconds and handles fast moving hazards.
- **Center vs sides** catches narrow obstacles other layers miss because of the average bias.

When more than one layer fires, highest severity wins. A DANGER from approach rate beats a WARNING from triangulation. If all layers are silent, the path is safe.

## Alert zones

The final distance estimate compares against three zones:

| Zone | Threshold | Level |
|---|---|---|
| Danger | < 1.0 m | DANGER |
| Warning | < 2.0 m | WARNING |
| Awareness | < 4.0 m | AWARENESS |

These zones drive the speech, beep, and vibration outputs described in [SpeechAndAudio](SpeechAndAudio.md). Asymmetric temporal smoothing in [Detection](Detection.md) prevents flicker when distances oscillate near a zone boundary.
