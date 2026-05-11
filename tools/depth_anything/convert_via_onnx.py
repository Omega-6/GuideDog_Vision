"""
Alternative conversion path: load Depth-Anything from ONNX via onnx2torch,
which produces a flattened PyTorch graph that traces cleanly. Then convert
the traced graph to CoreML mlprogram.

The HF transformers model has Dinov2 control-flow that doesn't trace
through torch.jit.trace (data-dependent ints). ONNX exports collapse that
control flow into a static graph, so onnx2torch can rebuild it as a
straightforward sequential model.
"""

import torch
import coremltools as ct
import onnx
from onnx2torch import convert as onnx_to_torch

# Use the FP32 ONNX as the cleanest source. Web uses the quantized variant
# but quantization-aware ops can confuse coremltools; we'll quantize on
# the CoreML side instead.
ONNX_PATH = "./depth-anything-small/onnx/model.onnx"
INPUT_SIZE = 256  # matches the web's input size. The ONNX has dynamic shape,
                  # so we trace at 256x256 for ~4x less compute on device.
OUTPUT_PATH = "DepthAnythingSmall.mlpackage"


def main():
    print(f"[1/4] Loading ONNX from {ONNX_PATH} ...")
    onnx_model = onnx.load(ONNX_PATH)

    print("[2/4] Converting ONNX graph to PyTorch via onnx2torch ...")
    torch_model = onnx_to_torch(onnx_model)
    torch_model.eval()

    print(f"[3/4] Tracing PyTorch graph (input {INPUT_SIZE}x{INPUT_SIZE}) ...")
    example = torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE)
    with torch.no_grad():
        traced = torch.jit.trace(torch_model, example, strict=False)

    # Sanity check: run the trace to make sure it produces output
    with torch.no_grad():
        out = traced(example)
        print(f"      Trace output shape: {tuple(out.shape) if hasattr(out, 'shape') else type(out)}")

    print("[4/4] Converting to CoreML mlprogram ...")
    image_input = ct.ImageType(
        name="pixel_values",
        shape=(1, 3, INPUT_SIZE, INPUT_SIZE),
        scale=1.0 / 255.0 / 0.226,
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

    mlmodel.short_description = (
        "Depth-Anything Small. 518x518 RGB input → relative depth map. "
        "Calibrate to metres via known-object triangulation."
    )
    mlmodel.author = "LiheYoung / GuideDog Vision integration"
    mlmodel.license = "Apache-2.0"
    mlmodel.save(OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
