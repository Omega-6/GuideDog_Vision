# GuideDog Vision

AI-powered navigation assistant for blind and visually impaired individuals.

**App Store:** [Download on the App Store](https://apps.apple.com/app/guidedog-vision/id6761731954)

**Website:** [Launch GuideDog Web](https://omega-6.github.io/GuideDog-Vision/)

## Overview

GuideDog Vision helps blind and visually impaired users navigate their surroundings safely. The native iOS app uses LiDAR, on-device AI models, and cloud AI to detect obstacles, walls, stairs, and other hazards in real time. The companion website provides the same core experience using browser-based detection and a cloud AI guide that acts as a sighted companion.

## Project Structure

```
GuideDog-Vision/
├── app/                        # iOS native app (Capacitor + Swift)
│   ├── ios/App/App/            # Swift source files + ML models
│   ├── www/                    # Web UI layer
│   └── capacitor.config.json
├── web/                        # PWA website (browser only, no LiDAR)
│   ├── index.html
│   ├── manifest.json
│   └── sw.js
├── models/
│   └── BlindGuideNav.mlpackage # Custom 55-class navigation model
├── docs/
│   ├── app/                    # Native app documentation
│   ├── web/                    # Website documentation
│   ├── models/                 # Custom model documentation
│   ├── PRIVACY.md
│   ├── REQUIREMENTS.md
│   └── TESTPLAN.md
```

## Technology Stack

| Component | Native App | Website |
|-----------|-----------|---------|
| Object Detection | YOLOv8n (CoreML) | COCO-SSD (TensorFlow.js) |
| Custom Model | BlindGuideNav | BlindGuideNav |
| Scene Segmentation | DeepLabV3 (CoreML) | N/A |
| Depth Sensing | ARKit LiDAR | Depth-Anything (Transformers.js) |
| Mesh Classification | ARKit sceneReconstruction | N/A |
| Wall Detection | LiDAR depth thresholds | Pixel variance analysis |
| Cloud AI | Claude Haiku 4.5 + GPT-4.1-mini | Claude Haiku 4.5 + GPT-4.1-mini |
| Speech | AVSpeechSynthesizer | Web Speech API |
| Voice Input | SFSpeechRecognizer | Web Speech API |

## Documentation

### Native App
- [Overview](docs/app/OVERVIEW.md)
- [Architecture](docs/app/ARCHITECTURE.md)
- [Detection Pipeline](docs/app/DETECTION.md)
- [Speech and Audio](docs/app/SPEECH_AND_AUDIO.md)
- [Distance Estimation](docs/app/DISTANCE.md)
- [Gestures and Voice](docs/app/GESTURES_AND_VOICE.md)
- [User Interface](docs/app/UI.md)
- [Cloud AI](docs/app/CLOUD_AI.md)
- [Design Decisions](docs/app/DESIGN_DECISIONS.md)

### Website
- [Overview](docs/web/OVERVIEW.md)
- [Architecture](docs/web/ARCHITECTURE.md)
- [Detection Pipeline](docs/web/DETECTION.md)
- [Speech and Audio](docs/web/SPEECH_AND_AUDIO.md)
- [Cloud AI Guide](docs/web/CLOUD_AI_GUIDE.md)
- [Gestures and Voice](docs/web/GESTURES_AND_VOICE.md)
- [User Interface](docs/web/UI.md)
- [Design Decisions](docs/web/DESIGN_DECISIONS.md)

### Models and Testing
- [BlindGuideNav Custom Model](docs/models/BLINDGUIDENAV.md)
- [Privacy Policy](docs/PRIVACY.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Test Plan](docs/TESTPLAN.md)

## Models

| Model | Size | Classes | Platform | Status |
|-------|------|---------|----------|--------|
| YOLOv8n | 6.2 MB | 80 COCO | Native app | Active |
| BlindGuideNav | 5.9 MB | 55 navigation | Native app | Loaded, ready for activation |
| DeepLabV3 | 21 MB | 21 PASCAL VOC | Native app | Active |
| COCO-SSD | ~5 MB | 80 COCO | Website | Active |
| Depth-Anything-small | ~25 MB | Depth map | Website + no-LiDAR fallback | Active |
| Claude Haiku 4.5 | Cloud | Vision + language | Both | Active |
| GPT-4.1-mini | Cloud | Vision + language | Both | Active |

## Requirements

### Native App
- iPhone with iOS 15 or later
- Best experience on LiDAR-equipped iPhones (iPhone 12 Pro and later)
- Camera and microphone access required
- Speech recognition permission for voice commands

### Website
- Modern browser with camera support (Chrome, Safari, Firefox)
- Internet connection for cloud AI features
- HTTPS required (camera access)

## Privacy

All on-device detection runs locally. Cloud AI is used for scene descriptions and stair detection only. No images are stored after processing. No account required. No personal data collected.

See [Privacy Policy](docs/PRIVACY.md) for full details.

## Student Project

Built as a student project to make navigation safer and more accessible for the visually impaired community.
