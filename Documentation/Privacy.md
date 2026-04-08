# Privacy Policy

**GuideDog Vision**

Last updated: April 7, 2026

## Data Collection

GuideDog Vision does not collect, store, or share any personal data.

## Camera

The app uses your camera to detect obstacles and navigate your surroundings. All object detection and depth analysis runs entirely on your device. Camera images are not saved or transmitted during normal operation.

When you trigger a scan (by double tapping or using a voice command), a single camera frame may be sent to a cloud AI service for scene description. This image is processed in real time and immediately discarded after the response is generated. No images are retained by the cloud services after processing.

## Microphone

The app uses your microphone for voice commands only. Audio is processed on device using Apple's SFSpeechRecognizer (native app) or the Web Speech API (website). Audio is not recorded, stored, or transmitted.

## LiDAR

LiDAR depth data is processed entirely on device and is never transmitted to any external service.

## Cloud AI Services

When you trigger a scan, camera images may be sent to the following services for scene description:

- **Anthropic (Claude Haiku 4.5):** processes the image and returns a text description
- **OpenAI (GPT-4.1-mini):** processes the image and returns a text description

Both services are accessed through a Cloudflare Worker proxy. The image is sent, a text response is received, and the image is immediately discarded. Neither service retains the image after processing.

On the website, the cloud AI runs automatically every 5 seconds as a guide companion. The same processing and discarding rules apply.

## On Device Processing

The following models run entirely on your device with no data transmission:

- YOLOv8n (object detection)
- BlindGuideNav (custom navigation detection)
- DeepLabV3 (scene segmentation)
- Depth-Anything (web depth estimation)
- COCO-SSD (web object detection)
- ARKit LiDAR and mesh classification

## No Account Required

GuideDog Vision does not require any sign up, login, or account creation. There is no user authentication system.

## No Personal Data

The app does not collect names, email addresses, location data, device identifiers, or any other personal information.

## Third Party SDKs

The app uses the following third party components:

- **Capacitor** (app framework): does not collect user data
- **TensorFlow.js** (web ML runtime): runs locally, no data transmission
- **Transformers.js** (web ML runtime): downloads model weights from HuggingFace CDN, no user data transmitted

## Contact

For questions about this privacy policy, visit https://github.com/Omega-6/GuideDog-Vision
