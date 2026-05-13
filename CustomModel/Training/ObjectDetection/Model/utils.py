#Utils.py - Utility functions for Object Detection Model
import torch
import numpy as np
import torch.nn.functional as F
from config import GRID_SIZE, NUM_BOXES, NUM_CLASSES, CONF_THRESHOLD, NMS_THRESHOLD, MAP_IOU_THRESHOLD

def decode_predictions(preds, conf_threshold=CONF_THRESHOLD):
    """
    Convert model predictions to bounding boxes.
    preds: (B, S, S, NUM_BOXES * 5 + NUM_CLASSES)
    Returns: List of lists of boxes [x, y, w, h, conf, class_id]
    """
    B, S, _, _ = preds.shape #B is batch size, S is grid size, _ is ignored

    #Creates preds and boxes_batch
    preds = preds.detach()
    boxes_batch = []

    for b in range(B): #Looping over batch
        boxes = []
        for i in range(S): #Looping over horizantal grids 
            for j in range(S): #Looping over vertical grids
                for box_idx in range(NUM_BOXES): #Looping over predicted boxes in each cell
                    o = box_idx * 5

                    # Objectness confidence: value between 0 and 1 indicating presence of object
                    obj_conf = torch.sigmoid(preds[b, i, j, o + 4])

                    # Removes low confidence boxes early
                    if obj_conf < conf_threshold:
                        continue

                    # XY offsets: value between 0 and 1 within the grid cell
                    x_cell = torch.sigmoid(preds[b, i, j, o + 0])
                    y_cell = torch.sigmoid(preds[b, i, j, o + 1])

                    # WH: normalized width and height (0–1, relative to full image size)
                    w = torch.sigmoid(preds[b, i, j, o + 2])
                    h = torch.sigmoid(preds[b, i, j, o + 3])

                    # Converts cell relative coords to global image coords
                    x = (j + x_cell) / S
                    y = (i + y_cell) / S

                    # Class prediction
                    class_logits = preds[b, i, j, NUM_BOXES * 5:] #Raw class scores
                    class_probs = F.softmax(class_logits, dim=-1) #Converts to class probabilities
                    cls = torch.argmax(class_probs) #Predicted class index
                    cls_conf = class_probs[cls] #Confidence of predicted class

                    # Final YOLO confidence: combines objectness and class confidence
                    score = obj_conf * cls_conf

                    # Skips boxes below confidence threshold
                    if score < conf_threshold:
                        continue

                    # Appends valid box to list
                    boxes.append([
                        x.item(), y.item(),
                        w.item(), h.item(),
                        score.item(),
                        cls.item()
                    ])
        boxes_batch.append(boxes)

    #Returns list of boxes per image in batch
    return boxes_batch



def targets_to_boxes(targets):
    """
    Convert ground-truth labels to box list.
    Returns same format as decode_predictions.
    """
    B, S, _, _ = targets.shape #B is batch size, S is grid size, _ is ignored
    all_boxes = []

    for b in range(B): #Looping over batch
        boxes = []
        for i in range(S): #Looping over horizantal grids
            for j in range(S): #Looping over vertical grids
                # Extracts cell target
                cell = targets[b, i, j]
                class_id = torch.argmax(cell[NUM_BOXES * 5:]).item() 

                for box_idx in range(NUM_BOXES): #Looping over boxes in each cell
                    o = box_idx * 5

                    # Objectness confidence
                    conf = cell[o + 4]

                    #Skips boxes with no object
                    if conf <= 0:
                        continue
                    
                    # Extracts box parameters
                    x_offset = cell[o + 0]
                    y_offset = cell[o + 1]

                    w = cell[o + 2]
                    h = cell[o + 3]

                    # Converts cell relative coords to global image coords
                    x = (j + x_offset) / S
                    y = (i + y_offset) / S

                    #Appends box to list
                    boxes.append([
                        x.item(),
                        y.item(),
                        w.item(),
                        h.item(),
                        conf.item(),
                        class_id
                    ])

        all_boxes.append(boxes)

    #Returns list of boxes per image in batch
    return all_boxes



def calculate_iou(b1, b2):
    """Calculate IoU(Intersection over Union) between two boxes [x, y, w, h]"""
    
    # Extracts box parameters
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2

    # Converts center coordinates to corner coordinates
    x1_min, x1_max = x1 - w1/2, x1 + w1/2
    y1_min, y1_max = y1 - h1/2, y1 + h1/2
    x2_min, x2_max = x2 - w2/2, x2 + w2/2
    y2_min, y2_max = y2 - h2/2, y2 + h2/2

    # Calculates intersection coordinates
    ix1 = max(x1_min, x2_min)
    iy1 = max(y1_min, y2_min)
    ix2 = min(x1_max, x2_max)
    iy2 = min(y1_max, y2_max)

    # Calculates intersection and union areas
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1) #Intersection area
    union = w1*h1 + w2*h2 - inter #Union area
    return inter / (union + 1e-6)  #Returns IoU value


def non_max_suppression(boxes, iou_threshold=NMS_THRESHOLD):
    """Remove duplicate detections"""
    
    # If no boxes, return empty list
    if len(boxes) == 0:
        return []

    # Sort boxes by confidence score in descending order
    boxes = sorted(boxes, key=lambda x: x[4], reverse=True)

    # List to hold final boxes after NMS
    keep = []

    while boxes: # Iterate while boxes remain
        chosen = boxes.pop(0) #Selects box with highest confidence
        keep.append(chosen) # Adds the chosen box to keep list

        boxes = [
            b for b in boxes
            if b[5] != chosen[5] or
            calculate_iou(chosen[:4], b[:4]) < iou_threshold # Remove overlapping boxes of the same class (class-aware NMS)
]

    #Returns list of boxes after NMS
    return keep


def calculate_map(all_preds, all_targets, iou_thresh=None):
    """
    Calculate mean Average Precision - mAP.
    
    Args:
        all_preds: List[List[[x,y,w,h,conf,class]]]
        all_targets: List[List[[x,y,w,h,conf,class]]]
        iou_thresh: IoU threshold (uses MAP_IOU_THRESHOLD from config if None)
    
    Returns:
        mAP score (0-1)
    """
    if iou_thresh is None: #Uses config value (0.3) if no threshold provided
        iou_thresh = MAP_IOU_THRESHOLD 
    
    aps = [] #Average Precisions
    
    # Calculate AP for each class
    for class_id in range(NUM_CLASSES): #Iterates over all classes
        # Lists to hold all predictions and targets for this class
        all_pred = []
        all_target = []
        
        # Collect all predictions and targets for this class
        for i, (pred, target) in enumerate(zip(all_preds, all_targets)): #Iterates over all images
            all_pred += [(i, p) for p in pred if p[5] == class_id] #Adds predictions of this class
            all_target += [(i, t) for t in target if t[5] == class_id] #Adds targets of this class
        
        # Skip if no targets for this class
        if len(all_target) == 0:
            continue
        
        # Sort predictions by confidence
        all_pred.sort(key=lambda x: x[1][4], reverse=True)
        
        # Track matched targets
        matched = set()
        tp, fp = [], [] #True Positives, False Positives
        
        # For each prediction, check if it matches a target
        for img_idx, pred_box in all_pred:
            best_iou = 0.0
            best_idx = -1
            
            # Find best matching target in same image
            for j, (t_img, t_box) in enumerate(all_target):
                if t_img != img_idx:
                    continue
                iou = calculate_iou(pred_box[:4], t_box[:4])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = j
            
            # Check if match is past the threshold and not already matched
            if best_iou >= iou_thresh and best_idx not in matched:
                tp.append(1)
                fp.append(0)
                matched.add(best_idx)
            else:
                tp.append(0)
                fp.append(1)
        
        # Calculate precision and recall
        tp = np.cumsum(tp)
        fp = np.cumsum(fp)
        
        # Use Precision-Recall curve to calculate AP
        recalls = tp / len(all_target)
        precisions = tp / (tp + fp + 1e-6)
        
        # Calculate AP using 11-point interpolation
        ap = 0
        for t in np.linspace(0, 1, 11): 
            p = np.max(precisions[recalls >= t]) if np.any(recalls >= t) else 0
            ap += p / 11
        
        # Add class AP to list
        aps.append(ap)
    
    # Return Final mAP score
    return np.mean(aps) if aps else 0.0