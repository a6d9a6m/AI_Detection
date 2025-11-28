"""
MobileNetV2 model adapted for single-channel log-Mel input
Modified first layer to accept 1-channel input instead of 3-channel RGB
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class InvertedResidual(nn.Module):
    """Inverted Residual Block for MobileNetV2"""

    def __init__(self, inp, oup, stride, expand_ratio):
        super(InvertedResidual, self).__init__()
        self.stride = stride
        hidden_dim = int(inp * expand_ratio)
        self.use_res_connect = self.stride == 1 and inp == oup

        layers = []
        if expand_ratio != 1:
            # Pointwise expansion
            layers.extend([
                nn.Conv2d(inp, hidden_dim, 1, 1, 0, bias=False),
                nn.BatchNorm2d(hidden_dim),
                nn.ReLU6(inplace=True),
            ])

        layers.extend([
            # Depthwise convolution
            nn.Conv2d(hidden_dim, hidden_dim, 3, stride, 1, groups=hidden_dim, bias=False),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU6(inplace=True),
            # Pointwise projection
            nn.Conv2d(hidden_dim, oup, 1, 1, 0, bias=False),
            nn.BatchNorm2d(oup),
        ])

        self.conv = nn.Sequential(*layers)

    def forward(self, x):
        if self.use_res_connect:
            return x + self.conv(x)
        else:
            return self.conv(x)


class MobileNetV2(nn.Module):
    """
    MobileNetV2 architecture adapted for DCASE2021 Task2

    Input shape: (batch, 1, 128, 64) - single-channel log-Mel patches
    Output: (batch, num_classes) - section classification logits
    """

    def __init__(self, num_classes=3, width_mult=1.0, dropout_rate=0.2):
        super(MobileNetV2, self).__init__()

        # Build inverted residual settings
        # t: expansion factor, c: output channels, n: repeat, s: stride
        inverted_residual_setting = [
            # t, c, n, s
            [1, 16, 1, 1],
            [6, 24, 2, 2],
            [6, 32, 3, 2],
            [6, 64, 4, 2],
            [6, 96, 3, 1],
            [6, 160, 3, 2],
            [6, 320, 1, 1],
        ]

        # Building first layer - MODIFIED FOR SINGLE CHANNEL INPUT
        input_channel = int(32 * width_mult)
        self.features = [nn.Sequential(
            nn.Conv2d(1, input_channel, 3, 2, 1, bias=False),  # 1 channel instead of 3
            nn.BatchNorm2d(input_channel),
            nn.ReLU6(inplace=True)
        )]

        # Building inverted residual blocks
        for t, c, n, s in inverted_residual_setting:
            output_channel = int(c * width_mult)
            for i in range(n):
                stride = s if i == 0 else 1
                self.features.append(
                    InvertedResidual(input_channel, output_channel, stride, expand_ratio=t)
                )
                input_channel = output_channel

        # Building last several layers
        last_channel = int(1280 * width_mult) if width_mult > 1.0 else 1280
        self.features.append(nn.Sequential(
            nn.Conv2d(input_channel, last_channel, 1, 1, 0, bias=False),
            nn.BatchNorm2d(last_channel),
            nn.ReLU6(inplace=True)
        ))

        # Make it sequential
        self.features = nn.Sequential(*self.features)

        # Classification head
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(last_channel, num_classes)

        # Initialize weights
        self._initialize_weights()

    def forward(self, x):
        """
        Forward pass

        Args:
            x: input tensor (batch, 1, 128, 64)

        Returns:
            logits: output logits (batch, num_classes)
        """
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.dropout(x)
        x = self.classifier(x)
        return x

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.zeros_(m.bias)


def get_model(num_classes=3, width_mult=1.0, dropout_rate=0.2):
    """
    Get MobileNetV2 model for section classification

    Args:
        num_classes: number of section classes (default: 3)
        width_mult: width multiplier for channels (default: 1.0)
        dropout_rate: dropout rate before classifier (default: 0.2)

    Returns:
        model: MobileNetV2 instance
    """
    return MobileNetV2(num_classes=num_classes, width_mult=width_mult, dropout_rate=dropout_rate)
