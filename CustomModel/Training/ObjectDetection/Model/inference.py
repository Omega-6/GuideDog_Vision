#Inference.py - Inference and visualization for YOLO Object Detection Model
import torch
import torchvision.transforms as transforms
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
import time

from model import YOLO
from utils import decode_predictions, non_max_suppression
from config import IMAGE_SIZE, DEVICE, CONF_THRESHOLD, NMS_THRESHOLD


class YOLOInference:
    """
    Inference class for YOLO Object Detection Model.
    Runs inference, visualization, and analysis.
    """
    def __init__(self, model_path, class_names=None):
        """
        Initialize inference.
        
        Args:
            model_path: Path to trained model checkpoint
            class_names: List of class names (optional)
        """
        self.device = DEVICE
        self.class_names = class_names
        
        # Load model
        print(f"Loading model from {model_path}")

        # Creates YOLO model and moves it to device
        self.model = YOLO().to(self.device)
        
        try:
            # Attempts to load model checkpoint
            checkpoint = torch.load(model_path, map_location=self.device)
            
            # Loads model weights
            self.model.load_state_dict(checkpoint['model_state_dict'])

            # Sets model to evaluation mode
            self.model.eval()
            
            # If epoch info is available, print it
            if 'epoch' in checkpoint:
                print(f"Model loaded (trained for {checkpoint['epoch']+1} epochs)")
            else:
                print(f"Model loaded successfully")

        except Exception as e: #If loading fails
            raise RuntimeError(f"Failed to load model: {e}") # Raises error with message
        
        # Image preprocessing 
        self.transform = transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)), # Resize to model input size
            transforms.ToTensor(), # Converts image to tensor
            transforms.Normalize( # Normalizes using ImageNet stats
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def predict(self, image_path, conf_threshold=CONF_THRESHOLD, 
                nms_threshold=NMS_THRESHOLD):
        """
        Run inference on a single image.
        
        Args:
            image_path: Path to image file
            conf_threshold: Confidence threshold
            nms_threshold: NMS IoU threshold
        
        Returns:
            boxes: List of [x, y, w, h, confidence, class_id]
            original_size: (width, height) of original image
        """

        # Attempts to load image
        try:
            image = Image.open(image_path).convert('RGB')
        except Exception as e: # Raises error if loading fails
            raise RuntimeError(f"Failed to load image {image_path}: {e}")
        
        original_size = image.size  # Stores original image size
        
        # Preprocess: adds batch dimension and moves to device
        image_tensor = self.transform(image).unsqueeze(0).to(self.device)
        
        # Run inference
        with torch.no_grad(): # Disables gradient computation
            predictions = self.model(image_tensor) # (1, S, S, NUM_BOXES*5 + NUM_CLASSES)
        
        # Decode predictions: converts to bounding boxes
        boxes = decode_predictions(predictions, conf_threshold=conf_threshold)[0]
        
        # Apply NMS: removes overlapping boxes
        boxes = non_max_suppression(boxes, iou_threshold=nms_threshold)

        # Returns boxes and original image size
        return boxes, original_size
    
    def predict_batch(self, image_paths, conf_threshold=CONF_THRESHOLD,
                     nms_threshold=NMS_THRESHOLD):
        """
        Run inference on multiple images.
        
        Args:
            image_paths: List of image file paths
            conf_threshold: Confidence threshold
            nms_threshold: NMS IoU threshold
        
        Returns:
            List of dictionaries with 'path', 'boxes', 'size'
        """
        results = []
        
        for img_path in image_paths: # Loops over image paths
            try: # Attempts to load and infer using predict()
                boxes, size = self.predict(img_path, conf_threshold, nms_threshold)

                # Appends results
                results.append({
                    'path': img_path,
                    'boxes': boxes,
                    'size': size,
                    'success': True
                })
            except Exception as e: # Raises errors during prediction if any image fails
                print(f"Failed on {img_path}: {e}")

                # Appends empty result on failure
                results.append({
                    'path': img_path,
                    'boxes': [],
                    'size': None,
                    'success': False
                })
        
        # Return list of results
        return results
    
    def visualize(self, image_path, conf_threshold=CONF_THRESHOLD,
                  nms_threshold=NMS_THRESHOLD, save_path=None):
        """
        Visualize predictions on an image by drawing bounding boxes.
        
        Args:
            image_path: Path to image
            conf_threshold: Confidence threshold
            nms_threshold: NMS threshold
            save_path: Optional path to save result
        
        Returns:
            boxes: Detected boxes
        """
        # Get predictions
        boxes, original_size = self.predict(image_path, conf_threshold, nms_threshold)

        # Apply NMS again for safety
        boxes = non_max_suppression(boxes, iou_threshold=nms_threshold)

        # Load original image
        image = Image.open(image_path).convert('RGB')
        
        # Create plot for visualization
        fig, ax = plt.subplots(1, figsize=(12, 9))

        # Display image on plot
        ax.imshow(image)
        
        # Get original image size
        width, height = original_size
        
        # Define colors for each class
        colors = plt.cm.rainbow(np.linspace(0, 1, 10))
        
        # Draw boxes
        for box in boxes: # Loops over detected boxes
            x, y, w, h, conf, class_id = box # Unpacks box parameters
            
            # Convert from normalized coords to pixel coords
            x1 = (x - w/2) * width
            y1 = (y - h/2) * height
            box_width = w * width
            box_height = h * height
            
            # Choose color based on class
            color = colors[int(class_id) % len(colors)]
            
            # Create rectangle for each bounding box
            rect = patches.Rectangle(
                (x1, y1), box_width, box_height,
                linewidth=2,
                edgecolor=color,
                facecolor='none'
            )

            # Adds rectangle to plot
            ax.add_patch(rect)
            
            # Determine label
            if self.class_names is not None and int(class_id) < len(self.class_names):
                label = self.class_names[int(class_id)]
            else:
                label = f'Class {int(class_id)}'
            
            # Add label with class name and confidence to plot
            ax.text(
                x1, y1 - 5,
                f'{label}: {conf:.2f}',
                color='white',
                fontsize=10,
                bbox=dict(facecolor=color, alpha=0.7)
            )
        
        # Finalize plot
        ax.axis('off')

        # Include title with number of detections and threshold
        plt.title(f'Detections: {len(boxes)} | Threshold: {conf_threshold:.2f}')
        plt.tight_layout()
        
        # Save if path provided
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=150)
            print(f'Saved to {save_path}')
        
        # Show plot
        plt.show()
        
        # Returns detected boxes
        return boxes
    
    def analyze_predictions(self, boxes, class_names=None):
        """
        Print detailed analysis of predictions.
        """
        if len(boxes) == 0: # If no boxes detected
            print("No detections") # Print message
            return # Exit function
        
        # Else continue with analysis
        print(f"DETECTION ANALYSIS")
        print(f"{'='*70}")
        print(f"Total detections: {len(boxes)}\n")
        
        # Group by class
        class_counts = {} # Creates empty dictionary
        for box in boxes: # Loops over detected boxes
            class_id = int(box[5]) # Gets class ID
            if class_id not in class_counts: # If class not in dict 
                class_counts[class_id] = [] # Add new class to dict
            class_counts[class_id].append(box) # Else adds box to existing class list
        
        # Print per-class statistics
        for class_id in sorted(class_counts.keys()): # Loops over each class
            count = len(class_counts[class_id]) # Counts boxes for class
            avg_conf = np.mean([b[4] for b in class_counts[class_id]]) # Average confidence for class
            
            if class_names is not None and class_id < len(class_names): # Gets class name if available
                name = class_names[class_id] # Uses provided class names
            else:
                name = f"Class {class_id}" # Else uses number
            
            # Prints class summary

            print(f"{name}:")
            print(f"   Count: {count}") 
            print(f"   Avg confidence: {avg_conf:.3f}")
            
            # List individual boxes
            for i, box in enumerate(class_counts[class_id], 1): # Loops over boxes in class
                x, y, w, h, conf, _ = box # Unpacks box parameters
                print(f"   [{i}] conf={conf:.3f}, pos=({x:.2f}, {y:.2f}), size=({w:.2f}×{h:.2f})") # Prints box details
            print()


def benchmark_speed(model_path, num_iterations=100):
    """
    Benchmark inference speed.
    """
    
    print(f"Benchmarking inference speed")

    # Create model and move it to device
    model = YOLO().to(DEVICE)

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=DEVICE)

    # Load model weights
    model.load_state_dict(checkpoint['model_state_dict'])

    # Set model to evaluation mode
    model.eval()
    
    # Dummy input
    dummy_input = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE).to(DEVICE)
    
    # Dummy run 
    with torch.no_grad():
        for _ in range(10):
            _ = model(dummy_input)
    
    # Real Benchmark
    times = []
    with torch.no_grad(): # Disables gradient computation
        for _ in range(num_iterations): # Loops for specified iterations
            start = time.time() # Start time
            _ = model(dummy_input) # Model inference
            if DEVICE == 'cuda': # Synchronizes for accurate timing
                torch.cuda.synchronize() # Ensures all CUDA ops complete
            times.append(time.time() - start) # End time and record duration
    
    avg_time = np.mean(times) * 1000  # Convert to ms
    fps = 1000 / avg_time # Calculate FPS
    
    # Print results
    print(f"Benchmark complete:")
    print(f"Average inference time: {avg_time:.2f} ms")
    print(f"Throughput: {fps:.1f} FPS")
    print(f"Device: {DEVICE}")


def main():
    """
    Main function to run inference and visualization.
    """

    # Class names for visualization
    CLASS_NAMES = [
        'Door', 'cabinetDoor', 'refrigeratorDoor', 'window', 'chair',
        'table', 'cabinet', 'couch', 'openedDoor', 'pole'
    ]
    
    # Initialize detector
    try: # Attempts to load model
        detector = YOLOInference('TrainedModels/final_model.pth', class_names=CLASS_NAMES)
    except Exception as e: # Raises error if loading fails
        print(f"Could not load model: {e}")
        print("Make sure you have trained the model first!")
        return
    
    # Run inference on single image
    image_path = '../Data/IMG_7009.jpg' # Update with test image path
    
    if not os.path.exists(image_path): # Checks if image exists
        print(f"Image not found: {image_path}") # Prints error message if not found
        print("Update the image_path in main() to point to your test image")
        return # Exits function
    
    # If it exists, run visualization
    print(f"\n Running inference on: {image_path}")

    # Creates visualization and gets boxes
    boxes = detector.visualize(
        image_path,
        conf_threshold=CONF_THRESHOLD,
        save_path='result.jpg'
    )
    
    # Analyze predictions
    detector.analyze_predictions(boxes, CLASS_NAMES)
    
    # Benchmark speed
    print(f"\n{'='*70}")
    benchmark_speed('best_model.pth')


if __name__ == '__main__':
    main()