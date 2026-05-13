# BlindGuideNav

## Overview

BlindGuideNav is the custom object detection model trained for GuideDog Vision. It recognizes 55 navigation relevant classes (curbs, crosswalks, stairs, doors, railings, traffic lights, wet floors, overhead obstacles). It runs in both the iOS app and the web PWA. On iOS it ships as a CoreML package and runs through the Vision framework. On web it ships as an ONNX file and runs through ONNX Runtime Web.

The model exists because general purpose object detectors waste capacity on classes a blind walker doesn't care about. A model trained on COCO knows how to find a teddy bear, a hot dog, and a pair of scissors. It does not know what a curb ramp looks like. BlindGuideNav puts its limited capacity on the things that affect walking safety.

## Why a custom model

The iOS app uses YOLOv8n (80 COCO classes). The website uses COCO-SSD (also 80 COCO classes). Both are good at common indoor and outdoor objects: people, vehicles, furniture, signage. Neither was trained on a navigation focused dataset, so neither produces useful detections for things like:

- Curb ramps (where the sidewalk meets the street)
- Crosswalk markings
- Doors in the open vs closed state
- Stairs going up vs going down
- Wet floors and floor signs
- Railings and handrails
- Pedestrian traffic signals
- Low overhead obstacles like branches and signs
- Tactile paving and warning strips

A blind person walking through a city runs into these things constantly. They are exactly what a sighted companion would point out. They aren't in COCO, so they aren't in COCO trained models.

Rather than fine tune YOLOv8n on top of its existing 80 class output head (which would still carry the COCO bias), a new model was trained from a curated 55 class dataset. The result is a smaller file (5.9 MB vs YOLOv8n's 6.2 MB) with a tighter decision boundary on the things that matter for navigation.

## How it works

Single stage object detector. Whole pipeline runs in one forward pass. Output is a list of bounding boxes, each tagged with class label and confidence.

### Input pipeline

One camera frame is the input. Goes through three preparation steps:

1. **Resize.** Camera frame (typically 1920 by 1080) is resized to the model input (640 by 640). Aspect ratio is preserved with letterboxing.
2. **Normalize.** Pixel values converted from 0 to 255 integer to 0.0 to 1.0 float. Channel order is RGB. No mean subtraction or scaling beyond the division.
3. **Tensor format.** The normalized image becomes a 4D tensor with shape `[1, 3, 640, 640]` (batch, channels, height, width). Standard format for image models in CoreML and ONNX.

### Architecture

Follows the standard single stage detector pattern:

- **Backbone.** A convolutional feature extractor that takes the input image and produces a hierarchy of feature maps at three scales. Learns generic visual features (edges, textures, shapes) that get reused for every class.
- **Neck.** A feature pyramid network that combines information from the three backbone scales. Small features (a distant crosswalk) get refined with help from large features (the road surface). Large features (a nearby door) get refined with help from small features (the door handle).
- **Detection head.** Three parallel prediction layers, one per scale, outputting bounding box coordinates, class probabilities, and an objectness score for every anchor position.

### Inference

Each forward pass produces a raw output tensor with every possible detection at every position and scale. Most aren't real objects. Two filtering steps clean it up:

1. **Confidence threshold.** Detections below the threshold (0.5 to 0.7 depending on class) are dropped. Removes the long tail of low confidence noise.
2. **Non maximum suppression.** When multiple overlapping boxes claim the same object, NMS keeps the highest scoring box and discards the others. Stops the model from announcing the same chair three times.

The result is a final list of (class label, confidence, bounding box) tuples. These flow into the same downstream announcement pipeline as the general purpose detector results.

## The 55 classes

The class list came out of walking through real navigation scenarios and noting every object or feature that affects whether the path ahead is safe. They group into eight categories.

**Moving Hazards.** person, car, truck, bus, motorcycle, bicycle, scooter, wheelchair. Highest priority because they move and can cause injury on contact.

**Ground Level Obstacles.** chair, bench, table, trash can, cone, bollard, fire hydrant, parking meter, planter, luggage, stroller, shopping cart. Don't move on their own but they sit at walking height and you will collide with them if not warned.

**Structural Elements.** wall, fence, railing, pole, pillar, barrier, gate. Define the edges of walkable space. Some are useful as landmarks (a railing tells you which way the stairs go). Others are obstacles.

**Ground Hazards.** curb, step, stairs going up, stairs going down, ramp, uneven surface, pothole, manhole. Change the elevation of the walking surface. A missed stair is one of the most dangerous failures a navigation system can have.

**Navigation Landmarks.** door (open), door (closed), elevator, escalator, crosswalk, traffic light, stop sign, yield sign, street sign, building entrance. Features a sighted person uses to know where they are and where to go next.

**Floor and Surface.** wet floor, carpet edge, mat, threshold, grate, drain. Slipping on a wet floor or catching a foot on a carpet edge are common indoor hazards.

**Overhead Obstacles.** low beam, sign overhang, branch, awning. A blind person scans with a cane near the ground. Overhead obstacles are invisible to a cane but very visible to a model that processes the full camera image.

**Other.** dog on leash, service counter, turnstile, revolving door. Miscellaneous features that didn't fit cleanly anywhere else.

## Inside the iOS app

On iPhone, BlindGuideNav ships as a CoreML package (`BlindGuideNav.mlpackage`) bundled into the app. Loading is one line of Swift through Vision:

```swift
let mlModel = try BlindGuideNav(configuration: MLModelConfiguration()).model
let visionModel = try VNCoreMLModel(for: mlModel)
let request = VNCoreMLRequest(model: visionModel) { request, error in
    // process detections
}
```

The Vision framework handles input pipeline automatically. It accepts a `CVPixelBuffer` (the camera format), performs the resize and normalization, and feeds the tensor to the model. The framework also dispatches inference to the Apple Neural Engine on supported hardware. On iPhone 13 and later, a forward pass takes about 15 to 25 ms. Older devices run on GPU or CPU with longer inference times.

The output flows into the same `ObjectDetector` pipeline that handles YOLOv8n results. Both detectors run on the ARSession frame loop. Their outputs merge into one deduplicated list before announcement.

## Inside the web PWA

On web, BlindGuideNav ships as an ONNX file (`BlindGuideNav.onnx`) loaded through ONNX Runtime Web. The export from PyTorch to ONNX preserves the full architecture and weights but converts the operator graph to a format that runs in any ONNX compatible runtime. The browser runtime uses WebAssembly (with SIMD on supported browsers) to execute the operators on the CPU.

```javascript
const session = await ort.InferenceSession.create('models/BlindGuideNav.onnx', {
    executionProviders: ['wasm'],
    graphOptimizationLevel: 'all'
});
```

A forward pass takes about 80 to 150 ms, slower than CoreML but still fast enough to run alongside the other layers. The result merges into the same pipeline as COCO-SSD inside the protection loop.

ONNX over TensorFlow.js was a deliberate call. ONNX Runtime Web uses one shared WebAssembly module across all loaded models. TensorFlow.js loads its own runtime. Sharing one runtime reduces per tab memory, which matters on iOS Safari.

## Specifications

| Property | Value |
|---|---|
| Format (iOS) | CoreML package (.mlpackage) |
| Format (Web) | ONNX (.onnx) |
| File size | 5.9 MB |
| Total classes | 55 |
| Input resolution | 640 by 640 |
| Input format | RGB, normalized 0.0 to 1.0 |
| Output | Bounding boxes with class label and confidence |
| iOS runtime | Apple Vision framework, Apple Neural Engine |
| Web runtime | ONNX Runtime Web, WebAssembly |
| iOS inference time | 15 to 25 ms per frame (iPhone 13 and later) |
| Web inference time | 80 to 150 ms per frame (modern phone browser) |
| Confidence threshold | 0.5 to 0.7 depending on class |
| Post processing | Non maximum suppression |
