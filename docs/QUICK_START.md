# 快速启动指南

## 第一次使用

### 1. 安装依赖

```bash
pip install -r requirements_web.txt
```

### 2. 启动Web界面

**方式1：双击启动（Windows）**
```
双击 start_web_ui.bat 文件
```

**方式2：命令行启动**
```bash
python src/app.py
```

### 3. 访问界面

在浏览器中打开：**http://localhost:5000**

## 快速测试流程

### 训练模型（Train标签页）
1. Machine Type: `fan`
2. Training Directory: `data/fan/train`
3. 点击 "Start Training"
4. 等待训练完成（可在输出框查看进度）

### 测试模型（Test标签页）
1. 点击"Refresh"刷新checkpoint列表
2. 选择刚训练的checkpoint
3. Machine Type: `fan`
4. Training Directory: `data/fan/train`
5. Test Directory: `data/fan/source_test`
6. 点击 "Start Testing"
7. 查看AUC结果

### 实时检测（Real-time Detection标签页）

**方式1：从麦克风**
1. 选择checkpoint
2. Audio Source: `Microphone`
3. Device: 选择CUDA或CPU
4. Microphone Device ID: 留空使用默认（可选）
5. ✅ **Enable Playback**: 勾选后可听到检测音频（实时外放）
6. Anomaly Threshold: `2.0`
7. Patch Frames: `64`
8. Buffer Duration: `10.0`秒（缓冲区长度）
9. Hop Duration: `0.5`秒（检测间隔）
10. 点击 "Start Detection"
11. 对着麦克风播放音频
12. 观察实时检测结果（可同时听到音频）

**方式2：从文件**
1. 选择checkpoint
2. Audio Source: `Audio File`
3. Audio File Path: `data/fan/source_test/section_00_source_test_anomaly_0000.wav`
4. Device: 选择CUDA或CPU
5. Realtime Mode: 勾选表示模拟实时播放（取消勾选则快速处理）
6. ✅ **Enable Playback**: 勾选后可听到检测音频（播放文件音频）
7. Anomaly Threshold: `2.0`
8. Patch Frames: `64`
9. Buffer Duration: `5.0`秒（文件模式可以设短一些）
10. Hop Duration: `0.5`秒
11. 点击 "Start Detection"
12. 观察检测结果（可同时听到音频）

## 实时检测界面说明

### Current Status卡片
- **Ready**: 准备就绪（灰色）
- **Running**: 正在检测（绿色，带脉冲动画）
- **Stopped**: 已停止（红色）

### Last Detection卡片
- **✓ Normal**: 检测到正常音频（绿色背景）
- **🚨 ANOMALY DETECTED**: 检测到异常（红色背景）
- 显示异常分数、预测类别、置信度

### Statistics卡片
- **Total**: 总检测次数
- **Anomalies**: 异常检测次数
- **Rate**: 异常率百分比

### Detection History
- 滚动显示所有检测记录
- 绿色：正常
- 红色：异常
- 蓝色：系统信息

## 常见问题

**Q: 如何停止训练/测试？**
A: 点击对应的"Stop"按钮

**Q: 如何停止实时检测？**
A: 点击"Stop Detection"按钮

**Q: 找不到checkpoint？**
A: 确保.pth文件在checkpoints目录中，然后点击"Refresh"

**Q: 实时检测没有输出？**
A: 检查checkpoint路径、音频源设置、麦克风权限

**Q: 如何调整检测灵敏度？**
A: 降低Anomaly Threshold值（如从2.0改为1.5）会提高敏感度

## 性能建议

- 使用GPU（CUDA）进行训练和检测
- 训练时batch_size根据显存调整
- 实时检测时threshold建议1.5-3.0之间
- 测试时hop_frames越小精度越高（但速度越慢）

## 技术支持

详细文档请查看 `README_WEB.md`
