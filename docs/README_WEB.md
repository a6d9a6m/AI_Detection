# Audio Anomaly Detection Web Interface

这是一个本地Web界面，用于音频异常检测系统的训练、测试和实时检测。通过图形化界面操作三个主要脚本：src/train.py、src/test_improved_scoring.py 和 src/realtime_detection.py。

## 功能特点

### 1. 训练模块 (Train)
- 配置训练参数（epochs, batch size, learning rate等）
- 选择机器类型和训练数据目录
- 实时查看训练日志输出
- 训练状态显示

### 2. 测试模块 (Test)
- 选择已训练的模型checkpoint
- 运行7种不同的评分策略
- 显示AUC结果对比
- 实时查看测试日志

### 3. 实时检测模块 (Real-time Detection)
- 支持从麦克风实时检测
- 支持从音频文件流式检测
- **实时可视化显示**：
  - 当前检测状态（Running/Stopped）
  - 最新检测结果（Normal/Anomaly）
  - 异常分数
  - 预测类别和置信度
  - 实时统计信息（总检测数、异常数、异常率）
- **鲜明的视觉反馈**：
  - 正常：绿色背景 ✓
  - 异常：红色背景 🚨
  - 实时更新历史记录

## 安装步骤

### 1. 安装Web界面依赖

```bash
pip install -r requirements_web.txt
```

### 2. 确保已有基础依赖

如果还没有安装项目的基础依赖，运行：

```bash
pip install -r requirements.txt
```

## 使用方法

### 启动Web界面

```bash
python src/app.py
```

服务器将在本地启动，访问地址：**http://localhost:5000**

### 界面使用指南

#### 1. 训练模型 (Train Tab)

1. 填写机器类型（如：fan）
2. 设置训练数据目录（如：data/fan/train）
3. 配置训练参数：
   - Epochs: 训练轮数（默认150）
   - Batch Size: 批大小（默认32）
   - Learning Rate: 学习率（默认0.001）
   - Optimizer: 优化器（Adam/AdamW）
   - Scheduler: 学习率调度器
   - Random Seed: 随机种子
4. 点击"Start Training"开始训练
5. 实时查看训练输出和状态

#### 2. 测试模型 (Test Tab)

1. 点击"Refresh"刷新可用的checkpoint列表
2. 从下拉菜单选择checkpoint
3. 填写机器类型和数据目录：
   - Training Directory: 训练数据目录（用于计算统计）
   - Test Directory: 测试数据目录
4. 配置参数（可选）：
   - Patch Frames: 默认64
   - Hop Frames: 默认16（越小越精确）
5. 点击"Start Testing"开始测试
6. 查看AUC结果卡片和详细日志

#### 3. 实时检测 (Real-time Detection Tab)

**从麦克风检测：**

1. 选择checkpoint
2. Audio Source: 选择"Microphone"
3. 设置异常阈值（推荐1.5-3.0，越低越敏感）
4. 可选：设置麦克风设备ID（留空使用默认）
5. 点击"Start Detection"开始检测

**从音频文件检测：**

1. 选择checkpoint
2. Audio Source: 选择"Audio File"
3. 输入音频文件路径（如：data/fan/source_test/...）
4. 设置异常阈值
5. 点击"Start Detection"开始检测

**实时显示说明：**

- **Current Status**: 显示检测状态（Ready/Running/Stopped）
- **Last Detection**: 显示最新检测结果
  - ✓ Normal（绿色）：正常音频
  - 🚨 ANOMALY DETECTED（红色）：检测到异常
  - 显示异常分数、预测类别、置信度
- **Statistics**: 实时统计信息
  - Total: 总检测次数
  - Anomalies: 异常检测次数
  - Rate: 异常率百分比
- **Detection History**: 滚动显示历史记录

**停止检测：**

点击"Stop Detection"按钮即可停止实时检测。

## 目录结构

```
baseline/
├── src/
│   ├── app.py                              # Flask后端服务器
│   ├── realtime_detection_websocket.py    # 支持WebSocket的实时检测脚本
│   ├── train.py                            # 训练脚本
│   ├── test_improved_scoring.py           # 测试脚本
│   └── realtime_detection.py              # 原始实时检测脚本
├── requirements_web.txt                # Web界面依赖
├── templates/
│   └── index.html                      # 前端HTML页面
├── static/
│   ├── style.css                       # CSS样式
│   └── app.js                          # JavaScript前端逻辑
├── checkpoints/                        # 模型检查点目录
├── results_step1/                      # 测试结果目录
└── data/                               # 数据目录
    └── fan/
        ├── train/                      # 训练数据
        └── source_test/                # 测试数据
```

## 技术架构

- **后端**: Flask + Flask-SocketIO（支持WebSocket实时通信）
- **前端**: HTML + CSS + JavaScript + Socket.IO
- **实时通信**: WebSocket（用于实时检测数据传输）
- **进程管理**: Python subprocess（后台运行训练/测试脚本）

## 特色功能

### 实时检测的视觉增强

1. **动态状态指示器**
   - 使用脉冲动画显示运行状态
   - 颜色编码（绿色=正常，红色=异常，灰色=就绪）

2. **检测结果实时更新**
   - 每0.5秒更新一次（可配置）
   - 显示异常分数和预测类别
   - 置信度百分比显示

3. **滚动历史记录**
   - 时间戳标注
   - 颜色区分正常/异常
   - 自动滚动到最新

4. **实时统计面板**
   - 总检测数
   - 异常检测数
   - 实时计算异常率

## 注意事项

1. **端口占用**: 默认使用5000端口，如被占用可在app.py中修改
2. **路径设置**: 所有文件路径必须正确，相对于项目根目录
3. **模型兼容**: 确保checkpoint与脚本版本兼容
4. **麦克风权限**: 实时检测需要麦克风访问权限
5. **性能**: 实时检测时建议使用GPU（CUDA）以获得更好性能

## 故障排除

### 问题1: 无法启动服务器

```bash
# 检查端口是否被占用
netstat -ano | findstr :5000
# 或修改src/app.py中的端口号
socketio.run(app, host='0.0.0.0', port=5001, debug=True)
```

### 问题2: Checkpoint未显示

1. 确保checkpoints目录存在
2. 确保.pth文件在checkpoints目录中
3. 点击"Refresh"按钮刷新列表

### 问题3: 实时检测无输出

1. 检查checkpoint路径是否正确
2. 确保麦克风已连接并授权
3. 查看浏览器控制台（F12）的错误信息

### 问题4: WebSocket连接失败

1. 检查Flask-SocketIO是否正确安装
2. 确保浏览器支持WebSocket
3. 检查防火墙设置

## 性能优化建议

1. **训练时**: 使用GPU，设置合适的batch_size
2. **测试时**: 使用较小的hop_frames获得更高精度
3. **实时检测时**:
   - 使用GPU加速
   - 调整buffer_duration和hop_duration平衡延迟和精度
   - 降低阈值提高敏感度

## 开发者信息

此Web界面是对原始命令行脚本的图形化封装，保留了所有原始功能并增加了实时可视化能力。

### 核心改进

1. **realtime_detection_websocket.py**:
   - 添加JSON输出格式
   - 添加预测类别和置信度信息
   - 输出重定向到stdout（日志到stderr）
   - 支持Flask后端读取

2. **实时通信架构**:
   - Flask-SocketIO处理WebSocket连接
   - 子进程输出通过管道传输
   - JavaScript实时解析JSON数据
   - 动态更新DOM元素

3. **响应式设计**:
   - 支持桌面和移动设备
   - 自适应布局
   - 现代化UI设计

## 许可证

与原项目保持一致。

## 联系方式

如有问题或建议，请参考原项目文档。
