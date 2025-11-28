#!/usr/bin/env python3
"""
实时音频异常检测
支持从麦克风或音频文件流实时检测异常
"""

import torch
import numpy as np
import sounddevice as sd
import librosa
import json
import time
import argparse
from collections import deque
from threading import Thread, Lock
import queue
import sys
from datetime import datetime

from src.features import LogMelExtractor
from src.model import get_model


class RealtimeAnomalyDetector:
    """实时异常检测器"""

    def __init__(
        self,
        checkpoint_path,
        device='cuda',
        sr=16000,
        buffer_duration=10.0,  # 缓冲区长度（秒）
        hop_duration=0.5,      # 检测间隔（秒）
        patch_frames=64,
        threshold=None,         # 异常阈值
        alert_callback=None     # 异常回调函数
    ):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.sr = sr
        self.buffer_duration = buffer_duration
        self.hop_duration = hop_duration
        self.patch_frames = patch_frames
        self.threshold = threshold
        self.alert_callback = alert_callback

        # 缓冲区设置
        self.buffer_samples = int(buffer_duration * sr)
        self.hop_samples = int(hop_duration * sr)

        # 音频缓冲区（环形缓冲）
        self.audio_buffer = deque(maxlen=self.buffer_samples)
        self.buffer_lock = Lock()

        # 检测队列
        self.detection_queue = queue.Queue()

        # 加载模型
        print(f"Loading model from {checkpoint_path}...")
        checkpoint = torch.load(checkpoint_path, map_location=self.device)

        # 加载特征提取器参数
        feature_params = checkpoint.get('feature_params', {})
        self.feature_extractor = LogMelExtractor(
            sr=feature_params.get('sr', 16000),
            n_mels=feature_params.get('n_mels', 128),
            n_fft=feature_params.get('n_fft', 1024),
            hop_length=feature_params.get('hop_length', 512),
            fmin=feature_params.get('fmin', 0),
            fmax=feature_params.get('fmax', 8000)
        )

        # 加载模型 - 使用get_model函数而不是AnomalyDetectionModel
        num_classes = checkpoint.get('num_classes', 3)
        self.model = get_model(
            num_classes=num_classes,
            width_mult=checkpoint.get('width_mult', 1.0),
            dropout_rate=checkpoint.get('dropout_rate', 0.2)
        )
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()

        # 加载统计信息（用于标准化）
        self.stats = checkpoint.get('stats', None)

        # 检测统计
        self.detection_count = 0
        self.anomaly_count = 0
        self.running = False

        print(f"Model loaded. Device: {self.device}")
        print(f"Buffer: {buffer_duration}s, Hop: {hop_duration}s")
        if self.threshold:
            print(f"Anomaly threshold: {self.threshold:.4f}")

    def audio_callback(self, indata, frames, time_info, status):
        """音频输入回调（sounddevice）"""
        if status:
            print(f"Audio status: {status}", file=sys.stderr)

        # 将音频数据加入缓冲区
        with self.buffer_lock:
            self.audio_buffer.extend(indata[:, 0])  # 单声道

    def extract_features_from_buffer(self):
        """从缓冲区提取特征"""
        with self.buffer_lock:
            if len(self.audio_buffer) < self.buffer_samples:
                return None

            # 获取缓冲区数据
            audio_data = np.array(list(self.audio_buffer))

        # 提取log-Mel特征
        mel_spec = librosa.feature.melspectrogram(
            y=audio_data,
            sr=self.sr,
            n_mels=self.feature_extractor.n_mels,
            n_fft=self.feature_extractor.n_fft,
            hop_length=self.feature_extractor.hop_length,
            fmin=self.feature_extractor.fmin,
            fmax=self.feature_extractor.fmax
        )
        log_mel = np.log(mel_spec + 1e-6)

        return log_mel

    def detect_anomaly(self, log_mel):
        """检测异常"""
        if log_mel is None:
            return None

        # 提取patches
        n_frames = log_mel.shape[1]
        if n_frames < self.patch_frames:
            return None

        patches = []
        for i in range(0, n_frames - self.patch_frames + 1, self.patch_frames // 4):
            patch = log_mel[:, i:i + self.patch_frames]
            patches.append(patch)

        if len(patches) == 0:
            return None

        # 转换为tensor
        patches = np.array(patches)
        patches_tensor = torch.FloatTensor(patches).unsqueeze(1).to(self.device)

        # 推理
        with torch.no_grad():
            logits = self.model(patches_tensor)
            probs = torch.softmax(logits, dim=1)

            # 计算异常分数
            max_probs = probs.max(dim=1)[0].cpu().numpy()
            entropy = -(probs * torch.log(probs + 1e-10)).sum(dim=1).cpu().numpy()

            # Score A: 1 - max(softmax)
            score_a = 1 - max_probs

            # Score B: entropy
            score_b = entropy

            # 标准化（如果有统计信息）
            if self.stats:
                score_a = (score_a - self.stats['score_a_mean']) / (self.stats['score_a_std'] + 1e-10)
                score_b = (score_b - self.stats['score_b_mean']) / (self.stats['score_b_std'] + 1e-10)

            # 组合分数
            combined_score = 0.5 * score_a + 0.5 * score_b

            # 聚合（使用95th percentile）
            final_score = float(np.percentile(combined_score, 95))

        return {
            'score': final_score,
            'max_prob': float(max_probs.max()),
            'entropy': float(entropy.max()),
            'num_patches': len(patches)
        }

    def detection_worker(self):
        """检测工作线程"""
        last_detection_time = time.time()

        while self.running:
            current_time = time.time()

            # 检查是否到达检测间隔
            if current_time - last_detection_time >= self.hop_duration:
                # 提取特征
                log_mel = self.extract_features_from_buffer()

                if log_mel is not None:
                    # 检测异常
                    result = self.detect_anomaly(log_mel)

                    if result is not None:
                        self.detection_count += 1
                        result['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        result['detection_id'] = self.detection_count

                        # 判断是否异常
                        is_anomaly = False
                        if self.threshold and result['score'] > self.threshold:
                            is_anomaly = True
                            self.anomaly_count += 1

                        result['is_anomaly'] = is_anomaly

                        # 输出结果
                        self.output_result(result)

                        # 触发回调
                        if is_anomaly and self.alert_callback:
                            self.alert_callback(result)

                last_detection_time = current_time

            time.sleep(0.01)  # 避免CPU占用过高

    def output_result(self, result):
        """输出检测结果"""
        status = "🚨 ANOMALY" if result['is_anomaly'] else "✓ Normal"
        print(f"[{result['timestamp']}] {status} | "
              f"Score: {result['score']:.4f} | "
              f"MaxProb: {result['max_prob']:.4f} | "
              f"Entropy: {result['entropy']:.4f} | "
              f"Patches: {result['num_patches']}")

    def start_microphone(self, device_id=None):
        """从麦克风开始检测"""
        print("\n" + "="*60)
        print("Starting real-time anomaly detection from microphone...")
        print("="*60)

        # 列出可用设备
        devices = sd.query_devices()
        print("\nAvailable audio devices:")
        for i, device in enumerate(devices):
            print(f"  [{i}] {device['name']}")

        if device_id is not None:
            print(f"\nUsing device: [{device_id}] {devices[device_id]['name']}")
        else:
            print(f"\nUsing default input device")

        print(f"\nPress Ctrl+C to stop...\n")

        self.running = True

        # 启动检测线程
        detection_thread = Thread(target=self.detection_worker, daemon=True)
        detection_thread.start()

        try:
            # 打开音频流
            with sd.InputStream(
                samplerate=self.sr,
                channels=1,
                callback=self.audio_callback,
                device=device_id,
                blocksize=self.hop_samples
            ):
                # 等待填充缓冲区
                print("Filling audio buffer...")
                time.sleep(self.buffer_duration)
                print("Detection started!\n")

                # 保持运行
                while self.running:
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\nStopping detection...")

        finally:
            self.running = False
            detection_thread.join(timeout=1.0)
            self.print_statistics()

    def start_file_stream(self, audio_file, realtime=True):
        """从音频文件流式检测"""
        print("\n" + "="*60)
        print(f"Starting real-time detection from file: {audio_file}")
        print("="*60)
        print(f"Press Ctrl+C to stop...\n")

        # 加载音频文件
        audio, sr = librosa.load(audio_file, sr=self.sr, mono=True)

        if sr != self.sr:
            print(f"Resampling from {sr}Hz to {self.sr}Hz...")
            audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sr)

        print(f"Audio loaded: {len(audio)/self.sr:.2f}s\n")

        self.running = True

        # 启动检测线程
        detection_thread = Thread(target=self.detection_worker, daemon=True)
        detection_thread.start()

        try:
            # 模拟实时流
            pos = 0
            chunk_size = self.hop_samples

            while pos < len(audio) and self.running:
                # 获取音频块
                chunk = audio[pos:pos + chunk_size]

                # 加入缓冲区
                with self.buffer_lock:
                    self.audio_buffer.extend(chunk)

                pos += chunk_size

                # 模拟实时播放
                if realtime:
                    time.sleep(self.hop_duration)
                else:
                    time.sleep(0.01)  # 快速模式

        except KeyboardInterrupt:
            print("\n\nStopping detection...")

        finally:
            self.running = False
            detection_thread.join(timeout=1.0)
            self.print_statistics()

    def print_statistics(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("Detection Statistics:")
        print("="*60)
        print(f"Total detections: {self.detection_count}")
        print(f"Anomalies detected: {self.anomaly_count}")
        if self.detection_count > 0:
            anomaly_rate = self.anomaly_count / self.detection_count * 100
            print(f"Anomaly rate: {anomaly_rate:.2f}%")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Real-time Anomaly Detection')

    # 模型参数
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Path to model checkpoint')
    parser.add_argument('--device', type=str, default='cuda',
                        choices=['cuda', 'cpu'],
                        help='Device to use')

    # 音频源
    parser.add_argument('--source', type=str, default='microphone',
                        choices=['microphone', 'file'],
                        help='Audio source')
    parser.add_argument('--audio_file', type=str,
                        help='Audio file path (if source=file)')
    parser.add_argument('--device_id', type=int,
                        help='Audio device ID (if source=microphone)')

    # 检测参数
    parser.add_argument('--buffer_duration', type=float, default=10.0,
                        help='Buffer duration in seconds')
    parser.add_argument('--hop_duration', type=float, default=0.5,
                        help='Detection hop duration in seconds')
    parser.add_argument('--patch_frames', type=int, default=64,
                        help='Patch frames')
    parser.add_argument('--threshold', type=float,
                        help='Anomaly threshold (z-score)')

    # 其他
    parser.add_argument('--realtime', action='store_true',
                        help='Simulate realtime playback for file input')

    args = parser.parse_args()

    # 创建检测器
    detector = RealtimeAnomalyDetector(
        checkpoint_path=args.checkpoint,
        device=args.device,
        buffer_duration=args.buffer_duration,
        hop_duration=args.hop_duration,
        patch_frames=args.patch_frames,
        threshold=args.threshold
    )

    # 启动检测
    if args.source == 'microphone':
        detector.start_microphone(device_id=args.device_id)
    else:
        if not args.audio_file:
            print("Error: --audio_file required when source=file")
            return
        detector.start_file_stream(args.audio_file, realtime=args.realtime)


if __name__ == '__main__':
    main()