"""
Flexible backbone models for DCASE2021 Task2
Support MobileNetV2, ResNet18, ResNet34
All adapted for single-channel log-Mel input
"""
import torch
import torch.nn as nn
import torchvision.models as models


class ResNetBackbone(nn.Module):
    """
    ResNet adapted for single-channel log-Mel input

    Args:
        backbone: 'resnet18' or 'resnet34'
        num_classes: number of output classes
        pretrained: use ImageNet pretrained weights (will adapt first conv)
        dropout_rate: dropout before classifier
    """

    def __init__(self, backbone='resnet18', num_classes=3, pretrained=False, dropout_rate=0.2):
        super(ResNetBackbone, self).__init__()

        # Load base model
        if backbone == 'resnet18':
            base_model = models.resnet18(pretrained=pretrained)
            self.feature_dim = 512
        elif backbone == 'resnet34':
            base_model = models.resnet34(pretrained=pretrained)
            self.feature_dim = 512
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")

        # Modify first conv layer for single-channel input
        original_conv1 = base_model.conv1
        self.conv1 = nn.Conv2d(
            in_channels=1,  # Single channel instead of 3
            out_channels=original_conv1.out_channels,
            kernel_size=original_conv1.kernel_size,
            stride=original_conv1.stride,
            padding=original_conv1.padding,
            bias=False
        )

        # If pretrained, average the weights across RGB channels
        if pretrained:
            # Average RGB weights to initialize single-channel conv
            with torch.no_grad():
                self.conv1.weight = nn.Parameter(
                    original_conv1.weight.mean(dim=1, keepdim=True)
                )

        # Copy other layers
        self.bn1 = base_model.bn1
        self.relu = base_model.relu
        self.maxpool = base_model.maxpool
        self.layer1 = base_model.layer1
        self.layer2 = base_model.layer2
        self.layer3 = base_model.layer3
        self.layer4 = base_model.layer4
        self.avgpool = base_model.avgpool

        # Custom classifier
        self.dropout = nn.Dropout(dropout_rate)
        self.fc = nn.Linear(self.feature_dim, num_classes)

        # Initialize new layers
        nn.init.normal_(self.fc.weight, 0, 0.01)
        nn.init.zeros_(self.fc.bias)
        if not pretrained:
            nn.init.kaiming_normal_(self.conv1.weight, mode='fan_out', nonlinearity='relu')

    def forward(self, x):
        """
        Forward pass

        Args:
            x: input tensor (batch, 1, 128, T)

        Returns:
            logits: output logits (batch, num_classes)
        """
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.dropout(x)
        x = self.fc(x)

        return x


class MobileNetV2Backbone(nn.Module):
    """
    MobileNetV2 adapted for single-channel input
    (Same as original model.py but wrapped for consistency)
    """

    def __init__(self, num_classes=3, width_mult=1.0, dropout_rate=0.2):
        super(MobileNetV2Backbone, self).__init__()

        from model import MobileNetV2
        self.model = MobileNetV2(num_classes, width_mult, dropout_rate)

    def forward(self, x):
        return self.model(x)


def get_backbone_model(backbone='mobilenetv2', num_classes=3, pretrained=False,
                       width_mult=1.0, dropout_rate=0.2):
    """
    Get backbone model

    Args:
        backbone: model architecture ('mobilenetv2', 'resnet18', 'resnet34')
        num_classes: number of classes
        pretrained: use pretrained weights (only for ResNet)
        width_mult: width multiplier (only for MobileNetV2)
        dropout_rate: dropout rate

    Returns:
        model: backbone model instance
    """
    if backbone == 'mobilenetv2':
        return MobileNetV2Backbone(num_classes, width_mult, dropout_rate)
    elif backbone in ['resnet18', 'resnet34']:
        return ResNetBackbone(backbone, num_classes, pretrained, dropout_rate)
    else:
        raise ValueError(f"Unsupported backbone: {backbone}")


def count_parameters(model):
    """Count trainable parameters"""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
