"""
Quick test script to verify the setup
Tests model creation, feature extraction, and data loading
"""
import torch
import numpy as np
from src.features import LogMelExtractor
from src.model import get_model
from src.dataset import DCASE2021Dataset

def test_feature_extraction():
    """Test log-Mel feature extraction"""
    print("Testing feature extraction...")
    extractor = LogMelExtractor(
        sr=16000,
        n_mels=128,
        n_fft=1024,
        hop_length=512,
        fmin=0,
        fmax=8000
    )

    # Create a dummy audio signal
    import librosa
    y = np.random.randn(16000 * 5)  # 5 seconds

    # Save to temporary file
    import tempfile
    import soundfile as sf
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sf.write(f.name, y, 16000)
        temp_path = f.name

    # Extract features
    log_mel = extractor.extract(temp_path)
    print(f"  log-Mel shape: {log_mel.shape}")
    assert log_mel.shape[0] == 128, "Expected 128 mel bins"

    # Extract patches
    patches = extractor.extract_patches(temp_path, patch_frames=64, hop_frames=32)
    print(f"  Number of patches: {len(patches)}")
    print(f"  Patch shape: {patches[0].shape}")
    assert patches[0].shape == (128, 64), "Expected patch shape (128, 64)"

    # Clean up
    import os
    os.remove(temp_path)

    print("  ✓ Feature extraction test passed!")


def test_model():
    """Test model creation and forward pass"""
    print("\nTesting model...")

    # Create model
    model = get_model(num_classes=3)
    print(f"  Model created with {sum(p.numel() for p in model.parameters())} parameters")

    # Test forward pass
    dummy_input = torch.randn(2, 1, 128, 64)  # (batch, channel, height, width)
    output = model(dummy_input)
    print(f"  Input shape: {dummy_input.shape}")
    print(f"  Output shape: {output.shape}")
    assert output.shape == (2, 3), "Expected output shape (2, 3)"

    # Test softmax
    probs = torch.softmax(output, dim=1)
    print(f"  Softmax output: {probs}")
    assert torch.allclose(probs.sum(dim=1), torch.ones(2)), "Softmax should sum to 1"

    print("  ✓ Model test passed!")


def test_dataset():
    """Test dataset loading"""
    print("\nTesting dataset loading...")

    import os
    import glob

    # Check if data exists
    train_dir = "data/fan/train"
    if not os.path.exists(train_dir):
        print(f"  ⚠ Data directory {train_dir} not found, skipping dataset test")
        return

    # Create feature extractor
    extractor = LogMelExtractor()

    # Create dataset
    dataset = DCASE2021Dataset(
        data_dir=train_dir,
        feature_extractor=extractor,
        patch_frames=64,
        mode='train'
    )

    print(f"  Dataset size: {len(dataset)}")

    if len(dataset) > 0:
        # Test getting an item
        patch, label = dataset[0]
        print(f"  Sample patch shape: {patch.shape}")
        print(f"  Sample label: {label}")
        assert patch.shape == (1, 128, 64), "Expected patch shape (1, 128, 64)"

        print("  ✓ Dataset test passed!")
    else:
        print("  ⚠ Dataset is empty")


def main():
    print("=" * 50)
    print("DCASE2021 Task2 Baseline 2 - Quick Test")
    print("=" * 50)

    try:
        test_feature_extraction()
        test_model()
        test_dataset()

        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
        print("\nYou can now:")
        print("1. Train a model:")
        print("   python src/train.py --train_dir data/fan/train --machine_type fan")
        print("\n2. Run inference:")
        print("   python src/inference.py --train_dir data/fan/train --test_dir data/fan/source_test --checkpoint checkpoints/model_fan_best.pth --machine_type fan")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
