# GuideDog Vision: Cloud AI Guide

## Purpose

The Cloud AI Guide is the PWA's primary compensation for the absence of LiDAR hardware. On the native iOS app, LiDAR provides precise depth measurements at 60fps, enabling real-time distance sensing for walls, stairs, and obstacles. The PWA has no access to LiDAR. Instead, the cloud AI acts as a sighted guide companion, scanning the camera feed every 5 seconds and describing what it sees in natural language.

The AI does not replace the local detection models. COCO-SSD and Depth-Anything continue to run independently. The AI supplements them by catching things they miss: stairs, floor conditions, signage, narrow passages, doors, and environmental context that object detection alone cannot provide.

---

## Cloudflare Worker

The PWA sends requests to a Cloudflare Worker at `guidedog.kpremks.workers.dev`. This worker acts as a proxy, forwarding the request to both Anthropic and OpenAI APIs. The worker handles API key management, so no API keys are exposed in the client-side code.

The worker accepts a JSON POST body with these fields:
- `image` - base64-encoded JPEG image data
- `provider` - "anthropic" or "openai"
- `mode` - "guide" (website) or "app" (native app)
- `context` - string of COCO-SSD detections for the AI to consider

---

## Guide Mode Prompt

When the website sends `mode='guide'`, the worker uses `SYSTEM_PROMPT_GUIDE`. This prompt instructs the AI:

> "You are walking beside a blind person as their sighted guide, helping them navigate their surroundings."

The prompt directs the AI to describe:
- What is directly ahead
- Obstacles and their positions
- Stairs (only if clearly visible in the image)
- Doors and doorways
- Floor conditions (wet, uneven, changes in surface)
- General surroundings for orientation
- Which direction appears clear for walking

Responses are limited to under 15 words. Brevity matters because the response is spoken aloud. Long responses delay the next scan cycle and overwhelm the user with information while they are trying to walk.

---

## App Mode Prompt (Different Behavior)

The native iOS app uses `mode='app'`, which triggers `SYSTEM_PROMPT_APP`. This prompt is safety-focused and stair-first. It prioritizes hazard detection over environmental description because the native app already has LiDAR for spatial awareness and YOLOv8 for object detection. The app needs the AI to catch edge cases, not describe the general scene.

Both modes use the same Cloudflare Worker. The only difference is which system prompt is selected based on the `mode` parameter. The website needs navigation guidance ("hallway ahead, door on left") because it lacks LiDAR. The app needs hazard confirmation ("stairs detected, stop") because it already has spatial data.

---

## Request Flow

### Timing

The cloud AI scan fires every 5 seconds (`CONFIG.AI_SCAN_INTERVAL = 5000`). This interval balances three concerns:

1. **Token cost.** Each request sends an image and receives a response, consuming API tokens on both Anthropic and OpenAI. Running more frequently would increase costs significantly.
2. **Responsiveness.** The user is walking and the environment changes. Five seconds is fast enough to catch new obstacles before the user reaches them at normal walking speed (about 1.4 meters per second, covering 7 meters in 5 seconds).
3. **Network latency.** Cloud AI responses take 1 to 3 seconds to return. Running scans more frequently would cause overlapping requests. The `state.aiScanInProgress` flag prevents this.

### Image Preparation

The system captures a frame from the video feed onto a canvas:
- Background mode: 960px max width, 720px max height, JPEG quality 0.75
- Detailed mode (user-triggered scan): 1280px max width, 960px max height, JPEG quality 0.9

The canvas is filled with black before drawing the video frame. This prevents transparent canvas regions from causing the `toDataURL` call to produce a PNG instead of JPEG on iOS, which would significantly increase the payload size.

### COCO-SSD Context

Up to 5 high-confidence COCO-SSD detections are formatted as a context string:

```
person 6ft ahead, chair 3ft left, car 10ft ahead
```

This context is sent alongside the image so the AI knows what the local model already detected. The AI can then focus on things COCO-SSD cannot detect: stairs, floor conditions, environmental hazards, and objects outside the 19 tracked classes.

### Racing Providers

The request is sent to both Anthropic and OpenAI simultaneously using `Promise.any()`. The first response to arrive is used. The other response is discarded. This provides two benefits:

1. **Lower latency.** The user gets the faster of the two responses, reducing the delay before hearing the AI description.
2. **Automatic failover.** If one provider is down or slow, the other still provides a response. The system does not need explicit failover logic.

---

## Response Handling

### Speaking Results

Cloud AI results are spoken directly via `speakAlert`. The priority depends on the parsed hazard level:
- Danger hazards (stairs, approaching vehicles): priority 3 (cancels current speech, speaks immediately)
- Warning hazards (walls, wet floors, narrow passages): priority 2 (queues naturally)
- Info (doors, general observations): priority 2

### Hazard Parsing

The `parseAIResult` function extracts structured hazard data from the AI's natural language response. It checks the response text against a series of regex patterns in priority order:

1. **Path clear** patterns (`path clear`, `no hazard`, `all clear`, `nothing`, `safe to proceed`): Returns `{ level: 'clear' }`, which clears `state.aiHazard`.

2. **Stairs/drops** (`stair`, `step down`, `drop-off`, `ledge`, `descend`, `going down`): DANGER. Speak: "Stairs ahead. Stop."

3. **Moving vehicles** (`car approaching`, `vehicle coming`, `cyclist`): DANGER. Speak: "Vehicle approaching! Be careful!"

4. **Walls/blocked paths** (`wall`, `dead end`, `blocked`, `barrier`, `fence`, `no through`, `path end`): WARNING. Speak: "Wall ahead. Slow down."

5. **Step up/curb** (`step up`, `curb`, `kerb`, `raised`, `bump`, `threshold`): WARNING. Speak: "Step up ahead."

6. **Wet/slippery** (`wet`, `slippery`, `icy`, `puddle`, `spill`, `damp`): WARNING. Speak: "Caution, wet or slippery floor."

7. **Narrow passage** (`narrow`, `tight gap`, `squeeze`, `low ceiling`, `duck`): WARNING. Speak: "Narrow passage or low obstacle ahead."

8. **Door/entrance** (`door`, `doorway`, `entrance`, `exit`, `gateway`, `gate`): INFO. Speak: "Door ahead."

9. **Generic hazard** (`hazard`, `caution`, `careful`, `danger`, `obstacle`, `block`): WARNING. Uses the AI text directly if under 80 characters.

10. **Fallback**: If no pattern matches, the result is treated as an INFO-level AI note. The text is spoken if under 80 characters.

### Hazard Persistence

Parsed hazards are stored in `state.aiHazard` with an expiry timestamp:
- Danger hazards persist for 4 seconds
- Warning hazards persist for 3 seconds

After expiry, `state.aiHazard` is set to null. This prevents stale AI observations from continuing to trigger alerts after the user has walked past the hazard.

---

## Error Handling and Backoff

When the Cloudflare Worker returns a non-200 status code or the fetch request throws an error, the system applies exponential backoff:

| Consecutive failures | Backoff duration |
|---------------------|-----------------|
| 1 | 10 seconds |
| 2 | 20 seconds |
| 3 | 40 seconds |
| 4+ | 60 seconds (maximum) |

The backoff is tracked by `_aiFailCount` and `_aiBackoffUntil`. Any successful response resets `_aiFailCount` to zero. During the backoff period, `fetchAI` returns null immediately without making a network request.

This prevents the system from hammering a broken endpoint, which would waste battery, consume mobile data, and fill the console with error messages. The maximum 60-second backoff ensures the system eventually retries even after sustained failures.
