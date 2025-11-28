# 随机种子使用指南

## ✅ 已添加随机种子支持

随机种子可以确保训练过程完全可重复，方便进行对比实验。

## 功能说明

### 1. 设置的随机源
```python
- Python random
- NumPy random
- PyTorch CPU random
- PyTorch CUDA random (单卡和多卡)
- CuDNN 确定性行为
```

### 2. 影响范围
- 数据增强的随机性
- 权重初始化
- Dropout 的随机性
- 数据加载的顺序（shuffle）
- 所有其他随机操作

## 使用方法

### 基础用法
```bash
# 使用固定种子
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --seed 42

# 不设置种子（每次随机）
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan
```

### 对比实验（推荐）
```bash
# 实验1：原始配置
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --patch_frames 64 \
    --epochs 150 \
    --seed 42 \
    --output_dir checkpoints/exp1

# 实验2：修改某个参数
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --patch_frames 128 \
    --epochs 150 \
    --seed 42 \
    --output_dir checkpoints/exp2

# 使用相同 seed，只有参数变化的影响会体现
```

### 多次运行取平均（推荐科研）
```bash
# 不同种子运行多次
for seed in 42 123 456 789 2024
do
    python src/train.py \
        --train_dir data/fan/train \
        --machine_type fan \
        --seed $seed \
        --output_dir checkpoints/seed_${seed}
done

# 然后对结果求平均和方差
```

## 推荐种子值

常用的"幸运数字"：
- `42` - 《银河系漫游指南》，ML社区最爱
- `0` - 简单直接
- `2024` - 当前年份
- `123` - 连续数字
- `1234567` - 更大的随机性

## 注意事项

### 1. 性能影响
```
启用确定性行为会略微降低训练速度（~5%）
原因：cudnn.deterministic=True 禁用了某些优化
```

### 2. 完全可重复的条件
要保证完全相同的结果，需要：
- ✅ 相同的随机种子
- ✅ 相同的硬件（GPU型号）
- ✅ 相同的CUDA/PyTorch版本
- ✅ 相同的参数配置
- ✅ 相同的数据

### 3. 查看使用的种子
训练时会打印：
```
Random seed set to: 42
============================================================
IMPROVED Training Configuration:
============================================================
Random seed: 42
...
```

种子也会保存在 checkpoint 中：
```python
checkpoint = torch.load('model_best.pth')
seed = checkpoint['args']['seed']
print(f"This model was trained with seed: {seed}")
```

## 实验最佳实践

### 1. 单次实验（快速验证）
```bash
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --seed 42
```

### 2. 对比实验（比较方法）
```bash
# 方法A
python src/train.py --seed 42 --dropout_rate 0.2 --output_dir exp_a

# 方法B
python src/train.py --seed 42 --dropout_rate 0.3 --output_dir exp_b

# 相同seed，差异只来自参数变化
```

### 3. 稳健性验证（发论文标准）
```bash
#!/bin/bash
# 运行5次不同种子
for seed in 42 123 456 789 2024
do
    python src/train.py \
        --train_dir data/fan/train \
        --machine_type fan \
        --patch_frames 64 \
        --epochs 200 \
        --seed $seed \
        --output_dir checkpoints/robust_seed${seed}

    # 评估
    python src/test_improved_scoring.py \
        --checkpoint checkpoints/robust_seed${seed}/model_fan_best.pth \
        --test_dir data/fan/source_test \
        --output_dir results/robust_seed${seed}
done

# 结果分析
python src/analyze_results.py --results_dir results/
```

## 示例输出

### 有种子
```
Random seed set to: 42
Using device: cuda
============================================================
IMPROVED Training Configuration:
============================================================
Random seed: 42
Patch frames: 64 (original: 64)
...
```

### 无种子
```
Using device: cuda
============================================================
IMPROVED Training Configuration:
============================================================
Random seed: None (random)
Patch frames: 64 (original: 64)
...
```

## 调试技巧

#### 验证可重复性
```bash
# 运行两次相同配置
python src/train.py --seed 42 --output_dir run1
python src/train.py --seed 42 --output_dir run2

# 比较结果是否相同
# 检查loss曲线是否完全一致
python src/compare_runs.py run1/history_fan.json run2/history_fan.json
```

### 检查随机性来源
```bash
# 如果结果仍然不一致，可能是：
# 1. 数据加载有外部随机性
# 2. GPU浮点运算误差累积
# 3. 使用了外部不确定的操作（如时间戳）
```

## 常见问题

**Q: 不设置seed会怎样？**
A: 每次训练结果都会略有不同，通常差异在 ±0.01 AUC 范围内。

**Q: 使用seed会影响性能吗？**
A: 略微影响训练速度（~5%），但不影响最终模型性能。

**Q: 为什么两次运行结果还是有细微差异？**
A: GPU浮点运算可能有微小误差，但差异应该很小（< 0.001）。

**Q: 推荐用什么seed？**
A:
- 快速实验：42（惯例）
- 对比实验：任意固定值，但所有实验用同一个
- 稳健性验证：多个不同的seed（如42, 123, 456, 789, 2024）

**Q: seed保存在哪里？**
A: 保存在 checkpoint 的 `args` 字段中，可以用以下代码读取：
```python
checkpoint = torch.load('model_best.pth')
print(checkpoint['args']['seed'])
```

## 推荐工作流

```bash
# 1. 初步实验（用固定seed快速验证）
python src/train.py --seed 42 --epochs 50

# 2. 找到好的配置后，多seed验证
for seed in 42 123 456
do
    python src/train.py --seed $seed --epochs 200
done

# 3. 报告结果时使用 mean ± std
# AUC: 0.725 ± 0.008 (n=3)
```
