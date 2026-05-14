# Sound Detection
## Overview
The Sound and Captions mode includes an audio classifer built onto the device that listens to external sounds through the microphone and announces relevant information to the user through digital abnners, speech, and haptic vibration. The classifier runs the YAMNet model in TFLite format using the MediaPipe Audio Tasks library. This downloaded model is then run locally on the device.


## Core Technical Details
Bucket aggregation over raw class scores: When we use bucket aggregation over the scores that YAMNet returns for the different AudioSet classes it makes a big difference. YAMNet returns scores for around 521 AudioSet classes. The problem is that some sounds are very similar and the confidence is split across classes. For example "Siren" gets a score of 0.18 "Police car siren" gets 0.14 and "Ambulance siren" gets 0.12. If we sum up the scores for each bucket that the user sees the siren bucket will get a score of 0.44 and that will trigger it.. If we do not do this each of the subclasses will be rejected because they are individually below the threshold. This is the difference between detecting a siren and missing it.


Ambient noise floor calibration: Before the system can classify any sounds it first measures the background noise in the room for around 1.5 seconds. This is called noise floor calibration. The system will only classify a sound if it is least 3 dB above the background noise. This prevents the system from wasting CPU power and giving positives when it is quiet. The background noise level is set to the median of the collected frames, not the average. This makes it more robust to a loud noise during the calibration.


Separate classify gate and ambient gate: The system has two gates: the classify gate and the ambient gate. The classify gate checks if the sound is 3 dB above the background noise. If it is the system will run the YAMNet model. The ambient gate checks if the sound is 12 dB above the background noise. If it is the system will make a " sound nearby" announcement when MediaPipe fails to load. These two gates serve purposes and are adjusted independently.


AudioWorklet over ScriptProcessor: The system uses AudioWorklet to capture audio off the thread. If this does not work it falls back, to using ScriptProcessor. Using AudioWorklet prevents buffering from delaying the user interface.


Disabled browser audio DSP: The system also disables the browsers processing. When it makes the getUserMedia call it explicitly disables echo cancellation, noise suppression and automatic gain control. These are the processing pipelines that the browser uses for voice calls. They suppress sounds like sirens, traffic and alarms.. These are the sounds that the GuideDog system specifically needs to detect.


Per-label announcement cooldown: The system has a per-label announcement cooldown. This means that each distinct sound label has its cooldown timestamp, which is stored in state.lastSoundSpeak. So if a siren is heard twice in 6 seconds it will only be announced once. This is really helpful because it stops the user from getting many repeated alerts when there are continuous sounds, like a siren that just keeps going. The per-label announcement cooldown is important because it helps to prevent this kind of flooding with repeated alerts, for the sound label.


## MediaPipe Module Loading
The MediaPipe Audio Tasks library is loaded in a <script type="module"> block at page load. Two CDN sources are tried in sequence:
1. https://cdn.jsdelivr.net/npm/@mediapipe/tasks-audio@0.10.35
2. https://esm.sh/@mediapipe/tasks-audio@0.10.35


When successful, the module is stored as window.__mpAudio and window.__mpAudioBase, and a mp-audio-ready custom event is dispatched. However, if it failed, mp-audio-failed is dispatched and the system falls back to ambient-only mode.


## Model Loading
loadAudioClassifier() is called the first time the user enables sound detection. When it runs, it does the following:
1. Waits for window.__mpAudio (the MediaPipe module) using an event listener with an 8-second safety timeout
2. Resolves FilesetResolver.forAudioTasks(wasmBase) using the CDN's /wasm path
3. Creates an AudioClassifier with:
A. Model: yamnet.tflite from storage.googleapis.com/mediapipe-models/
B. maxResults: 25 (wider grouping to merge similar classes)
C. scoreThreshold: 0.02 (low per-class threshold while the bucket sum determines detection)


The result is stored in _mpClassifier. If the function fails, it returns null and triggers ambient-only mode for the session.


## Audio Capture Pipeline


### Microphone Access
toggleSoundDetection() calls navigator.mediaDevices.getUserMedia with audio constraints that disable all browser DSP:


{


  echoCancellation: false,


  noiseSuppression: false,


  autoGainControl: false,


  channelCount: 1


}


The resulting MediaStream is stored in state.yamnetMicStream.


### Capture Node Setup


A MediaStreamAudioSourceNode is created from the stream. A silent gain node with a gain of zero is connected to the destination of the AudioContext. This way the browser pulls the graph without routing the audio to the speakers. The window size is 0.975 times the sample rate in samples. The YAMNet model was trained on windows of 0.975 seconds at a sampling rate of 16 kHz. This corresponds to 15,600 samples. In a 44.1 kHz AudioContext, the window size is 43,000 samples. The model can then resample internally if needed.


### AudioWorklet Path
If AudioWorkletNode is available, then the following runs:
1. A worklet processor is created as a Blob URL and registered
2. The processor accumulates mono PCM into a Float32Array of windowSamples length
3. When the buffer fills, it is transferred to the main thread via port.postMessage
4. The main thread calls onAudioWindow


### ScriptProcessor Fallback
If AudioWorklet is not available we use a ScriptProcessorNode with a buffer size of 4096. The ring buffer and window filling logic still work, as they run on the main thread. This gives a warning message. AudioWorklet is preferred for performance, but the ScriptProcessorNode is used as a fallback.


### Teardown (stopAudioCapture)
All nodes are disconnected, event handlers are cleared, and _ambientFloorDb is reset to null so calibration restarts fresh if sound detection is re-enabled.


## Ambient Noise Calibration
Before classifying any window, the system calibrates the ambient noise floor:


1. On the first window received, _ambientCalibrationDoneAt is set to Date.now() + 1500ms
2. Each window's RMS level (in dBFS) is pushed to _ambientCalibrationFrames
3. When Date.now() passes the deadline, the frames are sorted and the median is taken as _ambientFloorDb


Using the median, it makes the calibration robust to a single loud event during the calibration window.


### dBFS Computation
rmsDb = 20 × log10(max(sqrt(mean(samples²)), 1e-7))


The 1e-7 floor prevents -Infinity on a perfectly silent frame.


## Classification
### Gate Check
After calibration, each window is gated before classification:


if (rmsDb < _ambientFloorDb + CONFIG.AUDIO_CLASSIFY_GATE_DB) skip


CONFIG.AUDIO_CLASSIFY_GATE_DB = 3 dB. Windows within 3 dB of the ambient floor are silently skipped. This saves CPU and battery in quiet environments where no meaningful sound is present.


### Classify Call


const results = _mpClassifier.classify(samples, sampleRate);


MediaPipe returns an array of AudioClassifierResult objects. Each contains classifications[0].categories, sorted by score descending.


A _classifyBusy flag prevents overlapping calls. If the previous classify() call has not returned, the current window is dropped.


## Sound Detection: Buckets and Labels


### SOUND_BUCKETS
A two-level detection system maps user-facing labels to urgency levels. There are 37 buckets grouped into three urgency tiers:
1. Danger buckets (banner immediately): siren, fire_alarm, car_horn, truck_horn, train_horn, gunshot, explosion
2. Warning buckets (banner, queued): alarm, car_alarm, reversing, shouting, dog_warning, vehicle, traffic, train, bicycle_bell, thunder
3. Info buckets (banner): speech, conversation, music, crowd, applause, laughter, baby_cry, crying, knock, doorbell, door, phone, rain, alarm_clock, dog_info, cat


### SOUND_LABELS
SOUND_LABELS maps verbatim YAMNet category names to bucket keys. There are over 200 entries covering all major subclasses. From sirens to drum kits, the YAMNet categorizes them into one of the several buckets.


Music receives the broadest coverage: all AudioSet genre labels, all instrument classes, and all vocal-music subclasses roll up to the music bucket. This means a partial confidence split across "Pop music" 0.15, "Drum kit" 0.10, and "Electric guitar" 0.08 combines to 0.33, which exceeds the CONFIG.AUDIO_SCORE_THRESHOLD = 0.25 threshold.


### Bucket Aggregation and Winner Selection
handleMediaPipeResults() processes each classify result:


Sum scores per bucket. For each category returned, look up its bucket key in SOUND_LABELS. Accumulate scores: bucketSum[bucket] += c.score.
Track the top individual class per bucket for debug logging.
Reject below threshold. Any bucket whose summed score is below CONFIG.AUDIO_SCORE_THRESHOLD = 0.25 is discarded.
Pick the winner. Among buckets above threshold, prefer higher urgency. Within the same urgency tier, prefer higher summed score.
Dispatch. Call handleSoundLabel(meta.label, meta.urgency) with the winner's human-readable label and urgency tier.


### Ambient-Only Fallback
If MediaPipe fails to load, runAmbientGate() is used instead of classifyWindow(). It fires handleSoundLabel("Loud sound nearby", "warning") whenever the RMS level exceeds _ambientFloorDb + CONFIG.AUDIO_AMBIENT_GATE_DB (12 dB). This fallback never claims a specific category — it only announces that something loud is happening.


## Sound Event Dispatch (handleSoundLabel)
For each detected sound:


1. Show the sound banner (showSoundBanner) — a blue pill at the bottom of the screen above the caption box, visible for CONFIG.SOUND_BANNER_DURATION = 6000ms
2. Check per-label cooldown. If state.lastSoundSpeak[label] was set less than CONFIG.SOUND_SPEAK_COOLDOWN = 6000ms ago, skip announcement (but still show the banner)
3. Announce for warning and danger levels:
4. Update state.lastSoundSpeak[label]
5. Call speakAlert("sound_" + label, spoken, priority) — priority 3 for danger, 2 for warning
6. Call vibrateAlert(urgency)
7. Info-level sounds update the cooldown timestamp and show the banner but do not speak (they are informational, not safety-critical)


In Assist mode, doSpeak() is suppressed for deaf users (the state.appMode === 'assist' guard in doSpeak exits early). Banner display and vibration still work normally.


## Debug Instrumentation
Enable the debug panel with ?debug=1 in the URL, #debug in the hash, or localStorage.gd_debug = '1'.


The debug panel shows:


1. MediaPipe module load status
2. Model load status and time
3. Capture backend (AudioWorklet or ScriptProcessor)
4. Sample rate and window size
5. Window count, gated count, classified count
6. Announced vs suppressed counts
7. First classify latency (ms)
8. Current RMS (dBFS) and ambient floor (dBFS), with dB-above-floor
9. Rolling log of the last 14 events (dropped windows, classify results, announced labels)


The debug panel is rendered via requestAnimationFrame to avoid blocking the audio thread.




