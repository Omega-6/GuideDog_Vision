# DataDebug.py - Validate Object Detection Dataset Format
import os
import torch
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Dataset paths and parameters
TRAIN_IMG_DIR = '../Data/train/images'
TRAIN_LABEL_DIR = '../Data/train/labels'
NUM_CLASSES = 10

def check_dataset():
    """Check if dataset is properly formatted"""
    
    print("="*70)
    print("Dataset Validation")
    print("="*70)
    
    # Check if directories exist
    if not os.path.exists(TRAIN_IMG_DIR):
        print(f"ERROR: Image directory not found: {TRAIN_IMG_DIR}")
        return
    if not os.path.exists(TRAIN_LABEL_DIR):
        print(f"ERROR: Label directory not found: {TRAIN_LABEL_DIR}")
        return
    
    print(f"Directories exist")
    
    # Count files
    images = [f for f in os.listdir(TRAIN_IMG_DIR) if f.endswith(('.jpg', '.png'))]
    labels = [f for f in os.listdir(TRAIN_LABEL_DIR) if f.endswith('.txt')]
    
    print(f"\n Dataset Statistics:")
    print(f"   Images: {len(images)}")
    print(f"   Labels: {len(labels)}")
    
    if len(images) < 100: # Warn if too few images
        print(f"WARNING: Only {len(images)} images. Need at least 100+ for good results")
    
    # Check for mismatched files
    missing_labels = []
    for img in images[:10]:  # Check first 10 images
        label_name = img.replace('.jpg', '.txt').replace('.png', '.txt') # Find their corresponding label file
        if not os.path.exists(os.path.join(TRAIN_LABEL_DIR, label_name)): 
            missing_labels.append(img) # If label file missing, append it to list
    
    if missing_labels: # If any missing labels found
        print(f"ERROR: {len(missing_labels)} images missing labels:") # Warn user
        for m in missing_labels[:3]:
            print(f"   - {m}")
    else:
        print(f"All checked images have matching labels") # Else, confirm all images have labels
    
    # Validate label format
    print(f"\n Checking label format")

    # Initialize error tracking
    errors = []
    class_distribution = [0] * NUM_CLASSES
    total_boxes = 0
    
    for label_file in labels[:20]:  # Loop over first 20 label files
        label_path = os.path.join(TRAIN_LABEL_DIR, label_file) # Full path to label file
        
        try:
            with open(label_path, 'r') as f: # Attempt to open label file
                lines = f.readlines()
                
                if len(lines) == 0:
                    errors.append(f"{label_file}: Empty file") # If empty, log error
                    continue
                
                for line_num, line in enumerate(lines, 1): # Else, process each line
                    parts = line.strip().split()
                    
                    if len(parts) != 5: # Check for correct number of parts
                        errors.append(f"{label_file} line {line_num}: Expected 5 values, got {len(parts)}")
                        continue
                    
                    try: # Attempt to parse values
                        class_id, x, y, w, h = map(float, parts)
                        class_id = int(class_id)
                        
                        # Check ranges
                        if class_id < 0 or class_id >= NUM_CLASSES: # Invalid class ID
                            errors.append(f"{label_file} line {line_num}: Invalid class {class_id} (must be 0-{NUM_CLASSES-1})")
                        
                        # Check x, y, h, w are between 0 and 1
                        if not (0 <= x <= 1):
                            errors.append(f"{label_file} line {line_num}: x={x} not in [0,1]")
                        if not (0 <= y <= 1):
                            errors.append(f"{label_file} line {line_num}: y={y} not in [0,1]")
                        if not (0 < w <= 1):
                            errors.append(f"{label_file} line {line_num}: w={w} not in (0,1]")
                        if not (0 < h <= 1):
                            errors.append(f"{label_file} line {line_num}: h={h} not in (0,1]")
                        
                        # Count classes
                        if 0 <= class_id < NUM_CLASSES:
                            class_distribution[class_id] += 1
                        total_boxes += 1
                        
                    except ValueError:
                        errors.append(f"{label_file} line {line_num}: Cannot convert to numbers") # Log conversion error if occurs
        
        except Exception as e: 
            errors.append(f"{label_file}: {str(e)}") # Log file read errors if occurs
    
    if errors: # If any errors found
        print(f"Found {len(errors)} errors:") # Report number of errors
        for err in errors[:10]:  # Show first 10
            print(f"   - {err}")
    else: # If no errors found print confirmation
        print(f"All checked labels are valid")
    
    # Class distribution
    print(f"\n Class Distribution (first 20 label files):")
    print(f"   Total boxes: {total_boxes}")

    for i, count in enumerate(class_distribution): # Loop over each class
        if count > 0: # Only print classes that have boxes
            print(f"   Class {i}: {count} boxes ({count/total_boxes*100:.1f}%)") # Print class distribution
    
    # Check for imbalanced classes
    if total_boxes > 0: # Avoid division by zero
        max_class_pct = max(class_distribution) / total_boxes * 100 # Calculate max class percentage
        if max_class_pct > 70: # Warn if any class exceeds 70%
            print(f"WARNING: Class imbalance! One class is {max_class_pct:.1f}% of data")
    
    # Visualize a sample
    print(f"\n Visualizing sample image with boxes")

    # Visualize first image
    visualize_sample(images[0])
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if not errors and len(images) >= 100:
        print("Dataset looks good! Ready to train.")
    elif errors:
        print("Fix the errors above before training")
    else:
        print("Dataset is valid but may be too small for good results")


def visualize_sample(image_name):
    """Visualize one image with its bounding boxes"""
    
    # Load image path
    img_path = os.path.join(TRAIN_IMG_DIR, image_name)

    # Load corresponding label file path
    label_path = os.path.join(
        TRAIN_LABEL_DIR, 
        image_name.replace('.jpg', '.txt').replace('.png', '.txt')
    )
    
    # Load image
    image = Image.open(img_path).convert('RGB')
    width, height = image.size
    
    # Load boxes
    boxes = []
    if os.path.exists(label_path): # If label file exists
        with open(label_path, 'r') as f: # Open label file
            for line in f.readlines(): # Loop over each line
                parts = line.strip().split() # Split line into parts
                if len(parts) == 5: # If correct number of parts
                    class_id, x, y, w, h = map(float, parts) # Parse values
                    boxes.append([int(class_id), x, y, w, h]) # Append box
    
    # Plotting
    fig, ax = plt.subplots(1, figsize=(10, 8)) # Create plot
    ax.imshow(image) # Display image on plot
    
    # Draw boxes on image
    colors = plt.cm.rainbow(torch.linspace(0, 1, NUM_CLASSES))
    
    for box in boxes: # Loop over each box
        class_id, x, y, w, h = box # Unpack box
        
        # Convert from center coords to corner coords (pixels)
        x1 = (x - w/2) * width
        y1 = (y - h/2) * height
        box_width = w * width
        box_height = h * height
        
        # Create rectangle 
        rect = patches.Rectangle(
            (x1, y1), box_width, box_height,
            linewidth=2, 
            edgecolor=colors[class_id], 
            facecolor='none'
        )
        ax.add_patch(rect) # Add rectangle to plot
        
        # Add label iwth class ID
        ax.text(x1, y1-5, f'Class {class_id}', 
                color='white', fontsize=10,
                bbox=dict(facecolor=colors[class_id], alpha=0.7))
    
    # Format plot
    ax.axis('off') 
    plt.title(f'{image_name} - {len(boxes)} boxes') 
    plt.tight_layout()
    # Save figure
    plt.savefig('dataset_sample.png', dpi=150)
    print(f"   Saved visualization to: dataset_sample.png")
    # Show plot
    plt.show() 


if __name__ == '__main__':
    check_dataset()