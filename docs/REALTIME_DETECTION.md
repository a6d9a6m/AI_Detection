# 实时异常检测指南

## 概述

`src/realtime_detection.py` 实现了实时音频异常检测功能，支持：

- **麦克风输入**：实时从麦克风捕获音频并检测异常
- **文件流式输入**：模拟实时播放音频文件并检测
- **滑动窗口检测**：使用环形缓冲区持续监测
- **实时输出**：即时显示异常分数和状态

## 工作原理

### 1. 音频缓冲

```
音频输入 → 环形缓冲区(10秒) → 特征提取 → 模型推理 → 异常分数
           ↑                                            ↓
           └────────────── 滑动检测(0.5秒) ←─────────────┘
```

- **缓冲区长度**：默认 10 秒（可调）
- **检测间隔**：默认 0.5 秒（可调）
- **每次检测**：从完整缓冲区提取特征并推理

### 2. 实时流程

```python
1. 音频输入线程：
   - 持续读取音频 → 填充缓冲区

2. 检测线程：
   - 每 hop_duration 秒：
     a) 从缓冲区提取 log-Mel 特征
     b) 切分为多个 patches
     c) 模型推理得到分数
     d) 聚合并输出结果
     e) 判断是否超过阈值
```

### 3. 异常判断

- 计算 **Score A** (1 - max_prob) 和 **Score B** (entropy)
- 使用训练集统计进行 **Z-score 标准化**
- 组合分数 = 0.5 × score_a_z + 0.5 × score_b_z
- 使用 **95th percentile** 聚合多个 patches
- 与阈值比较判断是否异常

## 安装依赖

```bash
pip install sounddevice
```

或更新所有依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 方式 1：从麦克风实时检测

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source microphone \
    --threshold 2.0
```

**参数说明**：
- `--checkpoint`: 模型检查点路径
- `--source microphone`: 使用麦克风输入
- `--threshold`: 异常阈值（Z-score，推荐 1.5-3.0）

**输出示例**：

```
Starting real-time anomaly detection from microphone...
============================================================

Available audio devices:
  [0] Microsoft Sound Mapper - Input
  [1] Microphone (Realtek High Definition Audio)
  [2] ...

Using default input device

Press Ctrl+C to stop...

Filling audio buffer...
Detection started!

[2024-01-15 10:30:15.234] ✓ Normal | Score: 0.8234 | MaxProb: 0.7234 | Entropy: 1.2345 | Patches: 40
[2024-01-15 10:30:15.734] ✓ Normal | Score: 0.9123 | MaxProb: 0.6892 | Entropy: 1.3421 | Patches: 40
[2024-01-15 10:30:16.234] 🚨 ANOMALY | Score: 2.3456 | MaxProb: 0.3421 | Entropy: 2.1234 | Patches: 40
[2024-01-15 10:30:16.734] ✓ Normal | Score: 1.1234 | MaxProb: 0.6543 | Entropy: 1.4567 | Patches: 40
...

^C
Stopping detection...

============================================================
Detection Statistics:
============================================================
Total detections: 120
Anomalies detected: 15
Anomaly rate: 12.50%
============================================================
```

### 方式 2：指定音频设备

查看可用设备：

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

使用特定设备：

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source microphone \
    --device_id 1 \
    --threshold 2.0
```

### 方式 3：从音频文件流式检测

模拟实时播放：

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source file \
    --audio_file data/fan/source_test/section_00_source_test_normal_0000.wav \
    --threshold 2.0 \
    --realtime
```

快速模式（不等待实时播放）：

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source file \
    --audio_file data/fan/source_test/section_00_source_test_anomaly_0000.wav \
    --threshold 2.0
```

## 参数详解

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--checkpoint` | 模型检查点路径 | `checkpoints/model_fan_best.pth` |

### 音频源参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--source` | microphone | 音频源：microphone 或 file |
| `--audio_file` | - | 音频文件路径（source=file 时） |
| `--device_id` | 默认设备 | 音频设备 ID（source=microphone 时） |

### 检测参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--buffer_duration` | 10.0 | 缓冲区长度（秒） |
| `--hop_duration` | 0.5 | 检测间隔（秒） |
| `--patch_frames` | 64 | Patch 帧数 |
| `--threshold` | None | 异常阈值（Z-score） |

### 其他参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--device` | cuda | 计算设备：cuda 或 cpu |
| `--realtime` | False | 文件模式下是否模拟实时播放 |

## 参数调优建议

### 1. 缓冲区长度 (buffer_duration)

```bash
# 更短缓冲 = 更快响应，但特征不够完整
--buffer_duration 5.0

# 更长缓冲 = 更完整特征，但响应延迟
--buffer_duration 15.0

# 推荐：10 秒（平衡）
--buffer_duration 10.0
```

### 2. 检测间隔 (hop_duration)

```bash
# 更短间隔 = 更频繁检测，CPU 占用高
--hop_duration 0.25

# 更长间隔 = 更省资源，可能错过瞬时异常
--hop_duration 1.0

# 推荐：0.5 秒（平衡）
--hop_duration 0.5
```

### 3. 异常阈值 (threshold)

```bash
# 高灵敏度（更多误报）
--threshold 1.5

# 低灵敏度（更少误报）
--threshold 3.0

# 推荐：2.0-2.5
--threshold 2.0
```

**如何选择阈值**？

1. 在正常音频上运行，观察分数范围
2. 在异常音频上运行，观察分数范围
3. 选择能有效分离正常/异常的阈值

示例：

```bash
# 测试正常样本
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source file \
    --audio_file data/fan/source_test/section_00_source_test_normal_0000.wav

# 观察输出：Score: 0.8~1.2（大部分在此范围）

# 测试异常样本
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source file \
    --audio_file data/fan/source_test/section_00_source_test_anomaly_0000.wav

# 观察输出：Score: 2.0~3.5（大部分在此范围）
```

## 高级用法

### 1. 保存检测记录

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source microphone \
    --threshold 2.0 \
    | tee detection_log.txt
```

### 2. 过滤仅显示异常

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source microphone \
    --threshold 2.0 \
    | grep "ANOMALY"
```

### 3. 批量测试多个文件

创建 `test_files.txt`：

```
data/fan/source_test/section_00_source_test_normal_0000.wav
data/fan/source_test/section_00_source_test_anomaly_0000.wav
data/fan/source_test/section_01_source_test_normal_0000.wav
```

批量测试：

```bash
cat test_files.txt | while read file; do
    echo "Testing: $file"
    python src/realtime_detection.py \
        --checkpoint checkpoints/model_fan_best.pth \
        --source file \
        --audio_file "$file" \
        --threshold 2.0
    echo "---"
done
```

## 性能优化

### 1. CPU 模式（无 GPU）

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source microphone \
    --device cpu \
    --hop_duration 1.0  # 增加间隔降低 CPU 占用
```

### 2. 减少计算量

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source microphone \
    --patch_frames 32 \      # 更小的 patch
    --buffer_duration 5.0 \  # 更短的缓冲
    --hop_duration 1.0       # 更长的间隔
```

### 3. GPU 加速

确保 PyTorch 支持 CUDA：

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

使用 GPU：

```bash
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source microphone \
    --device cuda \
    --hop_duration 0.25  # GPU 可以更频繁检测
```

## 实际应用场景

### 场景 1：工业设备监控

```bash
# 持续监控风扇异常
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source microphone \
    --device_id 1 \
    --threshold 2.0 \
    --buffer_duration 10.0 \
    --hop_duration 0.5 \
    | tee logs/fan_monitor_$(date +%Y%m%d_%H%M%S).log
```

### 场景 2：质检系统

```bash
# 实时检测产线上的齿轮箱异常
python src/realtime_detection.py \
    --checkpoint checkpoints/model_gearbox_best.pth \
    --source microphone \
    --threshold 2.5 \
    --buffer_duration 15.0 \
    --hop_duration 0.5
```

### 场景 3：离线分析

```bash
# 快速分析录音文件
python src/realtime_detection.py \
    --checkpoint checkpoints/model_fan_best.pth \
    --source file \
    --audio_file recordings/test_20240115.wav \
    --threshold 2.0
```

## 输出说明

### 正常输出格式

```
[时间戳] 状态 | Score: 异常分数 | MaxProb: 最大概率 | Entropy: 熵 | Patches: patch数量
```

示例：

```
[2024-01-15 10:30:15.234] ✓ Normal | Score: 0.8234 | MaxProb: 0.7234 | Entropy: 1.2345 | Patches: 40
```

### 异常输出格式

```
[2024-01-15 10:30:16.234] 🚨 ANOMALY | Score: 2.3456 | MaxProb: 0.3421 | Entropy: 2.1234 | Patches: 40
```

### 统计信息

程序结束时显示：

```
============================================================
Detection Statistics:
============================================================
Total detections: 120       # 总检测次数
Anomalies detected: 15      # 检测到的异常数
Anomaly rate: 12.50%        # 异常率
============================================================
```

## 故障排除

### 问题 1：找不到音频设备

**错误**：

```
Error opening audio device
```

**解决**：

```bash
# 列出所有设备
python -c "import sounddevice as sd; print(sd.query_devices())"

# 指定设备 ID
python src/realtime_detection.py ... --device_id 1
```

### 问题 2：音频缓冲区下溢

**警告**：

```
Audio status: input underflow
```

**解决**：

```bash
# 增加缓冲区
--buffer_duration 15.0

# 或增加检测间隔
--hop_duration 1.0
```

### 问题 3：CPU 占用过高

**解决**：

```bash
# 增加检测间隔
--hop_duration 1.0

# 或使用 GPU
--device cuda

# 或使用更小的 patch
--patch_frames 32
```

### 问题 4：检测延迟过大

**解决**：

```bash
# 减小缓冲区
--buffer_duration 5.0

# 减小检测间隔
--hop_duration 0.25
```

### 问题 5：CUDA out of memory

**解决**：

```bash
# 使用 CPU
--device cpu

# 或减小 patch 数量（减小 buffer_duration）
--buffer_duration 5.0
```

## 系统要求

### 最低要求

- **CPU**: 2 核
- **内存**: 4GB
- **Python**: 3.7+
- **音频设备**: 支持 16kHz 采样率

### 推荐配置

- **CPU**: 4 核或更多
- **GPU**: NVIDIA GPU (可选，加速推理)
- **内存**: 8GB
- **音频设备**: 低延迟音频接口

## 性能参考

### CPU 模式 (Intel i7)

| hop_duration | CPU 占用 | 响应延迟 |
|--------------|----------|----------|
| 0.25s        | ~40%     | ~10.25s  |
| 0.5s         | ~20%     | ~10.5s   |
| 1.0s         | ~10%     | ~11s     |

### GPU 模式 (RTX 3080)

| hop_duration | CPU 占用 | GPU 占用 | 响应延迟 |
|--------------|----------|----------|----------|
| 0.25s        | ~15%     | ~10%     | ~10.25s  |
| 0.5s         | ~8%      | ~5%      | ~10.5s   |
| 1.0s         | ~5%      | ~3%      | ~11s     |

**响应延迟** = buffer_duration + hop_duration + 推理时间

## 与批处理推理的对比

| 特性 | 实时检测 | 批处理推理 (test_improved_scoring.py) |
|------|----------|---------------------------------------|
| 输入 | 麦克风/流式文件 | 完整音频文件 |
| 延迟 | ~10-11 秒 | 无要求 |
| 输出 | 持续输出 | 单次输出 |
| 用途 | 在线监控 | 离线分析 |
| 聚合 | 95th percentile | 多种策略对比 |
| 性能 | 需要优化 | 可大 batch |

## 常见问题

**Q: 为什么需要 10 秒缓冲区？**

A: 音频文件通常是 10 秒，需要足够长度才能提取完整特征并进行有效分类。

**Q: 可以减少响应延迟吗？**

A: 可以减小 buffer_duration，但会牺牲检测准确性。建议最小 5 秒。

**Q: 如何提高检测准确率？**

A:
1. 使用更好的模型（ResNet34）
2. 调整阈值
3. 增加 buffer_duration
4. 使用更密集的采样（减小 hop_duration）

**Q: 支持多通道音频吗？**

A: 当前仅支持单声道。多通道会自动转为单声道。

**Q: 可以同时监控多个设备吗？**

A: 需要运行多个实例，每个实例监控一个设备：

```bash
# 终端 1
python realtime_detection.py --checkpoint model_fan.pth --device_id 1

# 终端 2
python realtime_detection.py --checkpoint model_gearbox.pth --device_id 2
```

## 进一步改进

未来可能的改进方向：

1. **更快响应**：使用更短的时间窗口和增量特征提取
2. **更好的聚合**：使用 LSTM/Transformer 处理时序信息
3. **多设备支持**：单进程同时监控多个音频输入
4. **可视化界面**：实时显示波形和异常分数曲线
5. **告警功能**：异常时发送邮件/短信/推送通知
6. **记录保存**：自动保存异常片段用于后续分析

## 总结

实时异常检测系统提供了：

✅ 实时监控能力
✅ 灵活的参数配置
✅ 多种输入源支持
✅ 可调的灵敏度
✅ 详细的检测输出

适用于工业设备监控、质检系统、在线分析等场景。
