# Config.py - Configuration file for Object Detection Model
import torch

# Data Configuration
IMAGE_SIZE = 448 # Each image starts at 448x448 pixels
GRID_SIZE = 7 # Each image is split into a 7x7 Grid
NUM_BOXES = 1 # Each grid cell predicts a maximum of 1 bounding box
NUM_CLASSES = 10 # Total number of object classes

# Training Configuration
BATCH_SIZE = 16 # Number of images per training batch
EPOCHS = 100 # Number of full passes over the entire training dataset
WEIGHT_DECAY = 5e-4 # Creates a penalty for large weights to prevent overfitting
MOMENTUM = 0.9 # Controls how much past gradients influence current updates
LEARNING_RATE = 1e-3  # Initial learning rate for the model

# Learning Rate Configuration
LR_SCHEDULE = {
    0: 1e-3, # Epochs 0-49: 0.001
    50: 1e-4, # Epochs 50-74: 0.0001
    75: 5e-5 #Epochs 75-100: 0.00005
}

# Loss Weights Configuration
LAMBDA_COORD = 5.0 # Weight for bounding box coordinate loss     
LAMBDA_NOOBJ = 0.15 # Weight for no-object confidence loss    
LAMBDA_CLASS = 0.6 # Weight for class prediction loss

# Class Weighting Configuration
USE_CLASS_WEIGHTS = True # Enabling class weights to help with class imbalance
CLASS_WEIGHTS = [
    2.0,  # Class 0 - Door
    0.5,  # Class 1 - Cabinet Door (reduced weightage)
    1.5,  # Class 2 - Refrigerator Door
    3.0,  # Class 3 - Window
    3.0,  # Class 4 - Chair
    3.0,  # Class 5 - Table
    5.0,  # Class 6 - Cabinet
    5.0,  # Class 7 - Couch
    4.0,  # Class 8 - Opened Door
    3.0   # Class 9 - Pole
]

# Inference Configuration
CONF_THRESHOLD = 0.1 # Confidence threshold for filtering boxes
NMS_THRESHOLD = 0.45 # IoU threshold used by Non-Maximum Suppression to remove overlapping boxes.


# Data Augmentation Configuration
USE_AUGMENTATION = True # Enable data augmentation during training for better generalization
AUG_BRIGHTNESS = 0.3 # Brightness adjustment factor
AUG_CONTRAST = 0.3 # Contrast adjustment factor
AUG_SATURATION = 0.3 # Saturation adjustment factor
AUG_HUE = 0.05 # Hue adjustment factor
AUG_FLIP_PROB = 0.5 # Probability of horizontal flip

# Device Configuration
DEVICE = "mps" if torch.backends.mps.is_available() else \
         ("cuda" if torch.cuda.is_available() else "cpu") #Use MPS for Mac, else CUDA if available, else CPU for high efficiency

# Path Configuration
TRAIN_IMG_DIR = '../Data/train/images' # Path to training images
TRAIN_LABEL_DIR = '../Data/train/labels' # Path to training labels
VAL_IMG_DIR = '../Data/valid/images' # Path to validation images
VAL_LABEL_DIR = '../Data/valid/labels' # Path to validation labels

# Validation and Checkpointing Configuration
VALIDATE_EVERY = 5 # Use validation set every 5 epochs
SAVE_CHECKPOINT_EVERY = 10 # Save model checkpoint every 10 epochs
# Debug Configuration
DEBUG_PRINT_FREQ = 50 # Print debug info every 50 batches

# IOU Threshold for mAP Calculation Configuration
MAP_IOU_THRESHOLD = 0.3 # Use 0.3 IoU threshold for mAP calculation during training