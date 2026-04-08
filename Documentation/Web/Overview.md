# PWA Website Overview

## The Problem

Roughly **2.2 billion people** worldwide live with some form of vision impairment, including **43.3 million** who are completely blind and **295.1 million** with moderate to severe visual impairment. The most well known mobility aid is the guide dog, but only about **2 percent** of blind people actually have one. Cost (**$40,000 to $60,000** per dog), training time (**two years**), low graduation rates (**roughly one in three** dogs make it through), and waiting lists (**one to three years**) cap the supply far below what is needed.

The native GuideDog Vision iOS app helps close part of this gap, but it requires an iPhone, ideally one with LiDAR. The PWA website goes further: it runs in any modern web browser on any device, with no app store installation, no LiDAR requirement, and no cost. See the [README](../../README.md) for the full problem statement and source citations.

## What It Is

GuideDog Vision is a Progressive Web App (PWA) that helps blind and visually impaired users navigate their surroundings using a phone's camera and cloud AI. It runs in any modern web browser on any device. There is no app store installation required. Users open the URL, grant camera permission, and the system begins scanning automatically.

## Why a PWA Exists

The native iOS app has access to LiDAR hardware on iPhone Pro models, which provides precise depth sensing in real time. Most users do not have LiDAR devices. Many users cannot install native apps due to device restrictions, storage limits, or unfamiliarity with the App Store. The PWA serves as a universal fallback. Any device with a camera and a browser can run it.

## How It Compensates for No LiDAR

Without LiDAR, the PWA cannot measure absolute distances to objects. To compensate, it uses four detection layers working together:

1. **COCO-SSD** runs object detection locally in the browser using TensorFlow.js. It identifies 19 navigation-relevant objects from the COCO dataset and estimates distance through known-object triangulation.
2. **Depth-Anything** runs a relative depth estimation model locally using Transformers.js v2. It produces depth values from 0 to 255 that indicate relative nearness. These values are auto-calibrated against COCO-SSD detections when possible.
3. **Fast Wall Check** uses pixel variance analysis on the camera feed. It detects uniform surfaces (walls, doors, flat obstacles) instantly with no ML inference. This runs every 50 milliseconds.
4. **Cloud AI Guide** sends a camera frame to a Cloudflare Worker every 5 seconds. The cloud AI acts as a sighted guide companion, describing the scene and identifying hazards that the local models missed (stairs, wet floors, narrow passages, doors).

The cloud AI is the primary differentiator between the PWA and native app. Because the PWA lacks LiDAR, the cloud AI fills the role of a sighted companion who describes what is ahead, what obstacles exist, which direction is clear, and what the floor conditions look like.

## Browser Compatibility

The PWA works on Chrome, Safari, and Firefox. It has been tested on iOS Safari, Android Chrome, and desktop browsers. HTTPS is required for camera access, as browsers block `getUserMedia` on insecure origins. The service worker enables offline caching of the app shell, though cloud AI features require an internet connection.

## Best on Mobile Devices

The app is optimized for mobile phones. The camera faces forward when held naturally. The interface uses large touch targets, gesture controls, and speech output designed for one-handed use while walking. Desktop browsers work but are not the intended use case, as users would need to carry a laptop or use an external webcam.

## PWA Features

The app registers a service worker (`sw.js`) and includes a web app manifest (`manifest.json`) that enables "Add to Home Screen" on both iOS and Android. The viewport is locked to prevent zoom (`maximum-scale=1`), and `touch-action: manipulation` prevents double-tap zoom delays. Text selection is disabled to avoid accidental selections during gesture use.

## Privacy

All object detection and depth estimation run entirely on the user's device. Camera frames sent to the cloud AI are processed and immediately discarded. No images are stored. No account is required. No personal data is collected. The privacy screen is shown every time the app launches to remind users of these facts through spoken audio.
