# Software Requirements Specification

## GuideDog

**Version:** 1.0  
**Date:** January 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [Interface Requirements](#5-interface-requirements)
6. [System Constraints](#6-system-constraints)

---

## 1. Introduction

### 1.1 Purpose

This document describes what the GuideDog application does.

### 1.2 Scope

GuideDog is a navigation assistance application for visually impaired users. It runs on smartphones and uses the camera to detect obstacles, warning users through voice, sound, and vibration.

The application will:
- Detect common obstacles automatically
- Warn users before they encounter hazards
- Identify stairs, doors, and other important features
- Accept voice commands for additional information
- Work on both iOS and Android devices

The application will not:
- Provide turn-by-turn navigation directions
- Replace a white cane or guide dog entirely
- Work in complete darkness
- Detect every possible hazard

### 1.3 Definitions

**Obstacle**: Any object that could impede walking or cause injury.

**Detection**: The process of identifying an object in the camera view.

**Alert**: A warning delivered to the user through voice, sound, or vibration.

**Walking Path**: The central portion of the camera view where the user is likely to walk.

**Confidence**: A percentage indicating how certain the system is about a detection.

---

## 2. Overall Description

### 2.1 Product Perspective

GuideDog is a standalone application that runs in a web browser on a smartphone. It uses the phone's built-in camera, speakers, and vibration motor. For advanced features, it connects to cloud AI services over the internet.

The application does not require any additional hardware or accessories.

### 2.2 User Classes

**Primary Users: Blind and Visually Impaired Individuals**
- Cannot see the screen
- Rely entirely on audio and haptic feedback
- Need automatic protection without manual intervention
- May have varying levels of technology experience

**Secondary Users: Caregivers and Family Members**
- May help with initial setup
- Can see the screen
- May use the app to understand what the user is experiencing

### 2.3 Operating Environment

- Modern smartphone (iPhone or Android)
- iOS 14 or later, Android 8 or later
- Safari, Chrome, Firefox, or Edge browser
- Rear-facing camera
- Internet connection (for AI features)

### 2.4 Assumptions

- Users will hold the phone with the camera facing forward
- The environment has sufficient lighting for camera-based detection
- Users understand basic smartphone interactions (tapping, swiping)
- Users can hear spoken alerts or feel vibration alerts

---

## 3. Functional Requirements

### 3.1 Obstacle Detection

**REQ-1.1**: The system shall continuously monitor the camera feed for obstacles while active.

**REQ-1.2**: The system shall detect at least the following object types: people, chairs, tables, cars, bicycles, dogs, and common indoor furniture.

**REQ-1.3**: The system shall estimate the distance to detected objects with accuracy of plus or minus 0.5 meters for objects within 3 meters.

**REQ-1.4**: The system shall determine whether detected objects are in the user's walking path.

**REQ-1.5**: The system shall perform local detection at least 3 times per second.

**REQ-1.6**: Detection shall work without an internet connection.

### 3.2 AI Scene Analysis

**REQ-2.1**: The system shall analyze scenes using cloud AI to detect hazards that local detection cannot identify, including stairs, doors, wet floors, and walls.

**REQ-2.2**: The system shall perform AI analysis at least once every 5 seconds when connected to the internet.

**REQ-2.3**: The system shall call multiple AI providers simultaneously and use the fastest response.

**REQ-2.4**: The system shall continue functioning with local detection only if AI services are unavailable.

### 3.3 Alert System

**REQ-3.1**: The system shall alert users when obstacles are detected in their walking path within 2 meters.

**REQ-3.2**: Danger alerts (obstacles less than 1 meter away) shall include:
- A spoken warning identifying the obstacle and escape direction
- Rapid high-pitched audio beeps from the obstacle's direction
- A strong vibration pattern

**REQ-3.3**: Warning alerts (obstacles 1-2 meters away) shall include:
- A spoken caution message
- Medium-pitched audio beeps from the obstacle's direction
- A moderate vibration pattern

**REQ-3.4**: The system shall use spatial audio panning to indicate obstacle direction (left, center, or right).

**REQ-3.5**: The system shall not repeat the same alert within 4 seconds unless the situation changes.

**REQ-3.6**: The system shall only name specific objects when detection confidence exceeds 70 percent. Otherwise, it shall use the generic term "obstacle."

### 3.4 Voice Commands

**REQ-4.1**: The system shall accept voice commands when the user activates the microphone.

**REQ-4.2**: The system shall recognize and respond to the following commands:
- "What's around" - describe the surrounding area
- "Is it safe" - check if the path ahead is clear
- "Left" - describe what's on the left
- "Right" - describe what's on the right
- "Scan" - perform a detailed AI analysis
- "Stop" or "Pause" - temporarily disable alerts
- "Resume" - re-enable alerts
- "Help" - list available commands

**REQ-4.3**: Voice recognition shall have at least 80 percent accuracy in quiet environments.

**REQ-4.4**: Unrecognized commands shall receive a helpful response listing valid commands.

### 3.5 User Interface

**REQ-5.1**: The screen shall be divided into large touch zones that do not require precise tapping:
- Top zone: Trigger area description
- Bottom zone: Trigger AI scan
- Middle zone: Display status

**REQ-5.2**: The system shall support the following gestures:
- Swipe left: Check left side
- Swipe right: Check right side
- Hold for 2 seconds: Show help

**REQ-5.3**: Every touch interaction shall provide haptic confirmation.

**REQ-5.4**: The system shall speak all important information; no critical information shall be conveyed visually only.

### 3.6 Protection Loop

**REQ-6.1**: The system shall begin automatic protection immediately after startup and permission grant.

**REQ-6.2**: The protection loop shall pause when the app is backgrounded and resume when foregrounded.

**REQ-6.3**: Users shall be able to pause and resume automatic alerts via voice command or gesture.

---

## 4. Non-Functional Requirements

### 4.1 Performance

**REQ-7.1**: Local detection shall complete within 300 milliseconds per frame.

**REQ-7.2**: AI analysis shall complete within 3 seconds under normal network conditions.

**REQ-7.3**: Voice alerts shall begin within 500 milliseconds of threat detection.

**REQ-7.4**: The application shall use less than 200 megabytes of memory.

**REQ-7.5**: Battery consumption shall not exceed 30 percent per hour of active use.

### 4.2 Reliability

**REQ-8.1**: The application shall not crash during normal operation.

**REQ-8.2**: Network failures shall not cause the application to stop functioning; local detection shall continue.

**REQ-8.3**: The application shall recover gracefully from errors without requiring a restart.

### 4.3 Accessibility

**REQ-9.1**: The application shall be fully usable without visual feedback.

**REQ-9.2**: All features shall be accessible through voice commands.

**REQ-9.3**: Touch targets shall be at least 48 pixels in size.

**REQ-9.4**: The application shall be compatible with screen readers (VoiceOver, TalkBack).

**REQ-9.5**: The application shall meet WCAG 2.1 Level AA accessibility guidelines.

### 4.4 Security

**REQ-10.1**: API keys shall never be exposed to the client application.

**REQ-10.2**: Camera frames shall not be stored or transmitted except for real-time AI analysis.

**REQ-10.3**: No personal information shall be collected or stored.

### 4.5 Usability

**REQ-11.1**: First-time users shall receive spoken instructions explaining how to use the app.

**REQ-11.2**: The application shall provide consistent feedback for all interactions.

**REQ-11.3**: Error messages shall be spoken in plain language and suggest corrective actions.

---

## 5. Interface Requirements

### 5.1 User Interface

The main screen consists of:

```
+----------------------------------+
|  Status Badge      AI Indicator  |
+----------------------------------+
|                                  |
|          Alert Display           |
|    (icon, message, details)      |
|                                  |
|      Direction Indicators        |
|         (L)  (F)  (R)            |
|                                  |
+----------------------------------+
| [Describe]  [Mic]  [Scan]        |
+----------------------------------+
```

- Status Badge: Shows current safety status (Safe, Caution, Danger)
- AI Indicator: Shows whether AI analysis is active
- Alert Display: Shows current warning or all-clear message
- Direction Indicators: Highlight when obstacles are detected in that direction
- Bottom Buttons: Manual controls for description, voice input, and scanning

### 5.2 Hardware Interfaces

**Camera**
- Rear-facing camera required
- Minimum resolution: 640x480 pixels
- Frame rate: At least 15 frames per second

**Audio Output**
- Speaker or headphones required
- Stereo capability required for directional audio

**Microphone**
- Required for voice commands
- Standard smartphone microphone sufficient

**Vibration**
- Vibration motor required for haptic feedback
- If unavailable, audio alerts shall compensate

### 5.3 Software Interfaces

**TensorFlow.js**
- Provides machine learning inference in the browser
- COCO-SSD model for object detection

**OpenAI API**
- GPT-4o model for vision analysis
- Receives JPEG images, returns text descriptions

**Anthropic API**
- Claude model for vision analysis
- Receives JPEG images, returns text descriptions

**Cloudflare Workers**
- Serverless functions for API proxying
- Stores API keys securely

### 5.4 Communication Interfaces

- HTTPS for all network communication
- JSON format for API requests and responses
- Base64 encoding for image data

---

## 6. System Constraints

### 6.1 Technical Constraints

- Must run in a web browser (no native app installation)
- Must work on devices at least 3 years old
- Must function with JavaScript enabled
- Cannot access device sensors beyond camera, microphone, and vibration

### 6.2 Business Constraints

- Must be free for end users
- Must use free or low-cost hosting infrastructure
- API costs must be manageable for reasonable usage levels

### 6.3 Regulatory Constraints

- Must comply with accessibility regulations
- Must not collect personal data (GDPR/CCPA compliance)
- Must clearly request permissions before accessing camera/microphone

---

## Requirements Traceability

| Requirement | Implementation | Verification |
|-------------|----------------|--------------|
| REQ-1.1 | protectionLoop() | Manual test |
| REQ-1.2 | COCO-SSD model | Model specification |
| REQ-1.3 | estimateDistance() | Distance measurement test |
| REQ-1.4 | inPath calculation | Path detection test |
| REQ-1.5 | 300ms loop interval | Timing measurement |
| REQ-2.1 | analyzeWithAI() | AI response test |
| REQ-2.2 | 3000ms AI interval | Timing measurement |
| REQ-2.3 | Promise.allSettled() | Response time comparison |
| REQ-3.1 | threatLevel logic | Alert trigger test |
| REQ-3.2 | vibrateAlert('danger') | Danger alert test |
| REQ-3.3 | vibrateAlert('warning') | Warning alert test |
| REQ-3.4 | StereoPanner API | Audio direction test |
| REQ-3.5 | lastAlerts tracking | Deduplication test |
| REQ-3.6 | getDisplayName() | Confidence threshold test |
| REQ-4.1 | startListening() | Voice activation test |
| REQ-4.2 | handleVoiceCommand() | Command recognition test |

---

This document defines the requirements for GuideDog version 1.0. Changes to these requirements should be documented and approved before implementation.
