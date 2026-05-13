# Test Plan

## iOS app

### LiDAR detection

- Walk toward a wall. Distance updates in real time on screen.
- "Watch out" or "Stop" spoken within 3 feet.
- Haptic feedback gets faster as distance decreases.
- Walk away. Status returns to safe within 2 seconds.
- Hallway with walls on both sides. Left and right distances are reasonable.

### Object detection

- Point at a person. "Person" announced within 2 seconds.
- Point at a chair. "Chair" announced.
- Far away objects (beyond 15 feet) are not announced.
- Ghost filtering works (point at a poster or shadow, no false detection).
- Walk past an object. Not repeated excessively.
- YOLO + Apple human detector agreement: point at a poster of a person. "Person" should NOT be announced because Apple's human detector won't see a real human.

### Wall inference

- Point at a blank painted wall in good lighting. ARKit should drop to `.limited(.insufficientFeatures)`. Wall inference should still fire because all three depth zones are uniform.
- Announcements should escalate by distance: "Wall ahead" under 3 m, "Wall, X feet" under 2 m, "Wall nearby" under 1 m.
- `closestWall` accessor: verify the nearest wall gets announced regardless of which direction zone it's in.

### Mesh classification

- Walk toward a door. "Door" announced.
- Walk toward a wall (with features for ARKit). "Wall" detected and announced.
- Walk near a window. "Glass" announced when close.
- Mesh range goes out to 6 meters (was 4); verify walls get caught earlier.

### Voice commands

- Hold screen and say "What's around." Description spoken.
- "Is it safe." Safety check response.
- "Left." Left side description.
- "Right." Right side description.
- "Stop." Alerts pause.
- "Resume." Alerts resume.
- "Help." Help text spoken.
- "Scan." Cloud AI scan triggers.

### Cloud AI

- Double tap. "Scanning" spoken, then a description.
- Description mentions relevant features (doors, hallways, stairs if present).
- Doesn't repeat the same description consecutively.
- Disconnect internet. Double tap. Local fallback description spoken.

### Camera toggle

- Tap CAM. Camera preview appears behind the UI.
- Tap again. Preview disappears.
- All detection still works with preview off.

### Privacy and help

- Launch the app. Privacy screen appears.
- Tap. Transitions to the features screen.
- Features screen spoken aloud.
- Tap. App starts.
- Engine startup speech: "Loading. One moment." right away, then "GuideDog active." after the first depth callback.
- Kill and relaunch. Privacy and features screens appear again.

### Permissions

- First install. Camera permission dialog appears.
- Microphone permission appears when hold to speak is used.
- Speech recognition permission appears.
- Deny camera permission. App handles it (no crash).

### Non LiDAR devices

- Run on a non LiDAR iPhone (iPhone 13 mini).
- Depth-Anything model loads as fallback (preloaded on launch).
- Engine starts instantly when START tapped.
- Wall and obstacle detection still functions.
- Speech drops the "feet" suffix ("Person right" instead of "Person, 6 feet").

### AirPods and Bluetooth

- Connect AirPods before launching.
- All speech plays through AirPods.
- AirPods stay connected.

### Screen lock

- Leave the app running without touching the screen.
- Screen doesn't turn off (idle timer disabled).

---

## Website

### Detection

- Open the website on a mobile phone. Allow camera.
- Point at a person. Detection announced.
- Point at a wall. "Obstacle ahead" appears.
- Safety level changes on screen without delay.

### Cloud AI guide

- Wait 5 seconds after the app starts. Cloud AI description spoken.
- Descriptions are relevant to the scene.
- Same description doesn't repeat consecutively.
- Double tap. "Scanning" spoken, then detailed description.

### Depth model

- AI badge shows "AI + Depth Active" after the depth model loads.
- Walk toward a wall. Warning or danger state triggered.
- Walk away. Returns to safe.

### Gestures

- Double tap. Cloud AI scan triggers.
- Hold screen for 1 second. "Listening" spoken.
- While holding, say "What's around." Response.
- Swipe left. Left side description.
- Swipe right. Right side description.

### Homepage

- Land on the homepage. Welcome message plays: "Welcome to GuideDog. Press anywhere on the page for obstacle detection, or the second button for sounds and captions."
- Tap anywhere on the page. Welcome speech cancels. See mode (guide mode) starts.
- Tap the "Hear" button specifically. Hear mode starts (not See mode).
- Verify hero copy: "Eyes and ears, when you need them." with blue accent on "when you need them."

### Hear mode

- Sound classifier loads. Ring a doorbell or play a siren clip. Bucket label appears.
- Speak nearby. Live captions appear.

### Privacy and help

- Open the website. Privacy screen appears immediately.
- Silent mode reminder card is visible.
- Tap once. "Welcome to GuideDog" and privacy summary spoken.
- Tap again. Features screen appears and is spoken.
- Tap again. App starts.

### Speech

- Alerts are spoken (not just displayed).
- Walk toward an obstacle. "Watch out" spoken on state change.
- Walk away. "Path clear" spoken.
- Cloud AI descriptions are spoken and audible.

### Browser compatibility

- iOS Safari (primary target).
- Chrome (desktop and Android).
- Firefox.
- Camera access works on each.
- Speech synthesis works on each.

### Offline

- Disconnect internet.
- Local detection (COCO-SSD, depth model, wall check) keeps working.
- Cloud AI fails gracefully (no crash, no infinite retry).
- AI backoff kicks in (retries after increasing delays).

### Service worker

- Verify the cache version is `guidedog-v48`.
- Reload offline. App shell loads from cache.

---

## Edge cases

### Low light

- Dimly lit room. Detection still functions (may be degraded).
- Cloud AI can still describe the scene.

### Camera denied

- Deny camera permission.
- App/website doesn't crash.
- Appropriate error message is shown or spoken.

### Crowded scene

- Point at a room with many objects.
- Only the most important object is announced.
- No speech pile up.

### Narrow hallway

- Walk down a narrow hallway.
- Walls detected on sides.
- No constant "obstacle" alert spam.

### Fast movement

- Walk quickly past objects.
- App keeps up and doesn't announce stale detections.

---

## Performance benchmarks

| Metric | iOS App | Website |
|--------|-----------|---------|
| Object detection latency | < 100 ms (CoreML) | 150 to 200 ms (TensorFlow.js) |
| LiDAR depth update | 130 ms (every 4 frames) | N/A |
| Wall check (pixel variance) | N/A | < 5 ms |
| Cloud AI response | 2 to 5 seconds | 2 to 5 seconds |
| Depth-Anything (CoreML, iOS) | ~9 ms on iPhone 13 | N/A |
| Speech initiation | < 50 ms | < 100 ms |
| UI status update | Instant (no transition) | Instant (no transition) |
| Memory usage | ~150 MB | ~200 MB (with depth model) |
