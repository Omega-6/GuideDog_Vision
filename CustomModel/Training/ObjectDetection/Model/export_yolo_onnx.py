# Export_Yolo_Onnx.py - Export YOLO model to ONNX format
import torch
from model import YOLO 

device = "cpu" # Uses CPU for ONNX export

model = YOLO().to(device) # Create YOLO model and move it to device
model.eval() # Set model to evaluation mode

checkpoint = torch.load("TrainedModels/final_model.pth", map_location=device) # Load trained model
model.load_state_dict(checkpoint["model_state_dict"]) # Load weights into model

dummy_input = torch.randn(1, 3, 448, 448) # Create dummy input tensor


torch.onnx.export( # Start ONNX export
    model, # Model to be exported
    dummy_input, # Example input tensor
    "yolo.onnx", # Output file name
    opset_version=12, # ONNX opset version
    input_names=["input"], # Input tensor name
    output_names=["output"], # Output tensor name
    dynamic_axes={ # Dynamic axes for variable batch size
        "input": {0: "batch"}, 
        "output": {0: "batch"}
    }
)

print("YOLO exported to yolo.onnx") # Print Confirmation
