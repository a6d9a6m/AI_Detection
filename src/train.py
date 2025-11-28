"""
Training script for DCASE2021 Task2 Baseline 2

Train MobileNetV2 for section classification using only normal samples
"""
import os
import argparse
import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features import LogMelExtractor
from src.dataset import DCASE2021Dataset
from src.model import get_model


def set_seed(seed):
    """
    Set random seed for reproducibility

    Args:
        seed: random seed value
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)  # for multi-GPU

    # Make cudnn deterministic (may impact performance)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    print(f"Random seed set to: {seed}")


class WarmupScheduler:
    """
    Linear warmup scheduler
    Gradually increases learning rate from 0 to base_lr over warmup_epochs
    """
    def __init__(self, optimizer, warmup_epochs, base_lr):
        self.optimizer = optimizer
        self.warmup_epochs = warmup_epochs
        self.base_lr = base_lr
        self.current_epoch = 0

    def step(self):
        if self.current_epoch < self.warmup_epochs:
            lr = self.base_lr * (self.current_epoch + 1) / self.warmup_epochs
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = lr
        self.current_epoch += 1

    def get_lr(self):
        return self.optimizer.param_groups[0]['lr']


def train_epoch(model, dataloader, criterion, optimizer, device):
    """Train for one epoch"""
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    pbar = tqdm(dataloader, desc='Training')
    for batch_idx, (data, target) in enumerate(pbar):
        data, target = data.to(device), target.to(device)

        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += target.size(0)

        pbar.set_postfix({
            'loss': total_loss / (batch_idx + 1),
            'acc': 100. * correct / total
        })

    return total_loss / len(dataloader), 100. * correct / total


def validate(model, dataloader, criterion, device):
    """Validate the model"""
    model.eval()
    total_loss = 0
    correct = 0
    total = 0

    with torch.no_grad():
        for data, target in tqdm(dataloader, desc='Validation'):
            data, target = data.to(device), target.to(device)
            output = model(data)
            loss = criterion(output, target)

            total_loss += loss.item()
            pred = output.argmax(dim=1)
            correct += pred.eq(target).sum().item()
            total += target.size(0)

    return total_loss / len(dataloader), 100. * correct / total


def train(args):
    """Main training function"""
    # Set random seed for reproducibility
    if args.seed is not None:
        set_seed(args.seed)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize feature extractor
    feature_extractor = LogMelExtractor(
        sr=args.sr,
        n_mels=args.n_mels,
        n_fft=args.n_fft,
        hop_length=args.hop_length,
        fmin=args.fmin,
        fmax=args.fmax
    )

    # Create datasets
    train_dataset = DCASE2021Dataset(
        data_dir=args.train_dir,
        feature_extractor=feature_extractor,
        patch_frames=args.patch_frames,
        mode='train',
        augmentation=args.augmentation,
        aug_volume_range=(args.aug_volume_min, args.aug_volume_max),
        aug_time_shift=args.aug_time_shift,
        aug_freq_mask=args.aug_freq_mask,
        aug_time_mask=args.aug_time_mask
    )

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True
    )

    # Initialize model
    num_classes = len(set(train_dataset.section_labels))
    print(f"Number of section classes: {num_classes}")

    model = get_model(
        num_classes=num_classes,
        width_mult=args.width_mult,
        dropout_rate=args.dropout_rate
    ).to(device)

    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()

    # Select optimizer
    if args.optimizer == 'adamw':
        optimizer = optim.AdamW(
            model.parameters(),
            lr=args.lr,
            weight_decay=args.weight_decay
        )
        print(f"Using AdamW optimizer (lr={args.lr}, wd={args.weight_decay})")
    else:  # adam
        optimizer = optim.Adam(
            model.parameters(),
            lr=args.lr,
            weight_decay=args.weight_decay
        )
        print(f"Using Adam optimizer (lr={args.lr}, wd={args.weight_decay})")

    # Learning rate scheduler
    warmup_scheduler = None
    if args.warmup_epochs > 0:
        warmup_scheduler = WarmupScheduler(optimizer, args.warmup_epochs, args.lr)
        print(f"Using warmup for {args.warmup_epochs} epochs")

    if args.scheduler == 'cosine':
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer,
            T_0=10,
            T_mult=2,
            eta_min=args.lr * 0.01
        )
        print("Using Cosine Annealing with Warm Restarts scheduler")
    elif args.scheduler == 'plateau':
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=0.5,
            patience=5
        )
        print("Using ReduceLROnPlateau scheduler")
    else:
        scheduler = None
        print("No learning rate scheduler")

    # Training loop
    best_loss = float('inf')
    history = {
        'train_loss': [],
        'train_acc': [],
    }

    print(f"\n{'='*60}")
    print("IMPROVED Training Configuration:")
    print(f"{'='*60}")
    print(f"Random seed: {args.seed if args.seed is not None else 'None (random)'}")
    print(f"Patch frames: {args.patch_frames} (original: 64)")
    print(f"Batch size: {args.batch_size} (original: 64)")
    print(f"Epochs: {args.epochs} (original: 100)")
    print(f"Optimizer: {args.optimizer.upper()}")
    print(f"Learning rate: {args.lr}")
    print(f"Warmup epochs: {args.warmup_epochs}")
    print(f"Dropout: {args.dropout_rate} (original: 0.2)")
    print(f"Weight decay: {args.weight_decay} (original: 1e-5)")
    if args.augmentation:
        print(f"Data augmentation: Enabled")
        print(f"  - Volume range: [{args.aug_volume_min}, {args.aug_volume_max}]")
        print(f"  - Time shift: ±{args.aug_time_shift} frames")
        print(f"  - Freq mask: up to {args.aug_freq_mask} bins")
        print(f"  - Time mask: up to {args.aug_time_mask} frames")
    else:
        print(f"Data augmentation: Disabled")
    print(f"LR scheduler: {args.scheduler}")
    print(f"{'='*60}\n")

    print(f"Starting training for {args.epochs} epochs...")
    for epoch in range(1, args.epochs + 1):
        print(f"\nEpoch {epoch}/{args.epochs}")

        train_loss, train_acc = train_epoch(
            model, train_loader, criterion, optimizer, device
        )

        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)

        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")

        # Learning rate scheduling
        # Warmup phase
        if warmup_scheduler is not None and epoch <= args.warmup_epochs:
            warmup_scheduler.step()
        # Main scheduler phase (after warmup)
        elif scheduler is not None:
            if args.scheduler == 'plateau':
                scheduler.step(train_loss)
            else:  # cosine
                scheduler.step()

        # Print current learning rate
        current_lr = optimizer.param_groups[0]['lr']
        if warmup_scheduler is not None and epoch <= args.warmup_epochs:
            print(f"Learning rate: {current_lr:.6f} [Warmup {epoch}/{args.warmup_epochs}]")
        else:
            print(f"Learning rate: {current_lr:.6f}")

        # Save best model
        if train_loss < best_loss:
            best_loss = train_loss
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': train_loss,
                'num_classes': num_classes,
                'args': vars(args)
            }
            checkpoint_path = os.path.join(
                args.output_dir,
                f'model_{args.machine_type}_best.pth'
            )
            torch.save(checkpoint, checkpoint_path)
            print(f"Saved best model to {checkpoint_path}")

        # Save checkpoint every N epochs
        if epoch % args.save_interval == 0:
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': train_loss,
                'num_classes': num_classes,
                'args': vars(args)
            }
            checkpoint_path = os.path.join(
                args.output_dir,
                f'model_{args.machine_type}_epoch{epoch}.pth'
            )
            torch.save(checkpoint, checkpoint_path)

    # Save training history
    history_path = os.path.join(
        args.output_dir,
        f'history_{args.machine_type}.json'
    )
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)

    print(f"\nTraining completed!")
    print(f"Best loss: {best_loss:.4f}")


def main():
    parser = argparse.ArgumentParser(description='Train DCASE2021 Task2 Baseline 2')

    # General parameters
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility (default: None, random)')

    # Data parameters
    parser.add_argument('--train_dir', type=str, required=True,
                        help='Path to training data (e.g., data/fan/train)')
    parser.add_argument('--machine_type', type=str, required=True,
                        help='Machine type (e.g., fan, gearbox)')
    parser.add_argument('--output_dir', type=str, default='./checkpoints',
                        help='Output directory for checkpoints')

    # Feature parameters
    parser.add_argument('--sr', type=int, default=16000,
                        help='Sampling rate')
    parser.add_argument('--n_mels', type=int, default=128,
                        help='Number of mel bins')
    parser.add_argument('--n_fft', type=int, default=1024,
                        help='FFT window size (64ms at 16kHz)')
    parser.add_argument('--hop_length', type=int, default=512,
                        help='Hop length (32ms at 16kHz)')
    parser.add_argument('--fmin', type=int, default=0,
                        help='Minimum frequency')
    parser.add_argument('--fmax', type=int, default=8000,
                        help='Maximum frequency')
    parser.add_argument('--patch_frames', type=int, default=128,
                        help='Number of frames per patch (IMPROVED: 128 for better performance)')

    # Model parameters
    parser.add_argument('--width_mult', type=float, default=1.0,
                        help='Width multiplier for MobileNetV2')
    parser.add_argument('--dropout_rate', type=float, default=0.3,
                        help='Dropout rate (IMPROVED: 0.3 for better regularization)')

    # Training parameters
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size (IMPROVED: 32 due to longer patches)')
    parser.add_argument('--epochs', type=int, default=150,
                        help='Number of epochs (IMPROVED: 150 for better convergence)')
    parser.add_argument('--lr', type=float, default=1e-3,
                        help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-4,
                        help='Weight decay (IMPROVED: 1e-4 for stronger regularization)')
    parser.add_argument('--optimizer', type=str, default='adam',
                        choices=['adam', 'adamw'],
                        help='Optimizer type (adam or adamw)')
    parser.add_argument('--warmup_epochs', type=int, default=0,
                        help='Number of warmup epochs (0 to disable)')
    parser.add_argument('--num_workers', type=int, default=4,
                        help='Number of data loading workers')
    parser.add_argument('--augmentation', dest='augmentation', action='store_true', default=True,
                        help='Use data augmentation (SpecAugment, etc.)')
    parser.add_argument('--no-augmentation', dest='augmentation', action='store_false',
                        help='Disable data augmentation for faster training')

    # Data augmentation parameters
    parser.add_argument('--aug_volume_min', type=float, default=0.7,
                        help='Min volume scaling factor for augmentation')
    parser.add_argument('--aug_volume_max', type=float, default=1.3,
                        help='Max volume scaling factor for augmentation')
    parser.add_argument('--aug_time_shift', type=int, default=3,
                        help='Max time shift in frames (0 to disable)')
    parser.add_argument('--aug_freq_mask', type=int, default=15,
                        help='Max frequency bins to mask (0 to disable)')
    parser.add_argument('--aug_time_mask', type=int, default=15,
                        help='Max time frames to mask (0 to disable)')

    parser.add_argument('--save_interval', type=int, default=10,
                        help='Save checkpoint every N epochs')
    parser.add_argument('--scheduler', type=str, default='plateau',
                        choices=['plateau', 'cosine', 'none'],
                        help='Learning rate scheduler (IMPROVED: cosine recommended)')

    args = parser.parse_args()

    train(args)


if __name__ == '__main__':
    main()
