# GuideDog

# Try it out [GuideDog](https://omega-6.github.io/GuideDog/)
# Use this URL or scan this QR Code to visit GuideDog (For Best Experience, Use Mobile Devices):
[https://omega-6.github.io/GuideDog/](https://omega-6.github.io/GuideDog/)

Scan this QR code to open GuideDog on your phone:

![BlindGuide QR Code](blindguide-qr.png)


## Real-Time Navigation Assistant for the Visually Impaired

GuideDog is a smartphone application (also accessible on the web) that helps blind and visually impaired people navigate safely through their environment. It uses the phone's camera to detect obstacles, stairs, doors, and other hazards, then warns the user through voice alerts, directional sounds, and vibration patterns.

Unlike expensive guide dogs or specialized hardware, GuideDog runs entirely on a standard smartphone, making it accessible to anyone who needs it.

---

## Table of Contents

1. [The Problem We're Solving](#the-problem-were-solving)
2. [Our Solution](#our-solution)
3. [How It Works](#how-it-works)
4. [Technical Architecture](#technical-architecture)
5. [Key Features](#key-features)
6. [Installation and Setup](#installation-and-setup)
7. [Usage Guide](#usage-guide)
8. [Development Process](#development-process)
9. [Testing and Validation](#testing-and-validation)
10. [Future Plans](#future-plans)
11. [Acknowledgments](#acknowledgments)

---

## The Problem We're Solving

According to the World Health Organization, approximately 285 million people worldwide live with significant visual impairment or blindness. These individuals face daily challenges navigating both familiar and unfamiliar environments.

Current solutions have significant limitations:

**Guide Dogs** are highly effective but cost upwards of $50,000, require a two-year waitlist, and aren't available in many regions. Only about 2% of blind individuals have access to a guide dog.

**White Canes** are affordable and widely used, but they only detect obstacles at ground level and provide no advance warning. Users must physically contact obstacles to detect them.

**Specialized Electronic Devices** exist but typically cost between $1,000 and $5,000, require carrying additional equipment, and often have limited functionality.

**Existing Smartphone Apps** generally require manual activation for each scan and don't provide continuous, automatic protection.

We saw an opportunity: nearly every visually impaired person already carries a powerful computer in their pocket. Modern smartphones have cameras, speakers, vibration motors, and enough processing power to run machine learning models. We built GuideDog to take advantage of this existing hardware.

---

## Our Solution

GuideDog acts like a digital guide dog. Once activated, it continuously monitors the environment through the phone's camera and automatically warns users about obstacles before they encounter them.

The key insight behind our design is that blind users need protection, not just information on demand. Previous apps required users to manually trigger a scan, which meant they had to already suspect danger was present. GuideDog flips this model by assuming the user wants constant protection and only asking them to interact when they want additional details.

### Core Principles

**Automatic Protection**: The app runs continuously, scanning for obstacles every 300 milliseconds and using AI analysis every 3 seconds. Users don't need to remember to check for hazards.

**Multi-Modal Alerts**: Every warning comes through three channels: spoken words, directional audio beeps, and vibration patterns. This redundancy ensures users receive warnings even in noisy environments or when one sense is occupied.

**Voice-First Design**: The entire app can be operated without looking at the screen. All features are accessible through voice commands, and the interface uses large touch zones that don't require precise tapping.

**Fail-Safe Approach**: We designed the system to err on the side of caution. A false positive (warning about nothing) is far better than a false negative (missing a real hazard).

---

## How It Works

When a user opens GuideDog, the app immediately begins analyzing the camera feed. Two detection systems work in parallel:

### Local Object Detection

A machine learning model called COCO-SSD runs directly on the phone. This model can recognize 80 common objects including people, chairs, cars, dogs, tables, and bicycles. Because it runs locally, detection happens in real-time without any network delay.

When the model detects an object, the app estimates its distance based on how large it appears in the camera frame. Larger objects are closer; smaller objects are farther away. The app also determines whether the object is in the user's walking path or off to the side.

### Cloud AI Analysis

Some hazards are difficult for the local model to detect. Stairs, doorways, wet floors, and walls require understanding the scene rather than just recognizing individual objects. For these, GuideDog sends camera frames to cloud-based AI services (OpenAI's GPT-4o and Anthropic's Claude) that can understand complex visual scenes.

To minimize response time, the app calls both AI services simultaneously and uses whichever responds first. This "racing" approach typically cuts response time nearly in half compared to calling a single service.

### Alert Generation

When a hazard is detected, the app determines the appropriate response based on distance and severity:

**Danger Zone (less than 1 meter)**: The user receives an immediate, urgent alert: a spoken warning like "Stop! Chair! Go left!", rapid high-pitched beeps from the direction of the obstacle, and a strong vibration pattern.

**Warning Zone (1-2 meters)**: The user receives a caution alert: a spoken message like "Caution, person ahead", double beeps at medium pitch, and a moderate vibration.

**Awareness Zone (2-4 meters)**: The user hears a soft, single beep indicating something is present but not immediately threatening.

The spatial audio system pans sounds left or right to indicate the obstacle's direction. Users wearing headphones can quickly understand where the hazard is located.

---

## Technical Architecture

GuideDog consists of three main components:

### Frontend Application

The user-facing app is built as a Progressive Web Application (PWA) using standard web technologies: HTML, CSS, and JavaScript. This approach allows the app to run on any smartphone with a modern browser, regardless of whether it's iOS or Android.

The PWA can be installed to the home screen and works offline for basic functionality. It uses several browser APIs:

- MediaDevices API for camera access
- Web Audio API for spatial sound generation
- Web Speech API for voice recognition and text-to-speech
- Vibration API for haptic feedback
- Service Workers for offline capability

### Machine Learning Layer

TensorFlow.js runs the COCO-SSD object detection model directly in the browser. This eliminates the need for a backend server for basic detection and ensures the app works even without internet connectivity.

The model processes video frames at roughly 3-4 frames per second on modern smartphones, which is sufficient for walking-speed navigation.

### Cloud Backend

A Cloudflare Worker serves as an API proxy between the app and the AI services. This serverless function handles:

- Secure storage of API keys (never exposed to the client)
- Request routing to OpenAI and Anthropic
- CORS headers for browser compatibility
- Error handling and fallbacks

The Worker adds minimal latency (typically under 50ms) while keeping sensitive credentials secure.

### System Diagram

```
User's Smartphone
    |
    |-- Camera captures video frames
    |
    |-- TensorFlow.js (local)
    |       |
    |       |-- Detects objects (people, chairs, cars, etc.)
    |       |-- Estimates distance from object size
    |       |-- Runs every 300ms
    |
    |-- Cloud AI (remote, every 3 seconds)
    |       |
    |       |-- Cloudflare Worker (API proxy)
    |               |
    |               |-- OpenAI GPT-4o
    |               |-- Anthropic Claude
    |               |-- Returns scene analysis
    |
    |-- Alert System
            |
            |-- Voice synthesis (spoken warnings)
            |-- Spatial audio (directional beeps)
            |-- Vibration patterns (haptic feedback)
```

---

## Key Features

### Automatic Obstacle Detection

The core feature is continuous monitoring. Users don't need to do anything except carry their phone with the camera facing forward. The app handles everything automatically.

Detected object types include:
- People and animals
- Furniture (chairs, tables, couches)
- Vehicles (cars, bicycles, motorcycles)
- Street objects (fire hydrants, parking meters, stop signs)
- Luggage and personal items

### Stair and Step Detection

Falls on stairs are a leading cause of injury for visually impaired individuals. The cloud AI specifically looks for stairs, steps, curbs, and elevation changes. When detected, the app provides an immediate warning with details about the direction (up or down) and any handrails present.

### Voice Commands

Users can interact with the app entirely through voice:

- "What's around" - get a description of the surroundings
- "Is it safe" - check if the path ahead is clear
- "Left" or "Right" - check what's on either side
- "Scan" - trigger a detailed AI analysis
- "Stop" or "Pause" - temporarily disable alerts
- "Resume" - re-enable alerts
- "Help" - hear the list of available commands

Voice recognition activates when the user taps the microphone button, preventing accidental triggers from background conversation.

### Gesture Controls

For quick interactions without speaking, the app supports simple gestures:

- Tap the top third of the screen to describe the area
- Tap the bottom third to trigger an AI scan
- Swipe left or right to check those directions
- Hold for 2 seconds to hear the help guide

These large touch zones are designed for users who can't see the screen. There's no need for precise tapping.

### Directional Audio

The app uses stereo panning to indicate where obstacles are located. Sounds for obstacles on the left come from the left speaker; sounds on the right come from the right speaker. This spatial audio works with both phone speakers and headphones.

### Vibration Patterns

Different vibration patterns communicate different levels of urgency:

- Danger: Five rapid pulses
- Warning: Two medium pulses
- Confirmation: Single short pulse

Users can learn to recognize these patterns and understand the situation even in very noisy environments.

---

## Installation and Setup

### For End Users

The simplest way to use GuideDog is to visit the web app directly:

1. Open Safari (iOS) or Chrome (Android) on your smartphone
2. Navigate to the app URL
3. Allow camera and microphone permissions when prompted
4. The app will speak instructions on first launch

To install as a standalone app:

1. Open the web app in your browser
2. On iOS: Tap Share, then "Add to Home Screen"
3. On Android: Tap the menu, then "Install App" or "Add to Home Screen"
4. The app icon will appear alongside your other apps

### For Developers

To deploy your own instance:

1. Clone the repository
2. Create a Cloudflare account and set up a Worker
3. Add your OpenAI and Anthropic API keys as Worker secrets
4. Update the WORKER_URL in index.html to point to your Worker
5. Deploy the frontend to any static hosting service (GitHub Pages, Vercel, Netlify)

The app consists of just three files (index.html, manifest.json, sw.js), making deployment straightforward.

---

## Usage Guide

### Getting Started

When you first open GuideDog, you'll hear a welcome message explaining the basic controls. The app will ask for camera permission, which is required for obstacle detection.

Once permission is granted, protection begins automatically. Point your phone's camera in the direction you're walking. Most people hold the phone at chest level or attach it to a lanyard.

### Understanding Alerts

**"Stop! [object]! Go [direction]!"** - Something is very close. Stop immediately and move in the suggested direction.

**"Caution, [object] ahead"** - Something is approaching. Slow down and be prepared to stop.

**"Warning! Stairs ahead!"** - Stairs detected. Stop and carefully locate the stairs with your cane or by touch.

**Rapid beeping** - Immediate danger. The beeps come from the direction of the hazard.

**Double beep** - Caution. Something is present but not immediately dangerous.

### Tips for Best Results

- Hold the phone steady with the camera facing forward
- In bright sunlight, try to shade the camera slightly for better detection
- Headphones provide better spatial audio than phone speakers
- In noisy environments, rely more on vibration patterns
- The app works best at walking speed; running may outpace the detection

### Battery Considerations

GuideDog uses the camera and processor continuously, which does consume battery. In our testing, the app uses roughly 20-25% battery per hour of active use. For longer trips, consider bringing a portable charger.

---

## Development Process

### Initial Research

We began by interviewing visually impaired individuals about their navigation challenges. The consistent feedback was that existing solutions either required too much manual interaction or were prohibitively expensive. People wanted something that would just work automatically.

We also studied existing research on assistive technology and consulted accessibility guidelines from the W3C and various blindness organizations.

### Design Decisions

Several key decisions shaped the final product:

**Web-based rather than native**: Building a PWA allowed us to support both iOS and Android from a single codebase. It also means users can start using the app immediately without downloading anything from an app store.

**Hybrid AI approach**: Using both local detection and cloud AI gives us the best of both worlds. Local detection is fast and works offline. Cloud AI can understand complex scenes that confuse simpler models.

**Multi-modal feedback**: We learned early in testing that relying on any single feedback method was insufficient. Voice alerts can be missed in noisy environments. Vibration can be missed if the phone is in a bag. Sound direction is hard to discern from phone speakers. Using all three methods simultaneously ensures the message gets through.

**Conservative alerting**: We tuned the system to only name objects when the detection confidence is high (above 70%). For lower-confidence detections, the app says "obstacle" rather than potentially confusing users with an incorrect object name.

### Version History

The app went through multiple iterations:

- Version 1: Basic object detection and voice output
- Version 2: Added cloud AI integration for scene understanding
- Version 3: Redesigned interface for accessibility with large touch zones
- Version 4: Implemented dual-AI racing for faster responses
- Version 5: Improved voice recognition reliability
- Version 6: Added automatic continuous protection loop
- Version 7: Refined interface based on tester feedback, improved alert clarity

---

## Testing and Validation

### Technical Testing

We tested the app across multiple devices including iPhone 12, iPhone 14, Samsung Galaxy S21, Samsung Galaxy S23, and Google Pixel 7. All devices performed adequately, though newer phones with faster processors provided smoother performance.

Detection accuracy was measured by placing known objects at measured distances and recording whether the app correctly detected them and estimated their distance. The local detection model correctly identified objects in about 93% of cases, with distance estimates accurate to within 0.5 meters for objects closer than 3 meters.

AI response times averaged 1.8 seconds when racing both providers, compared to 2.5-3 seconds when using a single provider.

### User Testing

Five visually impaired individuals tested the app over a two-week period. Testers ranged in age from 16 to 62 and had varying levels of technology experience.

Key findings:

- All testers successfully navigated a test course with multiple obstacles
- Stair detection was highlighted as particularly valuable
- The automatic protection model was strongly preferred over manual scanning
- Voice command recognition worked well in quiet environments
- Battery consumption was a concern for longer outings

Testers suggested several improvements that were incorporated into the final version, including adjustable speech rate and a dedicated microphone button.

### Accessibility Compliance

We verified the app against WCAG 2.1 accessibility guidelines and tested with screen readers (VoiceOver on iOS, TalkBack on Android) to ensure compatibility.

---

## Future Plans

We have several enhancements planned:

**Depth Camera Support**: Newer iPhones include LiDAR sensors that provide accurate depth information. Integrating this data would improve distance estimation significantly.

**Indoor Mapping**: Partnering with indoor mapping providers could enable turn-by-turn navigation inside buildings.

**Transit Integration**: Connecting to public transit APIs would help users locate bus stops and train platforms.

**Multiple Languages**: Adding support for Spanish, Mandarin, Hindi, and other languages.

**Community Hazard Reporting**: Allowing users to report temporary hazards and share them with other GuideDog users.

---

## Acknowledgments

This project would not have been possible without the visually impaired individuals who tested early versions and provided invaluable feedback. Their real-world perspective shaped every aspect of the design.

We're grateful to the open-source community for TensorFlow.js and the various Web APIs that made this project possible.

We acknowledge the AI research teams at OpenAI and Anthropic whose vision models power the scene understanding features.

## Citations

References
TensorFlow.js: Machine Learning for the Web. Google Brain Team. https://www.tensorflow.org/js Apache 2.0 License.
COCO-SSD Object Detection Model. TensorFlow.js Models. https://github.com/tensorflow/tfjs-models/tree/master/coco-ssd Based on the COCO (Common Objects in Context) dataset by Lin, T.Y. et al. (2014).
OpenAI GPT-4o Vision API. OpenAI. https://platform.openai.com/docs/guides/vision
Anthropic Claude Vision API. Anthropic. https://docs.anthropic.com/claude/docs/vision
Web Speech API. W3C Community Group. https://wicg.github.io/speech-api/
Web Audio API. W3C Recommendation. https://www.w3.org/TR/webaudio/
Cloudflare Workers. Cloudflare, Inc. https://workers.cloudflare.com/

---

GuideDog was created with the belief that technology should adapt to people, not the other way around. We hope this tool makes a meaningful difference in the daily lives of visually impaired individuals.
