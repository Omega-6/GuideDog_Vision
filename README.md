# GuideDog Vision

AI powered navigation assistant for blind and visually impaired individuals.

| App Store | Website |
|:---:|:---:|
| <img src="qr-app.png" alt="QR code for GuideDog Vision on the App Store" width="240"> | <img src="qr-website.png" alt="QR code for GuideDog Vision website" width="240"> |
| Scan to download on iPhone | Scan to launch in your browser |

## The Problem

43 million people worldwide are completely blind, and another 295 million live with moderate to severe visual impairment. Despite the size of this population, only about 20 thousand people have access to a guide dog. The overwhelming majority of blind and visually impaired people navigate daily life without one, which limits their mobility and independence in ways most sighted people never have to think about.

Three major barriers explain why guide dogs reach so few of the people who need them:

- **Cost.** Breeding, raising, training, and placing a single guide dog runs into the tens of thousands of dollars before a handler ever takes the dog home. Most users do not pay this cost directly because nonprofits cover it through donations, but the supply of trained dogs is permanently capped by how much funding exists.
- **Access.** Guide dogs cannot go everywhere. They require special accommodations, they are restricted from certain environments, and the handler has to plan around the dog as well as around themselves.
- **Responsibility.** A guide dog needs daily exercise, food, grooming, veterinary care, and a safe living environment. Caring for a working animal is a long term commitment that not every blind person is in a position to take on.

GuideDog Vision was built to help close this gap. It does not replace a guide dog. A trained animal can do things software cannot, including making independent safety judgments and providing emotional companionship. What software can do is give a much larger population access to the kind of real time obstacle awareness, distance sensing, and scene understanding that a guide dog provides, on hardware they already own. An iPhone in a pocket and a website in a browser are not a substitute for a partner who has been training for two years, but they are available right now to anyone who needs them.

## Overview

GuideDog Vision helps blind and visually impaired users navigate their surroundings safely. The native iOS app uses LiDAR, specialized AI models, and cloud AI to detect obstacles, walls, stairs, and other hazards in real time. The companion website provides the same core experience using browser based detection and a cloud AI guide that acts as a sighted companion.

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

### Native App (iOS)

1. [Overview](docs/app/Overview.md)
2. [Architecture](docs/app/Architecture.md)
3. [Detection](docs/app/Detection.md)
4. [Distance](docs/app/Distance.md)
5. [Cloud AI](docs/app/CloudAI.md)
6. [Speech and Audio](docs/app/SpeechAndAudio.md)
7. [Gestures and Voice](docs/app/GesturesAndVoice.md)
8. [User Interface](docs/app/UI.md)
9. [Design Decisions](docs/app/DesignDecisions.md)

### Website (PWA)

1. [Overview](docs/web/Overview.md)
2. [Architecture](docs/web/Architecture.md)
3. [Detection](docs/web/Detection.md)
4. [Distance](docs/web/Distance.md)
5. [Cloud AI](docs/web/CloudAI.md)
6. [Speech and Audio](docs/web/SpeechAndAudio.md)
7. [Gestures and Voice](docs/web/GesturesAndVoice.md)
8. [User Interface](docs/web/UI.md)
9. [Design Decisions](docs/web/DesignDecisions.md)

### Models and Reference

- [BlindGuideNav Custom Model](docs/models/BlindGuideNav.md)
- [Requirements](docs/Requirements.md)
- [Test Plan](docs/TestPlan.md)
- [Privacy Policy](docs/Privacy.md)

## Models

| Model | Size | Classes | Platform |
|-------|------|---------|----------|
| YOLOv8n | 6.2 MB | 80 COCO | Native app | 
| BlindGuideNav | 5.9 MB | 55 navigation | Both |
| DeepLabV3 | 21 MB | 21 PASCAL VOC | Native app | 
| COCO-SSD | ~5 MB | 80 COCO | Website | 
| Depth-Anything-small | ~25 MB | Depth map | Website + no-LiDAR fallback | 
| Claude Haiku 4.5 | Cloud | Vision + language | Both |
| GPT-4.1-mini | Cloud | Vision + language | Both | 

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
