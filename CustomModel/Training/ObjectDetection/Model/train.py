#Train.py - Training script for Object Detection Model
import torch
from torch.utils.data import DataLoader
from torch.optim import SGD
from torch.optim.lr_scheduler import MultiStepLR
from tqdm import tqdm
import os

from model import YOLO
from dataset import YOLODataset, YOLODatasetDebug
from loss import YOLOLoss
from utils import decode_predictions, non_max_suppression, calculate_map, targets_to_boxes
from config import *

def train_one_epoch(model, loader, criterion, optimizer, device, epoch):
    """Train for one epoch."""
    model.train() # Set model to training mode
    total_loss = 0.0 # Resets training loss
    losses_dict = {'coord': 0.0, 'obj': 0.0, 'noobj': 0.0, 'class': 0.0} #resets losses

    pbar = tqdm(loader, desc=f"Epoch {epoch+1}/{EPOCHS}") # Progress bar

    for batch_idx, (images, targets) in enumerate(pbar): #Creates training loop
        # Moves data to device
        images = images.to(device)
        targets = targets.to(device)

        # Forward pass: model creates predictions from input images
        predictions = model(images)
        
        # Calculate YOLO loss
        output = criterion(predictions, targets)
        if isinstance(output, tuple):
            loss, loss_components = output
        else:
            loss = output
            loss_components = losses_dict

        # Backward pass: compute gradients of loss w.r.t. model parameters
        optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping - prevents high gradient values
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=10.0)
        
        # Update weights in model
        optimizer.step()

        # Updates total loss and individual losses
        total_loss += loss.item()
        for k in losses_dict:
            losses_dict[k] += loss_components[k]

        # Update progress bar
        pbar.set_postfix({
            'loss': f'{loss.item():.4f}',
            'obj': f'{loss_components["obj"]:.4f}',
            'noobj': f'{loss_components["noobj"]:.4f}'
        })
        
        # Debug print
        if batch_idx % DEBUG_PRINT_FREQ == 0 and batch_idx > 0:
            print(f"\n[Epoch {epoch+1} | Batch {batch_idx}/{len(loader)}]")
            print(f"  Loss: {loss.item():.4f}")
            print(f"  Coord: {loss_components['coord']:.4f} | "
                  f"Obj: {loss_components['obj']:.4f} | "
                  f"NoObj: {loss_components['noobj']:.4f} | "
                  f"Class: {loss_components['class']:.4f}")

    # Calculate averages - after training epoch
    avg_loss = total_loss / len(loader)
    for k in losses_dict:
        losses_dict[k] /= len(loader)

    return avg_loss, losses_dict

def validate(model, loader, criterion, device):
    """
    Validate the model using the validation dataset.
    """
    model.eval() #Set model to evaluation mode
    total_loss = 0.0 #Resets validation loss

    #Resets predictions and targets
    all_predictions = [] 
    all_targets = []

    with torch.no_grad(): #No gradient calculation for validation
        for images, targets in tqdm(loader, desc="Validation"): #Validation loop
            #Moves data to device
            images = images.to(device)
            targets = targets.to(device)

            #Forward pass: creating predictions
            predictions = model(images)
            
            #Calculate YOLO loss
            output = criterion(predictions, targets)
            loss = output[0] if isinstance(output, tuple) else output
            total_loss += loss.item()

            # Process predictions and targets for mAP calculation
            pred_boxes = decode_predictions(
                predictions,
                conf_threshold=0.3 #Using 0.3 confidence threshold
            )
            target_boxes = targets_to_boxes(targets)

            # Apply NMS to predictions to reduce overlapping
            pred_boxes = [non_max_suppression(b, iou_threshold=0.45) for b in pred_boxes]

            # Accumulate all predictions and targets
            all_predictions.extend(pred_boxes)
            all_targets.extend(target_boxes)

    # Compute and print validation statistics
    total_pred = sum(len(p) for p in all_predictions)
    total_tgt = sum(len(t) for t in all_targets)

    print(f"\n Validation Statistics:")
    print(f"   Total predictions (after NMS): {total_pred}")
    print(f"   Total targets: {total_tgt}")
    print(f"   Avg pred per image: {total_pred / max(len(all_predictions),1):.1f}")
    print(f"   Avg target per image: {total_tgt / max(len(all_targets),1):.1f}")

    avg_loss = total_loss / len(loader)

    # mAP measures detection quality across all classes and IoU thresholds
    # Calculate mAP only if there are predictions
    if total_pred == 0:
        mAP = 0.0 
    else:
        mAP = calculate_map(all_predictions, all_targets)

    # Return average loss and mAP
    return avg_loss, mAP

def save_checkpoint(model, optimizer, epoch, loss, filename):
    """Save model checkpoint"""
    # Create checkpoint dictionary
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss
    }

    # Save to file
    torch.save(checkpoint, filename)

    #Print confirmation
    print(f"Saved checkpoint: {filename}")


def load_checkpoint(model, optimizer, filename):
    """Load model checkpoint."""
    if os.path.exists(filename): # Check if file exists
        try:
            checkpoint = torch.load(filename, map_location=DEVICE) # Load checkpoint
            model.load_state_dict(checkpoint['model_state_dict']) # Load model weights
            optimizer.load_state_dict(checkpoint['optimizer_state_dict']) # Load optimizer state
            epoch = checkpoint['epoch'] # Get epoch it was saved at
            loss = checkpoint['loss'] # Get loss at that epoch
            print(f"Loaded checkpoint: {filename} (epoch {epoch})") # Print confirmation
            return epoch + 1, loss
        except Exception as e:
            print(f" Could not load checkpoint: {e}") # Print error message if loading fails
            return 0, float('inf')
    return 0, float('inf')


def main():
    print("YOLO TRAINING")
    
    print(f"\n Using device: {DEVICE}")
    
    # Loading Datasets
    print(f"\n Loading datasets")
    
    train_dataset = YOLODataset(
        TRAIN_IMG_DIR,
        TRAIN_LABEL_DIR,
        augment=True
    )

    val_dataset = YOLODataset(
        VAL_IMG_DIR,
        VAL_LABEL_DIR,
        augment=False
    )

    train_loader = DataLoader( #Creates batched data loader
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        pin_memory=True if DEVICE == 'cuda' else False
    )

    val_loader = DataLoader( #Creates batched data loader
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
        pin_memory=True if DEVICE == 'cuda' else False
    )
    
    # Dataset Stats
    print(f"   Training images: {len(train_dataset)}")
    print(f"   Validation images: {len(val_dataset)}")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Training batches: {len(train_loader)}")

    #Create YOLO model instance and moves it to device
    print(f"\n Creating model")
    model = YOLO().to(DEVICE)
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"   Parameters: {num_params:,}")
    
    # Using Class Weights if enabled
    if USE_CLASS_WEIGHTS:
        criterion = YOLOLoss(class_weights=CLASS_WEIGHTS) #YOLO loss with class weights
    else:
        criterion = YOLOLoss() #YOLO loss without class weights

    # Optimizer and Scheduler
    optimizer = SGD(
        model.parameters(),
        lr=LEARNING_RATE,
        momentum=MOMENTUM,
        weight_decay=WEIGHT_DECAY
    )

    milestones = [k for k in LR_SCHEDULE.keys() if k > 0]
    scheduler = MultiStepLR(
        optimizer,
        milestones=milestones,
        gamma=0.1
    )
    
    # Print training configuration
    print(f"\n  Training configuration:")
    print(f"   Learning rate: {LEARNING_RATE}")
    print(f"   LR schedule: {LR_SCHEDULE}")
    print(f"   LAMBDA_COORD: {LAMBDA_COORD}")
    print(f"   LAMBDA_NOOBJ: {LAMBDA_NOOBJ}")
    print(f"   Epochs: {EPOCHS}")

    start_epoch, _ = load_checkpoint(model, optimizer, 'checkpoint.pth')
    best_map = 0.0

    # Training Loop
    print(f"\n Starting training")
    
    for epoch in range(start_epoch, EPOCHS): #Creates epoch loop
        # Update learning rate if scheduled
        if epoch in LR_SCHEDULE:
            for param_group in optimizer.param_groups:
                param_group['lr'] = LR_SCHEDULE[epoch]
            print(f"\n Learning rate changed to: {LR_SCHEDULE[epoch]}")

        # Call training function
        train_loss, train_losses = train_one_epoch(
            model, train_loader, criterion, optimizer, DEVICE, epoch
        )

        # Print epoch summary
        print(f"\n{'='*70}")
        print(f"EPOCH {epoch+1}/{EPOCHS} SUMMARY")
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Coord:  {train_losses['coord']:.4f} (weight: {LAMBDA_COORD}x)")
        print(f"Obj:    {train_losses['obj']:.4f}")
        print(f"NoObj:  {train_losses['noobj']:.4f} (weight: {LAMBDA_NOOBJ}x)")
        print(f"Class:  {train_losses['class']:.4f}")

        # Validation step every VALIDATE_EVERY epochs
        if (epoch + 1) % VALIDATE_EVERY == 0:
            print(f"\n Running validation...")

            #Call validation function
            val_loss, mAP = validate(model, val_loader, criterion, DEVICE)
            
            # Print validation summary
            print(f"\n Validation Results:")
            print(f"   Val Loss: {val_loss:.4f}")
            print(f"   mAP:  {mAP:.4f}")

            # Save best model based on mAP
            if mAP > best_map:
                best_map = mAP
                save_checkpoint(model, optimizer, epoch, val_loss, "best_model.pth")
                print(f"New best mAP: {mAP:.4f}")
        
        # Save checkpoint every SAVE_CHECKPOINT_EVERY epochs
        if (epoch + 1) % SAVE_CHECKPOINT_EVERY == 0:
            save_checkpoint(model, optimizer, epoch, train_loss, 
                          f"checkpoint_epoch_{epoch+1}.pth")

        # Step the scheduler to update learning rate
        scheduler.step()

    # Training completed
    print(f"\n{'='*70}")
    print("TRAINING COMPLETE!")
    
    # Save final model
    save_checkpoint(model, optimizer, EPOCHS-1, train_loss, "final_model.pth")
    
    #Print final results
    print(f"\n Final Results:")
    print(f"   Best mAP: {best_map:.4f}")
    print(f"   Models saved:")
    print(f"   - best_model.pth (highest mAP)")
    print(f"   - final_model.pth (last epoch)")
    print(f"\n Training finished successfully!")


if __name__ == "__main__":
    main()