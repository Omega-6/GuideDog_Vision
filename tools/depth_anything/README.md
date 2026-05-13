# Depth-Anything CoreML Conversion

Tooling to convert Depth-Anything (the depth estimation model used by
the web PWA) into a CoreML `.mlpackage` so the iOS app can run it on
non Pro iPhones in place of LiDAR depth.

## What this produces

`DepthAnythingSmall.mlpackage`

- Source model: `LiheYoung/depth-anything-small-hf` (HuggingFace)
- Input: 256x256 RGB image (matches the web PWA input size)
- Output: `depth` tensor, shape `[1, 252, 252]`, FLOAT32
  - Returns relative depth, not meters.
  - Calibrate to meters at runtime using known object triangulation,
    the same way the web PWA does (see `web/index.html`,
    `updateDepthCalibration`).
- Weights: FP16, ~47 MB
- Precision: FLOAT16
- Deployment target: iOS 15
- Inference time: about 9 ms on iPhone 13

The iOS app preloads this model at app launch so the engine starts
instantly the moment the user taps START.

## How to regenerate

```sh
# One time setup
python3 -m venv venv
source venv/bin/activate
pip install coremltools onnx onnxsim huggingface_hub torch transformers onnx2torch

# Download the ONNX from HuggingFace and convert
python convert_via_onnx.py
```

The `.mlpackage` lands in this directory. Copy it into the Xcode project
(`app/ios/App/App/`) and drag into the App target.

## Why two scripts

`convert.py` is the textbook path: load the HuggingFace PyTorch model
directly, trace it, convert. It currently fails with a `_cast` error
because the Dinov2 backbone in transformers 5.x uses data dependent
control flow that doesn't trace cleanly. I kept it here as a record of
what I tried first.

`convert_via_onnx.py` is the path that works. Loads the ONNX export
(which has the control flow already flattened into a static graph),
rebuilds it as a PyTorch graph through `onnx2torch`, then converts that
to CoreML. Use this one.

## Why not commit the .mlpackage

The weights blob is 47 MB. Git handles binaries poorly. The conversion
is deterministic and takes about a minute on an Apple Silicon Mac, so
the script is the source of truth and the artifact is `.gitignore`d.

If you need to commit the model anyway (build reproducibility without
Python tooling), enable Git LFS first.

## Notes on size

- **47 MB** is FP16 weights. App Store allowed.
- Smaller variants:
  - INT8 via `ct.optimize.coreml.linear_quantize_weights` to about 24 MB,
    slight accuracy loss
  - Palettized to 6 bit lookups to about 18 MB
- Cutting input to 224x224 saves no weight space (input size doesn't
  change weight count) but cuts compute about 25 percent. 256 is the
  smallest input size that produces clean depth without obvious
  blockiness.
