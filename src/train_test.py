"""
Unified training and testing script with multiple backbone support
Supports MobileNetV2, ResNet18, ResNet34

Usage:
    # Train
    python train_test.py train --backbone resnet34 --train_dir data/fan/train --machine_type fan

    # Test
    python train_test.py test --checkpoint checkpoints/model_fan_best.pth --test_dir data/fan/source_test
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

from features import LogMelExtractor
from dataset import DCASE2021Dataset, DCASE2021EvalDataset
from backbones import get_backbone_model, count_parameters


def set_seed(seed):
    """Set random seed for reproducibility"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print(f"Random seed set to: {seed}")


class WarmupScheduler:
    """Linear warmup scheduler"""
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


def train_model(args):
    """Main training function"""
    # Set random seed
    if args.seed is not None:
        set_seed(args.seed)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Feature extractor
    feature_extractor = LogMelExtractor(
        sr=args.sr, n_mels=args.n_mels, n_fft=args.n_fft,
        hop_length=args.hop_length, fmin=args.fmin, fmax=args.fmax
    )

    # Dataset
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

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True
    )

    # Model
    num_classes = len(set(train_dataset.section_labels))
    print(f"Number of section classes: {num_classes}")

    model = get_backbone_model(
        backbone=args.backbone,
        num_classes=num_classes,
        pretrained=args.pretrained,
        width_mult=args.width_mult,
        dropout_rate=args.dropout_rate
    ).to(device)

    num_params = count_parameters(model)
    print(f"Model: {args.backbone}")
    print(f"Trainable parameters: {num_params:,}")

    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()

    if args.optimizer == 'adamw':
        optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        print(f"Using AdamW optimizer")
    else:
        optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        print(f"Using Adam optimizer")

    # Schedulers
    warmup_scheduler = None
    if args.warmup_epochs > 0:
        warmup_scheduler = WarmupScheduler(optimizer, args.warmup_epochs, args.lr)
        print(f"Using warmup for {args.warmup_epochs} epochs")

    if args.scheduler == 'cosine':
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=10, T_mult=2, eta_min=args.lr * 0.01
        )
        print("Using Cosine Annealing scheduler")
    elif args.scheduler == 'plateau':
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        print("Using ReduceLROnPlateau scheduler")
    else:
        scheduler = None

    # Training config summary
    print(f"\n{'='*60}")
    print("Training Configuration:")
    print(f"{'='*60}")
    print(f"Backbone: {args.backbone.upper()}")
    print(f"Pretrained: {args.pretrained}")
    print(f"Random seed: {args.seed if args.seed is not None else 'None (random)'}")
    print(f"Patch frames: {args.patch_frames}")
    print(f"Batch size: {args.batch_size}")
    print(f"Epochs: {args.epochs}")
    print(f"Optimizer: {args.optimizer.upper()}")
    print(f"Learning rate: {args.lr}")
    print(f"Warmup epochs: {args.warmup_epochs}")
    print(f"Dropout: {args.dropout_rate}")
    print(f"Weight decay: {args.weight_decay}")
    print(f"Data augmentation: {'Enabled' if args.augmentation else 'Disabled'}")
    if args.augmentation:
        print(f"  - Volume: [{args.aug_volume_min}, {args.aug_volume_max}]")
        print(f"  - Time shift: ±{args.aug_time_shift}")
        print(f"  - Freq mask: {args.aug_freq_mask}")
        print(f"  - Time mask: {args.aug_time_mask}")
    print(f"LR scheduler: {args.scheduler}")
    print(f"{'='*60}\n")

    # Training loop
    best_loss = float('inf')
    best_acc = 0.0
    history = {'train_loss': [], 'train_acc': []}

    print(f"Starting training for {args.epochs} epochs...")
    for epoch in range(1, args.epochs + 1):
        print(f"\nEpoch {epoch}/{args.epochs}")

        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)

        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)

        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")

        # Learning rate scheduling
        if warmup_scheduler is not None and epoch <= args.warmup_epochs:
            warmup_scheduler.step()
        elif scheduler is not None:
            if args.scheduler == 'plateau':
                scheduler.step(train_loss)
            else:
                scheduler.step()

        current_lr = optimizer.param_groups[0]['lr']
        if warmup_scheduler is not None and epoch <= args.warmup_epochs:
            print(f"Learning rate: {current_lr:.6f} [Warmup {epoch}/{args.warmup_epochs}]")
        else:
            print(f"Learning rate: {current_lr:.6f}")

        # Save best model
        if train_loss < best_loss:
            best_loss = train_loss
            best_acc = train_acc
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': train_loss,
                'accuracy': train_acc,
                'num_classes': num_classes,
                'backbone': args.backbone,
                'args': vars(args)
            }
            checkpoint_path = os.path.join(args.output_dir, f'model_{args.machine_type}_best.pth')
            torch.save(checkpoint, checkpoint_path)
            print(f"✓ Saved best model (loss: {train_loss:.4f}, acc: {train_acc:.2f}%)")

        # Save checkpoint
        if epoch % args.save_interval == 0:
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': train_loss,
                'accuracy': train_acc,
                'num_classes': num_classes,
                'backbone': args.backbone,
                'args': vars(args)
            }
            checkpoint_path = os.path.join(args.output_dir, f'model_{args.machine_type}_epoch{epoch}.pth')
            torch.save(checkpoint, checkpoint_path)

    # Save history
    history_path = os.path.join(args.output_dir, f'history_{args.machine_type}.json')
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)

    print(f"\n{'='*60}")
    print("Training completed!")
    print(f"Best loss: {best_loss:.4f}")
    print(f"Best accuracy: {best_acc:.2f}%")
    print(f"{'='*60}")


def test_model(args):
    """Test model and compute anomaly scores"""
    from test_improved_scoring import (
        calculate_enhanced_scores,
        aggregate_enhanced_scores,
        compute_statistics,
        evaluate_with_enhanced_scoring,
        calculate_metrics
    )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Load checkpoint
    print(f"Loading checkpoint: {args.checkpoint}")
    checkpoint = torch.load(args.checkpoint, map_location=device)

    # Get training args
    train_args = checkpoint.get('args', {})
    backbone = checkpoint.get('backbone', 'mobilenetv2')
    num_classes = checkpoint['num_classes']
    patch_frames = train_args.get('patch_frames', 64)

    print(f"Model info:")
    print(f"  Backbone: {backbone}")
    print(f"  Classes: {num_classes}")
    print(f"  Patch frames: {patch_frames}")

    # Feature extractor
    feature_extractor = LogMelExtractor(
        sr=args.sr, n_mels=args.n_mels, n_fft=args.n_fft,
        hop_length=args.hop_length, fmin=args.fmin, fmax=args.fmax
    )

    # Load model
    model = get_backbone_model(
        backbone=backbone,
        num_classes=num_classes,
        pretrained=False,
        dropout_rate=train_args.get('dropout_rate', 0.2)
    ).to(device)

    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    print(f"Model loaded successfully")

    # Datasets
    train_dataset = DCASE2021EvalDataset(
        args.train_dir, feature_extractor,
        patch_frames=patch_frames,
        hop_frames=args.hop_frames
    )

    test_dataset = DCASE2021EvalDataset(
        args.test_dir, feature_extractor,
        patch_frames=patch_frames,
        hop_frames=args.hop_frames
    )

    train_loader = DataLoader(train_dataset, batch_size=1, shuffle=False, num_workers=args.num_workers)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False, num_workers=args.num_workers)

    # Compute statistics
    stats = compute_statistics(model, train_loader, device)

    # Evaluate
    results = evaluate_with_enhanced_scoring(model, test_loader, device, stats)

    # Calculate metrics
    metrics = calculate_metrics(results)

    # Save results
    os.makedirs(args.output_dir, exist_ok=True)

    output_data = {
        'checkpoint': args.checkpoint,
        'backbone': backbone,
        'test_dir': args.test_dir,
        'metrics': metrics,
        'results': results,
        'args': vars(args)
    }

    results_path = os.path.join(
        args.output_dir,
        f'results_{os.path.basename(args.test_dir)}.json'
    )
    with open(results_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    # Save CSV
    csv_path = os.path.join(
        args.output_dir,
        f'scores_{os.path.basename(args.test_dir)}.csv'
    )
    with open(csv_path, 'w') as f:
        f.write('filename,label,section_id,num_patches,')
        f.write('baseline,mean_based,percentile,with_top2,with_consistency,comprehensive,ensemble\n')

        for r in results:
            f.write(f"{r['filename']},{r['label']},{r['section_id']},{r['num_patches']},")
            f.write(','.join([
                f"{r['score_baseline']:.6f}",
                f"{r['score_mean_based']:.6f}",
                f"{r['score_percentile']:.6f}",
                f"{r['score_with_top2']:.6f}",
                f"{r['score_with_consistency']:.6f}",
                f"{r['score_comprehensive']:.6f}",
                f"{r['score_ensemble']:.6f}"
            ]))
            f.write('\n')

    print(f"\nResults saved to: {results_path}")
    print(f"Scores saved to: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description='Train/Test DCASE2021 with multiple backbones')
    subparsers = parser.add_subparsers(dest='mode', help='train or test mode')

    # ===== TRAIN MODE =====
    train_parser = subparsers.add_parser('train', help='Train model')

    # General
    train_parser.add_argument('--seed', type=int, default=None)
    train_parser.add_argument('--train_dir', type=str, required=True)
    train_parser.add_argument('--machine_type', type=str, required=True)
    train_parser.add_argument('--output_dir', type=str, default='./checkpoints')

    # Feature parameters
    train_parser.add_argument('--sr', type=int, default=16000)
    train_parser.add_argument('--n_mels', type=int, default=128)
    train_parser.add_argument('--n_fft', type=int, default=1024)
    train_parser.add_argument('--hop_length', type=int, default=512)
    train_parser.add_argument('--fmin', type=int, default=0)
    train_parser.add_argument('--fmax', type=int, default=8000)
    train_parser.add_argument('--patch_frames', type=int, default=64,
                              help='Recommended: 64 or 96')

    # Model parameters
    train_parser.add_argument('--backbone', type=str, default='mobilenetv2',
                              choices=['mobilenetv2', 'resnet18', 'resnet34'],
                              help='Model backbone')
    train_parser.add_argument('--pretrained', action='store_true', default=False,
                              help='Use ImageNet pretrained weights (ResNet only)')
    train_parser.add_argument('--width_mult', type=float, default=1.0,
                              help='Width multiplier (MobileNetV2 only)')
    train_parser.add_argument('--dropout_rate', type=float, default=0.2)

    # Training parameters
    train_parser.add_argument('--batch_size', type=int, default=64,
                              help='Recommended: ≥64 for ResNet')
    train_parser.add_argument('--epochs', type=int, default=150)
    train_parser.add_argument('--lr', type=float, default=1e-3)
    train_parser.add_argument('--weight_decay', type=float, default=1e-5)
    train_parser.add_argument('--optimizer', type=str, default='adam',
                              choices=['adam', 'adamw'])
    train_parser.add_argument('--warmup_epochs', type=int, default=0)
    train_parser.add_argument('--scheduler', type=str, default='plateau',
                              choices=['plateau', 'cosine', 'none'])
    train_parser.add_argument('--num_workers', type=int, default=4)

    # Data augmentation
    train_parser.add_argument('--augmentation', dest='augmentation', action='store_true', default=True)
    train_parser.add_argument('--no-augmentation', dest='augmentation', action='store_false')
    train_parser.add_argument('--aug_volume_min', type=float, default=0.7)
    train_parser.add_argument('--aug_volume_max', type=float, default=1.3)
    train_parser.add_argument('--aug_time_shift', type=int, default=3)
    train_parser.add_argument('--aug_freq_mask', type=int, default=15)
    train_parser.add_argument('--aug_time_mask', type=int, default=15)

    train_parser.add_argument('--save_interval', type=int, default=10)

    # ===== TEST MODE =====
    test_parser = subparsers.add_parser('test', help='Test model')

    test_parser.add_argument('--checkpoint', type=str, required=True)
    test_parser.add_argument('--train_dir', type=str, required=True)
    test_parser.add_argument('--test_dir', type=str, required=True)
    test_parser.add_argument('--output_dir', type=str, default='./results_test')

    # Feature parameters (must match training)
    test_parser.add_argument('--sr', type=int, default=16000)
    test_parser.add_argument('--n_mels', type=int, default=128)
    test_parser.add_argument('--n_fft', type=int, default=1024)
    test_parser.add_argument('--hop_length', type=int, default=512)
    test_parser.add_argument('--fmin', type=int, default=0)
    test_parser.add_argument('--fmax', type=int, default=8000)
    test_parser.add_argument('--hop_frames', type=int, default=16)

    test_parser.add_argument('--num_workers', type=int, default=4)

    args = parser.parse_args()

    if args.mode == 'train':
        train_model(args)
    elif args.mode == 'test':
        test_model(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

