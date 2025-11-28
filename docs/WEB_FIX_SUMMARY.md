# Web界面问题修复说明

## 修复日期
2025-11-27

## 新增功能

### ✨ 音频播放功能（最新）
**功能描述**:
- 实时检测时可以同时播放音频
- 支持麦克风输入和文件输入的音频播放

**使用方法**:
1. 在实时检测页面勾选"Enable Playback"复选框
2. 开始检测后会自动播放音频
3. 麦克风模式：实时外放捕获的音频
4. 文件模式：播放文件音频

**技术实现**:
- 麦克风：使用sounddevice.OutputStream实时播放
- 文件：使用sounddevice.play播放音频文件
- 播放和检测独立线程，互不影响

**修改文件**:
- `realtime_detection_websocket.py`: 添加播放队列和回调
- `templates/index.html`: 添加Enable Playback复选框
- `static/app.js`: 收集enable_playback参数
- `app.py`: 传递--enable_playback参数给脚本

---

## 修复的问题

### 1. ✅ 模型类名错误
**问题描述**:
- `realtime_detection_websocket.py`中导入的`AnomalyDetectionModel`类不存在
- 报错：`ImportError: cannot import name 'AnomalyDetectionModel' from 'model'`

**解决方案**:
- 实际的类名是`MobileNetV2`
- 修改导入语句：`from model import MobileNetV2`
- 修改实例化代码使用`MobileNetV2`

**修改文件**:
- `realtime_detection_websocket.py`: 第21行和第75行

**验证方法**:
```bash
python src/test_imports.py
```

---

### 2. ✅ 脚本无法通过UI运行（虚拟环境问题）
**问题描述**:
- Flask调用脚本时使用系统Python而不是虚拟环境Python
- 导致报错：`ModuleNotFoundError: No module named 'numpy'`

**解决方案**:
- 修改`app.py`，使用`sys.executable`代替硬编码的`'python'`
- 所有subprocess调用都使用当前Python解释器
- 启动时显示Python解释器路径用于验证

**修改文件**:
- `app.py`: 所有`subprocess.Popen`命令从`'python'`改为`sys.executable`

**验证方法**:
```python
# 启动时会显示:
# Python解释器: D:\baseline\venv\Scripts\python.exe
```

---

### 3. ✅ 实时检测参数不完整
**问题描述**:
- UI页面缺少重要的实时检测参数
- 用户无法调整缓冲区、检测间隔等关键参数

**解决方案**:
添加以下参数到UI：
- ✅ **Device (计算设备)**: CUDA/CPU选择
- ✅ **Patch Frames (帧数)**: 64（默认）
- ✅ **Buffer Duration (缓冲区时长)**: 10.0秒（默认）
- ✅ **Hop Duration (检测间隔)**: 0.5秒（默认）
- ✅ **Realtime Mode (实时播放模式)**: 文件输入时是否模拟实时

**修改文件**:
- `templates/index.html`: 添加所有参数输入框
- `static/app.js`: 收集和发送所有参数
- `app.py`: 处理所有参数并传递给脚本

---

### 4. ✅ 实时检测输出捕获优化
**问题描述**:
- 实时检测无输出或输出不稳定
- 缺少详细的调试信息

**解决方案**:
- 改进stderr和stdout的分离读取
- 添加独立线程读取stderr日志
- 添加详细的调试输出（计数、状态信息）
- 使用`universal_newlines=True`确保文本模式
- 捕获所有异常并输出

**改进内容**:
```python
# 添加输出计数
output_count = 0
print(f"[JSON数据 #{output_count}] 检测结果")

# 独立stderr线程
def read_stderr():
    try:
        for line in iter(process.stderr.readline, ''):
            # 处理stderr
    except Exception as e:
        print(f"stderr读取错误: {e}")
```

---

## 新增的辅助工具

### 1. `test_imports.py`
快速验证导入是否正常：
- ✓ 测试所有必需模块的导入
- ✓ 验证模型类是否可以正常实例化
- ✓ 检查实时检测脚本的导入

使用方法：
```bash
python src/test_imports.py
```

### 2. `start_web_ui_auto.bat`
- 自动检测并激活虚拟环境
- 智能提示虚拟环境状态
- 一键启动Web界面

### 3. `diagnose_web_env.py`
环境诊断脚本，检查：
- ✓ Python版本
- ✓ 虚拟环境状态
- ✓ 必需包安装情况
- ✓ 必需文件完整性
- ✓ 必需目录存在性

使用方法：
```bash
python src/diagnose_web_env.py
```

### 4. `test_realtime_script.py`
- 测试实时检测脚本是否能正常运行
- 显示详细的stdout和stderr输出
- 快速验证环境配置

### 5. `WEB_FIX_SUMMARY.md`
完整的修复说明文档

---

## 参数对照表

### 实时检测完整参数

| UI参数名 | 命令行参数 | 默认值 | 说明 |
|---------|-----------|--------|------|
| Checkpoint | --checkpoint | 必填 | 模型检查点路径 |
| Audio Source | --source | microphone | 音频源（microphone/file） |
| Device | --device | cuda | 计算设备（cuda/cpu） |
| Audio File Path | --audio_file | - | 音频文件路径（file模式） |
| Microphone Device ID | --device_id | 默认设备 | 麦克风ID（可选） |
| Anomaly Threshold | --threshold | 2.0 | 异常阈值 |
| Patch Frames | --patch_frames | 64 | 每个patch的帧数 |
| Buffer Duration | --buffer_duration | 10.0 | 缓冲区时长（秒） |
| Hop Duration | --hop_duration | 0.5 | 检测间隔（秒） |
| Realtime Mode | --realtime | False | 文件实时播放模式 |

---

## 使用说明

### 1. 确保在虚拟环境中
```bash
# 激活虚拟环境
venv\Scripts\activate

# 验证环境
python src/diagnose_web_env.py
```

### 2. 启动Web界面
```bash
# 方式1: 自动激活虚拟环境并启动
start_web_ui_auto.bat

# 方式2: 手动启动
python src/app.py
```

### 3. 访问界面
打开浏览器访问: **http://localhost:5000**

---

## 测试流程

### 快速测试
1. **导入测试**:
   ```bash
   python src/test_imports.py
   ```

2. **环境检查**:
   ```bash
   python src/diagnose_web_env.py
   ```

3. **脚本测试**:
   ```bash
   python src/test_realtime_script.py
   ```

4. **启动服务**:
   ```bash
   python src/app.py
   ```

5. **浏览器测试**:
   - 打开 http://localhost:5000
   - 切换到"实时检测"标签页
   - 填写参数并点击"开始检测"
   - 观察输出和状态

---

## 常见问题排查

### Q1: 报错"cannot import name 'AnomalyDetectionModel'"
**原因**: 模型类名错误

**解决**:
- 这个问题已修复
- 运行`python src/test_imports.py`验证
- 确保使用最新版本的`realtime_detection_websocket.py`

### Q2: 报错"No module named 'xxx'"
**原因**: 不在虚拟环境中或包未安装

**解决**:
```bash
venv\Scripts\activate
pip install -r requirements_web.txt
```

### Q3: 实时检测无输出
**原因**:
- 音频文件路径错误
- Checkpoint路径错误
- CUDA不可用但选择了CUDA

**解决**:
1. 检查文件路径是否正确
2. 尝试使用CPU模式
3. 查看服务器控制台的详细输出

### Q3: 训练/测试启动失败
**原因**: 参数错误或数据路径不存在

**解决**:
1. 检查Training Directory是否存在
2. 查看服务器控制台的错误信息
3. 确认所有必填参数已填写

---

## 总结

所有问题已修复：
- ✅ 脚本可以正常通过UI运行（虚拟环境问题已解决）
- ✅ 实时检测参数已全部添加到页面
- ✅ 输出捕获已优化，可以看到详细信息
- ✅ 添加了多个辅助工具帮助诊断问题

现在Web界面功能完整，可以正常使用！
