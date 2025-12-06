# 音频异常检测系统

基于深度学习的工业设备音频异常检测系统，支持模型训练、实时检测、可视化分析和完整的商业化API服务。

##  快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动Web服务器

```bash
python server.py
```

服务器将在 `http://localhost:5000` 启动

### 访问Web界面

打开浏览器访问：
- 主页: `http://localhost:5000/index.html`
- 登录: `http://localhost:5000/login.html`
- 控制台: `http://localhost:5000/dashboard.html`

默认账号: `admin / admin123`

##  项目结构

```
baseline/
├── src/                          #  核心：模型训练预测
│   ├── train.py                 # 训练脚本
│   ├── predict.py               # 推理脚本
│   ├── dataset.py               # 数据集加载
│   ├── features.py              # 特征提取
│   ├── model.py                 # 模型定义
│   ├── backbones.py             # 骨干网络
│   ├── viz.py                   # 可视化工具
│   ├── realtime.py              # 实时检测
│   ├── paths.py                 # 路径配置
│   └── results/                 #  输出结果
│       ├── models/              # 训练好的模型(.pth)
│       ├── checkpoints/         # 训练checkpoint
│       ├── visualizations/      # 可视化图表(.png)
│       ├── reports/             # 生成的报告
│       └── features/            # 提取的特征(.npy)
│
├── web/                          #  Web服务
│   ├── services/                # 服务层
│   │   ├── api.py              # RESTful API服务
│   │   ├── training.py         # 训练管理服务
│   │   ├── report.py           # 报告生成服务
│   │   └── db.py               # 数据库模型
│   ├── templates/               # 前端HTML模板
│   │   ├── index.html
│   │   ├── login.html
│   │   └── dashboard.html
│   └── static/                  # 静态资源
│       ├── app.js
│       ├── dashboard.js
│       ├── main.css
│       └── style.css
│
├── tests/                        # 测试
├── data/                         # 数据目录
├── server.py                     # ⚡ 服务器启动脚本
├── database.db                   # SQLite数据库
├── API_DOCUMENTATION.md          # 📖 完整API文档
└── PROGRESS.md                   # 开发进度文档
```

##  核心功能

### 1. 模型训练

```bash
cd src
python train.py \
  --train_dir ../data/fan/train \
  --machine_type fan \
  --epochs 50 \
  --batch_size 32
```

### 2. 推理预测

```bash
cd src
python predict.py \
  --checkpoint ../results/models/model_fan_best.pth \
  --test_dir ../data/fan/test \
  --machine_type fan
```

### 3. 实时检测

```bash
cd src
python realtime.py \
  --checkpoint ../results/models/model_fan_best.pth \
  --machine_type fan \
  --audio_file test.wav
```

##  RESTful API

完整API文档请查看：[API_DOCUMENTATION.md](API_DOCUMENTATION.md)

### 快速示例

```python
import requests

# 登录
session = requests.Session()
session.post('http://localhost:5000/api/login', json={
    'username': 'admin',
    'password': 'admin123'
})

# 上传音频
with open('audio.wav', 'rb') as f:
    response = session.post('http://localhost:5000/api/voiceprints',
        files={'audio_file': f},
        data={'machine_type': 'fan'}
    )

# 开始训练
response = session.post('http://localhost:5000/api/training/start', json={
    'config': {
        'machine_type': 'fan',
        'train_dir': 'data/fan/train',
        'epochs': 50
    }
})

# 模型可视化
response = session.get('http://localhost:5000/api/models/1/visualize')

# 模型比较
response = session.post('http://localhost:5000/api/models/compare', json={
    'model_ids': [1, 2, 3]
})
```

##  主要特性

- ✅ **70+ RESTful API端点** - 完整的Web服务
- ✅ **会话认证 + API密钥** - 双重认证机制
- ✅ **多租户架构** - 支持数据隔离
- ✅ **模型训练与评估** - 支持真实数据训练
- ✅ **特征提取中断恢复** - Checkpoint机制
- ✅ **模型可视化与比较** - 训练曲线、性能对比
- ✅ **实时检测** - WebSocket支持
- ✅ **报告生成** - PDF/Excel/Word多格式
- ✅ **计费系统** - 资源使用追踪
- ✅ **审计日志** - 完整操作记录

##  测试

```bash
python tests/test_integration_full.py
```

39个集成测试用例，覆盖所有核心功能。

## 📖 文档

- [API完整文档](API_DOCUMENTATION.md) - 70+ API端点详细说明
- [开发进度](PROGRESS.md) - 功能清单和更新记录
- [集成测试](docs/integration_test_cases.md) - 测试用例文档

## 🔧 技术栈

### 后端
- **Flask** - Web框架
- **PyTorch** - 深度学习
- **SQLite** - 数据库
- **librosa** - 音频处理

### 前端
- **HTML5 + CSS3** - 界面
- **JavaScript** - 交互
- **Material Icons** - 图标

### 报告生成
- **reportlab** - PDF
- **openpyxl** - Excel
- **python-docx** - Word

##  Web界面特性

- ✅ 现代化蓝色主题
- ✅ 响应式设计
- ✅ 拖拽上传
- ✅ 实时数据更新
- ✅ Material Icons图标

##  更新日志

### v1.1 (2025-12-06) 🆕
- ✨ 重构项目结构，采用简洁命名
- ✨ 添加模型可视化功能（训练曲线）
- ✨ 添加模型比较功能（性能对比）
- ✨ 实现特征提取中断恢复（Checkpoint）
- ✨ 整合web资源到根目录
- ✨ 完整的API文档（70+端点）
- 🔧 统一结果输出到`src/results/`

### v1.0 (2025-11-28)
- 🎉 初始版本发布
- ✅ 完整的训练和推理功能
- ✅ 70+个API端点
- ✅ 集成测试覆盖

##  支持

- GitHub Issues
- Email: support@example.com

##  许可证

MIT License

---

**© 2025 Audio Anomaly Detection System**
