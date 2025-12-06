# API Documentation
# 音频异常检测系统 API 文档

**Version:** 1.1
**Base URL:** `http://localhost:5000`
**Last Updated:** 2025-12-06

## 目录

- [快速开始](#快速开始)
- [认证](#认证)
- [用户管理](#用户管理)
- [声纹数据管理](#声纹数据管理)
- [特征提取](#特征提取)
- [模型训练](#模型训练)
- [模型评估](#模型评估)
- [模型可视化与比较](#模型可视化与比较)
- [推理预测](#推理预测)
- [报告生成](#报告生成)
- [租户管理](#租户管理)
- [商业化服务](#商业化服务)

---

## 快速开始

### 启动服务器

```bash
python server.py
```

服务器将在 `http://0.0.0.0:5000` 启动

### 项目结构

```
baseline/
├── src/                    # 核心：模型训练预测
│   ├── train.py           # 训练脚本
│   ├── predict.py         # 推理脚本
│   ├── dataset.py         # 数据集
│   ├── features.py        # 特征提取
│   ├── model.py          # 模型定义
│   ├── backbones.py      # 骨干网络
│   ├── viz.py            # 可视化
│   ├── realtime.py       # 实时检测
│   ├── paths.py          # 路径配置
│   └── results/          # 输出结果
│       ├── models/       # 训练好的模型
│       ├── checkpoints/  # 训练checkpoint
│       ├── visualizations/ # 可视化图表
│       ├── reports/      # 生成的报告
│       └── features/     # 提取的特征
├── web/                   # Web服务
│   ├── services/         # 服务层
│   │   ├── api.py       # API服务
│   │   ├── training.py  # 训练服务
│   │   ├── report.py    # 报告服务
│   │   └── db.py        # 数据库模型
│   ├── templates/
│   └── static/
├── server.py             # 启动脚本
└── database.db           # SQLite数据库
```

---

## 认证

### 1. 用户注册

**Endpoint:** `POST /api/register`

**描述:** 注册新用户

**Request Body:**
```json
{
  "username": "user123",
  "password": "password123",
  "email": "user@example.com",
  "full_name": "张三"
}
```

**Response:** `201 Created`
```json
{
  "message": "User registered successfully",
  "user_id": 1
}
```

---

### 2. 用户登录

**Endpoint:** `POST /api/login`

**描述:** 用户登录，获取session

**Request Body:**
```json
{
  "username": "user123",
  "password": "password123"
}
```

**Response:** `200 OK`
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "user123",
    "email": "user@example.com",
    "role": "user"
  }
}
```

---

### 3. 用户登出

**Endpoint:** `POST /api/logout`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "message": "Logout successful"
}
```

---

### 4. 获取当前用户信息

**Endpoint:** `GET /api/me`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "user123",
  "email": "user@example.com",
  "full_name": "张三",
  "role": "user",
  "tenant_id": 1,
  "created_at": "2025-01-01 00:00:00"
}
```

---

## 用户管理

### 5. 列出所有用户

**Endpoint:** `GET /api/users`

**认证:** Required (Admin)

**Query Parameters:**
- `page` (int, optional): 页码，默认1
- `per_page` (int, optional): 每页数量，默认20

**Response:** `200 OK`
```json
{
  "users": [
    {
      "id": 1,
      "username": "user123",
      "email": "user@example.com",
      "role": "user",
      "created_at": "2025-01-01 00:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20
}
```

---

### 6. 更新用户信息

**Endpoint:** `PUT /api/users/<user_id>`

**认证:** Required (Admin or Self)

**Request Body:**
```json
{
  "email": "newemail@example.com",
  "full_name": "新名字",
  "role": "admin"
}
```

**Response:** `200 OK`
```json
{
  "message": "User updated successfully"
}
```

---

### 7. 删除用户

**Endpoint:** `DELETE /api/users/<user_id>`

**认证:** Required (Admin)

**Response:** `200 OK`
```json
{
  "message": "User deleted successfully"
}
```

---

## 声纹数据管理

### 8. 上传声纹数据

**Endpoint:** `POST /api/voiceprints`

**认证:** Required (Session)

**Request Body:** (multipart/form-data)
- `audio_file`: 音频文件
- `machine_type`: 机器类型 (e.g., "fan", "pump")
- `section_id`: 区段ID (optional)
- `label`: 标签 (0=正常, 1=异常, optional)
- `metadata`: JSON格式的元数据 (optional)

**Response:** `201 Created`
```json
{
  "message": "Voiceprint uploaded successfully",
  "voiceprint_id": 1,
  "file_path": "/path/to/audio.wav"
}
```

---

### 9. 获取声纹列表

**Endpoint:** `GET /api/voiceprints`

**认证:** Required (Session)

**Query Parameters:**
- `page` (int): 页码
- `per_page` (int): 每页数量
- `machine_type` (str, optional): 过滤机器类型

**Response:** `200 OK`
```json
{
  "voiceprints": [
    {
      "id": 1,
      "filename": "audio_001.wav",
      "file_path": "/path/to/audio.wav",
      "machine_type": "fan",
      "label": 0,
      "uploaded_at": "2025-01-01 00:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20
}
```

---

### 10. 获取单个声纹详情

**Endpoint:** `GET /api/voiceprints/<voiceprint_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "id": 1,
  "filename": "audio_001.wav",
  "file_path": "/path/to/audio.wav",
  "machine_type": "fan",
  "section_id": 0,
  "label": 0,
  "metadata": {},
  "uploaded_at": "2025-01-01 00:00:00"
}
```

---

### 11. 删除声纹数据

**Endpoint:** `DELETE /api/voiceprints/<voiceprint_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "message": "Voiceprint deleted successfully"
}
```

---

## 特征提取

### 12. 提取特征

**Endpoint:** `POST /api/features/extract`

**认证:** Required (Session)

**Request Body:**
```json
{
  "voiceprint_id": 1,
  "config": {
    "sr": 16000,
    "n_mels": 128,
    "n_fft": 1024,
    "hop_length": 512
  }
}
```

**Response:** `200 OK`
```json
{
  "message": "Feature extracted successfully",
  "feature_id": 1,
  "feature_path": "/path/to/feature.npy",
  "shape": [128, 64]
}
```

---

### 13. 批量提取特征

**Endpoint:** `POST /api/features/batch-extract`

**认证:** Required (Session)

**描述:** 支持中断恢复的批量特征提取

**Request Body:**
```json
{
  "voiceprint_ids": [1, 2, 3, 4, 5],
  "config": {
    "sr": 16000,
    "n_mels": 128
  },
  "task_id": "batch_extract_20250106_120000",
  "resume": false
}
```

**Response:** `200 OK`
```json
{
  "task_id": "batch_extract_20250106_120000",
  "status": "completed",
  "success_count": 5,
  "error_count": 0,
  "total_count": 5,
  "checkpoint_file": "/path/to/checkpoint.json",
  "results": [...]
}
```

---

### 14. 恢复中断的批量提取

**Endpoint:** `POST /api/features/batch-extract/resume/<task_id>`

**认证:** Required (Session)

**Request Body:**
```json
{
  "voiceprint_ids": [1, 2, 3, 4, 5],
  "config": {...}
}
```

**Response:** `200 OK`
```json
{
  "message": "Batch feature extraction resumed and completed",
  "previous_progress": {
    "completed": 2,
    "failed": 0,
    "total": 5
  },
  "final_result": {...}
}
```

---

### 15. 查询批量提取任务状态

**Endpoint:** `GET /api/features/batch-extract/status/<task_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "task_id": "batch_extract_20250106_120000",
  "status": "in_progress",
  "total": 5,
  "completed": 3,
  "failed": 0,
  "progress_percentage": 60.0,
  "can_resume": true
}
```

---

## 模型训练

### 16. 开始训练

**Endpoint:** `POST /api/training/start`

**认证:** Required (Session)

**Request Body:**
```json
{
  "config": {
    "machine_type": "fan",
    "train_dir": "data/fan/train",
    "model_type": "mobilenetv2",
    "epochs": 50,
    "batch_size": 32,
    "learning_rate": 0.001
  }
}
```

**Response:** `200 OK`
```json
{
  "message": "Training started",
  "task_id": "train_fan_20250106_120000"
}
```

---

### 17. 获取训练状态

**Endpoint:** `GET /api/training/status/<task_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "task_id": "train_fan_20250106_120000",
  "status": "running",
  "progress": 45.5,
  "current_epoch": 23,
  "total_epochs": 50,
  "metrics": {
    "train_loss": 0.25,
    "val_loss": 0.28,
    "train_acc": 92.5,
    "val_acc": 90.2
  }
}
```

---

### 18. 停止训练

**Endpoint:** `POST /api/training/stop/<task_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "message": "Training stopped",
  "task_id": "train_fan_20250106_120000"
}
```

---

### 19. 列出所有模型

**Endpoint:** `GET /api/models`

**认证:** Required (Session)

**Query Parameters:**
- `page` (int): 页码
- `per_page` (int): 每页数量
- `machine_type` (str, optional): 过滤机器类型

**Response:** `200 OK`
```json
{
  "models": [
    {
      "id": 1,
      "name": "Fan Anomaly Detector v1",
      "version": "1.0",
      "machine_type": "fan",
      "model_type": "mobilenetv2",
      "model_path": "/path/to/model.pth",
      "metrics": {
        "train_loss": 0.15,
        "val_loss": 0.18,
        "auc": 0.94
      },
      "created_at": "2025-01-01 00:00:00"
    }
  ],
  "total": 1
}
```

---

### 20. 获取模型详情

**Endpoint:** `GET /api/models/<model_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Fan Anomaly Detector v1",
  "version": "1.0",
  "machine_type": "fan",
  "model_type": "mobilenetv2",
  "model_path": "/path/to/model.pth",
  "config": {...},
  "metrics": {...},
  "created_at": "2025-01-01 00:00:00",
  "training_history": {
    "train_loss": [...],
    "val_loss": [...],
    "train_acc": [...],
    "val_acc": [...]
  }
}
```

---

### 21. 删除模型

**Endpoint:** `DELETE /api/models/<model_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "message": "Model deleted successfully"
}
```

---

## 模型评估

### 22. 评估模型

**Endpoint:** `POST /api/models/<model_id>/evaluate`

**认证:** Required (Session)

**Request Body:**
```json
{
  "test_dir": "data/fan/test"
}
```

**Response:** `200 OK`
```json
{
  "metrics": {
    "auc": 0.945,
    "accuracy": 92.5,
    "precision": 91.2,
    "recall": 93.8,
    "f1_score": 92.5
  },
  "confusion_matrix": [[45, 5], [3, 47]],
  "test_samples": 100
}
```

---

## 模型可视化与比较

### 23. 可视化模型训练历史

**Endpoint:** `GET /api/models/<model_id>/visualize`

**认证:** Required (Session)

**描述:** 生成训练曲线图（Loss/Accuracy）

**Response:** `200 OK`
```json
{
  "message": "Visualization generated successfully",
  "visualization_path": "/path/to/viz.png",
  "visualization_url": "/api/models/1/visualization/model_1_viz_20250106.png",
  "metrics": {
    "final_train_loss": 0.15,
    "final_val_loss": 0.18,
    "final_train_acc": 95.2,
    "final_val_acc": 92.3,
    "total_epochs": 50,
    "best_val_loss": 0.16,
    "best_val_acc": 93.5
  }
}
```

---

### 24. 下载模型可视化图片

**Endpoint:** `GET /api/models/<model_id>/visualization/<filename>`

**认证:** Required (Session)

**Response:** `200 OK` (Image file)

---

### 25. 比较多个模型

**Endpoint:** `POST /api/models/compare`

**认证:** Required (Session)

**描述:** 对比2-6个模型的性能

**Request Body:**
```json
{
  "model_ids": [1, 2, 3]
}
```

**Response:** `200 OK`
```json
{
  "message": "Model comparison completed",
  "comparison": {
    "models": [
      {
        "id": 1,
        "name": "Model v1",
        "metrics": {
          "final_train_loss": 0.15,
          "final_val_loss": 0.18,
          "final_val_acc": 92.3,
          "auc": 0.94
        }
      },
      ...
    ],
    "best_models": {
      "by_val_loss": 1,
      "by_val_acc": 2
    },
    "visualization_url": "/api/models/compare/visualization/comparison_20250106.png"
  }
}
```

---

### 26. 下载模型比较可视化

**Endpoint:** `GET /api/models/compare/visualization/<filename>`

**认证:** Required (Session)

**Response:** `200 OK` (Image file)

---

## 推理预测

### 27. 单次预测

**Endpoint:** `POST /api/predict`

**认证:** Required (Session)

**Request Body:** (multipart/form-data)
- `model_id`: 模型ID
- `audio_file`: 音频文件

**Response:** `200 OK`
```json
{
  "prediction": {
    "anomaly_score": 0.75,
    "is_anomaly": true,
    "confidence": 0.85,
    "label": "异常"
  },
  "model_id": 1,
  "filename": "test_audio.wav"
}
```

---

### 28. 批量预测

**Endpoint:** `POST /api/predict/batch`

**认证:** Required (Session)

**Request Body:**
```json
{
  "model_id": 1,
  "voiceprint_ids": [1, 2, 3, 4, 5]
}
```

**Response:** `200 OK`
```json
{
  "predictions": [
    {
      "voiceprint_id": 1,
      "anomaly_score": 0.25,
      "is_anomaly": false
    },
    ...
  ],
  "summary": {
    "total": 5,
    "normal": 3,
    "anomalous": 2
  }
}
```

---

## 报告生成

### 29. 生成报告

**Endpoint:** `POST /api/reports/generate`

**认证:** Required (Session)

**Request Body:**
```json
{
  "report_type": "detection",
  "format": "pdf",
  "config": {
    "title": "异常检测报告",
    "model_id": 1,
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "include_visualizations": true
  }
}
```

**Response:** `200 OK`
```json
{
  "message": "Report generated successfully",
  "report_id": 1,
  "report_path": "/path/to/report.pdf",
  "download_url": "/api/reports/1/download"
}
```

---

### 30. 下载报告

**Endpoint:** `GET /api/reports/<report_id>/download`

**认证:** Required (Session)

**Response:** `200 OK` (File download)

---

### 31. 列出报告

**Endpoint:** `GET /api/reports`

**认证:** Required (Session)

**Query Parameters:**
- `page` (int): 页码
- `per_page` (int): 每页数量

**Response:** `200 OK`
```json
{
  "reports": [
    {
      "id": 1,
      "title": "异常检测报告",
      "type": "detection",
      "format": "pdf",
      "created_at": "2025-01-01 00:00:00",
      "download_url": "/api/reports/1/download"
    }
  ],
  "total": 1
}
```

---

### 32. 删除报告

**Endpoint:** `DELETE /api/reports/<report_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "message": "Report deleted successfully"
}
```

---

## 租户管理

### 33. 创建租户

**Endpoint:** `POST /api/tenants`

**认证:** Required (Admin)

**Request Body:**
```json
{
  "name": "Company A",
  "contact_email": "contact@company-a.com",
  "resource_quota": {
    "max_users": 10,
    "max_models": 5,
    "max_storage_gb": 100
  }
}
```

**Response:** `201 Created`
```json
{
  "message": "Tenant created successfully",
  "tenant_id": 1
}
```

---

### 34. 获取租户列表

**Endpoint:** `GET /api/tenants`

**认证:** Required (Admin)

**Response:** `200 OK`
```json
{
  "tenants": [
    {
      "id": 1,
      "name": "Company A",
      "contact_email": "contact@company-a.com",
      "status": "active",
      "created_at": "2025-01-01 00:00:00"
    }
  ],
  "total": 1
}
```

---

### 35. 更新租户配额

**Endpoint:** `PUT /api/tenants/<tenant_id>/quota`

**认证:** Required (Admin)

**Request Body:**
```json
{
  "quota": {
    "max_users": 20,
    "max_models": 10,
    "max_storage_gb": 200
  }
}
```

**Response:** `200 OK`
```json
{
  "message": "Tenant quota updated successfully"
}
```

---

## 商业化服务

### 36. 生成API密钥

**Endpoint:** `POST /api/api-keys`

**认证:** Required (Session)

**Request Body:**
```json
{
  "name": "Production API Key",
  "permissions": ["read", "write"],
  "expires_at": "2026-01-01"
}
```

**Response:** `201 Created`
```json
{
  "message": "API key created successfully",
  "api_key": "sk_live_1234567890abcdef",
  "api_key_id": 1
}
```

---

### 37. 列出API密钥

**Endpoint:** `GET /api/api-keys`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "api_keys": [
    {
      "id": 1,
      "name": "Production API Key",
      "key_prefix": "sk_live_1234",
      "permissions": ["read", "write"],
      "created_at": "2025-01-01 00:00:00",
      "expires_at": "2026-01-01 00:00:00",
      "is_active": true
    }
  ]
}
```

---

### 38. 撤销API密钥

**Endpoint:** `DELETE /api/api-keys/<api_key_id>`

**认证:** Required (Session)

**Response:** `200 OK`
```json
{
  "message": "API key revoked successfully"
}
```

---

### 39. 查询账单记录

**Endpoint:** `GET /api/billing/records`

**认证:** Required (Session)

**Query Parameters:**
- `start_date` (str, optional): 开始日期
- `end_date` (str, optional): 结束日期
- `page` (int): 页码
- `per_page` (int): 每页数量

**Response:** `200 OK`
```json
{
  "records": [
    {
      "id": 1,
      "resource_type": "api_call",
      "quantity": 1000,
      "unit_price": 0.01,
      "total_amount": 10.00,
      "billing_cycle": "2025-01",
      "created_at": "2025-01-01 00:00:00"
    }
  ],
  "total": 1,
  "total_amount": 10.00
}
```

---

### 40. 生成发票

**Endpoint:** `POST /api/billing/invoice`

**认证:** Required (Session)

**Request Body:**
```json
{
  "billing_period": "2025-01"
}
```

**Response:** `200 OK`
```json
{
  "message": "Invoice generated successfully",
  "invoice": {
    "invoice_id": "INV-2025-01-001",
    "total_amount": 100.00,
    "status": "pending",
    "due_date": "2025-02-01"
  }
}
```

---

## 错误码

| Code | Message | Description |
|------|---------|-------------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或认证失败 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（如用户名已存在） |
| 500 | Internal Server Error | 服务器内部错误 |

---

## 认证方式

### Session认证（推荐用于Web界面）

1. 调用 `/api/login` 获取session
2. 后续请求自动携带session cookie

### API Key认证（推荐用于程序调用）

在请求头中添加：
```
X-API-Key: sk_live_your_api_key_here
```

---

## 示例代码

### Python

```python
import requests

# Session认证
session = requests.Session()
login_resp = session.post('http://localhost:5000/api/login', json={
    'username': 'user123',
    'password': 'password123'
})

# 上传音频
with open('audio.wav', 'rb') as f:
    upload_resp = session.post('http://localhost:5000/api/voiceprints', files={
        'audio_file': f
    }, data={
        'machine_type': 'fan'
    })

print(upload_resp.json())
```

### cURL

```bash
# 登录
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user123","password":"password123"}' \
  -c cookies.txt

# 上传音频
curl -X POST http://localhost:5000/api/voiceprints \
  -b cookies.txt \
  -F "audio_file=@audio.wav" \
  -F "machine_type=fan"
```

---

## 支持

如有问题，请查看：
- GitHub Issues: https://github.com/yourusername/audio-anomaly-detection
- Email: support@example.com

---

**© 2025 Audio Anomaly Detection System**
