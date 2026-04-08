# BlindGuideNav Custom Model

## Overview

BlindGuideNav is a custom CoreML object detection model designed specifically for blind pedestrian navigation. Unlike general purpose models such as YOLOv8n (which detects 80 generic COCO classes), BlindGuideNav focuses on 55 classes that are directly relevant to walking safely in indoor and outdoor environments.

## Origin

BlindGuideNav was developed as part of the BlindGuide project within the TSAStates26 initiative. The model was trained to address the limitations of generic object detectors, which often detect objects that are irrelevant to a blind person walking (such as food items, sports equipment, or animals) while missing navigation-specific features.

## Purpose

The goal of BlindGuideNav is to detect objects and environmental features that matter when a blind person is walking. This includes:

- Obstacles at walking height (chairs, tables, benches, bollards)
- Hazards on the ground (curbs, steps, uneven surfaces)
- Navigation landmarks (doors, elevators, crosswalks, signs)
- Moving hazards (people, vehicles, bicycles)
- Structural elements (walls, fences, railings, poles)

## Technical Specifications

| Property | Value |
|----------|-------|
| Format | CoreML (.mlpackage) |
| Size | 5.9 MB |
| Classes | 55 navigation-specific |
| Input | Camera image frame |
| Output | Bounding boxes with class labels and confidence scores |
| Runtime | Apple Neural Engine, GPU, or CPU via CoreML |
| Framework | Vision (VNCoreMLRequest) |

## How It Differs from YOLOv8n

| Aspect | YOLOv8n | BlindGuideNav |
|--------|---------|---------------|
| Total classes | 80 | 55 |
| Focus | General object detection | Navigation safety |
| Irrelevant classes | Many (food, animals, sports) | None (all classes curated for navigation) |
| Navigation features | Limited | Includes curbs, crosswalks, signs, railings |
| Training data | COCO dataset (generic photos) | Navigation-focused scenarios |
| Model size | 6.2 MB | 5.9 MB |

## 55 Navigation Classes

The classes were selected based on what a blind person would encounter while walking. Each class falls into one of these categories:

**Moving Hazards:** person, car, truck, bus, motorcycle, bicycle, scooter, wheelchair

**Ground Level Obstacles:** chair, bench, table, trash can, cone, bollard, fire hydrant, parking meter, planter, luggage, stroller, shopping cart

**Structural Elements:** wall, fence, railing, pole, pillar, barrier, gate

**Ground Hazards:** curb, step, stairs (up), stairs (down), ramp, uneven surface, pothole, manhole

**Navigation Landmarks:** door (open), door (closed), elevator, escalator, crosswalk, traffic light, stop sign, yield sign, street sign, building entrance

**Floor and Surface:** wet floor, carpet edge, mat, threshold, grate, drain

**Overhead Obstacles:** low beam, sign overhang, branch, awning

**Other:** dog on leash, service counter, turnstile, revolving door

## Current Status

BlindGuideNav is included in the GuideDog Vision project and loaded within the native iOS app. The model file is present in the Xcode project and compiles into the app bundle. It is currently available for activation alongside the existing YOLOv8n detection pipeline.

## Integration Paths

### Native App (iOS)

BlindGuideNav can run alongside YOLOv8n as a supplementary detector. Both models would process the same camera frame, and their results would be merged. BlindGuideNav would catch navigation-specific objects (curbs, crosswalks, railings) that YOLOv8n misses, while YOLOv8n would continue to handle general object detection.

The integration would use the same Vision framework pipeline that YOLOv8n currently uses:

```swift
let vnModel = try VNCoreMLModel(for: blindGuideNavModel)
let request = VNCoreMLRequest(model: vnModel)
```

### Website (Browser)

BlindGuideNav is a CoreML model and cannot run directly in a web browser. To use it on the website, the model would need to be converted to ONNX format and run via ONNX Runtime Web or Transformers.js. The conversion path is:

CoreML (.mlpackage) to PyTorch to ONNX to ONNX Runtime Web

This conversion is technically feasible but has not yet been implemented. The website currently uses COCO-SSD (TensorFlow.js) for object detection.
