# GuideDog Vision

GuideDog Vision was built so a phone could do some of the things a guide dog does for a blind person. The iPhone app watches what's in front of you with LiDAR and computer vision and tells you what it sees. The website does the same thing without LiDAR, in any browser, on any phone.

| App Store | Website |
|:---:|:---:|
| <img src="qr-app.png" alt="QR code for GuideDog Vision on the App Store" width="240"> | <img src="qr-website.png" alt="QR code for GuideDog Vision website" width="240"> |
| Scan to download on iPhone | Scan to launch in your browser |

## Why This Was Built

### How many people this affects

The World Health Organization counts about **2.2 billion people** worldwide living with some kind of vision impairment. **43.3 million** of them are fully blind. Another **295.1 million** have moderate to severe vision loss [1]. The number is climbing. Vision loss is projected to grow by **55 percent by 2050**, adding roughly **600 million more people** on top of today's totals [2].

The hardest numbers to read are the downstream ones. In the United States, the employment rate for blind and visually impaired adults sits around **44 percent**, compared to **77 percent** for everyone else [3]. People with vision loss are **1.6 to 2.8 times more likely** to develop depression [4]. Mobility, work, social life, mental health: it all compounds.

### The guide dog gap

Most people, when they think about mobility for blind people, picture a guide dog. The reality is that almost nobody who needs one has one. There are about **10,000 working guide dog teams in the entire United States**. Globally, only about **2 percent** of blind people work with a guide dog [5]. The other 98 percent get by without one.

Three reasons for the gap:

A trained guide dog costs **$40,000 to $60,000** to breed, raise, and place [5][6]. Most handlers don't pay that directly because nonprofits raise the money, but the supply of dogs is capped by how much funding the nonprofits can pull in. After placement, the dog still costs **$180 to $220 a month** in food, vet care, and supplies [5].

Training takes time. A guide dog takes about **two years** to fully train, and only about **one in three dogs** that enter a training program actually graduate [5]. Waiting lists run **one to three years** [7]. Some programs have stopped taking applications because they cannot keep up.

Even after placement, the dog cannot go everywhere. Some venues turn working animals away or require special accommodations. The dog itself needs a stable home, exercise, vet care, grooming. A working animal is a long term commitment that not everyone is positioned to take on.

### Where this app fits

GuideDog Vision is not a guide dog. A trained animal makes its own safety calls and is a companion. Software cannot do either of those things. What software can do is run on a phone someone already owns, watch the scene in front of them, and tell them about it. That covers a real chunk of what a sighted helper would do, and it's available to anyone who can install an app or open a URL.

---

**Sources**

1. World Health Organization. *Vision impairment and blindness fact sheet.* https://www.who.int/news-room/fact-sheets/detail/blindness-and-visual-impairment
2. Statista. *Vision Loss Predicted to Surge 55% by 2050.* https://www.statista.com/chart/31502/expected-number-of-people-with-vision-loss-globally/
3. McDonnall, M. C., & Sui, Z. (2019). *Employment and Unemployment Rates of People Who Are Blind or Visually Impaired.* https://journals.sagepub.com/doi/abs/10.1177/0145482X19887620
4. National Library of Medicine. *Visual Impairment and Mental Health: Unmet Needs and Treatment Options.* https://pmc.ncbi.nlm.nih.gov/articles/PMC7721280/
5. Dogster. *10 Service Dog Statistics: Training, Costs & FAQ.* https://www.dogster.com/statistics/service-dog-statistics
6. Hepper Pet Resources. *How Much is a Guide Dog: Cost Breakdown & FAQs.* https://articles.hepper.com/how-much-is-a-guide-dog/
7. All About Vision. *How to Get a Guide Dog: A Resource Guide.* https://www.allaboutvision.com/conditions/blindness-low-vision/how-to-get-a-guide-dog/

## Overview

The project has two halves that share the same goal.

The iPhone app uses ARKit LiDAR (on Pro models), YOLOv8n object detection, a custom 55 class navigation model trained for this project, Apple's mesh classifier for walls and doors, and a cloud AI fallback for scene descriptions. On non Pro iPhones it falls back to Depth-Anything, a neural depth estimator converted to CoreML, so the app still works without LiDAR.

The website is a Progressive Web App that runs in any modern browser. It has no LiDAR access at all, so it leans harder on machine learning: COCO-SSD for objects, Depth-Anything in the browser for relative depth, MediaPipe Audio Classifier for sound detection, the Web Speech API for live captions, and a cloud AI that runs every few seconds as a sighted companion.

Both halves talk to the same Cloudflare Worker, which races Claude Haiku 4.5 against GPT-4.1-mini and returns whichever responds first.

## Project Structure

```
GuideDog_Vision/
├── app/                          # iOS app (Capacitor + Swift)
│   ├── ios/App/App/              # Swift source files + ML models
│   ├── www/                      # WKWebView UI layer
│   └── capacitor.config.json
├── web/                          # PWA website (no LiDAR)
│   ├── index.html
│   ├── manifest.json
│   └── sw.js
├── CustomModel/
│   └── BlindGuideNav.mlpackage   # Custom 55 class navigation model
├── Documentation/
│   ├── App/                      # iOS app docs
│   ├── Web/                      # Website docs
│   ├── CustomModel/              # Custom model docs
│   ├── Privacy.md
│   └── TestPlan.md
```

## Technology Stack

| Component | iOS App | Website |
|-----------|-----------|---------|
| Object Detection | YOLOv8n (CoreML) | COCO-SSD (TensorFlow.js) |
| Custom Model | BlindGuideNav | BlindGuideNav |
| Scene Segmentation | DeepLabV3 (CoreML) | N/A |
| Depth Sensing | ARKit LiDAR (with Depth-Anything fallback) | Depth-Anything (Transformers.js) |
| Mesh Classification | ARKit sceneReconstruction | N/A |
| Wall Detection | LiDAR thresholds + uniform zone inference | Pixel variance |
| Sound Detection | N/A | MediaPipe Audio Classifier (YAMNet) |
| Captions | N/A | Web Speech API SpeechRecognition |
| Cloud AI | Claude Haiku 4.5 + GPT-4.1-mini | Claude Haiku 4.5 + GPT-4.1-mini |
| Speech Output | AVSpeechSynthesizer | Web Speech API |
| Voice Input | SFSpeechRecognizer | Web Speech API |

## Documentation

### iOS App

1. [Overview](Documentation/App/Overview.md)
2. [Architecture](Documentation/App/Architecture.md)
3. [Detection](Documentation/App/Detection.md)
4. [Distance](Documentation/App/Distance.md)
5. [Cloud AI](Documentation/App/CloudAI.md)
6. [Speech and Audio](Documentation/App/SpeechAndAudio.md)
7. [Gestures and Voice](Documentation/App/GesturesAndVoice.md)
8. [User Interface](Documentation/App/UI.md)
9. [Design Decisions](Documentation/App/DesignDecisions.md)

### Website (PWA)

1. [Overview](Documentation/Web/Overview.md)
2. [Architecture](Documentation/Web/Architecture.md)
3. [Detection](Documentation/Web/Detection.md)
4. [Distance](Documentation/Web/Distance.md)
5. [Cloud AI](Documentation/Web/CloudAI.md)
6. [Speech and Audio](Documentation/Web/SpeechAndAudio.md)
7. [Gestures and Voice](Documentation/Web/GesturesAndVoice.md)
8. [User Interface](Documentation/Web/UI.md)
9. [Design Decisions](Documentation/Web/DesignDecisions.md)

### Models and reference

- [BlindGuideNav Custom Model](Documentation/CustomModel/BlindGuideNav.md)
- [Test Plan](Documentation/TestPlan.md)
- [Privacy Policy](Documentation/Privacy.md)

## Models

| Model | Size | Classes | Where |
|-------|------|---------|----------|
| YOLOv8n | 6.2 MB | 80 COCO | iOS app |
| BlindGuideNav | 5.9 MB | 55 navigation | Both |
| DeepLabV3 | 21 MB | 21 PASCAL VOC | iOS app |
| COCO-SSD | ~5 MB | 80 COCO | Website |
| Depth-Anything (small) | ~47 MB FP16 | Depth map | Website + iOS fallback |
| Claude Haiku 4.5 | Cloud | Vision + language | Both |
| GPT-4.1-mini | Cloud | Vision + language | Both |

## Requirements

### iOS app

- iPhone running iOS 15 or later
- Best on LiDAR equipped iPhones (12 Pro and later Pro models)
- Camera and microphone access
- Speech recognition permission for voice commands

### Website

- Any modern browser with camera support (Safari, Chrome, Firefox)
- Internet connection for cloud AI features
- HTTPS (browsers require it for camera access)

## Privacy

All on device detection runs locally. Camera frames sent to cloud AI for scene descriptions are processed and immediately discarded. No images get stored. No account. No personal data collected.

Full details in the [Privacy Policy](Documentation/Privacy.md).
