# Depth-Anything CoreML Conversion

Tooling for converting Depth-Anything (the depth-estimation model used by
the web PWA) into a CoreML `.mlpackage` so the iOS app can run it on
non-Pro iPhones in place of LiDAR depth.

## What this produces

`DepthAnythingSmall.mlpackage`

- Source model: `LiheYoung/depth-anything-small-hf` (Hugging Face)
- Input: 256x256 RGB image (matches the web PWA input size)
- Output: `depth` tensor, shape `[1, 252, 252]`, FLOAT32
  - The model returns relative depth values, NOT meters.
  - Calibrate to meters at runtime using known-object triangulation,
    the same way the web PWA does (see `web/index.html`,
    `updateDepthCalibration`).
- Weights: FP16, ~47 MB
- Precision: FLOAT16
- Deployment target: iOS 15

## How to regenerate

```sh
# One-time setup
python3 -m venv venv
source venv/bin/activate
pip install coremltools onnx onnxsim huggingface_hub torch transformers onnx2torch

# Download the ONNX from HF and convert
python convert_via_onnx.py
```

The `.mlpackage` lands in this directory. Copy it into the Xcode project
(`app/ios/App/App/`) and drag into the App target.

## Why two scripts

- `convert.py` — the "textbook" path: load the HF PyTorch model directly,
  trace it, convert. **This currently fails** with a `_cast` error
  because the Dinov2 backbone in transformers 5.x uses data-dependent
  control flow that doesn't trace cleanly. Kept here as documentation of
  what was tried first.
- `convert_via_onnx.py` — the path that works. Loads the ONNX export
  (which has the control flow already flattened into a static graph),
  rebuilds it as a PyTorch graph via `onnx2torch`, then converts that to
  CoreML. **Use this one.**

## Why not commit the `.mlpackage`?

The weights blob is 47 MB. Git handles binaries poorly. The conversion is
deterministic and takes about a minute on an Apple Silicon Mac, so the
script is the source of truth and the artifact is `.gitignore`d.

If you need to commit the model anyway (e.g., for build reproducibility
without Python tooling), enable Git LFS first.

## Notes on size

- **47 MB** is FP16 weights. App Store-allowed.
- Smaller variants are possible:
  - INT8 via `ct.optimize.coreml.linear_quantize_weights` → ~24 MB,
    slight accuracy loss
  - Palettized to 6-bit lookups → ~18 MB
- Cut input to 224x224 saves no weight space (input size doesn't change
  weight count) but cuts compute ~25%. 256 is the smallest input size
  that produces clean depth without obvious blockiness.
