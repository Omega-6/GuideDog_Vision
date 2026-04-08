# Application Overview

## The Problem

Roughly **2.2 billion people** worldwide live with some form of vision impairment, including **43.3 million** who are completely blind and **295.1 million** with moderate to severe visual impairment. The most well known mobility aid is the guide dog, but only about **2 percent** of blind people actually have one. The remaining 98 percent navigate daily life without one because guide dogs cost **$40,000 to $60,000** to train, take **two years** to produce, and have wait lists that stretch from **one to three years**. Even after placement, only about a third of dogs entering a training program graduate.

GuideDog Vision is built to help close that gap. It does not replace a guide dog. A trained animal can do things software cannot. What software can do is provide real time obstacle awareness, distance sensing, and scene understanding on hardware that millions of blind people already own. See the [README](../../README.md) for the full problem statement and source citations.

## Purpose

GuideDog Vision is a native iOS application designed to provide real time navigation assistance to blind and visually impaired users. The app transforms an iPhone into an intelligent obstacle detection and scene understanding tool, using a combination of on device sensors, machine learning models, and cloud AI to describe the user's surroundings through speech, haptic feedback, and spatial audio.

The core philosophy is proactive protection. The user does not need to interact with the app to receive safety alerts. GuideDog continuously monitors the environment and announces obstacles, walls, doors, vehicles, and other hazards as the user walks. When the user wants more detail, gestures and voice commands provide on-demand scene descriptions.

## Target Users

The primary audience is people who are blind or have low vision. The interface is designed for eyes-free operation. All critical information is delivered through speech and haptics. The visual UI exists primarily for sighted helpers and debugging, not as the primary interaction surface.

Secondary users include orientation and mobility instructors who may use the camera preview and visual indicators during training sessions.

## Supported Devices

GuideDog Vision requires an iPhone running iOS 15 or later. The app runs on all iPhones that support ARKit world tracking, but the experience varies significantly based on hardware.

**LiDAR-equipped iPhones (recommended):** iPhone 12 Pro and later Pro models include a LiDAR scanner. These devices provide the full experience: centimeter-accurate depth readings at 30 frames per second, ARKit mesh classification for walls and doors, and the most reliable obstacle detection. The app performs best on these devices.

**Non-LiDAR iPhones:** iPhones without LiDAR still run the app. Object detection (YOLOv8n), scene segmentation (DeepLabV3), and cloud AI all function normally. For depth estimation, the app falls back to Depth-Anything, a neural network that estimates depth from monocular camera images. This fallback is less precise than LiDAR but still provides useful distance warnings.

## Feature List

### On-Device Detection

- **LiDAR Depth Processing.** Splits the depth map into left, center, and right zones. Reports distances with exponential moving average smoothing. Progressive distance bands trigger speech, haptics, and audio alerts as the user approaches obstacles.

- **YOLOv8n Object Detection.** Runs a YOLOv8n model through Apple's Vision framework and CoreML. Identifies 80 COCO object classes including people, vehicles, furniture, and common outdoor objects. Hardware-accelerated on the Apple Neural Engine.

- **ARKit Mesh Classification.** On LiDAR devices, ARKit reconstructs a 3D mesh of the environment and classifies surfaces as walls, doors, windows, seats, or tables. The app filters this mesh to a forward-facing 60-degree cone and announces relevant surfaces with distance and direction.

- **DeepLabV3 Semantic Segmentation.** A secondary detection layer that segments the entire camera frame into 21 PASCAL VOC classes. Announces large objects (greater than 15% frame coverage) that YOLOv8n missed, providing complementary coverage.

- **BlindGuideNav Custom Model.** A custom CoreML model trained on 55 navigation-specific classes. The model is loaded into the project and available for activation. It is designed to run alongside YOLOv8n for expanded detection coverage in future updates.

### Cloud AI

- **Dual-provider scene description.** When the user requests a scan (or when the scene changes), the app sends a compressed camera frame to a Cloudflare Worker that races Claude Haiku 4.5 against GPT-4.1-mini. Whichever responds first is spoken aloud. The prompt is safety-focused with a 15-word maximum, prioritizing stairs and immediate hazards.

### Interaction

- **Voice Commands.** The user holds the screen to activate speech recognition (SFSpeechRecognizer). Recognized commands include "what's around," "is it safe," "left," "right," "scan," "stop," "resume," and "help." Known commands execute immediately from partial recognition results for minimal latency.

- **Haptic Feedback.** UIImpactFeedbackGenerator provides haptic pulses that increase in frequency as the user approaches an obstacle. Caution-level obstacles pulse every 0.5 seconds. Danger-level obstacles pulse every 0.1 seconds.

- **Spatial Audio.** An AVAudioEngine generates directional beeps panned to the left or right stereo channel, indicating which side a danger-level obstacle is on. Beeps are limited to danger-level threats only. The spatial audio system pauses automatically during speech to prevent cognitive overload.

### Depth-Anything Fallback

On iPhones without LiDAR, the app loads a Depth-Anything model to estimate per-pixel depth from the monocular camera feed. This provides approximate distance information for the same progressive alert system that LiDAR drives on Pro models. The estimates are less precise but still support the core safety workflow of warning the user before they walk into obstacles.
