# Technical Documentation

## GuideDog - Code Architecture and Implementation Details

This document provides detailed technical information about the GuideDog codebase. It's intended for developers who want to understand, modify, or extend the application.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Application Architecture](#application-architecture)
3. [Core Modules](#core-modules)
4. [Key Algorithms](#key-algorithms)
5. [API Integration](#api-integration)
6. [Configuration Options](#configuration-options)
7. [Performance Considerations](#performance-considerations)
8. [Debugging Guide](#debugging-guide)

---

## Project Structure

The application is deliberately simple, consisting of only three files:

```
GuideDog/
    index.html      - Complete application (HTML, CSS, and JavaScript)
    manifest.json   - PWA manifest for installation
    sw.js           - Service Worker for offline support
```

We chose a single-file architecture for several reasons:

1. Simpler deployment (just copy three files to any web server)
2. Easier to understand (all code in one place)
3. Better offline caching (fewer files to manage)
4. No build step required

For a production application with a larger team, you might split the JavaScript into separate modules. For this project, keeping everything together made development and debugging faster.

---

## Application Architecture

The application follows a straightforward event-driven architecture. Here's how the pieces fit together:

### Initialization Flow

When the page loads:

1. The `init()` function runs
2. Camera permission is requested
3. TensorFlow.js loads the COCO-SSD model
4. Event listeners are attached for touch and button interactions
5. Speech recognition is initialized (if supported)
6. The protection loop begins

### Main Loop

The heart of the application is the `protectionLoop()` function. It runs continuously while the app is active:

```
protectionLoop()
    |
    |-- Run local object detection (every 300ms)
    |
    |-- Calculate threat level for each detection
    |       - Is it in the walking path?
    |       - How close is it?
    |       - What type of object is it?
    |
    |-- Trigger AI analysis (every 3 seconds)
    |       - Send frame to cloud
    |       - Check for stairs, doors, etc.
    |
    |-- Generate alerts if needed
    |       - Voice warnings
    |       - Audio beeps
    |       - Vibration patterns
    |
    |-- Update the visual display
    |
    |-- Schedule next iteration
```

### State Management

All application state lives in a single `state` object:

```javascript
const state = {
    video: null,           // Reference to the video element
    model: null,           // TensorFlow.js model
    isRunning: false,      // Is the protection loop active?
    isPaused: false,       // Has the user paused alerts?
    localDetections: [],   // Current frame's detected objects
    aiResult: null,        // Latest AI analysis result
    lastAIScan: 0,         // Timestamp of last AI call
    currentStatus: 'safe', // Current threat level
    currentObstacle: null, // Most dangerous current detection
    lastAlerts: {},        // Tracks recent alerts to prevent spam
    lastVibrate: 0,        // Timestamp of last vibration
    lastVoice: 0,          // Timestamp of last voice output
    recognition: null,     // Speech recognition instance
    isListening: false,    // Is voice recognition active?
    audioCtx: null         // Web Audio API context
};
```

This centralized state makes it easy to understand what data the application is tracking and to debug issues.

---

## Core Modules

The JavaScript code is organized into logical sections. Here's what each section does:

### Configuration

The `CONFIG` object holds all adjustable parameters:

```javascript
const CONFIG = {
    WORKER_URL: "https://guidedog.kpremks.workers.dev",
    
    // Distance thresholds (meters)
    DANGER_ZONE: 1.0,
    WARNING_ZONE: 2.0,
    AWARENESS_ZONE: 4.0,
    
    // Timing (milliseconds)
    AI_SCAN_INTERVAL: 3000,
    LOCAL_SCAN_INTERVAL: 300,
    VOICE_COOLDOWN: 2000,
    VIBRATE_COOLDOWN: 500,
    
    // Detection confidence threshold
    HIGH_CONFIDENCE: 0.7,
    
    // Object classifications
    CRITICAL: ["car", "bus", "truck", "motorcycle", "bicycle", "train"],
    OBSTACLES: ["person", "dog", "chair", "bench", ...]
};
```

Changing these values lets you tune the application's behavior. For example, increasing `DANGER_ZONE` to 1.5 would trigger danger alerts earlier, giving users more reaction time.

### Audio System

The audio module creates directional beeps using the Web Audio API:

```javascript
function playBeep(frequency, duration, pan, volume) {
    // Create oscillator (the sound source)
    const osc = audioCtx.createOscillator();
    osc.frequency.value = frequency;
    
    // Create gain node (volume control)
    const gain = audioCtx.createGain();
    gain.gain.setValueAtTime(volume, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
    
    // Create panner (left/right positioning)
    const panner = audioCtx.createStereoPanner();
    panner.pan.value = pan;  // -1 = left, 0 = center, 1 = right
    
    // Connect the nodes
    osc.connect(gain);
    gain.connect(panner);
    panner.connect(audioCtx.destination);
    
    // Play the sound
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
}
```

The `playAlertSound()` function uses this to create different patterns:
- Danger: Three rapid high-pitched beeps
- Warning: Two medium beeps
- Info: Single soft beep

### Speech System

Voice output uses the Web Speech API's synthesis feature:

```javascript
function speak(text, force) {
    // Rate limiting
    if (!force && Date.now() - state.lastVoice < VOICE_COOLDOWN) {
        return;
    }
    
    // Stop any ongoing speech
    speechSynthesis.cancel();
    
    // Create and speak the utterance
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.volume = 1.0;
    speechSynthesis.speak(utterance);
    
    state.lastVoice = Date.now();
}
```

The `speakAlert()` function adds deduplication to prevent repeating the same warning:

```javascript
function speakAlert(key, text) {
    if (Date.now() - (state.lastAlerts[key] || 0) < 4000) {
        return;  // Don't repeat within 4 seconds
    }
    state.lastAlerts[key] = Date.now();
    speak(text, true);
}
```

### Voice Recognition

Voice input uses the Web Speech API's recognition feature:

```javascript
function initSpeechRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    state.recognition = new SR();
    state.recognition.continuous = false;
    state.recognition.interimResults = false;
    state.recognition.lang = 'en-US';
    
    state.recognition.onresult = (event) => {
        const text = event.results[0][0].transcript.toLowerCase();
        handleVoiceCommand(text);
    };
}
```

The `handleVoiceCommand()` function maps recognized phrases to actions:

```javascript
function handleVoiceCommand(text) {
    if (text.includes('around') || text.includes('describe')) {
        describeArea();
    } else if (text.includes('safe')) {
        checkSafety();
    } else if (text.includes('left')) {
        speakDirection('left');
    }
    // ... and so on
}
```

### Local Detection

Object detection uses TensorFlow.js with the COCO-SSD model:

```javascript
async function detectLocal() {
    const predictions = await state.model.detect(state.video);
    
    return predictions.map(p => {
        // Calculate position (left, center, right)
        const centerX = (p.bbox[0] + p.bbox[2] / 2) / videoWidth;
        let position = 'ahead';
        if (centerX < 0.35) position = 'left';
        else if (centerX > 0.65) position = 'right';
        
        // Estimate distance from size
        const size = Math.max(p.bbox[2], p.bbox[3]) / maxDimension;
        const distance = estimateDistance(size);
        
        // Check if in walking path
        const inPath = centerX > 0.25 && centerX < 0.75;
        
        return {
            name: p.class,
            position: position,
            distance: distance,
            inPath: inPath,
            confidence: p.score
        };
    });
}
```

### AI Analysis

Cloud AI analysis handles complex scene understanding:

```javascript
async function analyzeWithAI() {
    // Capture frame to canvas
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    canvas.getContext('2d').drawImage(state.video, 0, 0, 640, 480);
    
    // Convert to base64 JPEG
    const imageData = canvas.toDataURL('image/jpeg', 0.7).split(',')[1];
    
    // Race both AI providers
    const results = await Promise.allSettled([
        fetchAI(imageData, 'openai'),
        fetchAI(imageData, 'anthropic')
    ]);
    
    // Return first successful response
    for (const r of results) {
        if (r.status === 'fulfilled' && r.value) {
            return r.value;
        }
    }
    return null;
}
```

---

## Key Algorithms

### Distance Estimation

We estimate real-world distance based on how large an object appears in the camera frame. The relationship isn't linear, so we use a lookup approach:

```javascript
function estimateDistance(relativeSize) {
    if (relativeSize > 0.60) return 0.5;   // Very large = very close
    if (relativeSize > 0.45) return 1.0;
    if (relativeSize > 0.30) return 1.5;
    if (relativeSize > 0.20) return 2.0;
    if (relativeSize > 0.10) return 3.0;
    if (relativeSize > 0.05) return 4.0;
    return 5.0;                             // Small = far away
}
```

These thresholds were calibrated empirically by measuring actual distances and recording the corresponding object sizes. The accuracy is roughly plus or minus 0.5 meters for objects closer than 3 meters.

### Threat Assessment

The protection loop assesses threat level for each detected object:

```javascript
for (const detection of detections) {
    // Ignore objects not in the walking path
    if (!detection.inPath) continue;
    
    // Check distance against thresholds
    if (detection.distance < DANGER_ZONE) {
        threatLevel = 'danger';
        mostDangerous = detection;
        break;  // Immediate danger, stop searching
    } else if (detection.distance < WARNING_ZONE) {
        if (threatLevel !== 'danger') {
            threatLevel = 'warning';
            mostDangerous = detection;
        }
    }
}
```

Objects are also prioritized by type. A car at 2 meters is more dangerous than a chair at 2 meters, so we check against the `CRITICAL` and `OBSTACLES` lists.

### Confidence-Based Naming

To avoid confusing users with incorrect object identifications, we only name objects when confidence is high:

```javascript
function getDisplayName(detection) {
    if (detection.confidence >= CONFIG.HIGH_CONFIDENCE) {
        return detection.name;  // "chair", "person", etc.
    } else {
        return 'obstacle';      // Generic fallback
    }
}
```

This means a detection with 60% confidence will be announced as "obstacle ahead" rather than potentially wrong information like "refrigerator ahead" (when it's actually a filing cabinet).

---

## API Integration

### Cloudflare Worker

The Worker handles API calls securely:

```javascript
export default {
    async fetch(request, env) {
        const { image, provider } = await request.json();
        
        const prompt = `You help a blind person navigate. In 1-2 sentences, 
                        describe only critical safety info: stairs, steps, 
                        doors, wet floors, obstacles.`;
        
        let result;
        if (provider === 'anthropic') {
            result = await callAnthropic(env.ANTHROPIC_API_KEY, image, prompt);
        } else {
            result = await callOpenAI(env.OPENAI_API_KEY, image, prompt);
        }
        
        return new Response(JSON.stringify({ result }));
    }
};
```

API keys are stored as Worker secrets and never sent to the client.

### Request Format

The client sends:
```json
{
    "image": "<base64-encoded-jpeg>",
    "provider": "openai" | "anthropic"
}
```

The Worker returns:
```json
{
    "result": "Stairs going down ahead, about 5 steps. Handrail on right."
}
```

---

## Configuration Options

### Adjusting Sensitivity

To make alerts trigger earlier (more cautious):
```javascript
DANGER_ZONE: 1.5,   // Was 1.0
WARNING_ZONE: 3.0,  // Was 2.0
```

To reduce false alerts (less cautious):
```javascript
DANGER_ZONE: 0.7,
WARNING_ZONE: 1.5,
```

### Adjusting Timing

For more frequent AI scans (uses more data):
```javascript
AI_SCAN_INTERVAL: 2000,  // Was 3000
```

For less frequent local scans (saves battery):
```javascript
LOCAL_SCAN_INTERVAL: 500,  // Was 300
```

### Adding Object Types

To treat additional objects as critical:
```javascript
CRITICAL: ["car", "bus", "truck", "motorcycle", "bicycle", "train", "skateboard"]
```

---

## Performance Considerations

### Battery Usage

The main battery consumers are:
1. Camera capture (continuous)
2. TensorFlow.js inference (every 300ms)
3. Screen display

To reduce battery usage:
- Lower the camera resolution
- Increase the scan interval
- Dim the screen (or turn it off entirely)

### Memory Usage

The COCO-SSD model uses approximately 50MB of memory. Combined with the video stream and application code, total memory usage is typically around 150-180MB.

If memory becomes an issue on older devices, you could:
- Reduce camera resolution
- Process every other frame instead of every frame

### Network Usage

Each AI analysis call sends a JPEG image (roughly 30-50KB compressed) and receives a text response. At one call every 3 seconds, this works out to approximately 0.5-1MB per minute when the app is actively using cloud AI.

---

## Debugging Guide

### Console Logging

The application logs key events to the console:
- "Speaking: [text]" for voice output
- "Heard: [text]" for voice input
- "AI error: [details]" for API issues

Open the browser developer tools to see these logs.

### Common Issues

**No voice output**: The browser requires user interaction before playing audio. Make sure the user has tapped something on the page first.

**Camera not working**: Check that camera permissions were granted. Some browsers require HTTPS for camera access.

**AI analysis failing**: Check the browser console for error messages. Common causes are network issues or API key problems.

**Poor detection accuracy**: Make sure there's adequate lighting. The COCO-SSD model struggles in very dark or very bright conditions.

### Testing Without a Device

You can test most functionality on a desktop computer with a webcam. The voice and vibration features will behave differently, but the core detection logic will work.

---

## Code Style Notes

The codebase follows these conventions:

- Functions are named with camelCase
- Constants are UPPER_SNAKE_CASE
- Comments explain "why" rather than "what"
- Error handling uses try-catch with silent fallbacks (the app should never crash)
- All browser APIs are feature-detected before use

The code prioritizes readability over cleverness. Where a more elegant solution would be harder to understand, we chose the simpler approach.

---

This documentation covers the main technical aspects of GuideDog. For questions not addressed here, examine the source code directly or contact the development team.
