#Model.py - YOLO Object Detection Model
import torch
import torch.nn as nn
from config import GRID_SIZE, NUM_CLASSES, NUM_BOXES, IMAGE_SIZE, DEVICE


class YOLO(nn.Module):
    """
    YOLO detection network.
    
    Architecture:
    - Convolutional backbone for feature extraction
    - Adaptive pooling to ensure 7x7 output
    - 1x1 conv head for predictions
    
    Output: (batch, GRID_SIZE, GRID_SIZE, NUM_BOXES*5 + NUM_CLASSES)
    """
    def __init__(self): #Runs when model is created
        super().__init__()
        
        # CNN Backbone: Feature extraction
        self.features = nn.Sequential(

            #Image Size: 448x448 - Needs to be reduced to GRID_SIZE: 7x7
            
            # Block 1: 3 Channels (RGB) + 64 channel depth + 7x7 convolution + MaxPool
            self._conv(3, 64, kernel_size=7, stride=2, padding=3), # Image Size: 448 -> 224
            nn.MaxPool2d(2, 2),  # Image Size: 224 -> 112

            # Block 2: 3 Channels + 192 channel depth + 3x3 convolution + MaxPool
            self._conv(64, 192, kernel_size=3, stride=1, padding=1),
            nn.MaxPool2d(2, 2),  # Image Size: 112 -> 56
            
            # Block 3: Uses 1x1 and 3x3 convolutions + 512 channel depth + MaxPool
            self._conv(192, 128, kernel_size=1),
            self._conv(128, 256, kernel_size=3, stride=1, padding=1),
            self._conv(256, 256, kernel_size=1),
            self._conv(256, 512, kernel_size=3, stride=1, padding=1),
            nn.MaxPool2d(2, 2),  # Image Size: 56 -> 28
            
            # Block 4: 3x3 convolution + 1024 channel depth
            self._conv(512, 1024, kernel_size=3, stride=1, padding=1),
        )
        
        # Adaptive Pooling - Force output to 7x7
        # This ensures output is exactly GRID_SIZE x GRID_SIZE regardless of input variations
        self.pool = nn.AdaptiveAvgPool2d((GRID_SIZE, GRID_SIZE)) # Image Size: 28 -> 7
        
        # DETECTION HEAD
        # Converts features to predictions
        # 1x1 convolution to predict:
        # - NUM_BOXES bounding boxes per cell: [x, y, w, h, confidence] × NUM_BOXES
        # - NUM_CLASSES class probabilities per cell
        out_channels = NUM_BOXES * 5 + NUM_CLASSES
        
        self.pred = nn.Conv2d(
            1024,
            out_channels,
            kernel_size=1,
            stride=1,
            padding=0
        )
        
        # Weight initialization
        self._initialize_weights()
    
    def _conv(self, in_c, out_c, kernel_size, stride=1, padding=0):
        """
        Convolutional block with BatchNorm and LeakyReLU. Avoids repeating code.
        """
        return nn.Sequential( #Full functional block
            nn.Conv2d(in_c, out_c, kernel_size, stride, padding, bias=False),
            nn.BatchNorm2d(out_c),
            nn.LeakyReLU(0.1, inplace=True)
        )
    
    def _initialize_weights(self):
        """
        Initialize network weights for better training stability.
        """
        for m in self.modules(): #Iterate through all modules/layers
            if isinstance(m, nn.Conv2d): # If layer is convolutional
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu') # He initialization
                if m.bias is not None: # Set bias to 0 if it exists
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d): # If layer is batch normalization
                nn.init.constant_(m.weight, 1) # Set weight to 1
                nn.init.constant_(m.bias, 0) # Set bias to 0
    
    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: (batch, 3, IMAGE_SIZE, IMAGE_SIZE)
        
        Returns:
            predictions: (batch, GRID_SIZE, GRID_SIZE, NUM_BOXES*5 + NUM_CLASSES)
        """
        # Feature extraction: Runs image through CNN backbone
        x = self.features(x)  # (batch, 1024, H, W)
        
        # Force to 7x7 grid
        x = self.pool(x)  # (batch, 1024, 7, 7)
        
        # Predictions
        x = self.pred(x)  # (batch, NUM_BOXES*5+NUM_CLASSES, 7, 7)
        
        # Reshape to (batch, 7, 7, NUM_BOXES*5+NUM_CLASSES)
        x = x.permute(0, 2, 3, 1)
        
        # Return final output
        return x
    
    def count_parameters(self):
        """Count trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad) #Sum of all parameters that require gradients



def test_model():
    """
    Utility function to test if model works correctly.
    """
    
    # Creates model and moves it to device
    model = YOLO().to(DEVICE)
    
    # Print model info
    print(f"Model created successfully!")
    print(f"Parameters: {model.count_parameters():,}")
    print(f"Output shape per image: ({GRID_SIZE}, {GRID_SIZE}, {NUM_BOXES*5 + NUM_CLASSES})")
    
    # Test forward pass using dummy input
    dummy_input = torch.randn(2, 3, IMAGE_SIZE, IMAGE_SIZE).to(DEVICE)
    output = model(dummy_input)
    
    # Print forward pass summary
    print(f"Forward pass successful!")
    print(f"Input shape: {dummy_input.shape}")
    print(f"Output shape: {output.shape}")
    
    # Verify output shape
    expected_shape = (2, GRID_SIZE, GRID_SIZE, NUM_BOXES * 5 + NUM_CLASSES)
    assert output.shape == expected_shape, f"Expected {expected_shape}, got {output.shape}"
    print(f"Output shape is correct!")
    
    # Return the model
    return model


if __name__ == '__main__':
    test_model()