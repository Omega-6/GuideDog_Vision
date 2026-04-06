# GuideDog Vision

AI-powered navigation assistant for blind and visually impaired individuals.

## Overview

GuideDog Vision uses LiDAR, camera AI, and voice to detect obstacles, walls, stairs, and hazards in real time — keeping users safe as they walk.

### Features

- **LiDAR Distance Sensing** — real-time distance measurements in feet
- **AI Object Detection** — YOLOv8n identifies people, chairs, vehicles, furniture and more
- **ARKit Mesh Classification** — detects walls, doors, windows from 3D mesh
- **Cloud AI Scene Analysis** — detects stairs, wet floors, doors, and contextual hazards
- **Voice Commands** — "What's around", "Is it safe", "Left", "Right", "Scan", "Help"
- **Haptic Feedback** — vibration patterns match obstacle urgency
- **Spatial Audio** — directional beeps indicate obstacle direction

### Controls

| Gesture | Action |
|---------|--------|
| Hold screen | Speak a voice command |
| Double tap | Scan surroundings |
| Swipe left/right | Check sides |
| CAM button | Toggle camera preview |

## Project Structure

```
GuideDog-Vision/
├── app/                    # iOS native app (Capacitor + Swift)
│   ├── ios/App/App/        # Swift source files
│   ├── www/                # Web UI layer
│   └── capacitor.config.json
├── web/                    # PWA website (browser-only, no LiDAR)
│   ├── index.html
│   ├── manifest.json
│   └── sw.js
└── docs/                   # Documentation
    ├── PRIVACY.md
    ├── REQUIREMENTS.md
    ├── TECHNICAL.md
    └── TESTPLAN.md
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| iOS App | Swift + Capacitor 8.3 |
| Object Detection | YOLOv8n (CoreML) |
| Scene Segmentation | DeepLabV3 (CoreML) |
| Depth Sensing | ARKit LiDAR / Depth-Anything (web) |
| Cloud AI | Cloudflare Worker, Claude Haiku, GPT-4.1-mini |
| Speech | AVSpeechSynthesizer / Web Speech API |

## Requirements

- iPhone with iOS 15+
- Works best with LiDAR (iPhone 12 Pro and later)
- Camera and microphone access required

## Privacy

All detection runs on-device. Cloud AI is optional. No data collected. See [Privacy Policy](docs/PRIVACY.md).

## Website

PWA available at: https://omega-6.github.io/GuideDog/

## License

Student project — built to make navigation safer for the visually impaired community.
