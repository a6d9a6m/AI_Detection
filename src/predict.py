"""
Inference and anomaly detection for DCASE2021 Task2 Baseline 2

Calculate anomaly scores based on classification uncertainty:
- Score A: 1 - max(softmax)
- Score B: entropy of softmax distribution
- Combined: weighted sum of normalized scores
"""
import os
import argparse
import json
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm
from sklearn.metrics import roc_auc_score, roc_curve
from features import LogMelExtractor
from dataset import DCASE2021EvalDataset
from model import get_model


def calculate_scores(probs):
    """
    Calculate anomaly scores from softmax probabilities

    Args:
        probs: softmax probabilities, shape (num_patches, num_classes)

    Returns:
        max_prob: maximum probability for each patch
        entropy: entropy for each patch
    """
    # Score A: maximum probability
    max_prob = probs.max(dim=1)[0].cpu().numpy()

    # Score B: entropy
    entropy = -(probs * torch.log(probs + 1e-10)).sum(dim=1).cpu().numpy()

    return max_prob, entropy


def compute_statistics(model, dataloader, device):
    """
    Compute statistics (mean, std) of scores on normal training data
    for Z-score normalization

    Args:
        model: trained model
        dataloader: dataloader for normal training data
        device: torch device

    Returns:
        stats: dictionary with mean and std for max_prob and entropy
    """
    model.eval()
    all_max_probs = []
    all_entropies = []

    print("Computing statistics on normal training data...")
    with torch.no_grad():
        for patches, _, _, _ in tqdm(dataloader):
            num_files = patches.size(0)

            for i in range(num_files):
                file_patches = patches[i].to(device)  # (num_patches, 1, 128, 64)

                # Get predictions
                logits = model(file_patches)
                probs = F.softmax(logits, dim=1)

                # Calculate scores
                max_prob, entropy = calculate_scores(probs)
                all_max_probs.extend(max_prob)
                all_entropies.extend(entropy)

    all_max_probs = np.array(all_max_probs)
    all_entropies = np.array(all_entropies)

    stats = {
        'max_prob_mean': float(all_max_probs.mean()),
        'max_prob_std': float(all_max_probs.std()),
        'entropy_mean': float(all_entropies.mean()),
        'entropy_std': float(all_entropies.std())
    }

    print(f"Statistics computed:")
    print(f"  max_prob: mean={stats['max_prob_mean']:.4f}, std={stats['max_prob_std']:.4f}")
    print(f"  entropy: mean={stats['entropy_mean']:.4f}, std={stats['entropy_std']:.4f}")

    return stats


def evaluate(model, dataloader, device, stats, args):
    """
    Evaluate model on test data and calculate anomaly scores

    Args:
        model: trained model
        dataloader: dataloader for test data
        device: torch device
        stats: statistics for normalization
        args: arguments

    Returns:
        results: dictionary with results for each file
    """
    model.eval()
    results = []

    print("Evaluating on test data...")
    with torch.no_grad():
        for patches, labels, section_ids, filenames in tqdm(dataloader):
            num_files = patches.size(0)

            for i in range(num_files):
                file_patches = patches[i].to(device)  # (num_patches, 1, 128, 64)
                label = labels[i].item()
                section_id = section_ids[i].item()
                filename = filenames[i]

                # Get predictions
                logits = model(file_patches)
                probs = F.softmax(logits, dim=1)

                # Calculate scores for each patch
                max_prob, entropy = calculate_scores(probs)

                # Normalize scores using Z-score
                max_prob_z = (max_prob - stats['max_prob_mean']) / (stats['max_prob_std'] + 1e-10)
                entropy_z = (entropy - stats['entropy_mean']) / (stats['entropy_std'] + 1e-10)

                # Calculate anomaly scores
                # Score A: 1 - max_prob (higher means more anomalous)
                score_a = 1 - max_prob

                # Score B: entropy (higher means more uncertain)
                score_b = entropy

                # Normalized scores
                score_a_z = 1 - max_prob_z
                score_b_z = entropy_z

                # Combined score (weighted sum of normalized scores)
                score_combined = args.alpha * score_a_z + (1 - args.alpha) * score_b_z

                # Aggregate scores across patches
                if args.aggregation == 'max':
                    agg_score_a = score_a.max()
                    agg_score_b = score_b.max()
                    agg_score_combined = score_combined.max()
                elif args.aggregation == 'percentile':
                    agg_score_a = np.percentile(score_a, args.percentile)
                    agg_score_b = np.percentile(score_b, args.percentile)
                    agg_score_combined = np.percentile(score_combined, args.percentile)
                elif args.aggregation == 'mean':
                    agg_score_a = score_a.mean()
                    agg_score_b = score_b.mean()
                    agg_score_combined = score_combined.mean()

                results.append({
                    'filename': filename,
                    'label': label,
                    'section_id': section_id,
                    'score_a': float(agg_score_a),
                    'score_b': float(agg_score_b),
                    'score_combined': float(agg_score_combined),
                    'num_patches': len(max_prob)
                })

    return results


def calculate_metrics(results):
    """
    Calculate evaluation metrics (AUC)

    Args:
        results: list of result dictionaries

    Returns:
        metrics: dictionary with AUC scores
    """
    labels = np.array([r['label'] for r in results])
    scores_a = np.array([r['score_a'] for r in results])
    scores_b = np.array([r['score_b'] for r in results])
    scores_combined = np.array([r['score_combined'] for r in results])

    metrics = {}

    if len(np.unique(labels)) > 1:
        metrics['auc_score_a'] = roc_auc_score(labels, scores_a)
        metrics['auc_score_b'] = roc_auc_score(labels, scores_b)
        metrics['auc_score_combined'] = roc_auc_score(labels, scores_combined)
    else:
        print("Warning: Only one class present in test data, cannot calculate AUC")
        metrics['auc_score_a'] = 0.0
        metrics['auc_score_b'] = 0.0
        metrics['auc_score_combined'] = 0.0

    return metrics


def main():
    parser = argparse.ArgumentParser(description='Evaluate DCASE2021 Task2 Baseline 2')

    # Data parameters
    parser.add_argument('--train_dir', type=str, required=True,
                        help='Path to training data (for statistics)')
    parser.add_argument('--test_dir', type=str, required=True,
                        help='Path to test data')
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Path to model checkpoint')
    parser.add_argument('--machine_type', type=str, required=True,
                        help='Machine type (e.g., fan, gearbox)')
    parser.add_argument('--output_dir', type=str, default='./results',
                        help='Output directory for results')

    # Feature parameters
    parser.add_argument('--sr', type=int, default=16000,
                        help='Sampling rate')
    parser.add_argument('--n_mels', type=int, default=128,
                        help='Number of mel bins')
    parser.add_argument('--n_fft', type=int, default=1024,
                        help='FFT window size')
    parser.add_argument('--hop_length', type=int, default=512,
                        help='Hop length')
    parser.add_argument('--fmin', type=int, default=0,
                        help='Minimum frequency')
    parser.add_argument('--fmax', type=int, default=8000,
                        help='Maximum frequency')
    parser.add_argument('--patch_frames', type=int, default=64,
                        help='Number of frames per patch')
    parser.add_argument('--hop_frames', type=int, default=32,
                        help='Hop size between patches')

    # Scoring parameters
    parser.add_argument('--alpha', type=float, default=0.5,
                        help='Weight for combining scores (0-1)')
    parser.add_argument('--aggregation', type=str, default='max',
                        choices=['max', 'percentile', 'mean'],
                        help='Aggregation method for patch scores')
    parser.add_argument('--percentile', type=float, default=95,
                        help='Percentile for aggregation (if method=percentile)')

    # Other parameters
    parser.add_argument('--num_workers', type=int, default=4,
                        help='Number of data loading workers')
    parser.add_argument('--batch_size', type=int, default=1,
                        help='Batch size (keep at 1 for eval)')

    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Load checkpoint
    print(f"Loading checkpoint from {args.checkpoint}")
    checkpoint = torch.load(args.checkpoint, map_location=device)

    # Initialize feature extractor
    feature_extractor = LogMelExtractor(
        sr=args.sr,
        n_mels=args.n_mels,
        n_fft=args.n_fft,
        hop_length=args.hop_length,
        fmin=args.fmin,
        fmax=args.fmax
    )

    # Initialize model
    num_classes = checkpoint['num_classes']
    model = get_model(num_classes=num_classes).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    print(f"Model loaded successfully (num_classes={num_classes})")

    # Create datasets
    train_dataset = DCASE2021EvalDataset(
        data_dir=args.train_dir,
        feature_extractor=feature_extractor,
        patch_frames=args.patch_frames,
        hop_frames=args.hop_frames
    )

    test_dataset = DCASE2021EvalDataset(
        data_dir=args.test_dir,
        feature_extractor=feature_extractor,
        patch_frames=args.patch_frames,
        hop_frames=args.hop_frames
    )

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers
    )

    # Compute statistics on normal training data
    stats = compute_statistics(model, train_loader, device)

    # Save statistics
    stats_path = os.path.join(args.output_dir, f'stats_{args.machine_type}.json')
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Statistics saved to {stats_path}")

    # Evaluate on test data
    results = evaluate(model, test_loader, device, stats, args)

    # Calculate metrics
    metrics = calculate_metrics(results)

    print("\n" + "=" * 50)
    print("Evaluation Results")
    print("=" * 50)
    print(f"Machine Type: {args.machine_type}")
    print(f"Test Directory: {args.test_dir}")
    print(f"Number of test files: {len(results)}")
    print(f"\nMetrics:")
    print(f"  AUC (Score A - 1-max_prob): {metrics['auc_score_a']:.4f}")
    print(f"  AUC (Score B - entropy): {metrics['auc_score_b']:.4f}")
    print(f"  AUC (Combined): {metrics['auc_score_combined']:.4f}")
    print("=" * 50)

    # Save results
    results_path = os.path.join(
        args.output_dir,
        f'results_{args.machine_type}_{os.path.basename(args.test_dir)}.json'
    )
    output_data = {
        'args': vars(args),
        'metrics': metrics,
        'results': results
    }
    with open(results_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\nResults saved to {results_path}")

    # Save scores to CSV for easy viewing
    csv_path = os.path.join(
        args.output_dir,
        f'scores_{args.machine_type}_{os.path.basename(args.test_dir)}.csv'
    )
    with open(csv_path, 'w') as f:
        f.write('filename,label,section_id,score_a,score_b,score_combined\n')
        for r in results:
            f.write(f"{r['filename']},{r['label']},{r['section_id']},"
                   f"{r['score_a']:.6f},{r['score_b']:.6f},{r['score_combined']:.6f}\n")
    print(f"Scores saved to {csv_path}")


if __name__ == '__main__':
    main()

