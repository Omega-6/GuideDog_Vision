# GuideDog Vision

AI powered navigation assistant for blind and visually impaired individuals.

| App Store | Website |
|:---:|:---:|
| <img src="qr-app.png" alt="QR code for GuideDog Vision on the App Store" width="240"> | <img src="qr-website.png" alt="QR code for GuideDog Vision website" width="240"> |
| Scan to download on iPhone | Scan to launch in your browser |

## The Problem

### The Scale of Vision Loss

According to the World Health Organization, at least **2.2 billion people** worldwide live with some form of vision impairment. Of those, **43.3 million are completely blind** and another **295.1 million** have moderate to severe visual impairment [1]. The total is growing. Vision loss is projected to increase by roughly **55 percent by 2050**, affecting another **600 million people** on top of the current count [2].

The impact reaches far beyond the inability to see. In the United States, the employment rate for people with visual impairments is around **44 percent**, compared to **77 percent** for people without disabilities [3]. People with vision loss are **1.6 to 2.8 times more likely to experience depression** than people with full vision, and a meaningful share report clinically significant depressive symptoms [4]. The day to day challenges (mobility, independence, employment, social connection) compound into mental health outcomes that affect life quality long after the initial diagnosis.

### The Guide Dog Gap

The most well known mobility aid for blind individuals is the guide dog. The reality is that almost no one who needs one actually has one. There are only about **10,000 working guide dog teams in the entire United States**, and globally only about **2 percent of blind and partially sighted people** work with a guide dog [5]. The other 98 percent navigate daily life without one.

Three major barriers explain the gap:

**Cost.** Breeding, raising, and training a single guide dog costs between **$40,000 and $60,000** before the dog is ever placed with a handler [5][6]. Recipients do not usually pay this directly because nonprofit programs raise the money through donations, but the supply of trained dogs is permanently capped by how much funding exists. On top of the upfront cost, ongoing care runs roughly **$180 to $220 per month** for food, veterinary care, and supplies [5].

**Supply and waiting lists.** Even if cost were no object, the supply is limited by the training process itself. A guide dog takes about **two years to fully train**, and only about **one in three dogs** that enter a training program actually graduate [5]. Wait lists for an applicant matched with a trained dog stretch from **one year to three years** [7]. Some programs have suspended applications entirely because they cannot keep up with demand.

**Access and responsibility.** Even after a handler receives a guide dog, the dog cannot go everywhere. Some venues require special accommodations or restrict working animals altogether. The dog itself needs daily exercise, food, grooming, veterinary care, and a safe living environment. A working animal is a long term commitment that not every blind person is positioned to take on.

### Where GuideDog Vision Fits

GuideDog Vision was built to help close the gap. It does not replace a guide dog. A trained animal can do things software cannot, including making independent safety judgments and providing emotional companionship. What software can do is give a much larger population access to real time obstacle awareness, distance sensing, and scene understanding on hardware they already own. An iPhone in a pocket and a website in a browser are not a substitute for a partner who has been training for two years, but they are available right now, for free, to anyone who needs them.

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
