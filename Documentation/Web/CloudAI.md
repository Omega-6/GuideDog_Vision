# Web Cloud AI Guide

## Reason for Cloud-Based AI Integration

The website has no LiDAR, no ARKit, no Neural Engine. Browsers can't reach any of those sensors or accelerators even when the underlying hardware is present. The website only has the camera image and whatever models can run in the browser through TensorFlow.js or ONNX Runtime Web.

This is a much harder starting point than the iOS app. The local models (COCO-SSD, Depth-Anything, BlindGuideNav, the pixel variance wall check) catch common obstacles, but they share the same limit as the iOS local models: they detect things, they don't understand scenes. They can't tell you there's a low overhanging branch you need to duck under, that the path ahead splits into a sidewalk and a parking lot, that the door on the left is the entrance and the door on the right is staff only, or that the floor changes from concrete to gravel just past the curb. These are exactly the things a sighted companion would mention. They require visual reading, not object detection.

The cloud AI acts as that sighted companion. A vision language model takes one camera frame and describes what it sees. It catches the context the local models can't read.

On the website the cloud AI runs continuously, not on demand. Every 5 seconds the website sends a frame to the cloud and speaks the response. This is the primary compensation for the absence of LiDAR. On the iOS app the cloud AI fires only when the user asks because LiDAR already provides reliable distance. On the website, the local models alone aren't enough, so the cloud AI fills the gap continuously.

## Purpose

The Cloud AI Guide scans the camera feed every 5 seconds and describes what it sees in natural language. Descriptions cover obstacles, stairs, doorways, floor conditions, environmental context, and which direction looks clear for walking.

It doesn't replace the local models. COCO-SSD, Depth-Anything, BlindGuideNav, and the pixel variance wall check keep running. The AI supplements them.

---

## Cloudflare Worker

The website sends requests to a Cloudflare Worker at `guidedog.kpremks.workers.dev`. The Worker forwards the request to both Anthropic and OpenAI. It handles API keys, so the client never has them.

The worker accepts a JSON POST body with:
- `image` - base64 JPEG
- `provider` - "anthropic" or "openai"
- `mode` - "guide" (website) or "app" (iOS)
- `context` - string of COCO-SSD detections

The Worker races both providers and returns whichever responds first. Both routes support streaming via SSE.

---

## Guide mode prompt

When `mode='guide'`, the worker uses `SYSTEM_PROMPT_GUIDE`:

> "You are walking beside a blind person as their sighted guide, helping them navigate their surroundings."

The prompt directs the AI to describe:
- What is directly ahead
- Obstacles and their positions
- Stairs (only if clearly visible)
- Doors and doorways
- Floor conditions (wet, uneven, surface changes)
- General surroundings for orientation
- Which direction appears clear for walking

Responses are limited to under 15 words. Brevity matters because the response is spoken. Long responses delay the next scan and overwhelm the user mid walk.

---

## App mode prompt

The iOS app uses `mode='app'`, which triggers `SYSTEM_PROMPT_APP`. That prompt is safety focused and stair first. It prioritizes hazard detection because the app already has LiDAR for spatial awareness and YOLO for objects. The app needs the AI to catch edge cases, not describe the scene in general.

Both modes use the same Worker. The `mode` parameter picks the prompt. The website needs navigation guidance ("hallway ahead, door on left") because it lacks LiDAR. The app needs hazard confirmation ("stairs detected, stop") because it already has spatial data.

---

## Request flow

### Timing

The cloud scan fires every 5 seconds (`CONFIG.AI_SCAN_INTERVAL = 5000`). This interval balances three things:

1. Token cost. Each request hits both Anthropic and OpenAI. More frequent scans multiply cost.
2. Walking speed. At 1.4 m/s, a person covers 7 m in 5 seconds. Indoor obstacles are usually spaced farther than that. For dense environments, the local models provide continuous coverage between AI scans.
3. Response latency. Cloud responses take 1 to 3 seconds. A 5 second cycle ensures the previous response has come back before the next request fires. `state.aiScanInProgress` prevents overlap.

### Image prep

The system captures a frame from the video to a canvas:
- Background mode: 960px max width, 720px max height, JPEG quality 0.75
- User triggered scan: 1280px max width, 960px max height, JPEG quality 0.9

The canvas is filled with black before drawing the video frame. This stops transparent canvas regions from making `toDataURL` produce a PNG instead of JPEG on iOS, which would balloon the payload.

### COCO-SSD context

Up to 5 high confidence detections are formatted as a context string:

```
person 6ft ahead, chair 3ft left, car 10ft ahead
```

This tells the AI what the local model already found, so the AI can focus on things COCO-SSD can't detect: stairs, floor conditions, environmental hazards, and objects outside the 19 tracked classes.

### Racing providers

The request goes to both Anthropic and OpenAI through `Promise.any()`. First response wins. The other is discarded. Two benefits:

1. Lower latency. The user gets the faster of the two responses.
2. Automatic failover. If one provider is down or slow, the other still responds.

---

## Response handling

### Speaking results

Results are spoken through `speakAlert`. Priority depends on the parsed hazard level:
- Danger (stairs, approaching vehicles): priority 3 (cancels current speech, speaks immediately)
- Warning (walls, wet floors, narrow passages): priority 2 (queues naturally)
- Info (doors, general observations): priority 2

### Hazard parsing

`parseAIResult` checks the response against regex patterns in priority order:

1. **Path clear** (`path clear`, `no hazard`, `all clear`, `nothing`, `safe to proceed`): returns `{ level: 'clear' }`, clears `state.aiHazard`.

2. **Stairs/drops** (`stair`, `step down`, `drop-off`, `ledge`, `descend`, `going down`): DANGER. "Stairs ahead. Stop."

3. **Moving vehicles** (`car approaching`, `vehicle coming`, `cyclist`): DANGER. "Vehicle approaching! Be careful!"

4. **Walls/blocked paths** (`wall`, `dead end`, `blocked`, `barrier`, `fence`, `no through`, `path end`): WARNING. "Wall ahead. Slow down."

5. **Step up/curb** (`step up`, `curb`, `kerb`, `raised`, `bump`, `threshold`): WARNING. "Step up ahead."

6. **Wet/slippery** (`wet`, `slippery`, `icy`, `puddle`, `spill`, `damp`): WARNING. "Caution, wet or slippery floor."

7. **Narrow passage** (`narrow`, `tight gap`, `squeeze`, `low ceiling`, `duck`): WARNING. "Narrow passage or low obstacle ahead."

8. **Door/entrance** (`door`, `doorway`, `entrance`, `exit`, `gateway`, `gate`): INFO. "Door ahead."

9. **Generic hazard** (`hazard`, `caution`, `careful`, `danger`, `obstacle`, `block`): WARNING. Uses the AI text directly if under 80 characters.

10. **Fallback:** if no pattern matches, the result is treated as an INFO note. Text is spoken if under 80 characters.

### Hazard persistence

Parsed hazards are stored in `state.aiHazard` with an expiry timestamp:
- Danger: 4 seconds
- Warning: 3 seconds

After expiry, `state.aiHazard` is set to null. Stops stale AI observations from continuing to trigger alerts after the user has walked past the hazard.

---

## Error handling and backoff

When the Worker returns a non 200 or the fetch throws, exponential backoff kicks in:

| Consecutive failures | Backoff |
|---|---|
| 1 | 10 seconds |
| 2 | 20 seconds |
| 3 | 40 seconds |
| 4+ | 60 seconds (max) |

Tracked by `_aiFailCount` and `_aiBackoffUntil`. Any successful response resets `_aiFailCount` to zero. During backoff, `fetchAI` returns null immediately without making a network request.

Stops the system from hammering a broken endpoint, which would waste battery, consume data, and fill the console with errors. The 60 second max ensures retry happens eventually even after sustained failures.
