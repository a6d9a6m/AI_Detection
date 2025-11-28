"""
Dataset loader for DCASE2021 Task2 Baseline 2
Handles loading and preprocessing of audio data
"""
import os
import glob
import random
import numpy as np
import torch
from torch.utils.data import Dataset
from features import LogMelExtractor


class DCASE2021Dataset(Dataset):
    """
    Dataset for DCASE2021 Task2

    Args:
        data_dir: path to data directory (e.g., 'data/fan/train')
        feature_extractor: LogMelExtractor instance
        patch_frames: number of frames per patch (default: 64)
        mode: 'train' or 'eval'
        augmentation: whether to apply data augmentation
        aug_volume_range: (min, max) for amplitude scaling
        aug_time_shift: max time shift in frames
        aug_freq_mask: max frequency bins to mask
        aug_time_mask: max time frames to mask
    """

    def __init__(
        self,
        data_dir,
        feature_extractor,
        patch_frames=64,
        mode='train',
        augmentation=True,
        aug_volume_range=(0.7, 1.3),
        aug_time_shift=3,
        aug_freq_mask=15,
        aug_time_mask=15
    ):
        self.data_dir = data_dir
        self.feature_extractor = feature_extractor
        self.patch_frames = patch_frames
        self.mode = mode
        self.augmentation = augmentation and (mode == 'train')

        # Augmentation parameters
        self.aug_volume_range = aug_volume_range
        self.aug_time_shift = aug_time_shift
        self.aug_freq_mask = aug_freq_mask
        self.aug_time_mask = aug_time_mask

        # Get all audio files
        self.audio_files = sorted(glob.glob(os.path.join(data_dir, '*.wav')))

        # Extract section labels from filenames
        self.section_labels = []
        for audio_file in self.audio_files:
            filename = os.path.basename(audio_file)
            section_id = int(filename.split('_')[1])  # section_XX
            self.section_labels.append(section_id)

        print(f"Loaded {len(self.audio_files)} files from {data_dir}")
        print(f"Sections: {set(self.section_labels)}")

    def __len__(self):
        return len(self.audio_files)

    def __getitem__(self, idx):
        """
        Get a single sample

        Returns:
            patch: tensor of shape (1, n_mels, patch_frames)
            label: section ID
        """
        audio_path = self.audio_files[idx]
        label = self.section_labels[idx]

        # Extract log-Mel spectrogram
        log_mel = self.feature_extractor.extract(audio_path)
        n_mels, n_frames = log_mel.shape

        # Random crop a patch during training
        if self.mode == 'train':
            if n_frames > self.patch_frames:
                start = random.randint(0, n_frames - self.patch_frames)
                patch = log_mel[:, start:start + self.patch_frames]
            else:
                # Pad if too short
                patch = np.zeros((n_mels, self.patch_frames))
                patch[:, :n_frames] = log_mel
        else:
            # For eval, take the first patch
            if n_frames >= self.patch_frames:
                patch = log_mel[:, :self.patch_frames]
            else:
                patch = np.zeros((n_mels, self.patch_frames))
                patch[:, :n_frames] = log_mel

        # Apply augmentation
        if self.augmentation:
            patch = self._augment(patch)

        # Convert to tensor (1, n_mels, patch_frames)
        patch = torch.FloatTensor(patch).unsqueeze(0)
        label = torch.LongTensor([label])[0]

        return patch, label

    def _augment(self, patch):
        """
        Apply data augmentation (including SpecAugment)

        Args:
            patch: log-Mel patch (n_mels, patch_frames)

        Returns:
            augmented patch
        """
        patch = patch.copy()
        n_mels, n_frames = patch.shape

        # Amplitude scaling
        if random.random() < 0.5:
            scale = random.uniform(*self.aug_volume_range)
            patch = patch * scale

        # Time shifting
        if random.random() < 0.3 and self.aug_time_shift > 0:
            shift = random.randint(-self.aug_time_shift, self.aug_time_shift)
            if shift != 0:
                patch = np.roll(patch, shift, axis=1)

        # SpecAugment: Frequency masking
        if random.random() < 0.5 and self.aug_freq_mask > 0:
            num_masks = random.randint(1, 2)
            for _ in range(num_masks):
                f = random.randint(5, self.aug_freq_mask)
                f0 = random.randint(0, max(0, n_mels - f))
                patch[f0:f0 + f, :] = 0

        # SpecAugment: Time masking
        if random.random() < 0.5 and self.aug_time_mask > 0:
            num_masks = random.randint(1, 2)
            for _ in range(num_masks):
                t = random.randint(5, self.aug_time_mask)
                t0 = random.randint(0, max(0, n_frames - t))
                patch[:, t0:t0 + t] = 0

        return patch


class DCASE2021EvalDataset(Dataset):
    """
    Evaluation dataset that returns all patches from each audio file

    Args:
        data_dir: path to data directory
        feature_extractor: LogMelExtractor instance
        patch_frames: number of frames per patch
        hop_frames: hop size between patches
    """

    def __init__(
        self,
        data_dir,
        feature_extractor,
        patch_frames=64,
        hop_frames=32
    ):
        self.data_dir = data_dir
        self.feature_extractor = feature_extractor
        self.patch_frames = patch_frames
        self.hop_frames = hop_frames

        # Get all audio files
        self.audio_files = sorted(glob.glob(os.path.join(data_dir, '*.wav')))

        # Extract labels (normal=0, anomaly=1) from filenames
        self.labels = []
        self.section_ids = []
        for audio_file in self.audio_files:
            filename = os.path.basename(audio_file)
            parts = filename.split('_')

            # Extract section ID
            section_id = int(parts[1])  # section_XX
            self.section_ids.append(section_id)

            # Extract anomaly label
            if 'normal' in filename:
                self.labels.append(0)
            elif 'anomaly' in filename:
                self.labels.append(1)
            else:
                self.labels.append(0)  # Default to normal

        print(f"Loaded {len(self.audio_files)} files from {data_dir}")
        print(f"Normal: {sum(1 for l in self.labels if l == 0)}, "
              f"Anomaly: {sum(1 for l in self.labels if l == 1)}")

    def __len__(self):
        return len(self.audio_files)

    def __getitem__(self, idx):
        """
        Get all patches from a single audio file

        Returns:
            patches: tensor of shape (num_patches, 1, n_mels, patch_frames)
            label: 0 for normal, 1 for anomaly
            filename: audio filename
        """
        audio_path = self.audio_files[idx]
        label = self.labels[idx]
        section_id = self.section_ids[idx]
        filename = os.path.basename(audio_path)

        # Extract all patches
        patches = self.feature_extractor.extract_patches(
            audio_path,
            patch_frames=self.patch_frames,
            hop_frames=self.hop_frames
        )

        # Convert to tensor (num_patches, 1, n_mels, patch_frames)
        patches = np.array(patches)
        patches = torch.FloatTensor(patches).unsqueeze(1)

        return patches, label, section_id, filename
