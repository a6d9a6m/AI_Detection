"""
Visualization script for DCASE2021 Task2 Baseline 2
Visualize anomaly detection results with clear indicators of correct/incorrect predictions
"""
import os
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.metrics import roc_curve, auc, confusion_matrix
import seaborn as sns

# Set style
sns.set_style("whitegrid")
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 100


def load_results(results_path):
    """Load results from JSON file"""
    with open(results_path, 'r') as f:
        data = json.load(f)
    return data


def plot_score_distribution(results, labels, scores, score_name, ax, threshold=None):
    """
    Plot score distribution for normal vs anomaly

    Args:
        results: list of result dictionaries
        labels: array of true labels (0=normal, 1=anomaly)
        scores: array of anomaly scores
        score_name: name of the score
        ax: matplotlib axis
        threshold: decision threshold (optional)
    """
    normal_scores = scores[labels == 0]
    anomaly_scores = scores[labels == 1]

    # Plot histograms
    bins = np.linspace(scores.min(), scores.max(), 30)
    ax.hist(normal_scores, bins=bins, alpha=0.6, color='green', label='Normal', density=True)
    ax.hist(anomaly_scores, bins=bins, alpha=0.6, color='red', label='Anomaly', density=True)

    # Add threshold line if provided
    if threshold is not None:
        ax.axvline(threshold, color='black', linestyle='--', linewidth=2, label=f'Threshold: {threshold:.3f}')

    ax.set_xlabel('Anomaly Score')
    ax.set_ylabel('Density')
    ax.set_title(f'{score_name} Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)


def plot_roc_curve(labels, scores, score_name, ax):
    """
    Plot ROC curve

    Args:
        labels: array of true labels
        scores: array of anomaly scores
        score_name: name of the score
        ax: matplotlib axis

    Returns:
        auc_score: AUC value
        threshold: optimal threshold
    """
    fpr, tpr, thresholds = roc_curve(labels, scores)
    auc_score = auc(fpr, tpr)

    # Find optimal threshold (Youden's J statistic)
    j_scores = tpr - fpr
    optimal_idx = np.argmax(j_scores)
    optimal_threshold = thresholds[optimal_idx]

    # Plot ROC curve
    ax.plot(fpr, tpr, color='blue', lw=2, label=f'ROC (AUC = {auc_score:.4f})')
    ax.plot([0, 1], [0, 1], color='gray', linestyle='--', lw=1, label='Random')
    ax.plot(fpr[optimal_idx], tpr[optimal_idx], 'ro', markersize=8,
            label=f'Optimal (thr={optimal_threshold:.3f})')

    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title(f'{score_name} ROC Curve')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    return auc_score, optimal_threshold


def plot_predictions(results, scores, threshold, score_name, ax):
    """
    Plot predictions with correct/incorrect indicators

    Args:
        results: list of result dictionaries
        scores: array of anomaly scores
        threshold: decision threshold
        score_name: name of the score
        ax: matplotlib axis
    """
    labels = np.array([r['label'] for r in results])
    predictions = (scores > threshold).astype(int)
    correct = (predictions == labels)

    # Separate into categories
    true_positive = (labels == 1) & correct
    true_negative = (labels == 0) & correct
    false_positive = (labels == 0) & ~correct
    false_negative = (labels == 1) & ~correct

    # Plot points
    indices = np.arange(len(scores))

    if true_positive.any():
        ax.scatter(indices[true_positive], scores[true_positive],
                  color='darkgreen', marker='o', s=50, label='True Positive', alpha=0.7)

    if true_negative.any():
        ax.scatter(indices[true_negative], scores[true_negative],
                  color='lightgreen', marker='o', s=50, label='True Negative', alpha=0.7)

    if false_positive.any():
        ax.scatter(indices[false_positive], scores[false_positive],
                  color='orange', marker='x', s=100, label='False Positive', linewidths=2)

    if false_negative.any():
        ax.scatter(indices[false_negative], scores[false_negative],
                  color='red', marker='x', s=100, label='False Negative', linewidths=2)

    # Add threshold line
    ax.axhline(threshold, color='black', linestyle='--', linewidth=2, label='Threshold')

    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Anomaly Score')
    ax.set_title(f'{score_name} Predictions (Accuracy: {correct.sum()}/{len(correct)})')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)


def plot_confusion_matrix(labels, predictions, ax):
    """
    Plot confusion matrix

    Args:
        labels: true labels
        predictions: predicted labels
        ax: matplotlib axis
    """
    cm = confusion_matrix(labels, predictions)

    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=['Normal', 'Anomaly'],
                yticklabels=['Normal', 'Anomaly'],
                cbar_kws={'label': 'Count'})

    ax.set_xlabel('Predicted Label')
    ax.set_ylabel('True Label')
    ax.set_title('Confusion Matrix')

    # Add accuracy text
    accuracy = np.trace(cm) / np.sum(cm)
    ax.text(1, -0.3, f'Accuracy: {accuracy:.2%}',
            transform=ax.transAxes, ha='center', fontsize=12, weight='bold')


def plot_section_wise_performance(results, scores, threshold, ax):
    """
    Plot performance by section ID

    Args:
        results: list of result dictionaries
        scores: array of anomaly scores
        threshold: decision threshold
        ax: matplotlib axis
    """
    section_ids = np.array([r['section_id'] for r in results])
    labels = np.array([r['label'] for r in results])
    predictions = (scores > threshold).astype(int)

    unique_sections = sorted(set(section_ids))
    accuracies = []
    counts = []

    for section_id in unique_sections:
        mask = section_ids == section_id
        if mask.sum() > 0:
            section_accuracy = (predictions[mask] == labels[mask]).mean()
            accuracies.append(section_accuracy * 100)
            counts.append(mask.sum())
        else:
            accuracies.append(0)
            counts.append(0)

    # Plot bars
    bars = ax.bar(range(len(unique_sections)), accuracies, color='steelblue', alpha=0.7)

    # Add count labels
    for i, (bar, count) in enumerate(zip(bars, counts)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'n={count}',
                ha='center', va='bottom', fontsize=9)

    ax.set_xlabel('Section ID')
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Accuracy by Section')
    ax.set_xticks(range(len(unique_sections)))
    ax.set_xticklabels([f'S{s:02d}' for s in unique_sections])
    ax.set_ylim([0, 105])
    ax.grid(True, alpha=0.3, axis='y')


def create_summary_table(results, labels, predictions, ax):
    """
    Create a summary table with key metrics

    Args:
        results: list of result dictionaries
        labels: true labels
        predictions: predicted labels
        ax: matplotlib axis
    """
    ax.axis('off')

    # Calculate metrics
    tp = np.sum((labels == 1) & (predictions == 1))
    tn = np.sum((labels == 0) & (predictions == 0))
    fp = np.sum((labels == 0) & (predictions == 1))
    fn = np.sum((labels == 1) & (predictions == 0))

    accuracy = (tp + tn) / len(labels)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Create table data
    table_data = [
        ['Metric', 'Value'],
        ['Total Samples', f'{len(labels)}'],
        ['Normal Samples', f'{np.sum(labels == 0)}'],
        ['Anomaly Samples', f'{np.sum(labels == 1)}'],
        ['', ''],
        ['True Positives', f'{tp}'],
        ['True Negatives', f'{tn}'],
        ['False Positives', f'{fp}'],
        ['False Negatives', f'{fn}'],
        ['', ''],
        ['Accuracy', f'{accuracy:.2%}'],
        ['Precision', f'{precision:.2%}'],
        ['Recall', f'{recall:.2%}'],
        ['F1 Score', f'{f1:.4f}'],
    ]

    # Create table
    table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                     colWidths=[0.4, 0.4])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Style header row
    for i in range(2):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Style separator rows
    table[(4, 0)].set_facecolor('#E7E6E6')
    table[(4, 1)].set_facecolor('#E7E6E6')
    table[(9, 0)].set_facecolor('#E7E6E6')
    table[(9, 1)].set_facecolor('#E7E6E6')

    ax.set_title('Performance Summary', fontsize=12, weight='bold', pad=20)


def visualize_results(results_path, output_dir=None, score_type='combined'):
    """
    Create comprehensive visualization of results

    Args:
        results_path: path to results JSON file
        output_dir: output directory for figures (if None, will display)
        score_type: 'score_a', 'score_b', or 'combined'
    """
    # Load results
    print(f"Loading results from {results_path}")
    data = load_results(results_path)

    results = data['results']
    metrics = data['metrics']
    args = data['args']

    machine_type = args['machine_type']
    test_dir = os.path.basename(args['test_dir'])

    # Extract data
    labels = np.array([r['label'] for r in results])
    scores_a = np.array([r['score_a'] for r in results])
    scores_b = np.array([r['score_b'] for r in results])
    scores_combined = np.array([r['score_combined'] for r in results])

    # Select score type
    score_map = {
        'score_a': (scores_a, 'Score A (1 - max_prob)', 'auc_score_a'),
        'score_b': (scores_b, 'Score B (entropy)', 'auc_score_b'),
        'combined': (scores_combined, 'Combined Score', 'auc_score_combined')
    }

    scores, score_name, auc_key = score_map[score_type]
    auc_value = metrics[auc_key]

    print(f"Visualizing {score_name}")
    print(f"AUC: {auc_value:.4f}")
    print(f"Total samples: {len(results)}")
    print(f"Normal: {np.sum(labels == 0)}, Anomaly: {np.sum(labels == 1)}")

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    ax1 = fig.add_subplot(gs[0, 0])  # Score distribution
    ax2 = fig.add_subplot(gs[0, 1])  # ROC curve
    ax3 = fig.add_subplot(gs[0, 2])  # Confusion matrix
    ax4 = fig.add_subplot(gs[1, :])  # Predictions plot
    ax5 = fig.add_subplot(gs[2, 0])  # Section-wise performance
    ax6 = fig.add_subplot(gs[2, 1])  # Summary table

    # Plot 1: Score distribution
    _, optimal_threshold = plot_roc_curve(labels, scores, score_name, ax2)
    plot_score_distribution(results, labels, scores, score_name, ax1, optimal_threshold)

    # Plot 2: ROC curve (already plotted above)

    # Plot 3: Confusion matrix
    predictions = (scores > optimal_threshold).astype(int)
    plot_confusion_matrix(labels, predictions, ax3)

    # Plot 4: Predictions with correct/incorrect indicators
    plot_predictions(results, scores, optimal_threshold, score_name, ax4)

    # Plot 5: Section-wise performance
    plot_section_wise_performance(results, scores, optimal_threshold, ax5)

    # Plot 6: Summary table
    create_summary_table(results, labels, predictions, ax6)

    # Add main title
    fig.suptitle(f'DCASE2021 Task2 - {machine_type.upper()} - {test_dir}\n'
                 f'{score_name} (AUC = {auc_value:.4f})',
                 fontsize=14, weight='bold', y=0.98)

    # Save or show
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir,
                                   f'visualization_{machine_type}_{test_dir}_{score_type}.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved visualization to {output_path}")
    else:
        plt.show()

    plt.close()


def visualize_all_scores(results_path, output_dir=None):
    """
    Create visualizations for all score types

    Args:
        results_path: path to results JSON file
        output_dir: output directory for figures
    """
    for score_type in ['score_a', 'score_b', 'combined']:
        print(f"\n{'='*50}")
        visualize_results(results_path, output_dir, score_type)


def create_comparison_plot(results_paths, output_path=None):
    """
    Create comparison plot across multiple experiments

    Args:
        results_paths: list of paths to results JSON files
        output_path: path to save comparison plot
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for results_path in results_paths:
        data = load_results(results_path)
        results = data['results']
        args = data['args']

        machine_type = args['machine_type']
        test_dir = os.path.basename(args['test_dir'])
        label = f"{machine_type}_{test_dir}"

        labels = np.array([r['label'] for r in results])
        scores_a = np.array([r['score_a'] for r in results])
        scores_b = np.array([r['score_b'] for r in results])
        scores_combined = np.array([r['score_combined'] for r in results])

        # Plot ROC curves
        for i, (scores, name) in enumerate([
            (scores_a, 'Score A'),
            (scores_b, 'Score B'),
            (scores_combined, 'Combined')
        ]):
            fpr, tpr, _ = roc_curve(labels, scores)
            auc_score = auc(fpr, tpr)
            axes[i].plot(fpr, tpr, lw=2, label=f'{label} (AUC={auc_score:.3f})')
            axes[i].set_xlabel('False Positive Rate')
            axes[i].set_ylabel('True Positive Rate')
            axes[i].set_title(f'{name} ROC Curves')
            axes[i].legend(loc='lower right', fontsize=8)
            axes[i].grid(True, alpha=0.3)

    # Add diagonal line
    for ax in axes:
        ax.plot([0, 1], [0, 1], 'k--', lw=1)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved comparison plot to {output_path}")
    else:
        plt.show()

    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Visualize DCASE2021 Task2 results')

    parser.add_argument('--results', type=str, required=True,
                        help='Path to results JSON file')
    parser.add_argument('--output_dir', type=str, default='./visualizations',
                        help='Output directory for visualizations')
    parser.add_argument('--score_type', type=str, default='all',
                        choices=['score_a', 'score_b', 'combined', 'all'],
                        help='Score type to visualize')
    parser.add_argument('--compare', type=str, nargs='+',
                        help='Multiple result files to compare')

    args = parser.parse_args()

    if args.compare:
        # Comparison mode
        print("Creating comparison plot...")
        output_path = os.path.join(args.output_dir, 'comparison.png')
        create_comparison_plot(args.compare, output_path)
    else:
        # Single result visualization
        if args.score_type == 'all':
            visualize_all_scores(args.results, args.output_dir)
        else:
            visualize_results(args.results, args.output_dir, args.score_type)


if __name__ == '__main__':
    main()
