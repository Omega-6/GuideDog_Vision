# BlindGuideNav

## Overview

BlindGuideNav is a custom object detection model built specifically for GuideDog Vision. It recognizes 55 navigation relevant classes that matter to a person who cannot see, such as curbs, crosswalks, stairs, doors, railings, traffic lights, wet floors, and overhead obstacles. It runs in both the iOS app and the web PWA as part of the active detection pipeline. On iOS it ships as a CoreML package and runs through the Vision framework. On the web it ships as an ONNX file and runs through ONNX Runtime Web.

The model exists because general purpose object detectors waste capacity on classes a blind walker does not care about. A model trained on COCO knows how to find a teddy bear, a hot dog, and a pair of scissors, but does not know what a curb ramp looks like. BlindGuideNav focuses its limited capacity on the things that affect safety while walking.

## Why a Custom Model

The native iOS app uses YOLOv8n (80 COCO classes) and the web PWA uses COCO-SSD (also 80 COCO classes) as their general object detectors. Both models are excellent at common indoor and outdoor objects: people, vehicles, furniture, signage. Neither model was trained on a navigation focused dataset, so neither model produces useful detections for things like:

- Curb ramps (where the sidewalk meets the street)
- Crosswalk markings on the road surface
- Doors in the open versus closed state
- Stairs going up versus stairs going down
- Wet floors and floor signs
- Railings and handrails
- Pedestrian traffic signals
- Low overhead obstacles such as branches and signs
- Tactile paving and warning strips

A blind person walking through a city encounters these features constantly. They are exactly the things a sighted companion would point out. They are not in the COCO dataset, so they are not in COCO trained models.

Rather than fine tune YOLOv8n on top of its existing 80 class output head (which would still carry the bias toward COCO categories) the project trains a new model from a curated 55 class dataset. The result is a smaller file (5.9 MB versus YOLOv8n's 6.2 MB) with a tighter decision boundary on the things that matter for navigation.

## How It Works

BlindGuideNav is a single stage object detector. The entire pipeline runs in one forward pass through the model. The output is a list of bounding boxes, each tagged with a class label and a confidence score.

### Input Pipeline

A single camera frame is the input. The frame goes through three preparation steps before it enters the model:

1. **Resize.** The camera frame (typically 1920 by 1080 from the rear camera) is resized to the model input resolution (640 by 640). The resize preserves the aspect ratio with letterboxing to avoid distortion.
2. **Normalize.** Pixel values are converted from 0 to 255 integer range to 0.0 to 1.0 floating point range. Channel order is RGB. No mean subtraction or scaling beyond the simple division.
3. **Tensor format.** The normalized image becomes a 4D tensor with shape `[1, 3, 640, 640]` (batch size, channels, height, width). This is the standard format for image models in both CoreML and ONNX.

### Model Architecture

The model follows the single stage detector pattern that has become standard for real time object detection. It has three main components:

- **Backbone.** A convolutional feature extractor that takes the input image and produces a hierarchy of feature maps at three different scales. The backbone learns generic visual features such as edges, textures, and shapes that get reused for every class.
- **Neck.** A feature pyramid network that combines information from the three backbone scales. Small features (like a distant crosswalk) get refined with help from large features (like the road surface). Large features (like a nearby door) get refined with help from small features (like the door handle).
- **Detection head.** Three parallel prediction layers, one for each scale, that output bounding box coordinates, class probabilities, and an objectness score for every anchor position.

### Inference

Each forward pass produces a raw output tensor that contains every possible detection at every position and scale. Most of these are not real objects. Two filtering steps reduce the raw output to a clean list of detections:

1. **Confidence threshold.** Any detection with a confidence score below the threshold (0.5 to 0.7 depending on the class) is dropped immediately. This removes the long tail of low confidence noise.
2. **Non maximum suppression (NMS).** When multiple overlapping boxes claim to detect the same object, NMS keeps the highest scoring box and discards the others. This prevents the model from announcing the same chair three times when its detection head fired three slightly different boxes around the same chair.

The result is a final list of `(class label, confidence, bounding box)` tuples. These flow into the same downstream announcement pipeline as the general purpose detector results.

## The 55 Classes

The classes were selected by walking through real navigation scenarios and listing every object or feature that affects whether the path ahead is safe. The result groups into eight categories.

**Moving Hazards.** person, car, truck, bus, motorcycle, bicycle, scooter, wheelchair. These are the highest priority because they move and can cause injury on contact.

**Ground Level Obstacles.** chair, bench, table, trash can, cone, bollard, fire hydrant, parking meter, planter, luggage, stroller, shopping cart. These do not move on their own but they sit at walking height and the user will collide with them if not warned.

**Structural Elements.** wall, fence, railing, pole, pillar, barrier, gate. These define the edges of walkable space. Some are useful as orientation landmarks (a railing tells you which way the stairs go). Others are obstacles to avoid.

**Ground Hazards.** curb, step, stairs going up, stairs going down, ramp, uneven surface, pothole, manhole. These change the elevation of the walking surface. A missed stair is one of the most dangerous failures a navigation system can have.

**Navigation Landmarks.** door (open), door (closed), elevator, escalator, crosswalk, traffic light, stop sign, yield sign, street sign, building entrance. These are the features a sighted person uses to know where they are and where to go next.

**Floor and Surface.** wet floor, carpet edge, mat, threshold, grate, drain. Slipping on a wet floor or catching a foot on a carpet edge are common indoor hazards.

**Overhead Obstacles.** low beam, sign overhang, branch, awning. A blind person scans with a cane near the ground. Overhead obstacles are invisible to a cane but very visible to a model that processes the full camera image.

**Other.** dog on leash, service counter, turnstile, revolving door. Miscellaneous features that did not fit cleanly in the other categories but still matter for navigation.

## Inside the iOS App

On iPhone, BlindGuideNav ships as a CoreML package (`BlindGuideNav.mlpackage`) bundled into the app. Loading the model is one line of Swift through Apple's Vision framework:

```swift
let mlModel = try BlindGuideNav(configuration: MLModelConfiguration()).model
let visionModel = try VNCoreMLModel(for: mlModel)
let request = VNCoreMLRequest(model: visionModel) { request, error in
    // process detections
}
```

The Vision framework handles the input pipeline automatically. It accepts a `CVPixelBuffer` (the format the camera delivers), performs the resize and normalization, and feeds the tensor to the model. The framework also dispatches inference to the Apple Neural Engine when the device has one. On iPhone 13 and later, a single forward pass takes roughly 15 to 25 milliseconds. On older devices the GPU or CPU runs the model with longer inference times.

The output flows into the same `ObjectDetector` pipeline that handles YOLOv8n results. Both detectors run on the ARSession frame loop. Their outputs merge into a single deduplicated list before the announcement system picks which object to speak.

## Inside the Web PWA

On the web, BlindGuideNav ships as an ONNX file (`BlindGuideNav.onnx`) loaded through ONNX Runtime Web. The export from PyTorch to ONNX preserves the full model architecture and weights but converts the operator graph to a format that runs in any ONNX compatible runtime. The browser runtime uses WebAssembly (with SIMD acceleration on supported browsers) to execute the operators on the CPU.

```javascript
const session = await ort.InferenceSession.create('models/BlindGuideNav.onnx', {
    executionProviders: ['wasm'],
    graphOptimizationLevel: 'all'
});
```

A single forward pass in the browser takes roughly 80 to 150 milliseconds, which is slower than the CoreML version but still fast enough to run alongside the other detection layers. The result merges into the same pipeline as COCO-SSD inside the protection loop.

The ONNX format is a deliberate choice over TensorFlow.js. ONNX Runtime Web uses a single shared WebAssembly module across all loaded models, while TensorFlow.js loads its own runtime. Sharing one runtime reduces the per tab memory footprint, which matters on iOS Safari where the per tab memory budget is tight.

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
