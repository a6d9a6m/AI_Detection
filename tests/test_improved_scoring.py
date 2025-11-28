"""
Step 1 Improvement: Enhanced Scoring Strategy (No Retraining Needed)

This script tests improved scoring methods on existing trained models:
1. Multi-statistics aggregation (max, mean, std, percentiles)
2. Prediction consistency metrics
3. Top-2 probability difference
4. Smaller hop for more patches

Usage:
    python test_improved_scoring.py \
        --train_dir data/fan/train \
        --test_dir data/fan/source_test \
        --checkpoint checkpoints/model_fan_best.pth \
        --machine_type fan
"""
import os
import argparse
import json
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm
from sklearn.metrics import roc_auc_score
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features import LogMelExtractor
from src.dataset import DCASE2021EvalDataset
from src.model import get_model


def calculate_enhanced_scores(probs):
    """
    Calculate multiple types of anomaly indicators from softmax probabilities

    Args:
        probs: softmax probabilities, shape (num_patches, num_classes)

    Returns:
        dict with various score types
    """
    probs_np = probs.cpu().numpy()
    num_patches, num_classes = probs_np.shape

    # ===== Basic scores =====
    # Maximum probability per patch
    max_prob = probs.max(dim=1)[0].cpu().numpy()

    # Entropy per patch
    entropy = -(probs * torch.log(probs + 1e-10)).sum(dim=1).cpu().numpy()

    # ===== New: Top-2 difference =====
    # Difference between top-1 and top-2 probabilities
    # Small difference = uncertain prediction
    top2_probs = torch.topk(probs, k=min(2, num_classes), dim=1)[0].cpu().numpy()
    if top2_probs.shape[1] == 2:
        top2_diff = top2_probs[:, 0] - top2_probs[:, 1]
    else:
        top2_diff = top2_probs[:, 0]

    # ===== New: Prediction consistency =====
    # Check if predictions are consistent across patches
    pred_classes = probs.argmax(dim=1).cpu().numpy()

    # Count each predicted class
    class_counts = np.bincount(pred_classes, minlength=num_classes)
    dominant_class_count = class_counts.max()

    # Consistency ratio (0=very inconsistent, 1=all same)
    consistency_ratio = dominant_class_count / num_patches

    # Prediction entropy (entropy over class distribution)
    class_distribution = class_counts / num_patches
    pred_entropy = -np.sum(class_distribution * np.log(class_distribution + 1e-10))

    return {
        # Per-patch scores
        'max_prob': max_prob,           # Shape: (num_patches,)
        'entropy': entropy,              # Shape: (num_patches,)
        'top2_diff': top2_diff,         # Shape: (num_patches,)

        # Global consistency scores
        'consistency_ratio': consistency_ratio,  # Scalar
        'pred_entropy': pred_entropy,            # Scalar
        'num_patches': num_patches
    }


def aggregate_enhanced_scores(scores_dict):
    """
    Aggregate per-patch scores using multiple statistics

    Returns:
        dict with aggregated anomaly scores
    """
    agg = {}

    # ===== Max probability aggregation =====
    max_prob = scores_dict['max_prob']
    agg['max_prob_max'] = float(np.max(max_prob))
    agg['max_prob_mean'] = float(np.mean(max_prob))
    agg['max_prob_std'] = float(np.std(max_prob))
    agg['max_prob_min'] = float(np.min(max_prob))
    agg['max_prob_p95'] = float(np.percentile(max_prob, 95))
    agg['max_prob_p75'] = float(np.percentile(max_prob, 75))
    agg['max_prob_p25'] = float(np.percentile(max_prob, 25))
    agg['max_prob_p05'] = float(np.percentile(max_prob, 5))

    # ===== Entropy aggregation =====
    entropy = scores_dict['entropy']
    agg['entropy_max'] = float(np.max(entropy))
    agg['entropy_mean'] = float(np.mean(entropy))
    agg['entropy_std'] = float(np.std(entropy))
    agg['entropy_p95'] = float(np.percentile(entropy, 95))
    agg['entropy_p75'] = float(np.percentile(entropy, 75))

    # ===== Top-2 difference aggregation =====
    top2_diff = scores_dict['top2_diff']
    agg['top2_diff_min'] = float(np.min(top2_diff))
    agg['top2_diff_mean'] = float(np.mean(top2_diff))
    agg['top2_diff_p05'] = float(np.percentile(top2_diff, 5))
    agg['top2_diff_p25'] = float(np.percentile(top2_diff, 25))

    # ===== Consistency scores =====
    agg['consistency_ratio'] = float(scores_dict['consistency_ratio'])
    agg['pred_entropy'] = float(scores_dict['pred_entropy'])
    agg['num_patches'] = int(scores_dict['num_patches'])

    return agg


def compute_statistics(model, dataloader, device):
    """
    Compute mean and std for all score types on normal training data
    """
    model.eval()
    all_agg_scores = []

    print("Computing statistics on normal training data...")
    with torch.no_grad():
        for patches, _, _, _ in tqdm(dataloader):
            num_files = patches.size(0)

            for i in range(num_files):
                file_patches = patches[i].to(device)

                logits = model(file_patches)
                probs = F.softmax(logits, dim=1)

                scores_dict = calculate_enhanced_scores(probs)
                agg_scores = aggregate_enhanced_scores(scores_dict)
                all_agg_scores.append(agg_scores)

    # Calculate statistics for each score type
    stats = {}
    score_keys = all_agg_scores[0].keys()

    for key in score_keys:
        if key == 'num_patches':
            continue
        values = [s[key] for s in all_agg_scores]
        stats[f'{key}_mean'] = float(np.mean(values))
        stats[f'{key}_std'] = float(np.std(values))

    print(f"Statistics computed from {len(all_agg_scores)} training files")
    return stats


def evaluate_with_enhanced_scoring(model, dataloader, device, stats):
    """
    Evaluate using enhanced scoring strategies
    """
    model.eval()
    results = []

    print("Evaluating with enhanced scoring...")
    with torch.no_grad():
        for patches, labels, section_ids, filenames in tqdm(dataloader):
            num_files = patches.size(0)

            for i in range(num_files):
                file_patches = patches[i].to(device)
                label = labels[i].item()
                section_id = section_ids[i].item()
                filename = filenames[i]

                logits = model(file_patches)
                probs = F.softmax(logits, dim=1)

                scores_dict = calculate_enhanced_scores(probs)
                agg_scores = aggregate_enhanced_scores(scores_dict)

                # Convert to anomaly scores (normalize and invert where needed)
                anomaly_scores = {}
                for key, value in agg_scores.items():
                    if key == 'num_patches':
                        continue

                    mean_key = f'{key}_mean'
                    std_key = f'{key}_std'

                    if mean_key in stats and std_key in stats:
                        # Z-score normalization
                        z_score = (value - stats[mean_key]) / (stats[std_key] + 1e-10)

                        # Determine anomaly direction
                        if 'max_prob' in key or 'top2_diff' in key or 'consistency_ratio' in key:
                            # Low value = anomalous
                            anomaly_scores[key] = -z_score
                        else:
                            # High value = anomalous (entropy, pred_entropy)
                            anomaly_scores[key] = z_score

                # ===== Define multiple scoring strategies =====

                # Strategy 1: Original baseline (max-based)
                score_baseline = 0.5 * anomaly_scores.get('max_prob_max', 0) + \
                                0.5 * anomaly_scores.get('entropy_max', 0)

                # Strategy 2: Mean-based (more stable)
                score_mean_based = 0.5 * anomaly_scores.get('max_prob_mean', 0) + \
                                  0.5 * anomaly_scores.get('entropy_mean', 0)

                # Strategy 3: Percentile-based (original p95)
                score_percentile = 0.5 * anomaly_scores.get('max_prob_p95', 0) + \
                                  0.5 * anomaly_scores.get('entropy_p95', 0)

                # Strategy 4: With Top-2 difference
                score_with_top2 = 0.3 * anomaly_scores.get('max_prob_p95', 0) + \
                                 0.3 * anomaly_scores.get('entropy_p95', 0) + \
                                 0.4 * anomaly_scores.get('top2_diff_min', 0)

                # Strategy 5: With consistency
                score_with_consistency = 0.3 * anomaly_scores.get('max_prob_p95', 0) + \
                                        0.3 * anomaly_scores.get('entropy_p95', 0) + \
                                        0.2 * anomaly_scores.get('consistency_ratio', 0) + \
                                        0.2 * anomaly_scores.get('pred_entropy', 0)

                # Strategy 6: Multi-statistics comprehensive
                score_comprehensive = 0.2 * anomaly_scores.get('max_prob_max', 0) + \
                                     0.15 * anomaly_scores.get('max_prob_mean', 0) + \
                                     0.1 * anomaly_scores.get('max_prob_std', 0) + \
                                     0.15 * anomaly_scores.get('entropy_p95', 0) + \
                                     0.15 * anomaly_scores.get('top2_diff_min', 0) + \
                                     0.15 * anomaly_scores.get('consistency_ratio', 0) + \
                                     0.1 * anomaly_scores.get('pred_entropy', 0)

                # Strategy 7: Simple ensemble (average of all strategies)
                score_ensemble = np.mean([
                    score_baseline, score_mean_based, score_percentile,
                    score_with_top2, score_with_consistency, score_comprehensive
                ])

                results.append({
                    'filename': filename,
                    'label': label,
                    'section_id': section_id,
                    'num_patches': agg_scores['num_patches'],

                    # Different strategies
                    'score_baseline': float(score_baseline),
                    'score_mean_based': float(score_mean_based),
                    'score_percentile': float(score_percentile),
                    'score_with_top2': float(score_with_top2),
                    'score_with_consistency': float(score_with_consistency),
                    'score_comprehensive': float(score_comprehensive),
                    'score_ensemble': float(score_ensemble),

                    # Store all individual scores for analysis
                    **{f'raw_{k}': float(v) for k, v in anomaly_scores.items()}
                })

    return results


def calculate_metrics(results):
    """Calculate AUC for all strategies"""
    labels = np.array([r['label'] for r in results])

    if len(np.unique(labels)) < 2:
        print("WARNING: Only one class in test set, cannot calculate AUC")
        return {}

    strategy_names = [
        'score_baseline',
        'score_mean_based',
        'score_percentile',
        'score_with_top2',
        'score_with_consistency',
        'score_comprehensive',
        'score_ensemble'
    ]

    metrics = {}
    print("\n" + "="*70)
    print("AUC Results by Strategy:")
    print("="*70)

    for strategy in strategy_names:
        scores = np.array([r[strategy] for r in results])
        auc = roc_auc_score(labels, scores)
        metrics[f'auc_{strategy}'] = float(auc)

        # Pretty print
        strategy_display = strategy.replace('score_', '').replace('_', ' ').title()
        print(f"{strategy_display:.<40} {auc:.4f}")

    print("="*70)

    # Find best strategy
    best_strategy = max(metrics.items(), key=lambda x: x[1])
    improvement = best_strategy[1] - metrics.get('auc_score_baseline', 0)

    print(f"\nBest Strategy: {best_strategy[0].replace('auc_score_', '')}")
    print(f"Best AUC: {best_strategy[1]:.4f}")
    print(f"Improvement over baseline: {improvement:+.4f} ({improvement/metrics.get('auc_score_baseline', 1)*100:+.1f}%)")
    print("="*70 + "\n")

    return metrics


def main():
    parser = argparse.ArgumentParser(
        description='Test improved scoring strategies (Step 1 improvement)'
    )

    parser.add_argument('--train_dir', type=str, required=True,
                        help='Training data directory')
    parser.add_argument('--test_dir', type=str, required=True,
                        help='Test data directory')
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Model checkpoint path')
    parser.add_argument('--machine_type', type=str, required=True,
                        help='Machine type (fan, gearbox, etc.)')
    parser.add_argument('--output_dir', type=str, default='./results_step1',
                        help='Output directory')

    # Feature parameters (use same as training)
    parser.add_argument('--sr', type=int, default=16000)
    parser.add_argument('--n_mels', type=int, default=128)
    parser.add_argument('--n_fft', type=int, default=1024)
    parser.add_argument('--hop_length', type=int, default=512)
    parser.add_argument('--fmin', type=int, default=0)
    parser.add_argument('--fmax', type=int, default=8000)
    parser.add_argument('--patch_frames', type=int, default=64)

    # IMPROVED: Smaller hop for more patches
    parser.add_argument('--hop_frames', type=int, default=16,
                        help='Hop between patches (default=16, original=32)')

    parser.add_argument('--num_workers', type=int, default=4)
    parser.add_argument('--batch_size', type=int, default=1)

    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    print(f"Hop frames: {args.hop_frames} (original was 32)")
    print()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load model
    print(f"Loading model from: {args.checkpoint}")
    checkpoint = torch.load(args.checkpoint, map_location=device)

    feature_extractor = LogMelExtractor(
        sr=args.sr, n_mels=args.n_mels, n_fft=args.n_fft,
        hop_length=args.hop_length, fmin=args.fmin, fmax=args.fmax
    )

    num_classes = checkpoint['num_classes']
    model = get_model(num_classes=num_classes).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    print(f"Model loaded (num_classes={num_classes})\n")

    # Create datasets with smaller hop
    train_dataset = DCASE2021EvalDataset(
        args.train_dir, feature_extractor,
        patch_frames=args.patch_frames,
        hop_frames=args.hop_frames
    )

    test_dataset = DCASE2021EvalDataset(
        args.test_dir, feature_extractor,
        patch_frames=args.patch_frames,
        hop_frames=args.hop_frames
    )

    train_loader = DataLoader(train_dataset, batch_size=1, shuffle=False,
                             num_workers=args.num_workers)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False,
                            num_workers=args.num_workers)

    # Step 1: Compute statistics
    stats = compute_statistics(model, train_loader, device)

    # Save statistics
    stats_path = os.path.join(args.output_dir,
                             f'stats_step1_{args.machine_type}.json')
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Statistics saved to: {stats_path}\n")

    # Step 2: Evaluate
    results = evaluate_with_enhanced_scoring(model, test_loader, device, stats)

    # Step 3: Calculate metrics
    metrics = calculate_metrics(results)

    # Save results
    output_data = {
        'args': vars(args),
        'metrics': metrics,
        'results': results
    }

    results_path = os.path.join(
        args.output_dir,
        f'results_step1_{args.machine_type}_{os.path.basename(args.test_dir)}.json'
    )
    with open(results_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Detailed results saved to: {results_path}")

    # Save CSV
    csv_path = os.path.join(
        args.output_dir,
        f'scores_step1_{args.machine_type}_{os.path.basename(args.test_dir)}.csv'
    )
    with open(csv_path, 'w') as f:
        f.write('filename,label,section_id,num_patches,')
        f.write(','.join([
            'baseline', 'mean_based', 'percentile', 'with_top2',
            'with_consistency', 'comprehensive', 'ensemble'
        ]))
        f.write('\n')

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

    print(f"Scores CSV saved to: {csv_path}")


if __name__ == '__main__':
    main()
