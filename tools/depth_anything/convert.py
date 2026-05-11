"""
Convert depth-anything-small from Hugging Face PyTorch to CoreML mlpackage.

Approach:
  1. Load LiheYoung/depth-anything-small-hf via transformers
  2. Trace the model with a dummy 256x256 RGB tensor (matches what the
     web pipeline feeds it — see web/index.html runDepthDetection)
  3. Convert the traced module to CoreML mlprogram, FP16 precision, iOS15+
  4. Save to DepthAnythingSmall.mlpackage

The output mlpackage takes a Float32 image of shape [1, 3, 256, 256]
already normalized (ImageNet mean/std) and produces a depth map. We do
the normalization on the iOS side because Vision framework handles it
during scaleFill preprocessing.
"""

import torch
import coremltools as ct
from transformers import AutoModelForDepthEstimation

MODEL_ID = "LiheYoung/depth-anything-small-hf"
INPUT_SIZE = 256  # match web's input size
OUTPUT_PATH = "DepthAnythingSmall.mlpackage"


class TracedDepthAnything(torch.nn.Module):
    """Wraps the HF model to return only the depth tensor (not a dict).
    Tracing through models that return ModelOutput dicts is fragile, so
    we strip down to a pure tensor in / tensor out."""

    def __init__(self, hf_model):
        super().__init__()
        self.model = hf_model

    def forward(self, pixel_values):
        # The HF DepthAnythingForDepthEstimation returns a
        # DepthEstimatorOutput with .predicted_depth (B, H, W).
        out = self.model(pixel_values=pixel_values)
        return out.predicted_depth


def main():
    print(f"[1/4] Loading {MODEL_ID} ...")
    hf_model = AutoModelForDepthEstimation.from_pretrained(MODEL_ID)
    hf_model.eval()

    wrapped = TracedDepthAnything(hf_model)
    wrapped.eval()

    print(f"[2/4] Tracing with dummy input ({INPUT_SIZE}x{INPUT_SIZE})...")
    example = torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE)
    with torch.no_grad():
        traced = torch.jit.trace(wrapped, example, strict=False)

    print("[3/4] Converting to CoreML mlprogram ...")
    # We declare the input as an ImageType so iOS apps can feed a
    # CVPixelBuffer directly. The image_scale + bias values apply
    # ImageNet normalization at runtime inside the model.
    image_input = ct.ImageType(
        name="pixel_values",
        shape=(1, 3, INPUT_SIZE, INPUT_SIZE),
        scale=1.0 / 255.0 / 0.226,             # mean of (0.229, 0.224, 0.225) ≈ 0.226
        bias=[-0.485 / 0.229, -0.456 / 0.224, -0.406 / 0.225],
        color_layout=ct.colorlayout.RGB,
    )
    mlmodel = ct.convert(
        traced,
        source="pytorch",
        inputs=[image_input],
        outputs=[ct.TensorType(name="depth")],
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS15,
        compute_precision=ct.precision.FLOAT16,
    )

    print(f"[4/4] Saving {OUTPUT_PATH} ...")
    mlmodel.short_description = (
        "Depth-Anything Small. Estimates relative depth from a 256x256 RGB image. "
        "Output values are relative (not metres); calibrate via known-object "
        "triangulation."
    )
    mlmodel.author = "LiheYoung / GuideDog Vision integration"
    mlmodel.license = "Apache-2.0"
    mlmodel.save(OUTPUT_PATH)
    print("Done.")


if __name__ == "__main__":
    main()
