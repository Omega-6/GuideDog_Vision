# Test Plan

## Native App Testing

### LiDAR Detection
- Walk toward a wall. Verify distance updates in real time on screen.
- Verify "Watch out" or "Stop" is spoken when within 3 feet.
- Verify haptic feedback increases as distance decreases.
- Walk away from the wall. Verify status returns to safe within 2 seconds.
- Test in a hallway with walls on both sides. Verify left and right distances are reasonable.

### Object Detection
- Point camera at a person. Verify "Person" is announced within 2 seconds.
- Point camera at a chair. Verify "Chair" is announced.
- Verify that objects far away (beyond 15 feet) are not announced.
- Verify ghost objects are filtered (point at a poster or shadow, confirm no false detection).
- Walk past an object. Verify it is not repeated excessively.

### Mesh Classification
- Walk toward a door. Verify "Door" is announced.
- Walk toward a wall. Verify "Wall" is detected and announced.
- Walk near a window. Verify "Glass" is announced when close.

### Voice Commands
- Hold screen and say "What's around." Verify a description is spoken.
- Hold and say "Is it safe." Verify safety check response.
- Hold and say "Left." Verify left side description.
- Hold and say "Right." Verify right side description.
- Hold and say "Stop." Verify alerts pause.
- Hold and say "Resume." Verify alerts resume.
- Hold and say "Help." Verify help text is spoken.
- Hold and say "Scan." Verify cloud AI scan triggers.

### Cloud AI
- Double tap to trigger a scan. Verify "Scanning" is spoken followed by a description.
- Verify the cloud AI description mentions relevant features (doors, hallways, stairs if present).
- Verify cloud AI does not repeat the exact same description consecutively.
- Disconnect from internet. Double tap to scan. Verify local fallback description is spoken.

### Camera Toggle
- Tap the CAM button. Verify camera preview appears behind the UI.
- Tap again. Verify camera preview disappears.
- Verify all detection continues working with camera preview off.

### Privacy and Help Screens
- Launch the app. Verify privacy screen appears.
- Tap anywhere. Verify it transitions to the features screen.
- Verify features screen is spoken aloud.
- Tap anywhere. Verify the app starts and "Welcome to GuideDog" is spoken (or similar).
- Kill and relaunch. Verify privacy and features screens appear again.

### Permissions
- On first install, verify camera permission dialog appears.
- Verify microphone permission dialog appears when hold-to-speak is first used.
- Verify speech recognition permission dialog appears.
- Deny camera permission. Verify the app handles it gracefully (no crash).

### Non-LiDAR Devices
- Run on an iPhone without LiDAR (ex:. iPhone 13 mini).
- Verify Depth-Anything model loads as fallback.
- Verify wall/obstacle detection still functions (using depth model thresholds).

### AirPods and Bluetooth
- Connect AirPods before launching the app.
- Verify all speech plays through AirPods.
- Verify AirPods remain connected (do not disconnect on app launch).

### Screen Lock
- Leave the app running without touching the screen.
- Verify the screen does not turn off (idle timer disabled).

---

## Website Testing

### Detection
- Open the website on a mobile phone. Allow camera access.
- Point camera at a person. Verify detection is announced.
- Point camera at a wall. Verify "Obstacle ahead" appears.
- Verify the safety level (safe/warning/danger) changes on screen without delay.

### Cloud AI Guide
- After the app starts, wait 5 seconds. Verify a cloud AI description is spoken.
- Verify descriptions are relevant to the actual scene.
- Verify the same description does not repeat consecutively.
- Double tap. Verify "Scanning" is spoken followed by a detailed description.

### Depth Model
- Verify the AI badge shows "AI + Depth Active" after the depth model loads.
- Walk toward a wall. Verify warning or danger state is triggered.
- Walk away. Verify it returns to safe.

### Gestures
- Double tap. Verify cloud AI scan triggers.
- Hold screen for 1 second. Verify "Listening" is spoken.
- While holding, say "What's around." Verify response.
- Swipe left. Verify left side description.
- Swipe right. Verify right side description.

### Privacy and Help Flow
- Open the website. Verify privacy screen appears immediately.
- Tap once. Verify "Welcome to GuideDog" and privacy summary are spoken.
- Tap again. Verify features screen appears and is spoken.
- Tap again. Verify the app starts.

### Speech
- Verify alerts are spoken (not just displayed visually).
- Walk toward an obstacle. Verify "Watch out" is spoken on state change.
- Walk away. Verify "Path clear" is spoken.
- Verify cloud AI descriptions are spoken and audible.

### Browser Compatibility
- Test on iOS Safari (primary target).
- Test on Chrome (desktop and Android).
- Test on Firefox.
- Verify camera access works on each browser.
- Verify speech synthesis works on each browser.

### Offline Behavior
- Disconnect from internet.
- Verify local detection (COCO-SSD, depth model, wall check) continues working.
- Verify cloud AI gracefully fails (no crash, no infinite retry).
- Verify AI backoff kicks in (retries after increasing delays).

---

## Edge Cases

### Low Light
- Test in a dimly lit room. Verify detection still functions (may be degraded).
- Verify cloud AI can still describe the scene.

### Camera Denied
- Deny camera permission when prompted.
- Verify the app/website does not crash.
- Verify an appropriate error message is shown or spoken.

### Crowded Scene
- Point camera at a room with many objects.
- Verify only the most important object is announced (not all of them).
- Verify no speech pile-up occurs.

### Narrow Hallway
- Walk down a narrow hallway.
- Verify walls are detected on sides.
- Verify the app does not spam "obstacle" alerts constantly.

### Fast Movement
- Walk quickly past objects.
- Verify the app keeps up and does not announce stale detections.

---

## Performance Benchmarks

| Metric | Native App | Website |
|--------|-----------|---------|
| Object detection latency | Less than 100ms (CoreML) | 150-200ms (TensorFlow.js) |
| LiDAR depth update | 130ms (every 4 frames) | N/A |
| Wall check (pixel variance) | N/A | Less than 5ms |
| Cloud AI response | 2-5 seconds | 2-5 seconds |
| Speech initiation | Less than 50ms | Less than 100ms |
| UI status update | Instant (no transition) | Instant (no transition) |
| Memory usage | ~150 MB | ~200 MB (with depth model) |
