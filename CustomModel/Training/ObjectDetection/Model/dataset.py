#Dataset.py - YOLO Dataset Class with Augmentation and Validation
import torch
from torch.utils.data import Dataset
from PIL import Image
import torchvision.transforms as transforms
import os
import numpy as np
from config import (
    IMAGE_SIZE, GRID_SIZE, NUM_CLASSES, NUM_BOXES,
    USE_AUGMENTATION, AUG_BRIGHTNESS, AUG_CONTRAST,
    AUG_SATURATION, AUG_HUE, AUG_FLIP_PROB
)

class YOLODataset(Dataset):
    """
    YOLO dataset with proper augmentation and validation.
    Label format (YOLO): class_id x_center y_center width height (all 0-1)
    """
    def __init__(self, img_dir, label_dir, augment=True): 
        # Dataset initialization
        self.img_dir = img_dir # Image directory
        self.label_dir = label_dir # Label directory
        self.augment = augment and USE_AUGMENTATION # Use augmentation if enabled

        # Load image filenames
        self.images = [
            f for f in os.listdir(img_dir)
            if f.endswith(('.jpg', '.png', '.jpeg'))
        ]

        # If no images found, raise error
        if len(self.images) == 0:
            raise ValueError(f"No images found in {img_dir}")

        # Print dataset info
        print(f"Loaded {len(self.images)} images from {img_dir}")

        # Base image preprocessing
        self.base_transform = transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)), # Resize to model size
            transforms.ToTensor(), # Convert image to tensor
            transforms.Normalize( # Normalize with ImageNet stats
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        # Setup augmentation transforms if enabled
        if self.augment: 
            self.augment_transform = transforms.ColorJitter( #change color properties to augment data
                brightness=AUG_BRIGHTNESS,
                contrast=AUG_CONTRAST,
                saturation=AUG_SATURATION,
                hue=AUG_HUE
            )
            print(f"Using data augmentation (ColorJitter + HFlip)")
        else:
            self.augment_transform = None # If no augmentation, set to None

    def __len__(self):
        return len(self.images) # Return dataset size

    def __getitem__(self, idx):
        img_name = self.images[idx] # Get image filename

        # Load image and label paths
        img_path = os.path.join(self.img_dir, img_name)
        label_path = os.path.join(
            self.label_dir, # Locates label file
            img_name.replace('.jpg', '.txt')
                    .replace('.png', '.txt')
                    .replace('.jpeg', '.txt')
        )

        try: # Attempt to open image
            image = Image.open(img_path).convert("RGB")
        except Exception as e: # Raise error if image loading fails
            raise RuntimeError(f"Failed to load image {img_path}: {e}")

        # Augmentation
        flip = False # Whether image is flipped for augmentation
        if self.augment: # If augmentation is enabled
            if np.random.rand() < 0.3: # 30% chance to apply color jitter
                image = self.augment_transform(image)
            if np.random.rand() < AUG_FLIP_PROB: # 50% chance to apply horizontal flip
                image = transforms.functional.hflip(image)
                flip = True

        image = self.base_transform(image) # Final preprocessing

        # Prepare target tensor
        target = torch.zeros((GRID_SIZE, GRID_SIZE, NUM_BOXES * 5 + NUM_CLASSES))

        if not os.path.exists(label_path): # If label file doesn't exist
            return image, target # Return image and empty target

        try: # Attempt to read label file
            with open(label_path, 'r') as f: 
                lines = f.readlines() 
        except Exception as e:
            print(f"Warning: Could not read {label_path}: {e}")
            return image, target

        if len(lines) == 0: # If no labels, return image and empty target
            return image, target

        
        for line_num, line in enumerate(lines): # Process each label line
            parts = line.strip().split() # Split line into parts
            if len(parts) != 5: # Raise error if format is incorrect
                print(f"Warning: {img_name} line {line_num+1}: Expected 5 values")
                continue

            try: # Attempt to parse label values
                class_id, x, y, w, h = map(float, parts)
                class_id = int(class_id)
            except ValueError: # Raise warning if conversion fails
                print(f"Warning: {img_name} line {line_num+1}: Cannot parse values")
                continue

            # Prevent zero-size boxes
            EPS = 1e-6 # Small constant to avoid zero dimensions
            if w <= 0 or h <= 0: # If width or height is zero or negative
                print( # Print warning and fix dimensions
                    f"Warning: {img_name} line {line_num+1}: "
                    f"Zero-size box fixed (w={w:.6f}, h={h:.6f})"
                )
                w = max(w, EPS)
                h = max(h, EPS)

            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1): # If oords are not between 0 and 1
                print(  # Print warning for invalid coords
                    f"Warning: {img_name} line {line_num+1}: "
                    f"Invalid coords: x={x:.3f} y={y:.3f} w={w:.3f} h={h:.3f}"
                )
                continue

            if class_id < 0 or class_id >= NUM_CLASSES: # If class ID is invalid
                print( # Print warning for invalid class ID
                    f"Warning: {img_name} line {line_num+1}: "
                    f"Invalid class {class_id}"
                )
                continue
            
            # Apply horizontal flip if needed
            if flip:
                x = 1.0 - x

            # Assign box to grid cell
            # Determine grid cell
            i = int(y * GRID_SIZE)
            j = int(x * GRID_SIZE)
            i = min(i, GRID_SIZE - 1)
            j = min(j, GRID_SIZE - 1)

            # Calculate box coords relative to cell
            x_cell = x * GRID_SIZE - j
            y_cell = y * GRID_SIZE - i

            # Clamp values to [0, 1] for safety
            x_cell = max(0.0, min(1.0, x_cell))
            y_cell = max(0.0, min(1.0, y_cell))

            for box_idx in range(NUM_BOXES): # Find first available box slot
                offset = box_idx * 5 # Offset for this box
                if target[i, j, offset + 4] == 0: # If this box slot is free
                    # Assign box values
                    target[i, j, offset + 0] = x_cell
                    target[i, j, offset + 1] = y_cell
                    target[i, j, offset + 2] = w
                    target[i, j, offset + 3] = h
                    target[i, j, offset + 4] = 1.0
                    target[i, j, NUM_BOXES * 5 + class_id] = 1.0
                    break

        # Return image and target tensor
        return image, target


class YOLODatasetDebug(YOLODataset):
    """YOLO Dataset with debug info on first item retrieval."""
    def __getitem__(self, idx):
        # Get image and target from parent class
        image, target = super().__getitem__(idx)

        if idx == 0: # Only for first item
            # Print debug info
            print(f"\n DATASET DEBUG — image {idx}: {self.images[idx]}")
            obj_cells = target[target[..., 4] == 1] 

            print(f"Number of object cells: {obj_cells.shape[0]}") # Count object cells

            if obj_cells.shape[0] > 0: # If there are object cells
                # Print first few object cells
                print("First few GT cells (x_cell, y_cell, w, h, conf):")
                print(obj_cells[:5, :5])
            else:
                print(" No object cells found!") # Warn if no objects found
                
        # Return image and target
        return image, target
