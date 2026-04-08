# Cloud AI Scene Description

## Why Cloud AI Exists

The native iOS app already has LiDAR depth sensing, ARKit mesh classification, YOLOv8n object detection, BlindGuideNav navigation detection, and DeepLabV3 semantic segmentation. All five layers run on the device with no network access required. So why send anything to the cloud at all?

The local detection layers are fast and reliable but they cannot read context. They know that a wall is 1.2 meters ahead. They know that a person is on the right at 3 meters. They cannot tell the user that the wall has a sign on it that says "Restroom," that the person is a store employee at a service counter, that the floor changes from tile to carpet at the doorway, or that the staircase ten feet ahead descends rather than ascends. These are exactly the kinds of details a sighted companion would mention. They require visual reading of the scene as a whole, not detection of individual objects.

A general purpose vision language model can produce that kind of description from a single camera frame in under three seconds. The cloud AI fills the gap between object detection and scene understanding. It is not a replacement for the local detection layers. It is a layer on top of them that catches the context they miss.

The cloud AI in the iOS app fires only on demand (user requested scan) or when the scene meaningfully changes (mesh classification delta). It does not run continuously. The local layers handle the continuous safety job, and the cloud AI handles the occasional "what is going on around me?" job that the local layers cannot answer alone.

## AISceneDescriber

The AISceneDescriber provides on demand scene understanding by sending a camera frame to two cloud AI providers simultaneously and speaking whichever response arrives first. This AI race approach minimizes latency, because the user hears the fastest response regardless of which provider won.

**Why race two providers.** Calling one provider would still work, but every provider has occasional latency spikes (cold starts, network blips, server load). Sending the same request to two providers in parallel and using whichever response arrives first cuts the average response time and provides automatic failover if one provider is down. The cost is a doubled token spend, which is acceptable because cloud AI fires only on user demand or scene change, not continuously.

## Providers and Infrastructure

The app sends requests to a Cloudflare Worker at `guidedog.kpremks.workers.dev`. The Worker proxies the request to two AI providers:

- **Anthropic (Claude Haiku 4.5):** A compact, fast model optimized for visual understanding.
- **OpenAI (GPT-4.1-mini):** A small model with strong image analysis capabilities.

API keys are stored as Worker secrets, not in the app binary. The app sends only the image and the provider name. The Worker attaches the API key and forwards the request.

### System Prompt

The Worker uses `SYSTEM_PROMPT_APP`, a safety-focused prompt that instructs the model to:
- Describe the scene in 15 words or fewer.
- Prioritize stairs, steps, and elevation changes above all other features.
- Focus on immediate navigation hazards rather than general scene context.

This prompt produces concise, actionable descriptions like "Stairs descending ahead, handrail on right" or "Open sidewalk, parked car on left."

## Image Preparation

Camera frames are prepared for upload on a background thread to prevent blocking the AR frame pipeline:

1. Convert the CVPixelBuffer to a CIImage, then to a CGImage, then to a UIImage.
2. Resize to a maximum dimension of 384 pixels. This resolution is sufficient for scene understanding while keeping the payload small.
3. Compress to JPEG at 0.3 quality. This aggressive compression further reduces payload size. At 384px and 0.3 quality, a typical frame is roughly 15 to 30 KB.
4. Base64-encode the JPEG data.

All of this processing happens on a `DispatchQueue.global(qos: .userInitiated)` thread. The base64 string is then sent in a JSON POST body to the Worker.

## Timeout

Each request has a 5-second timeout configured on the URLSession. If neither provider responds within 5 seconds, the race fails and the `onError` callback fires, which triggers a local fallback description.

## Trigger Conditions

### User-Initiated Scan

The user can trigger a scan in two ways:
- **Double-tap gesture** on the screen.
- **Voice command** ("scan" or "what's around").

User-initiated scans speak the result at user priority (urgency 7.0), which interrupts any current speech. The engine speaks "Scanning now" immediately, then sends the camera frame to the cloud.

### Scene Change (Mesh Classification)

The engine monitors the center mesh classification from ARKit. When the classification label changes (for example, from "Wall" to "Door," indicating the user has entered a new room or area), and at least 20 seconds have passed since the last cloud scan, the engine automatically triggers a cloud AI description.

These background scans speak at info priority (urgency 1.0). They do not interrupt danger or caution alerts. If a danger alert is playing, the scene description waits or is dropped.

This trigger was chosen over a timer-based approach because it only fires when the scene has genuinely changed. A timer would fire every N seconds regardless of whether anything new is visible, wasting API tokens and producing repetitive descriptions.

## Duplicate Suppression

When a cloud AI response arrives, the engine compares the first 80 characters (lowercased) against the previous response. If they match, the response is not spoken. This prevents the app from repeating "Open hallway with doors on both sides" multiple times if the scene has not changed between scans.

## Local Fallback

If the cloud AI fails (both providers time out, the network is unavailable, or the Worker returns an error), the engine falls back to `describeAreaLocal()`. This method constructs a description from locally available data:

1. Center LiDAR distance in feet, with risk level.
2. Left distance in feet.
3. Right distance in feet.
4. The two most recent YOLO detections (label and direction).

The result sounds like: "Ahead, 8 feet, caution. Left, 12 feet. Right, 6 feet. Person ahead. Chair on left." This is less descriptive than cloud AI but provides actionable navigation information without network connectivity.

## Scan Suppression Window

When a scan is active (user-initiated or background), the `isScanActive` flag is set to `true`. This flag suppresses distance band speech announcements for 5 seconds. The purpose is to prevent a "Heads up" or "Something ahead" announcement from interrupting the scan result. Haptics and spatial audio continue during this window because they use different output channels and do not compete with speech.

After 5 seconds, `isScanActive` resets to `false` and normal distance band announcements resume. The 5-second window is long enough for the cloud AI race to complete and the response to be spoken.

## Cooldown

The AISceneDescriber enforces a 5-second cooldown between scans. Requests made within 5 seconds of the previous scan are silently dropped. This prevents rapid-fire scans from overwhelming the API and from producing a queue of stale descriptions.

## Race Implementation

The race is implemented using a `DispatchGroup` with two concurrent URL session data tasks. A boolean flag (`finished`) and an NSLock protect the first-result selection:

1. Both tasks start simultaneously.
2. The first task to return a successful result sets `finished = true` and stores its description.
3. The second task's result is logged but not used.
4. When both tasks complete (success or failure), the `group.notify` block fires on the main thread.
5. If at least one result arrived, it is delivered via the `onDescription` callback.
6. If both failed, the `onError` callback fires with a combined error message.
