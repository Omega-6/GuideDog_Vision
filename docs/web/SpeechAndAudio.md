# Speech and Audio System

## What Makes This System Non Trivial

The web speech and audio system has to deal with iOS Safari, which is the most restrictive environment for browser audio. Several workarounds were discovered through testing and are now baked into the design:

- **Audio unlock primer utterance.** iOS Safari blocks `speechSynthesis.speak()` until a user gesture occurs. The fix is to call `speak()` with an empty string, volume 0, and rate 10 (max) on the very first touch. The user hears nothing but the speech engine becomes unlocked for all subsequent calls.
- **Document level touch listeners.** The unlock listeners attach to `document` rather than to specific UI elements, because privacy and help overlays use higher z index values that intercept touches before they reach lower elements. Document level listeners catch every touch regardless of which overlay is currently visible.
- **Never call `cancel()` before `speak()`.** On iOS Safari, calling `speechSynthesis.cancel()` immediately before `speak()` can silently drop the new utterance. The `doSpeak` wrapper never cancels. Only the priority 3 danger path cancels, and even then it waits 50 milliseconds before speaking the replacement.
- **Exponential gain envelope on beeps.** Each tone uses a gain ramp from the target volume down to 0.01 over the duration. An abrupt cutoff would produce an audible click on most speakers. The exponential ramp produces a clean fade.
- **`onended` audio node disconnect.** Every oscillator, gain, and panner is disconnected after the beep finishes to prevent memory leaks from accumulated audio nodes.
- **Three independent encoding dimensions.** Urgency is encoded by frequency (500, 800, 1200 Hz), beep count (1, 2, 3), and volume (0.3, 0.5, 0.7). All three reinforce the same severity signal so the user picks up on the urgency even if one dimension is masked by background noise.
- **Stereo panning for spatial cues.** Left obstacles pan to -0.8, right obstacles pan to +0.8, ahead plays at 0. The user gets directional information without needing the system to speak the word "left" or "right."

## Overview

The PWA uses three audio channels to communicate with the user: synthesized speech (via the Web Speech API), tonal beeps (via the Web Audio API), and haptic vibration (via the Vibration API). These channels serve different purposes. Speech conveys detailed information. Beeps provide directional and urgency cues. Vibration gives tactile confirmation that works even when the phone is muted.

---

## Speech Synthesis

### doSpeak Function

The `doSpeak` function is the lowest-level speech wrapper. It creates a `SpeechSynthesisUtterance`, sets the rate (default 1.1x) and volume (1.0), and calls `speechSynthesis.speak()`.

Critically, `doSpeak` never calls `speechSynthesis.cancel()` before speaking. This is an intentional workaround for an iOS Safari bug. On iOS Safari, calling `cancel()` immediately before `speak()` can cause the utterance to be silently dropped. The speech queue simply never plays the new utterance. By never canceling, utterances queue naturally and play in order.

The function attaches `onend` and `onerror` handlers that reset the `_currentSpeechPriority` variable to 0, indicating that no priority-locked speech is active.

### speak Function

The `speak` function is used for user-initiated speech (button taps, voice command responses). It accepts a `force` flag. When `force` is true, it calls `speechSynthesis.cancel()` before speaking. This is acceptable because user-initiated speech should interrupt any current alert. The user explicitly requested information, so interrupting a background alert is the correct behavior.

When `force` is false, the function checks `CONFIG.VOICE_COOLDOWN` (1.5 seconds) to prevent the same information from being repeated too quickly. If the user is currently using voice recognition (`state.isListening`), speech recognition is stopped before speaking, since the microphone and speaker cannot both be active on most devices.

### speakAlert Function

The `speakAlert` function is used for automated alerts from the detection system. It has three priority tiers with zero cooldowns:

**Priority 3 (Danger):**
- Calls `speechSynthesis.cancel()` to interrupt any current speech
- Waits 50 milliseconds (via `setTimeout`) to let the cancel take effect
- Speaks at 1.3x rate for urgency
- This is the only automated path that cancels current speech

**Priority 2 (Warning):**
- Queues naturally via `doSpeak` at 1.1x rate
- Does not cancel current speech
- Will play after any currently speaking utterance finishes

**Priority 1 (Info):**
- Same behavior as priority 2
- Queues naturally

All three priority tiers have zero cooldowns. The cooldown map is `{ 3: 0, 2: 0, 1: 0 }`. Previous versions used cooldowns of 2 to 3 seconds, but these caused alerts to feel delayed. Users reported missing important warnings because the cooldown timer had not expired. Setting all cooldowns to zero ensures every alert is delivered immediately. Duplicate alerts are prevented by the temporal smoothing in the detection system, not by the speech system.

Each alert uses a `key` parameter (such as `"fast_danger"` or `"stairs"`) that is tracked in `state.lastAlerts`. The cooldown is checked against this key, but since cooldowns are zero, the check always passes. The key mechanism remains in the code to allow per-alert cooldowns to be reintroduced if needed.

---

## iOS Safari Audio Unlock

iOS Safari blocks both `speechSynthesis.speak()` and `AudioContext` playback until a user gesture (touch or click) occurs. The app handles this with a multi-step unlock process:

### Document-Level Listeners

Two event listeners are attached at the document level, not to any specific UI element:

```
document.addEventListener('touchstart', unlockAudio, { once: true, passive: true });
document.addEventListener('click', unlockAudio, { once: true });
```

These fire on the very first touch or click anywhere on the page. Using `{ once: true }` ensures they remove themselves after firing.

### unlockAudio Function

This function does two things:

1. **Resumes the AudioContext.** If the `AudioContext` is in a `suspended` state (which it always is on iOS until a gesture), it calls `resume()`.

2. **Speaks a primer utterance.** On the first call only (tracked by `state.audioUnlocked`), it creates a `SpeechSynthesisUtterance` with an empty string, volume set to 0, and rate set to 10 (maximum speed). This silent utterance "unlocks" the speech synthesis engine on iOS. Without this primer, subsequent calls to `speechSynthesis.speak()` would be silently ignored.

The primer utterance is intentionally silent and fast so the user does not hear anything. It exists solely to satisfy iOS Safari's requirement that speech synthesis be initiated from a user gesture.

### Why Document Level

In earlier versions, the unlock listeners were attached only to the `alertArea` element. This failed when overlays (privacy screen, help screen) were shown on top, because touches on the overlay did not reach the `alertArea`. Attaching to `document` ensures any touch anywhere on the page triggers the unlock, regardless of which element has focus or which overlay is visible.

---

## Web Audio API: Beeps

### AudioContext Initialization

The `initAudio` function creates a new `AudioContext` (or `webkitAudioContext` on older Safari). If the Web Audio API is unavailable, the AI badge text changes to "Audio Unavailable" and the system continues without tonal alerts. Speech and vibration still function.

### playBeep Function

The `playBeep` function generates a sine wave tone with the following parameters:

- **Frequency:** in Hz (e.g., 500, 800, 1200)
- **Duration:** in seconds (e.g., 0.1, 0.15, 0.2)
- **Pan:** stereo panning from -1 (full left) to 1 (full right), default 0 (center)
- **Volume:** gain level from 0 to 1, default 0.5

The audio graph is:

```
Oscillator (sine wave) -> Gain (envelope) -> StereoPanner -> Destination (speakers)
```

The gain envelope starts at the specified volume and ramps exponentially to 0.01 over the duration. This creates a natural fade-out rather than an abrupt cutoff, which would produce an audible click.

All audio nodes (oscillator, gain, panner) are disconnected in the `onended` handler to prevent memory leaks from accumulated audio nodes.

### playAlertSound Function

This function translates urgency levels into distinct beep patterns:

**Danger:** Three rapid 1200Hz beeps at 0.7 volume, spaced 150ms apart. The high frequency and rapid repetition convey urgency.

**Warning:** Two 800Hz beeps at 0.5 volume, spaced 200ms apart. The lower frequency and wider spacing convey caution without panic.

**Info:** One 500Hz beep at 0.3 volume. A single low-frequency tone at reduced volume conveys awareness.

The `position` parameter controls stereo panning. Obstacles on the left pan to -0.8. Obstacles on the right pan to 0.8. Obstacles ahead play in the center. This spatial audio helps the user locate the direction of an obstacle without verbal description.

---

## Vibration API

### vibrate Function

The `vibrate` function wraps `navigator.vibrate()` with a cooldown check. Vibrations are rate-limited to one every 400 milliseconds (`CONFIG.VIBRATE_COOLDOWN`) to prevent continuous buzzing that would desensitize the user.

The function uses optional chaining (`navigator.vibrate?.()`) and a try-catch wrapper, since the Vibration API is not available on all platforms (notably iOS Safari does not support it).

### vibrateAlert Function

Vibration patterns per urgency level:

**Danger:** `[200, 100, 200, 100, 200]` - Three long buzzes with short pauses. The pattern is 200ms buzz, 100ms pause, 200ms buzz, 100ms pause, 200ms buzz. Total duration is 800ms.

**Warning:** `[150, 100, 150]` - Two medium buzzes with a short pause. Total duration is 400ms.

**Info:** `[100]` - One short buzz. Total duration is 100ms.

The longer patterns for higher urgency levels provide a stronger tactile signal. Users learn to associate the vibration pattern with severity without needing to hear the audio.
