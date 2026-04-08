# Requirements

## Purpose

GuideDog Vision is a navigation assistant designed to help blind and visually impaired individuals move safely through indoor and outdoor environments. The system uses a combination of on-device AI models, hardware sensors, and cloud AI to detect obstacles, identify hazards, and provide real time audio guidance.

## Target Users

- Blind individuals navigating independently
- Visually impaired individuals who need supplementary awareness
- Sighted companions who want to understand what the app detects (via camera preview)

## Platform Requirements

### Native iOS App

| Requirement | Details |
|-------------|---------|
| Operating System | iOS 15.0 or later |
| Device | iPhone (iPad not supported) |
| Recommended | iPhone 12 Pro or later (LiDAR equipped) |
| Camera | Rear camera access required |
| Microphone | Required for voice commands |
| Speech Recognition | Required for voice input |
| Storage | Approximately 50 MB (app + models) |
| Internet | Required for cloud AI features (optional for core detection) |

### PWA Website

| Requirement | Details |
|-------------|---------|
| Browser | Chrome, Safari, or Firefox (modern versions) |
| Protocol | HTTPS required (for camera access) |
| Camera | Rear camera access required |
| Internet | Required for cloud AI and model downloads |
| Device | Mobile phone recommended (camera facing forward while walking) |

## Functional Requirements

### Core Detection

1. The system must detect obstacles in the user's walking path and announce them via speech.
2. The system must provide real time distance information (native app via LiDAR, website via depth estimation).
3. The system must distinguish between danger (very close), warning (approaching), and safe states.
4. The system must update the safety level on screen without noticeable delay.

### Object Detection

5. The system must identify common navigation obstacles: people, chairs, tables, vehicles, benches, and similar objects.
6. The system must filter out irrelevant detections (food items, small objects, animals).
7. The system must require a minimum confidence of 70% before naming an object.
8. The system must use a consecutive detection filter to eliminate ghost detections.

### Cloud AI

9. The system must send camera frames to cloud AI for scene description when triggered by the user (double tap) or automatically (website every 5 seconds).
10. The system must prioritize stair and step detection in cloud AI responses.
11. The system must provide a local fallback description when cloud AI is unavailable.
12. The system must not repeat the same cloud AI description consecutively.

### Audio Output

13. The system must speak all safety level changes (safe, warning, danger).
14. The system must use priority-based speech so that danger alerts are never interrupted by lower priority messages.
15. The system must provide haptic feedback that matches the urgency of detected hazards (native app only).
16. The system must not overwhelm the user with excessive or overlapping speech.

### User Input

17. The system must support gesture-based interaction: hold to speak, double tap to scan, swipe to check sides.
18. The system must support voice commands: "what's around", "is it safe", "left", "right", "stop", "resume", "scan", "help".
19. The system must work without any visible buttons (gesture-only interface).

### Privacy and Onboarding

20. The system must show a privacy notice and feature overview on every launch.
21. The system must speak the privacy notice and features aloud for blind users.
22. The system must allow the user to progress through screens by tapping anywhere.
23. The system must not require any account creation or personal data.

### Accessibility

24. The system must keep the screen awake during navigation (native app).
25. The system must disable zoom and text selection to prevent accidental interactions.
26. The system must work with AirPods and Bluetooth headphones without disconnecting them (native app).
27. The system must support VoiceOver labeling on interactive elements (aria-label attributes).

## API Dependencies

| Service | Purpose | Required |
|---------|---------|----------|
| Cloudflare Worker | Proxy for cloud AI requests | Yes (for cloud features) |
| Anthropic API | Claude Haiku 4.5 scene description | Yes (for cloud features) |
| OpenAI API | GPT-4.1-mini scene description | Yes (for cloud features) |
| HuggingFace CDN | Depth-Anything model download | Yes (website depth model) |
| jsDelivr CDN | TensorFlow.js and COCO-SSD | Yes (website detection) |

## Non-Functional Requirements

- Object detection latency must be under 200ms on the native app.
- UI safety level updates must appear within 50ms of state change.
- Cloud AI responses must be received within 5 seconds or the request times out.
- The app must not crash when permissions are denied.
- The app must handle poor network conditions gracefully with exponential backoff.
- The website must load the privacy screen within 2 seconds of page open.
