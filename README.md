# DCASE2021 Task2 Baseline 2

严格复现 DCASE2021 Task2 Baseline 2 的训练与推理系统，并支持多种 backbone 增强。

## 🆕 新功能

### 实时异常检测 ⭐
- ✅ **麦克风实时监控** - 从麦克风实时捕获音频并检测异常
- ✅ **流式文件检测** - 模拟实时播放音频文件并检测
- ✅ **滑动窗口检测** - 使用环形缓冲区持续监测
- ✅ **即时输出** - 实时显示异常分数和状态

```bash
# 从麦克风实时检测
python src/realtime_detection.py --checkpoint checkpoints/model_fan_best.pth --source microphone --threshold 2.0

# 从音频文件流式检测
python src/realtime_detection.py --checkpoint checkpoints/model_fan_best.pth --source file --audio_file test.wav --threshold 2.0
```

详见 **REALTIME_DETECTION.md**

### 多 Backbone 支持
- ✅ **MobileNetV2** - 原始轻量级模型（2.2M 参数）
- ✅ **ResNet18** - 更强模型（11M 参数）
- ✅ **ResNet34** - 最强推荐（21M 参数，提升 2-3% AUC）

使用新的 `src/train_test.py` 脚本：
```bash
# 训练 ResNet34
python src/train_test.py train --backbone resnet34 --train_dir data/fan/train --machine_type fan

# 测试
python src/train_test.py test --checkpoint checkpoints/model_fan_best.pth --test_dir data/fan/source_test
```

详见 **RESNET_GUIDE.md**

## 系统概述

本项目实现了基于 **MobileNetV2** 的异常声音检测系统，通过训练一个 **section 分类器**（仅使用正常数据），利用分类不确定性进行异常检测。

### 核心特性

- **特征**：log-Mel 频谱图（128 bins, 64ms window, 32ms hop）
- **模型**：MobileNetV2（第一层改为单通道输入）
- **训练**：仅使用正常样本进行 section ID 分类
- **推理**：通过 softmax 不确定性计算异常分数
- **异常分数**：
  - Score A: `1 - max(softmax)`
  - Score B: `entropy`
  - Combined: 标准化后的加权组合

## 项目结构

```
baseline/
├── src/                 # 源代码目录
│   ├── features.py          # log-Mel 特征提取
│   ├── model.py            # MobileNetV2 模型定义
│   ├── backbones.py        # 多 backbone 支持（MobileNet/ResNet）
│   ├── dataset.py          # 数据集加载器
│   ├── train.py            # 训练脚本
│   ├── train_test.py       # 统一训练测试脚本（支持多 backbone）
│   ├── inference.py        # 推理和异常检测脚本
│   ├── test_improved_scoring.py  # 改进的评分策略
│   ├── realtime_detection.py     # ⭐ 实时异常检测
│   ├── visualize.py        # 结果可视化脚本
│   ├── test.py             # 快速测试脚本
│   ├── app.py              # Web应用主程序
│   └── web/                # Web界面相关文件
│       ├── templates/      # HTML模板
│       └── static/         # CSS和JavaScript文件
├── tests/              # 测试脚本目录
│   ├── test_web_connection.py  # Web连接测试
│   └── diagnose_web_env.py      # Web环境诊断
├── requirements.txt    # 依赖包
├── run_train.sh/bat    # 批量训练脚本
├── run_eval.sh/bat     # 批量评估脚本
├── run_visualize.sh/bat # 批量可视化脚本
├── run_workflow.sh/bat # 完整工作流
├── run_resnet34.sh/bat # ResNet34 专用脚本
├── test_realtime.sh/bat # ⭐ 实时检测测试脚本
└── data/              # 数据目录
    ├── fan/
    │   ├── train/
    │   ├── source_test/
    │   └── target_test/
    └── gearbox/
        ├── train/
        ├── source_test/
        └── target_test/
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 完整工作流程（一键运行）

**Linux/Mac:**
```bash
bash run_workflow.sh
```

**Windows:**
```cmd
run_workflow.bat
```

这个脚本会自动完成：
1. 训练模型
2. 在测试集上评估
3. 生成可视化结果

### 详细使用方法

## 使用方法

### 1. 训练模型

训练 fan 数据：

```bash
python src/train.py \
    --train_dir data/fan/train \
    --machine_type fan \
    --output_dir checkpoints \
    --batch_size 64 \
    --epochs 100 \
    --lr 1e-3
```

训练 gearbox 数据：

```bash
python src/train.py \
    --train_dir data/gearbox/train \
    --machine_type gearbox \
    --output_dir checkpoints \
    --batch_size 64 \
    --epochs 100 \
    --lr 1e-3
```

### 2. 推理和评估

评估 source_test：

```bash
python src/inference.py \
    --train_dir data/fan/train \
    --test_dir data/fan/source_test \
    --checkpoint checkpoints/model_fan_best.pth \
    --machine_type fan \
    --output_dir results \
    --aggregation max \
    --alpha 0.5
```

评估 target_test：

```bash
python src/inference.py \
    --train_dir data/fan/train \
    --test_dir data/fan/target_test \
    --checkpoint checkpoints/model_fan_best.pth \
    --machine_type fan \
    --output_dir results \
    --aggregation percentile \
    --percentile 95 \
    --alpha 0.5
```

或者在 Windows 上运行：
```cmd
run_eval.bat
```

### 3. 结果可视化

可视化单个结果文件（显示所有评分类型）：

```bash
python src/visualize.py \
    --results results/results_fan_source_test.json \
    --output_dir visualizations \
    --score_type all
```

可视化特定评分类型：

```bash
python src/visualize.py \
    --results results/results_fan_source_test.json \
    --output_dir visualizations \
    --score_type combined
```

比较多个实验结果：

```bash
python src/visualize.py \
    --compare results/results_fan_source_test.json results/results_gearbox_source_test.json \
    --output_dir visualizations
```

或者使用批处理脚本可视化所有结果：

**Linux/Mac:**
```bash
bash run_visualize.sh
```

**Windows:**
```cmd
run_visualize.bat
```

#### 可视化内容

生成的可视化包含以下内容：

1. **分数分布图** - 正常样本 vs 异常样本的分数分布
2. **ROC 曲线** - 包含 AUC 值和最优阈值
3. **混淆矩阵** - 分类结果的混淆矩阵
4. **预测结果图** - 每个样本的预测，用颜色标注正确/错误
   - 🟢 绿色圆点：正确分类（TP/TN）
   - ❌ 红色/橙色叉号：错误分类（FP/FN）
5. **Section 性能** - 按 section ID 分组的准确率
6. **性能摘要表** - 详细指标（准确率、精确率、召回率、F1）

## 参数说明

### 特征参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--sr` | 16000 | 采样率 (Hz) |
| `--n_mels` | 128 | Mel bins 数量 |
| `--n_fft` | 1024 | FFT 窗口大小（64ms @ 16kHz） |
| `--hop_length` | 512 | 帧移（32ms @ 16kHz） |
| `--fmin` | 0 | 最小频率 (Hz) |
| `--fmax` | 8000 | 最大频率 (Hz) |
| `--patch_frames` | 64 | 每个 patch 的帧数 |

### 训练参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--batch_size` | 64 | 批次大小 |
| `--epochs` | 100 | 训练轮数 |
| `--lr` | 1e-3 | 学习率 |
| `--weight_decay` | 1e-5 | 权重衰减 |
| `--dropout_rate` | 0.2 | Dropout 比率 |
| `--augmentation` | True | 数据增强 |

### 推理参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--alpha` | 0.5 | 分数组合权重（0-1） |
| `--aggregation` | max | 聚合方法：max/percentile/mean |
| `--percentile` | 95 | 百分位数（用于 percentile 聚合） |
| `--hop_frames` | 32 | 推理时 patch 间的帧移 |

## 技术细节

### 1. 特征提取

```python
# log-Mel 参数
sr = 16000          # 采样率
n_mels = 128        # Mel bins
n_fft = 1024        # 64ms window @ 16kHz
hop_length = 512    # 32ms hop @ 16kHz
fmin = 0            # 最小频率
fmax = 8000         # 最大频率

# 转换为 log 尺度
log_mel = log(mel_spectrogram + 1e-6)
```

### 2. 模型结构

- **Backbone**: MobileNetV2
- **输入**: (1, 128, 64) - 单通道 log-Mel patch
- **输出**: (num_classes,) - section 分类 logits
- **修改**: 第一层卷积改为 `Conv2d(1, 32, ...)`

### 3. 训练策略

- **数据**: 仅使用正常样本
- **任务**: Section ID 分类（K 类）
- **损失**: CrossEntropyLoss
- **优化器**: Adam (lr=1e-3, weight_decay=1e-5)
- **调度器**: ReduceLROnPlateau

### 4. 异常分数计算

对每个音频 patch：

```python
# 获取 softmax 概率
probs = softmax(logits)

# Score A: 最大概率的倒数
score_a = 1 - max(probs)

# Score B: 熵
score_b = -sum(probs * log(probs))

# Z-score 标准化（基于训练集统计）
score_a_z = (score_a - mean_a) / std_a
score_b_z = (score_b - mean_b) / std_b

# 组合分数
score_combined = alpha * score_a_z + (1 - alpha) * score_b_z
```

对整个音频文件：

```python
# 聚合所有 patch 的分数
if aggregation == 'max':
    final_score = max(patch_scores)
elif aggregation == 'percentile':
    final_score = percentile(patch_scores, 95)
elif aggregation == 'mean':
    final_score = mean(patch_scores)
```

### 5. 评估指标

- **AUC**: Area Under ROC Curve
- 分别计算 Score A、Score B 和 Combined Score 的 AUC

## 输出文件

### 训练输出

- `checkpoints/model_{machine_type}_best.pth` - 最佳模型
- `checkpoints/model_{machine_type}_epoch{N}.pth` - 周期检查点
- `checkpoints/history_{machine_type}.json` - 训练历史

### 推理输出

- `results/stats_{machine_type}.json` - 正常数据统计
- `results/results_{machine_type}_{test_type}.json` - 详细结果
- `results/scores_{machine_type}_{test_type}.csv` - 分数表格

## 数据格式

音频文件命名格式：

```
section_{XX}_source_train_normal_{XXXX}_strength_{X}_ambient.wav
section_{XX}_source_test_normal_{XXXX}.wav
section_{XX}_source_test_anomaly_{XXXX}.wav
```

其中：
- `section_{XX}`: section ID (00, 01, 02, ...)
- `normal/anomaly`: 正常或异常样本
- `source/target`: 源域或目标域

## 论文参考

本实现基于 DCASE2021 Challenge Task2 Baseline 2:

- **任务**: Unsupervised Anomalous Sound Detection
- **方法**: Section-based classification with uncertainty
- **论文**: DCASE2021 Challenge Technical Report

## 注意事项

1. **仅使用正常数据训练** - 训练集中不包含异常样本
2. **Section 分类** - 模型学习区分不同的 section ID
3. **不确定性检测** - 异常样本会产生更高的分类不确定性
4. **标准化** - 使用训练集统计进行 Z-score 标准化很重要
5. **聚合策略** - max 或 95th percentile 通常效果较好

## License

MIT License
