#Loss.py - YOLO Loss Function
import torch
import torch.nn as nn
from config import LAMBDA_COORD, LAMBDA_NOOBJ, LAMBDA_CLASS

def intersection_over_union(boxes_preds, boxes_targets):
    '''
    Computes Intersection over Union(IoU) between predicted and target bounding boxes.
    IoU measures how much two boxes overlap (0: no overlap, 1: perfect match).
    '''
    # Converts center coordinates to corner coordinates for predicted boxes
    b1_x1 = boxes_preds[..., 0] - boxes_preds[..., 2] / 2
    b1_y1 = boxes_preds[..., 1] - boxes_preds[..., 3] / 2
    b1_x2 = boxes_preds[..., 0] + boxes_preds[..., 2] / 2
    b1_y2 = boxes_preds[..., 1] + boxes_preds[..., 3] / 2

    # Converts center coordinates to corner coordinates for target boxes
    b2_x1 = boxes_targets[..., 0] - boxes_targets[..., 2] / 2
    b2_y1 = boxes_targets[..., 1] - boxes_targets[..., 3] / 2
    b2_x2 = boxes_targets[..., 0] + boxes_targets[..., 2] / 2
    b2_y2 = boxes_targets[..., 1] + boxes_targets[..., 3] / 2

    # Calculates intersection coordinates
    inter_x1 = torch.max(b1_x1, b2_x1)
    inter_y1 = torch.max(b1_y1, b2_y1)
    inter_x2 = torch.min(b1_x2, b2_x2)
    inter_y2 = torch.min(b1_y2, b2_y2)

    # Calculates intersection area
    inter = (inter_x2 - inter_x1).clamp(0) * (inter_y2 - inter_y1).clamp(0)

    # Calculates areas of both boxes
    area1 = (b1_x2 - b1_x1).clamp(0) * (b1_y2 - b1_y1).clamp(0)
    area2 = (b2_x2 - b2_x1).clamp(0) * (b2_y2 - b2_y1).clamp(0)

    # Calculates and returns IoU
    return inter / (area1 + area2 - inter + 1e-6)


class YOLOLoss(nn.Module):
    '''
    YOLO Loss Function implementation.
    Combines coordinate, objectness, no-object, and classification losses.
    '''
    def __init__(self, class_weights=None): # Initializes YOLOLoss with optional class weights for classification loss.
        super().__init__()
        self.mse = nn.MSELoss(reduction="sum") # Mean Squared Error loss for regression tasks

        if class_weights is not None: # Use class weights if provided
            self.register_buffer(
                "class_weights",
                torch.tensor(class_weights, dtype=torch.float32)
            )
        else:
            self.class_weights = None # Otherwise, no class weights

    def forward(self, preds, targets): # Computes the YOLO loss given predictions and targets.
        B, S, _, _ = preds.shape # Batch size, grid size, unused, unused
        device = preds.device # Get device of predictions

        # Split predictions and targets into raw box parameters and class probabilities
        pred_raw = preds[..., :5]
        pred_cls = preds[..., 5:]

        # Split targets into raw box parameters and class probabilities
        tgt_raw = targets[..., :5]
        tgt_cls = targets[..., 5:]

        # Object mask to control loss application
        obj_mask = tgt_raw[..., 4] == 1

        # Grid Creation: 7x7 grid for YOLO
        grid_y, grid_x = torch.meshgrid(
            torch.arange(S, device=device),
            torch.arange(S, device=device),
            indexing="ij"
        )

        # Decode Predictions

        # Keeps x,y in (0,1) range within cell using sigmoid
        pred_xy_cell = torch.sigmoid(pred_raw[..., 0:2])

        # Keeps w,h in (0,1) range using sigmoid and clamps to avoid zero and negatives
        pred_wh = torch.sigmoid(pred_raw[..., 2:4]).clamp(1e-4, 1.0)

        # Objectness score between 0 and 1
        pred_conf = torch.sigmoid(pred_raw[..., 4])

        # Converts cell-relative coords to global image coords
        pred_x = (grid_x.unsqueeze(0) + pred_xy_cell[..., 0]) / S
        pred_y = (grid_y.unsqueeze(0) + pred_xy_cell[..., 1]) / S

        #Creates final predicted box coords
        pred_xy = torch.stack([pred_x, pred_y], dim=-1)
        pred_box = torch.cat([pred_xy, pred_wh], dim=-1)

        # Decode Targets 

        # Keeps x,y in (0,1) range within cell using sigmoid
        tgt_xy_cell = tgt_raw[..., 0:2]

        # Keeps w,h in (0,1) range using sigmoid and clamps to avoid zero and negatives
        tgt_wh = tgt_raw[..., 2:4]

        # Converts cell-relative coords to global image coords
        tgt_x = (grid_x.unsqueeze(0) + tgt_xy_cell[..., 0]) / S
        tgt_y = (grid_y.unsqueeze(0) + tgt_xy_cell[..., 1]) / S

        # Creates final predicted box coords
        tgt_xy = torch.stack([tgt_x, tgt_y], dim=-1)
        tgt_box = torch.cat([tgt_xy, tgt_wh], dim=-1)

        # Compute Losses
        if obj_mask.any(): # Only compute if there are objects in batch
            coord_loss = self.mse(pred_xy[obj_mask], tgt_xy[obj_mask]) # Computes coordinate loss based on predicted xy vs target xy
            
            #Stabilizes wh loss using square root to increase sensitivity to small boxes
            coord_loss += self.mse( 
                torch.sqrt(pred_wh[obj_mask]),
                torch.sqrt(tgt_wh[obj_mask])
            )

            # Computes IoU for object boxes
            iou = intersection_over_union(pred_box[obj_mask], tgt_box[obj_mask]).detach()

            # Objectness loss: predicted confidence vs IoU
            obj_loss = self.mse(
                pred_conf[obj_mask],
                iou
            )

            # Classification loss for object boxes
            pred_cls_obj = pred_cls[obj_mask]

            # Gets target class indices
            tgt_cls_idx = torch.argmax(tgt_cls[obj_mask], dim=-1).long().to(device)

            # Cross Entropy Loss with optional class weights
            ce = nn.CrossEntropyLoss(
                weight=self.class_weights,
                reduction="sum"
            ).to(device)

            # Loss based on predicted vs target classes
            class_loss = ce(pred_cls_obj, tgt_cls_idx)

        else: # No objects in batch
            coord_loss = obj_loss = class_loss = torch.tensor(0.0, device=device) # Prevents errors

        # No-objectness loss for boxes without objects
        noobj_loss = self.mse( 
            pred_conf[~obj_mask],
            torch.zeros_like(pred_conf[~obj_mask])
        )

        # Computes total loss with weighting factors
        total_loss = (
            LAMBDA_COORD * coord_loss +
            obj_loss +
            LAMBDA_NOOBJ * noobj_loss +
            LAMBDA_CLASS * class_loss
        ) / B

        # Returns total loss and individual components for monitoring
        return total_loss, {
            "coord": coord_loss.item() / B,
            "obj": obj_loss.item() / B,
            "noobj": noobj_loss.item() / B,
            "class": class_loss.item() / B,
        }
