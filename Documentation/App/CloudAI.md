# Cloud AI Scene Description

## Why cloud AI exists in the iOS app

The app already has LiDAR depth, ARKit mesh classification, YOLOv8n, BlindGuideNav, and DeepLabV3 all running on device. So why send anything to the cloud?

The local layers are fast and reliable but they can't read context. They know a wall is 1.2 m ahead. They know a person is on the right at 3 m. They cannot tell you that the wall has a sign on it that says "Restroom," that the person is a store employee at a service counter, that the floor changes from tile to carpet at the doorway, or that the staircase ahead descends rather than ascends. These are exactly the things a sighted companion would mention. They require reading the scene as a whole, not just detecting individual objects.

A vision language model produces that kind of description from one camera frame in under three seconds. The cloud AI fills the gap between object detection and scene understanding. It's not a replacement for the local layers. It's a layer on top of them.

The cloud AI in the iOS app fires only on demand (user requested scan) or when the scene meaningfully changes (mesh classification delta). It does not run continuously. The local layers handle continuous safety. The cloud AI handles the occasional "what is going on around me?" job.

## AISceneDescriber

The AISceneDescriber provides on demand scene understanding by sending a camera frame to two cloud AI providers at once and speaking whichever response arrives first. The race minimizes latency. Calling one provider would work, but every provider has occasional latency spikes (cold starts, network blips, server load). Sending the same request to two providers in parallel and using whichever wins cuts average response time and provides automatic failover if one is down. The cost is doubled tokens, which is acceptable because cloud AI fires on user demand or scene change, not continuously.

## Providers

Requests go to a Cloudflare Worker at `guidedog.kpremks.workers.dev`. The Worker proxies to:

- **Anthropic (Claude Haiku 4.5):** compact, fast model optimized for visual understanding.
- **OpenAI (GPT-4.1-mini):** small model with strong image analysis.

API keys are stored as Worker secrets, not in the app binary. The app sends only the image and the provider name. The Worker attaches the key and forwards the request.

### System prompt

The Worker uses `SYSTEM_PROMPT_APP`, a safety focused prompt that instructs the model to:
- Describe the scene in 15 words or fewer
- Prioritize stairs, steps, and elevation changes above everything else
- Focus on immediate navigation hazards, not general scene context

This produces concise, actionable descriptions like "Stairs descending ahead, handrail on right" or "Open sidewalk, parked car on left."

## Image prep

Camera frames are prepared on a background thread to avoid blocking the AR pipeline:

1. Convert the CVPixelBuffer to CIImage to CGImage to UIImage.
2. Resize to a maximum dimension of 384 pixels. Enough for scene understanding, keeps the payload small.
3. Compress to JPEG at 0.3 quality. At 384px and 0.3 quality, a typical frame is 15 to 30 KB.
4. Base64 encode.

All of this happens on `DispatchQueue.global(qos: .userInitiated)`. The base64 string then goes in a JSON POST to the Worker.

## Timeout

Each request has a 5 second timeout on the URLSession. If neither provider responds in 5 seconds, the race fails and the `onError` callback fires, which triggers the local fallback description.

## Triggers

### User scan

The user can trigger a scan two ways:
- Double tap on the screen
- Voice command ("scan" or "what's around")

User scans speak the result at user priority (urgency 7.0), which interrupts any current speech. The engine says "Scanning now" immediately, then sends the camera frame to the cloud.

### Scene change

The engine monitors the center mesh classification. When the label changes (for example, wall to door, indicating you've entered a new area) and at least 20 seconds have passed since the last cloud scan, the engine automatically triggers a cloud AI description.

These background scans speak at info priority (urgency 1.0). They don't interrupt danger or caution alerts. If a danger alert is playing, the scene description waits or is dropped.

This trigger was chosen over a timer because it only fires when the scene genuinely changes. A timer would fire every N seconds regardless of whether anything new is visible, wasting tokens.

## Duplicate suppression

When a cloud response arrives, the engine compares the first 80 characters (lowercased) against the previous response. If they match, the new response is not spoken. Stops the app from repeating "Open hallway with doors on both sides" multiple times if the scene hasn't changed.

## Local fallback

If both providers time out, the network is unavailable, or the Worker returns an error, the engine falls back to `describeAreaLocal()`. This constructs a description from local data:

1. Center LiDAR distance in feet, with risk level
2. Left distance in feet
3. Right distance in feet
4. The two most recent YOLO detections (label and direction)

Result: "Ahead, 8 feet, caution. Left, 12 feet. Right, 6 feet. Person ahead. Chair on left." Less descriptive than cloud AI but still actionable without a network.

## Scan suppression

When a scan is active, the `isScanActive` flag suppresses distance band speech for 5 seconds. This prevents "Heads up" or "Something ahead" from interrupting the scan result. Haptics and spatial audio continue because they're different output channels.

After 5 seconds, `isScanActive` resets and normal band announcements resume. The 5 second window is long enough for the race to complete and the response to be spoken.

## Cooldown

The AISceneDescriber enforces a 5 second cooldown between scans. Requests inside the window are silently dropped. Stops rapid fire scans from overwhelming the API and producing a queue of stale descriptions.

## Race implementation

The race uses a `DispatchGroup` with two concurrent URL session data tasks. A boolean flag (`finished`) and an `NSLock` protect first result selection:

1. Both tasks start at once.
2. The first task to return a successful result sets `finished = true` and stores its description.
3. The second task's result is logged but ignored.
4. When both tasks complete (success or failure), the `group.notify` block fires on the main thread.
5. If at least one result arrived, it goes to `onDescription`.
6. If both failed, `onError` fires with a combined error message.
