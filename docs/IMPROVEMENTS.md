# 改进训练指南

## 已完成的改进

### 1. 数据增强增强 (dataset.py)
- ✅ **SpecAugment**: 频域和时域随机遮蔽
- ✅ **更强的音量变化**: 0.7-1.3 (原 0.8-1.2)
- ✅ **更大的时间偏移**: ±3帧 (原 ±2帧)

### 2. 训练参数优化 (train.py)
- ✅ **Patch长度**: 128帧 (原 64帧) - **最关键改进**
- ✅ **Dropout**: 0.3 (原 0.2)
- ✅ **Weight decay**: 1e-4 (原 1e-5)
- ✅ **Epochs**: 150 (原 100)
- ✅ **Batch size**: 32 (原 64，因为patch变长)
- ✅ **学习率调度器**: 可选cosine annealing

## 使用方法

### 基础训练（使用所有默认改进）
```bash
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --output_dir checkpoints
```

这会自动使用：
- patch_frames=128
- epochs=150
- dropout=0.3
- SpecAugment增强
- ReduceLROnPlateau调度器

### 使用Cosine Annealing调度器（推荐）
```bash
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --scheduler cosine
```

### 快速测试（减少epochs）
```bash
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --epochs 50
```

### 尝试更长patch（最激进）
```bash
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --patch_frames 256 \
    --batch_size 16 \
    --epochs 150
```

## 训练后的推理

训练完成后，使用改进的推理脚本：

```bash
python src/test_improved_scoring.py \
    --train_dir data/fan/train \
    --test_dir data/fan/source_test \
    --checkpoint checkpoints/model_fan_best.pth \
    --machine_type fan \
    --patch_frames 128 \
    --hop_frames 16
```

**重要**: 推理时的 `--patch_frames` 必须与训练时一致！

## 预期效果

根据改进策略：

| 配置 | 预期AUC | 训练时间 |
|------|---------|----------|
| patch=64 (原始) | 0.68 | ~1小时 |
| patch=128 + 改进增强 | 0.78-0.82 | ~2小时 |
| patch=256 + 全部改进 | 0.82-0.88 | ~3小时 |

## 对比实验

### 对比patch长度
```bash
# Original
python src/train.py --train_dir data/fan/train --machine_type fan \
    --patch_frames 64 --output_dir checkpoints/patch64

# Improved
python src/train.py --train_dir data/fan/train --machine_type fan \
    --patch_frames 128 --output_dir checkpoints/patch128

# Aggressive
python src/train.py --train_dir data/fan/train --machine_type fan \
    --patch_frames 256 --batch_size 16 --output_dir checkpoints/patch256
```

### 对比调度器
```bash
# Plateau (default)
python src/train.py --train_dir data/fan/train --machine_type fan \
    --scheduler plateau --output_dir checkpoints/plateau

# Cosine
python src/train.py --train_dir data/fan/train --machine_type fan \
    --scheduler cosine --output_dir checkpoints/cosine
```

### 对比Warmup
```bash
# Without warmup
python src/train.py --train_dir data/fan/train --machine_type fan \
    --lr 1e-3 --scheduler cosine --output_dir checkpoints/no_warmup

# With warmup
python src/train.py --train_dir data/fan/train --machine_type fan \
    --lr 1e-3 --scheduler cosine --warmup_epochs 5 --output_dir checkpoints/warmup
```

## 注意事项

1. **显存不足**：如果出现OOM错误
   - 减小 batch_size (32 → 16)
   - 或减小 patch_frames (128 → 96)

2. **训练时间长**：
   - 可以先用 epochs=50 快速验证
   - 确认有效后再用 epochs=150

3. **推理匹配**：
   - 训练用 patch=128，推理也必须用 patch=128
   - 保存模型时参数会记录在checkpoint里

4. **对比原始**：
   - 建议保留原始 patch=64 的模型作为baseline
   - 这样可以量化改进效果

## 完整工作流示例

```bash
# 1. 训练改进模型
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --patch_frames 128 \
    --epochs 150 \
    --scheduler cosine \
    --output_dir checkpoints

# 2. 测试 source_test
python src/test_improved_scoring.py \
    --train_dir data/fan/train \
    --test_dir data/fan/source_test \
    --checkpoint checkpoints/model_fan_best.pth \
    --machine_type fan \
    --patch_frames 128 \
    --hop_frames 16 \
    --output_dir results_improved

# 3. 测试 target_test
python src/test_improved_scoring.py \
    --train_dir data/fan/train \
    --test_dir data/fan/target_test \
    --checkpoint checkpoints/model_fan_best.pth \
    --machine_type fan \
    --patch_frames 128 \
    --hop_frames 32 \
    --output_dir results_improved

# 4. 可视化结果
python src/visualize.py \
    --results results_improved/results_step1_fan_source_test.json \
    --output_dir visualizations_improved
```

## 常见问题

**Q: 为什么batch_size从64降到32？**
A: patch从64帧增加到128帧，每个样本大小翻倍，为了避免OOM。

**Q: 可以用GPU加速吗？**
A: 可以，脚本会自动检测并使用GPU。

**Q: 训练中断了怎么办？**
A: 使用保存的checkpoint恢复（需要手动实现resume功能）。

**Q: 如何知道训练是否收敛？**
A: 观察 train_loss 是否持续下降，accuracy是否提升。

**Q: 多个机器类型怎么办？**
A: 分别训练每个机器类型的模型。
