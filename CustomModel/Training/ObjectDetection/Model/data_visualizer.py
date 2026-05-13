# Data-Visualizer.py - Visualize YOLO Ground Truth Labels for Debugging
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import numpy as np
from config import GRID_SIZE 
# List of class names
CLASS_NAMES = [
    'Door', 'cabinetDoor', 'refrigeratorDoor', 'window', 'chair',
    'table', 'cabinet', 'couch', 'openedDoor', 'pole'
]

def parse_yolo_label(label_line):
    """
    Parses a YOLO label string into structured bounding boxes.
    """
    parts = label_line.strip().split() # Split line into tokens
    boxes = [] # Initialize empty list for boxes
    
    for i in range(0, len(parts), 5): # Looping over each box (5 values each)
        if i + 4 < len(parts): # Ensure enough parts for a box
            # Extract box values
            class_id = int(parts[i]) 
            x = float(parts[i+1])
            y = float(parts[i+2])
            w = float(parts[i+3])
            h = float(parts[i+4])

            # Append box to list
            boxes.append([class_id, x, y, w, h]) 
    
    # Return list of boxes
    return boxes
    

def visualize_ground_truth(image_path, label_line, save_path='gt_visualization.png'):
    """
    Visualize YOLO ground truth labels on an image
    
    Args:
        image_path: Path to image
        label_line: String with YOLO format labels
        save_path: Where to save the visualization
    """
    # Load image
    img = Image.open(image_path)
    img_width, img_height = img.size
    
    # Parse labels
    boxes = parse_yolo_label(label_line)
    
    # Create figure
    fig, ax = plt.subplots(1, figsize=(15, 10))
    ax.imshow(img)
    
    # Colors for each class
    colors = plt.cm.rainbow(np.linspace(0, 1, len(CLASS_NAMES)))
    
    print(f"\n{'='*70}")
    print(f"GROUND TRUTH ANALYSIS")
    print(f"{'='*70}")
    print(f"Image size: {img_width}x{img_height}")
    print(f"Total boxes: {len(boxes)}\n")
    
    # Count boxes per class
    class_counts = {}
    for box in boxes: # Loop over each box
        class_id = box[0] # Extract class ID
        class_counts[class_id] = class_counts.get(class_id, 0) + 1 # Increment count for that class
    
    print("Class distribution:")
    for class_id, count in sorted(class_counts.items()): # Sort by class ID
        print(f"  {CLASS_NAMES[class_id]:20s} (class {class_id}): {count:2d} boxes") # Print class count
    
    print(f"\n{'='*70}")
    print("BOX DETAILS:")
    print(f"{'='*70}\n")
    
    # Draw each box
    for idx, box in enumerate(boxes):
        class_id, x_center, y_center, width, height = box
        
        # Convert to pixel coordinates
        x_center_px = x_center * img_width
        y_center_px = y_center * img_height
        width_px = width * img_width
        height_px = height * img_height
        
        # Calculate corners
        x1 = x_center_px - width_px / 2
        y1 = y_center_px - height_px / 2
        x2 = x_center_px + width_px / 2
        y2 = y_center_px + height_px / 2
        
        # Print details
        print(f"Box {idx+1}: {CLASS_NAMES[class_id]}")
        print(f"  Normalized: center=({x_center:.4f}, {y_center:.4f}), size=({width:.4f}x{height:.4f})")
        print(f"  Pixels:     center=({x_center_px:.1f}, {y_center_px:.1f}), size=({width_px:.1f}x{height_px:.1f})")
        print(f"  Corners:    ({x1:.1f}, {y1:.1f}) to ({x2:.1f}, {y2:.1f})")
        print()
        
        # Draw rectangle
        color = colors[class_id]
        rect = patches.Rectangle(
            (x1, y1), width_px, height_px,
            linewidth=3,
            edgecolor=color,
            facecolor='none'
        )
        ax.add_patch(rect)
        
        # Add label
        label = f'{CLASS_NAMES[class_id]} #{idx+1}'
        ax.text(
            x1, y1 - 5,
            label,
            color='white',
            fontsize=10,
            weight='bold',
            bbox=dict(facecolor=color, alpha=0.8, pad=2)
        )
        
        # Add center point
        ax.plot(x_center_px, y_center_px, 'r+', markersize=10, markeredgewidth=2)
    
    # Plot formatting
    ax.axis('off')
    plt.title(f'Ground Truth Labels: {len(boxes)} objects', fontsize=16, weight='bold')
    plt.tight_layout()

    # Save plot
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved visualization to: {save_path}")

    # Show plot
    plt.show()
    
    return boxes

def analyze_first_box_in_grid(label_line, grid_size=GRID_SIZE):
    """
    Analyze how the first box maps to grid cells
    """

    # Parse labels
    boxes = parse_yolo_label(label_line)
    
    # Check if any boxes exist
    if len(boxes) == 0:
        print("No boxes found!")
        return
    
    # Analyze first box
    box = boxes[0]

    # Unpack box
    class_id, x, y, w, h = box
    
    print(f"\n{'='*70}")
    print(f"GRID CELL MAPPING FOR FIRST BOX")
    print(f"{'='*70}\n")
    
    # Print box info
    print(f"Class: {CLASS_NAMES[class_id]} (ID: {class_id})")
    print(f"Normalized coordinates: x={x:.6f}, y={y:.6f}, w={w:.6f}, h={h:.6f}\n")
    
    # Calculate grid cell
    grid_j = int(x * grid_size)  # Grid column
    grid_i = int(y * grid_size)  # Grid Row
    
    # Calculate within-cell offsets
    x_cell = x * grid_size - grid_j
    y_cell = y * grid_size - grid_i
    
    # Print mapping details
    print(f"Grid mapping (GRID_SIZE={grid_size}):")
    print(f"  Grid cell: row={grid_i}, col={grid_j} (cell [{grid_i}, {grid_j}])")
    print(f"  Within-cell offset: x_cell={x_cell:.6f}, y_cell={y_cell:.6f}")
    print(f"  Box size in cell: w={w:.6f}, h={h:.6f}")
    
    # Print expected target tensor location
    print(f"\nTarget tensor location:")
    print(f"  target[{grid_i}, {grid_j}, 0:5] should contain:")
    print(f"    [0] x_cell: {x_cell:.6f}")
    print(f"    [1] y_cell: {y_cell:.6f}")
    print(f"    [2] w:      {w:.6f}")
    print(f"    [3] h:      {h:.6f}")
    print(f"    [4] conf:   1.0")
    print(f"  target[{grid_i}, {grid_j}, 5+{class_id}] should be 1.0")
    
    # Visualize grid
    print(f"\n{'='*70}")
    print(f"GRID VISUALIZATION ({grid_size}x{grid_size}):")
    print(f"{'='*70}\n")
    
    for i in range(grid_size): # Loop over rows
        row = "" 
        for j in range(grid_size): # Loop over columns
            if i == grid_i and j == grid_j: # Mark cell with box
                row += " [X] "
            else:
                row += "  .  "
        print(row)
    
    print(f"\n[X] marks cell [{grid_i}, {grid_j}] containing box 1")


if __name__ == '__main__':
    # Label line for testing
    label_line = "1 0.431758 0.735761 0.063581 0.175870 1 0.288637 0.649826 0.069339 0.025913 1 0.219952 0.642837 0.054742 0.021717 1 0.289000 0.737533 0.069290 0.123196 1 0.518685 0.767935 0.095435 0.133261 6 0.470645 0.454000 0.517032 0.304522 1 0.606637 0.777674 0.061565 0.132783 8 0.868919 0.621761 0.216871 0.542609 7 0.621944 0.878207 0.357403 0.243587 7 0.122226 0.736783 0.244452 0.120435 1 0.628605 0.684326 0.091790 0.029000 1 0.520508 0.673217 0.091790 0.029000 1 0.365185 0.726022 0.065532 0.162739"
    
    # Image path for testing
    image_path = '../Data/test/images/1251.png'  # Update this path
    
    print("YOLO GROUND TRUTH DEBUGGER")
    print("="*70)
    
    # Analyze grid cell mapping for first box
    analyze_first_box_in_grid(label_line)
    
    # Visualize all ground truth boxes
    visualize_ground_truth(image_path, label_line)