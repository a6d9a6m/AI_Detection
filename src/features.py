"""
Feature extraction module for DCASE2021 Task2 Baseline 2
Log-Mel spectrogram extraction with specified parameters
"""
import numpy as np
import librosa


class LogMelExtractor:
    """
    Extract log-Mel spectrogram features

    Parameters:
    - sr: sampling rate (16000 Hz)
    - n_mels: number of mel bins (128)
    - n_fft: FFT window size (1024 for 64ms at 16kHz)
    - hop_length: hop size (512 for 32ms at 16kHz)
    - fmin/fmax: frequency range (0-8000 Hz)
    """

    def __init__(
        self,
        sr=16000,
        n_mels=128,
        n_fft=1024,
        hop_length=512,
        fmin=0,
        fmax=8000,
        power=2.0
    ):
        self.sr = sr
        self.n_mels = n_mels
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.fmin = fmin
        self.fmax = fmax
        self.power = power

    def extract(self, audio_path):
        """
        Extract log-Mel spectrogram from audio file

        Args:
            audio_path: path to audio file

        Returns:
            log_mel: log-Mel spectrogram, shape (n_mels, n_frames)
        """
        # Load audio
        y, sr = librosa.load(audio_path, sr=self.sr, mono=True)

        # Compute mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels,
            fmin=self.fmin,
            fmax=self.fmax,
            power=self.power
        )

        # Convert to log scale (log(x + epsilon))
        log_mel = np.log(mel_spec + 1e-6)

        return log_mel

    def extract_patches(self, audio_path, patch_frames=64, hop_frames=32):
        """
        Extract overlapping patches from audio

        Args:
            audio_path: path to audio file
            patch_frames: number of frames per patch (T=64)
            hop_frames: hop size between patches

        Returns:
            patches: list of patches, each shape (n_mels, patch_frames)
        """
        log_mel = self.extract(audio_path)
        n_mels, n_frames = log_mel.shape

        patches = []
        start = 0
        while start + patch_frames <= n_frames:
            patch = log_mel[:, start:start + patch_frames]
            patches.append(patch)
            start += hop_frames

        # Handle last incomplete patch if exists
        if start < n_frames and len(patches) > 0:
            # Pad the last patch
            last_patch = np.zeros((n_mels, patch_frames))
            remaining = n_frames - start
            last_patch[:, :remaining] = log_mel[:, start:]
            patches.append(last_patch)

        return patches
