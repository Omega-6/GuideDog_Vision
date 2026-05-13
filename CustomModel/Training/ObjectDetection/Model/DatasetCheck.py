# DatasetCheck.py - Verify YOLO Dataset Loading and Target Formatting
from dataset import YOLODataset
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import torch

dataset = YOLODataset( # Initialize dataset without augmentation
    '../Data/train/images',
    '../Data/train/labels',
    augment=False
)

# Get a sample
image, target = dataset[0]

print("Dataset Verification")
print(f"{'='*70}\n")

# Print image and target shapes
print(f"Image tensor shape: {image.shape}")
print(f"Target tensor shape: {target.shape}")

# Count objects
obj_mask = target[..., 4] == 1 # Find cells with objects
num_objects = obj_mask.sum().item() # Count number of objects
print(f"Number of objects in target: {num_objects}")

if num_objects > 0: # If there are objects
    # Show object details
    print(f"\nObject cells:")
    for i in range(target.shape[0]): # Loop over grid rows
        for j in range(target.shape[1]): # Loop over grid columns
            if target[i, j, 4] == 1: # If this cell has an object
                # Extract box details
                x_cell = target[i, j, 0].item()
                y_cell = target[i, j, 1].item()
                w = target[i, j, 2].item()
                h = target[i, j, 3].item()
                class_id = torch.argmax(target[i, j, 5:]).item()
                
                # Convert back to global coords
                x = (j + x_cell) / 7
                y = (i + y_cell) / 7
                
                # Print box info
                print(f"  Cell [{i},{j}]: class={class_id}, "
                        f"global_pos=({x:.3f},{y:.3f}), size=({w:.3f}x{h:.3f})")
else: # Print warning if no objects found
    print("WARNING: No objects found in this sample!")

print(image, target)