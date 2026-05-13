# YOLO Object Detection Model
Created by TSA Software Development 2025-2026

## Overview
This project uses a YOLO-style detection model built from scratch using PyTorch. This model is able to detect multiple objects, identify their coordinates, and class them into 1 of 10 groups provided. After that, it is also able to create color-coding bounding boxes to visualize where the object are. This model is then exported to a onnx model to then run on the user's mobile device. 

This project includes:
    A custom YOLO model
    Dataset loader with augmentation
    YOLO loss function
    Training utilities
    Inference + visualization tools
    Dataset validation and debugging scripts
    ONNX export for deployment

## Objectives
    Create a program capable of making a object detection machine learning model.
    Create the Convolutional Neural Network Backbone as well as Loss function necessary to allow for a YOLO model.
    Train a YOLO-style Neural Network for object detection
    Predict bounding boxes onto an image
    Visualize and analyze predictions
    Evaluate performance using mAP and improve

## How YOLO Works
The image is resized to a certain pixel dimension (448 x 448)
The model then divides it into grids in both columns and rows (7 x 7)
Each grid can predict a certain amount of boxes(1), if any
Each box is formatted as such: (center x, center y, width relative to image, height relative to image, confidence)
It also predicts the probabilites for each class, which later gets assigned to the highest probability
Predictions are decoded into real image coordinates
Non-Max Suppression (NMS) removes duplicate detections
Final detections are visualized and evaluated

## Project Structure
.
model.py              # YOLO neural network
loss.py               # YOLO loss function
dataset.py            # Dataset loader + augmentation
utils.py              # Decoding, IoU, NMS, mAP
inference.py          # Inference & visualization
export_onnx.py        # Export trained model to ONNX
check_dataset.py      # Dataset validation before training
verify_dataset.py     # Dataset verification check
config.py             # All hyperparameters
requirements.txt      # Python dependencies
TrainedModels/
   final_model.pth.   # Final model
README.md             # Readme document(Currently on)

## Dependencies

Install all dependencies needed by running this command before running any programs:
"pip install -r requirements.txt"

## Dataset
Using dataset https://www.kaggle.com/datasets/thepbordin/indoor-object-detection
Images are in .png and .jpg formats
Labels are in .txt format
Each label.txt can have several or no target boxes
Each target box has this format: class_id x_center y_center width height
All values should be between 0 and 1

## Dataset Validation and Verification
To ensure check the following on the dataset, run "python3 check_dataset.py"
    Verifies image/label pairing
    Checks label formatting
    Detects invalid coordinates
    Reports class imbalance
    Visualizes sample bounding boxes

To visualize the data, run "python3 data_visualizer.py"

To validate the dataset, run "python3 data_debug.py"

All of these are not needed to run for the YOLO model to work, they all just ensure the dataset is strong and usable.

## Training
The training uses the custom YOLO Loss function, MSE for box regression, Cross-Entropy for classification, and IoU-based objectness target

Key hyperparamters are initalized and can be changes in config.py

To train the model, run "python3 train.py"

Training the model does take a significant amount of computer resources and requires several hours to run

## Inference
To run an inference on a single image, change the model path and image path in 
inference.py to the desired model and image

After that, run "python3 inference.py" to see the model's predictions

## Evaluation
As an evaluation metric, mAP, or Mean Average Precision, is calculated in utils.py.
It uses a IoU threshold as well as an 11-point interpolation to find the mAP.

This is found directly when running the training

## Model Export
When satisfied with the model, change the model path in export_yolo_onnx.py to the desired path. 

Then, run "python3 export_yolo_onnx.py" to turn the .pth model into a .onnx model, which can run much smoother on phones and in browsers. The file "yolo.onnx" should appear afterwards. 

This .onnx model already created for the current .pth model


