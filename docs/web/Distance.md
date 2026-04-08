# Distance Estimation

## The Problem

The native iOS app has LiDAR. It can measure the distance to a wall in centimeters, in real time, without any inference. The web PWA does not have that. A web browser cannot access LiDAR even on iPhones that have the hardware. The only inputs available to the website are the camera image and a depth model that produces relative depth values, not absolute meters.

This forces the web side to do real distance math. The website cannot just read a sensor. It has to reconstruct distance from geometry and from the rate of change of pixel values. Four techniques work together to fill the gap.

## Layer 1: Known Object Triangulation

When COCO-SSD or BlindGuideNav detects an object whose real world height is known (a person, a car, a chair), the website estimates distance from the pinhole camera model. The math is simple geometry. The bigger the object appears in the image relative to its real size, the closer it is to the camera.

The formula is:

```
distance = (realHeight × imageHeight) / (2 × bboxHeight × tan(FOV / 2))
```

Where:
- `realHeight` is the known physical height of the object in meters
- `imageHeight` is the video frame height in pixels
- `bboxHeight` is the detected bounding box height in pixels
- `FOV` is the camera's vertical field of view (assumed 55 degrees, typical for phone rear cameras)

The camera FOV is converted to radians internally. The `getCameraFOV()` function returns the assumed value.

### Known Heights Table

The website maintains a curated table of real world heights for 24 common COCO classes. These are the objects most likely to appear in a navigation scenario:

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

### Clamping and Sanity Checks

Distance results are clamped between 0.3 meters and 8.0 meters. Anything closer than 0.3 meters is almost certainly a camera artifact (a finger over the lens, a label on a piece of furniture). Anything beyond 8 meters is too far to matter for pedestrian navigation since the user will not collide with it before the next frame arrives.

### Fallback for Unknown Objects

When an object is detected but is not in the known heights table, the website falls back to a coarser bounding box ratio table:

| Bbox area as fraction of frame | Estimated distance |
|---|---|
| > 60% | 0.5 m |
| > 45% | 1.0 m |
| > 30% | 1.5 m |
| > 20% | 2.0 m |
| > 10% | 3.0 m |
| smaller | 4.0 m |

This is much less accurate than triangulation but it gives a usable estimate when no other information is available.

## Layer 2: Auto Calibration of Relative Depth

The Depth-Anything model produces a depth map where every pixel has a value from 0 to 255. Higher values mean closer. The catch is that these values are relative, not absolute. A center pixel value of 200 means "closer than something at 100" but does not directly correspond to a number of meters.

This is where triangulation becomes the calibration source. The website turns the relative depth model into an absolute distance model by using known object detections as ground truth measurements.

### How It Works

When COCO-SSD or BlindGuideNav detects a known size object that meets three conditions:

1. The object is in the "ahead" position (center of the frame)
2. The detection confidence is at least 0.7
3. The triangulated distance is between 0.5 and 5.0 meters

Then the website records a calibration pair: the current center depth value paired with the triangulated real distance. Subsequent depth readings use this pair to convert raw depth values to meters.

The conversion formula uses the inverse relationship between depth value and distance:

```
distance = (calibration_depth × calibration_meters) / current_depth
```

### Why This Is Non Trivial

The depth model on its own only knows that pixel A is closer than pixel B. The bounding box detector on its own only knows distances to objects whose real size is in the lookup table. Neither method can measure the distance to a wall (which is not in the height table) or to an unknown object (which is not in any table). By combining the two, the website measures absolute distance to anything the depth model can see, even if it has never seen that object before. The known size objects act as living rulers that the depth model uses to learn what its raw values mean in this specific scene.

### Smoothing the Calibration

A single calibration update should not throw off the entire mapping. If a person walks past the camera and the triangulation is slightly off because the person is partly out of frame, that one bad reading should not poison future depth estimates.

To prevent this, calibration uses an exponential moving average with alpha = 0.3. The new calibration value contributes 30 percent and the existing calibration retains 70 percent. Outliers get smoothed out across multiple frames. A consistent shift in calibration (because the user has walked into a hallway with different lighting) eventually wins out, but a single bad frame cannot derail the system.

## Layer 3: Approach Rate Detection

Even before any calibration has happened, the depth model produces useful information about the rate of change. If the center depth value has been increasing for several consecutive frames, something is getting closer regardless of what the actual distance is in meters.

### How It Works

The website tracks the center depth value across the last 6 frames in a rolling window (`state.depthHistory`). On each cycle, it checks for a monotonic rise in depth values:

- The values must increase from one frame to the next for at least 4 consecutive frames
- The average frame to frame rate of increase is computed

If the rise pattern is detected:

| Average rate | Result |
|---|---|
| > 15 per frame | DANGER ("Approaching fast") |
| > 8 per frame | WARNING ("Something getting closer") |

### Why This Matters

This layer is the safety net for the very first seconds after the website opens. The depth model has loaded but no calibration data exists yet. Triangulation cannot help because the user might be looking at a wall (not a known object). Approach rate detection works regardless. It only requires that the depth values show a consistent rising trend.

It also handles fast moving hazards that would otherwise be missed. A car approaching at 5 m/s would only trigger triangulation when the bounding box gets large enough, which might be too late. Approach rate fires the moment the depth signal starts climbing, often a full second before the triangulation thresholds would trigger.

## Layer 4: Center vs Sides Deviation

The depth map gets sampled in three regions:

- **Center strip:** 30 to 70 percent of frame width, 15 to 85 percent of frame height
- **Left strip:** less than 22 percent of frame width
- **Right strip:** greater than 78 percent of frame width

The center strip corresponds to where the user is walking. The side strips correspond to the periphery. Most rooms have walls or furniture on the sides at moderate distance, which the user does not need to be warned about because they are not in the walking path.

The interesting question is whether the center is significantly closer than the sides. If yes, there is something in the user's path that is not just the natural background. The website checks two thresholds:

| Center minus side average | Result |
|---|---|
| > 0.35 (normalized) | DANGER ("Obstacle directly ahead") |
| > 0.20 (normalized) | WARNING ("Obstacle in path") |

This catches narrow obstacles like poles, signs, and railings that fill the center but do not extend to the periphery. A pure center distance threshold would miss these because the absolute value might be high but the side comparison shows the obstacle is genuinely in the path.

## How the Layers Combine

The four distance techniques run concurrently. They produce overlapping signals that the protection loop merges into a single threat assessment:

- **Triangulation** is the highest accuracy source when it has a known object detection to work from. It anchors the absolute distance reading.
- **Auto calibrated depth** extends triangulation to the rest of the scene, including walls and unknown objects.
- **Approach rate** is the calibration free safety net. It works in the first few seconds and handles fast moving hazards.
- **Center vs sides** catches narrow obstacles that other layers miss because of the average bias.

When more than one layer fires, the highest severity wins. A DANGER from approach rate beats a WARNING from triangulation. If all layers are silent, the path is safe.

## Distance Zones for Alerts

The final distance estimate gets compared against three zones to determine the alert level:

| Zone | Distance threshold | Alert level |
|---|---|---|
| Danger zone | less than 1.0 meter | DANGER |
| Warning zone | less than 2.0 meters | WARNING |
| Awareness zone | less than 4.0 meters | AWARENESS |

These zones drive the speech, beep, and vibration outputs described in [SpeechAndAudio](SpeechAndAudio.md). Asymmetric temporal smoothing in [Detection](Detection.md) prevents the alert level from flickering when distances oscillate near a zone boundary.
