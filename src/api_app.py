"""
音频异常检测系统 - RESTful API服务器
支持完整的数据管理、模型训练、报告生成和商业化服务功能
"""

from flask import Flask, request, jsonify, session, send_file, send_from_directory
from flask_cors import CORS
from functools import wraps
import os
import json
from datetime import datetime, timedelta
import traceback

# 导入数据库模型
from models import (
    Database, User, VoiceprintData, Model, Report,
    APIKey, AuditLog
)

# 导入服务层
from training_service import training_manager, feature_manager, evaluation_manager
from report_service import report_generator, template_manager

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 判断web目录位置（支持从根目录或src目录启动）
if os.path.exists(os.path.join(BASE_DIR, 'web', 'templates')):
    # 从src目录启动
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'web', 'templates')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'web', 'static')
elif os.path.exists(os.path.join(BASE_DIR, 'src', 'web', 'templates')):
    # 从根目录启动
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'src', 'web', 'templates')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'src', 'web', 'static')
else:
    # 尝试相对于工作目录
    TEMPLATE_FOLDER = os.path.join(os.getcwd(), 'src', 'web', 'templates')
    STATIC_FOLDER = os.path.join(os.getcwd(), 'src', 'web', 'static')

# 初始化Flask应用
app = Flask(__name__,
            template_folder=TEMPLATE_FOLDER,
            static_folder=STATIC_FOLDER,
            static_url_path='/static')
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
CORS(app)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化数据库
db = Database()


# ===== 认证装饰器 =====

def login_required(f):
    """要求登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """要求管理员权限的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        user = User.get_by_id(session['user_id'])
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'Admin permission required'}), 403

        return f(*args, **kwargs)
    return decorated_function


def api_key_required(f):
    """要求API密钥的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        key_info = APIKey.verify(api_key)
        if not key_info:
            return jsonify({'error': 'Invalid API key'}), 401

        # 将API密钥信息添加到请求上下文
        request.api_key_info = key_info
        return f(*args, **kwargs)
    return decorated_function


# ===== 用户认证 API =====

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        # 获取默认租户ID
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tenants WHERE name = ?", ('Default Tenant',))
        tenant = cursor.fetchone()
        tenant_id = tenant['id'] if tenant else 1
        conn.close()

        user_id = User.create(username, password, email, tenant_id=tenant_id)

        if user_id:
            AuditLog.log('user_register', user_id=user_id,
                        details={'username': username})
            return jsonify({'message': 'User created successfully', 'user_id': user_id}), 201
        else:
            return jsonify({'error': 'Username already exists'}), 409

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        user = User.authenticate(username, password)

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['tenant_id'] = user['tenant_id']

            AuditLog.log('user_login', user_id=user['id'],
                        details={'username': username},
                        ip_address=request.remote_addr)

            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role'],
                    'tenant_id': user['tenant_id']
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    user_id = session.get('user_id')
    AuditLog.log('user_logout', user_id=user_id)

    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前用户信息"""
    user = User.get_by_id(session['user_id'])
    if user:
        return jsonify(user), 200
    return jsonify({'error': 'User not found'}), 404


# ===== 声纹数据管理 API =====

@app.route('/api/voiceprints', methods=['POST'])
@login_required
def upload_voiceprint():
    """上传声纹数据 (TN-F-001)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # 验证文件格式
        allowed_extensions = {'.wav', '.mp3', '.flac', '.ogg'}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Invalid file format. Allowed: {allowed_extensions}'}), 400

        # 保存文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 获取文件信息
        file_size = os.path.getsize(filepath)

        # 尝试获取音频元数据
        import librosa
        try:
            y, sr = librosa.load(filepath, sr=None)
            duration = len(y) / sr
            sample_rate = sr
        except:
            duration = None
            sample_rate = None

        # 从文件名或请求中获取机器类型和section
        machine_type = request.form.get('machine_type', 'unknown')
        section = request.form.get('section', 'unknown')

        # 创建数据库记录
        data_id = VoiceprintData.create(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id'),
            filename=filename,
            file_path=filepath,
            file_size=file_size,
            file_format=file_ext,
            duration=duration,
            sample_rate=sample_rate,
            machine_type=machine_type,
            section=section,
            metadata=json.loads(request.form.get('metadata', '{}'))
        )

        AuditLog.log('voiceprint_upload', user_id=session['user_id'],
                    tenant_id=session.get('tenant_id'),
                    resource_type='voiceprint', resource_id=data_id,
                    details={'filename': filename})

        return jsonify({
            'message': 'File uploaded successfully',
            'data_id': data_id,
            'filename': filename
        }), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/voiceprints/batch', methods=['POST'])
@login_required
def batch_upload_voiceprints():
    """批量上传声纹数据 (TN-F-005)"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files')
        results = []
        errors = []

        for file in files:
            try:
                if file.filename == '':
                    continue

                # 验证文件格式
                allowed_extensions = {'.wav', '.mp3', '.flac', '.ogg'}
                file_ext = os.path.splitext(file.filename)[1].lower()

                if file_ext not in allowed_extensions:
                    errors.append({'filename': file.filename, 'error': 'Invalid format'})
                    continue

                # 保存文件
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"{timestamp}_{file.filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # 获取文件信息
                file_size = os.path.getsize(filepath)

                # 创建数据库记录
                data_id = VoiceprintData.create(
                    user_id=session['user_id'],
                    tenant_id=session.get('tenant_id'),
                    filename=filename,
                    file_path=filepath,
                    file_size=file_size,
                    file_format=file_ext,
                    machine_type=request.form.get('machine_type', 'unknown'),
                    section=request.form.get('section', 'unknown')
                )

                results.append({'filename': filename, 'data_id': data_id})

            except Exception as e:
                errors.append({'filename': file.filename, 'error': str(e)})

        AuditLog.log('voiceprint_batch_upload', user_id=session['user_id'],
                    tenant_id=session.get('tenant_id'),
                    details={'count': len(results), 'errors': len(errors)})

        return jsonify({
            'message': f'Uploaded {len(results)} files',
            'results': results,
            'errors': errors
        }), 201 if results else 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/voiceprints', methods=['GET'])
@login_required
def list_voiceprints():
    """获取声纹数据列表 (TN-F-003)"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        data_list = VoiceprintData.list_all(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id'),
            limit=limit,
            offset=offset
        )

        return jsonify({
            'data': data_list,
            'count': len(data_list),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/voiceprints/<int:data_id>', methods=['GET'])
@login_required
def get_voiceprint_detail(data_id):
    """获取声纹数据详情 (TN-F-011)"""
    try:
        data = VoiceprintData.get_by_id(data_id)

        if not data:
            return jsonify({'error': 'Data not found'}), 404

        # 检查权限（租户隔离）
        if data['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        return jsonify(data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/voiceprints/<int:data_id>/download', methods=['GET'])
@login_required
def download_voiceprint(data_id):
    """下载声纹数据 (TN-F-012)"""
    try:
        data = VoiceprintData.get_by_id(data_id)

        if not data:
            return jsonify({'error': 'Data not found'}), 404

        # 检查权限
        if data['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        AuditLog.log('voiceprint_download', user_id=session['user_id'],
                    resource_type='voiceprint', resource_id=data_id)

        return send_file(data['file_path'], as_attachment=True,
                        download_name=data['filename'])

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/voiceprints/<int:data_id>', methods=['DELETE'])
@login_required
def delete_voiceprint(data_id):
    """删除声纹数据 (TN-F-004)"""
    try:
        data = VoiceprintData.get_by_id(data_id)

        if not data:
            return jsonify({'error': 'Data not found'}), 404

        # 检查权限
        if data['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        success = VoiceprintData.delete(data_id)

        if success:
            AuditLog.log('voiceprint_delete', user_id=session['user_id'],
                        resource_type='voiceprint', resource_id=data_id,
                        details={'filename': data['filename']})

            return jsonify({'message': 'Data deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete data'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/voiceprints/search', methods=['GET'])
@login_required
def search_voiceprints():
    """搜索声纹数据 (TN-F-008)"""
    try:
        query = request.args.get('q', '')

        if not query:
            return jsonify({'error': 'Search query required'}), 400

        results = VoiceprintData.search(
            query=query,
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id')
        )

        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 模型管理 API =====

@app.route('/api/models', methods=['GET'])
@login_required
def list_models():
    """获取模型列表 (TN-F-018)"""
    try:
        machine_type = request.args.get('machine_type')

        models = Model.list_all(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id'),
            machine_type=machine_type
        )

        return jsonify({
            'models': models,
            'count': len(models)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/<int:model_id>', methods=['GET'])
@login_required
def get_model_detail(model_id):
    """获取模型详情"""
    try:
        model = Model.get_by_id(model_id)

        if not model:
            return jsonify({'error': 'Model not found'}), 404

        # 检查权限
        if model['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        return jsonify(model), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 报告管理 API =====

@app.route('/api/reports', methods=['GET'])
@login_required
def list_reports():
    """获取报告列表 (TN-F-031)"""
    try:
        reports = Report.list_all(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id')
        )

        return jsonify({
            'reports': reports,
            'count': len(reports)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/<int:report_id>', methods=['GET'])
@login_required
def get_report_detail(report_id):
    """获取报告详情"""
    try:
        report = Report.get_by_id(report_id)

        if not report:
            return jsonify({'error': 'Report not found'}), 404

        # 检查权限
        if report['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        return jsonify(report), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== API密钥管理 =====

@app.route('/api/keys', methods=['POST'])
@login_required
def create_api_key():
    """创建API密钥 (TN-F-050)"""
    try:
        data = request.json
        name = data.get('name', 'API Key')
        permissions = data.get('permissions', ['read'])

        key_id, key = APIKey.create(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id'),
            name=name,
            permissions=permissions
        )

        AuditLog.log('api_key_create', user_id=session['user_id'],
                    resource_type='api_key', resource_id=key_id,
                    details={'name': name})

        return jsonify({
            'message': 'API key created successfully',
            'key_id': key_id,
            'api_key': key,
            'warning': 'Please save this key securely. It will not be shown again.'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 公开API（需要API密钥） =====

@app.route('/api/public/detect', methods=['POST'])
@api_key_required
def public_api_detect():
    """公开的异常检测API (TN-F-048)"""
    try:
        # TODO: 实现异常检测逻辑
        # 这里可以调用现有的inference.py中的检测功能

        AuditLog.log('api_detection', user_id=request.api_key_info['user_id'],
                    tenant_id=request.api_key_info['tenant_id'],
                    details={'endpoint': '/api/public/detect'})

        return jsonify({
            'message': 'Detection API - Not implemented yet',
            'status': 'success'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 系统监控 API =====

@app.route('/api/system/status', methods=['GET'])
@login_required
def system_status():
    """系统状态监控 (TN-F-060)"""
    try:
        # Mock系统状态
        status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': 'up',
                'api': 'up',
                'training': 'up'
            },
            'metrics': {
                'cpu_usage': 45.2,
                'memory_usage': 62.8,
                'disk_usage': 38.5,
                'active_users': 12,
                'total_models': 5,
                'total_reports': 150
            }
        }

        return jsonify(status), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 审计日志 API =====

@app.route('/api/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    """获取审计日志 (TN-F-039)"""
    try:
        limit = int(request.args.get('limit', 100))

        logs = AuditLog.get_logs(
            tenant_id=session.get('tenant_id'),
            limit=limit
        )

        return jsonify({
            'logs': logs,
            'count': len(logs)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 健康检查 =====

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200


# ===== 训练管理 API =====

@app.route('/api/training/start', methods=['POST'])
@login_required
def start_training():
    """启动训练任务 (TN-F-016)"""
    try:
        config = request.json

        result = training_manager.start_training(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id'),
            config=config
        )

        if 'error' in result:
            return jsonify(result), 400

        AuditLog.log('training_start', user_id=session['user_id'],
                    tenant_id=session.get('tenant_id'),
                    resource_type='training_task', resource_id=result['db_id'],
                    details={'machine_type': config.get('machine_type')})

        return jsonify(result), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/training/tasks', methods=['GET'])
@login_required
def list_training_tasks():
    """获取训练任务列表"""
    try:
        tasks = training_manager.list_tasks(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id')
        )

        return jsonify({
            'tasks': tasks,
            'count': len(tasks)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/training/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_training_task_status(task_id):
    """获取训练任务状态"""
    try:
        task = training_manager.get_task_status(task_id)

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # 检查权限
        if task['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        return jsonify(task), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 特征提取 API =====

@app.route('/api/features/extract', methods=['POST'])
@login_required
def extract_features():
    """提取特征 (TN-F-015)"""
    try:
        data = request.json
        voiceprint_id = data.get('voiceprint_id')
        config = data.get('config', {})

        if not voiceprint_id:
            return jsonify({'error': 'voiceprint_id required'}), 400

        result = feature_manager.extract_features(voiceprint_id, config)

        if 'error' in result:
            return jsonify(result), 400

        AuditLog.log('feature_extract', user_id=session['user_id'],
                    resource_type='feature', resource_id=result['feature_id'])

        return jsonify(result), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/features/batch-extract', methods=['POST'])
@login_required
def batch_extract_features():
    """批量提取特征 (TN-F-023, TN-F-013)"""
    try:
        data = request.json
        voiceprint_ids = data.get('voiceprint_ids', [])
        config = data.get('config', {})
        task_id = data.get('task_id')  # 可选：用于恢复任务
        resume = data.get('resume', False)  # 可选：是否从中断点恢复

        if not voiceprint_ids:
            return jsonify({'error': 'voiceprint_ids required'}), 400

        result = feature_manager.batch_extract_features(
            voiceprint_ids,
            config,
            task_id=task_id,
            resume=resume
        )

        AuditLog.log('feature_batch_extract', user_id=session['user_id'],
                    details={
                        'count': result['success_count'],
                        'task_id': result.get('task_id'),
                        'resumed': resume
                    })

        return jsonify(result), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/features/batch-extract/resume/<task_id>', methods=['POST'])
@login_required
def resume_batch_extract_features(task_id):
    """恢复中断的批量特征提取任务 (TN-F-013)"""
    try:
        import os
        import json

        # 查找checkpoint文件
        checkpoint_dir = os.path.join(os.path.dirname(__file__), '..', 'checkpoints', 'feature_extraction')
        checkpoint_file = os.path.join(checkpoint_dir, f"{task_id}.json")

        if not os.path.exists(checkpoint_file):
            return jsonify({'error': f'Checkpoint not found for task {task_id}'}), 404

        # 读取checkpoint获取原始任务信息
        with open(checkpoint_file, 'r') as f:
            progress = json.load(f)

        # 获取原始的voiceprint_ids列表（需要从请求中提供）
        data = request.json
        voiceprint_ids = data.get('voiceprint_ids', [])
        config = data.get('config', {})

        if not voiceprint_ids:
            return jsonify({'error': 'voiceprint_ids required for resume'}), 400

        # 调用batch_extract_features with resume=True
        result = feature_manager.batch_extract_features(
            voiceprint_ids,
            config,
            task_id=task_id,
            resume=True
        )

        AuditLog.log('feature_batch_extract_resume', user_id=session['user_id'],
                    details={
                        'task_id': task_id,
                        'previous_completed': progress.get('completed', 0),
                        'current_completed': result['success_count']
                    })

        return jsonify({
            'message': 'Batch feature extraction resumed and completed',
            'previous_progress': {
                'completed': progress.get('completed', 0),
                'failed': progress.get('failed', 0),
                'total': progress.get('total', 0)
            },
            'final_result': result
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/features/batch-extract/status/<task_id>', methods=['GET'])
@login_required
def get_batch_extract_status(task_id):
    """查询批量特征提取任务状态 (TN-F-013)"""
    try:
        import os
        import json

        checkpoint_dir = os.path.join(os.path.dirname(__file__), '..', 'checkpoints', 'feature_extraction')
        checkpoint_file = os.path.join(checkpoint_dir, f"{task_id}.json")

        if not os.path.exists(checkpoint_file):
            return jsonify({'error': f'Task {task_id} not found'}), 404

        with open(checkpoint_file, 'r') as f:
            progress = json.load(f)

        return jsonify({
            'task_id': task_id,
            'status': progress.get('status', 'in_progress'),
            'total': progress.get('total', 0),
            'completed': progress.get('completed', 0),
            'failed': progress.get('failed', 0),
            'progress_percentage': (progress.get('completed', 0) / progress.get('total', 1)) * 100 if progress.get('total', 0) > 0 else 0,
            'can_resume': progress.get('status') != 'completed'
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ===== 模型评估 API =====

@app.route('/api/models/<int:model_id>/evaluate', methods=['POST'])
@login_required
def evaluate_model(model_id):
    """评估模型 (TN-F-017)"""
    try:
        data = request.json
        test_dir = data.get('test_dir')

        if not test_dir:
            return jsonify({'error': 'test_dir required'}), 400

        result = evaluation_manager.evaluate_model(model_id, test_dir)

        if 'error' in result:
            return jsonify(result), 400

        AuditLog.log('model_evaluate', user_id=session['user_id'],
                    resource_type='model', resource_id=model_id)

        return jsonify(result), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/<int:model_id>/visualize', methods=['GET'])
@login_required
def visualize_model(model_id):
    """可视化模型训练历史 (TN-F-014)"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        # 获取模型信息
        model = Model.get_by_id(model_id)

        if not model:
            return jsonify({'error': 'Model not found'}), 404

        # 检查权限
        if model['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        # 获取训练历史
        metrics = model.get('metrics', {})
        history = metrics.get('history', {})

        if not history:
            return jsonify({'error': 'No training history available'}), 404

        # 创建可视化目录
        viz_dir = os.path.join(os.path.dirname(__file__), '..', 'visualizations')
        os.makedirs(viz_dir, exist_ok=True)

        # 生成训练曲线图
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        viz_filename = f'model_{model_id}_viz_{timestamp}.png'
        viz_path = os.path.join(viz_dir, viz_filename)

        # 创建2x2子图
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Model Training History - {model["name"]}', fontsize=16, fontweight='bold')

        # 获取训练数据
        epochs = history.get('epochs', list(range(1, len(history.get('train_loss', [])) + 1)))
        train_loss = history.get('train_loss', [])
        val_loss = history.get('val_loss', [])
        train_acc = history.get('train_acc', [])
        val_acc = history.get('val_acc', [])

        # 图1: 训练和验证损失
        if train_loss or val_loss:
            axes[0, 0].plot(epochs[:len(train_loss)], train_loss, 'b-', label='Train Loss', linewidth=2)
            if val_loss:
                axes[0, 0].plot(epochs[:len(val_loss)], val_loss, 'r-', label='Val Loss', linewidth=2)
            axes[0, 0].set_xlabel('Epoch')
            axes[0, 0].set_ylabel('Loss')
            axes[0, 0].set_title('Training and Validation Loss')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)

        # 图2: 训练和验证准确率
        if train_acc or val_acc:
            axes[0, 1].plot(epochs[:len(train_acc)], train_acc, 'b-', label='Train Acc', linewidth=2)
            if val_acc:
                axes[0, 1].plot(epochs[:len(val_acc)], val_acc, 'r-', label='Val Acc', linewidth=2)
            axes[0, 1].set_xlabel('Epoch')
            axes[0, 1].set_ylabel('Accuracy (%)')
            axes[0, 1].set_title('Training and Validation Accuracy')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)

        # 图3: 损失对比柱状图（最终值）
        if train_loss and val_loss:
            categories = ['Train Loss', 'Val Loss']
            values = [train_loss[-1], val_loss[-1]]
            colors = ['#1f77b4', '#ff7f0e']
            axes[1, 0].bar(categories, values, color=colors, alpha=0.7)
            axes[1, 0].set_ylabel('Loss')
            axes[1, 0].set_title('Final Loss Comparison')
            axes[1, 0].grid(True, alpha=0.3, axis='y')
            # 添加数值标签
            for i, v in enumerate(values):
                axes[1, 0].text(i, v, f'{v:.4f}', ha='center', va='bottom')

        # 图4: 准确率对比柱状图（最终值）
        if train_acc and val_acc:
            categories = ['Train Acc', 'Val Acc']
            values = [train_acc[-1], val_acc[-1]]
            colors = ['#1f77b4', '#ff7f0e']
            axes[1, 1].bar(categories, values, color=colors, alpha=0.7)
            axes[1, 1].set_ylabel('Accuracy (%)')
            axes[1, 1].set_title('Final Accuracy Comparison')
            axes[1, 1].set_ylim([0, 100])
            axes[1, 1].grid(True, alpha=0.3, axis='y')
            # 添加数值标签
            for i, v in enumerate(values):
                axes[1, 1].text(i, v, f'{v:.2f}%', ha='center', va='bottom')

        plt.tight_layout()
        plt.savefig(viz_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        AuditLog.log('model_visualize', user_id=session['user_id'],
                    resource_type='model', resource_id=model_id)

        return jsonify({
            'message': 'Visualization generated successfully',
            'visualization_path': viz_path,
            'visualization_url': f'/static/../visualizations/{viz_filename}',
            'metrics': {
                'final_train_loss': train_loss[-1] if train_loss else None,
                'final_val_loss': val_loss[-1] if val_loss else None,
                'final_train_acc': train_acc[-1] if train_acc else None,
                'final_val_acc': val_acc[-1] if val_acc else None,
                'total_epochs': len(epochs),
                'best_val_loss': min(val_loss) if val_loss else None,
                'best_val_acc': max(val_acc) if val_acc else None
            }
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/<int:model_id>/visualization/<filename>')
@login_required
def download_visualization(model_id, filename):
    """下载模型可视化图片"""
    try:
        viz_dir = os.path.join(os.path.dirname(__file__), '..', 'visualizations')
        return send_from_directory(viz_dir, filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/api/models/compare', methods=['POST'])
@login_required
def compare_models():
    """比较多个模型 (TN-F-015)"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        data = request.json
        model_ids = data.get('model_ids', [])

        if len(model_ids) < 2:
            return jsonify({'error': 'At least 2 models required for comparison'}), 400

        if len(model_ids) > 6:
            return jsonify({'error': 'Maximum 6 models can be compared at once'}), 400

        # 获取所有模型信息
        models = []
        for model_id in model_ids:
            model = Model.get_by_id(model_id)
            if not model:
                return jsonify({'error': f'Model {model_id} not found'}), 404

            # 检查权限
            if model['tenant_id'] != session.get('tenant_id'):
                return jsonify({'error': f'Access denied to model {model_id}'}), 403

            models.append(model)

        # 准备比较数据
        comparison_data = {
            'models': [],
            'metrics_comparison': {}
        }

        # 收集每个模型的指标
        metric_keys = ['train_loss', 'val_loss', 'train_acc', 'val_acc', 'auc']
        for model in models:
            metrics = model.get('metrics', {})
            history = metrics.get('history', {})

            model_info = {
                'id': model['id'],
                'name': model['name'],
                'version': model['version'],
                'machine_type': model['machine_type'],
                'model_type': model['model_type'],
                'created_at': model['created_at'],
                'metrics': {
                    'final_train_loss': history.get('train_loss', [None])[-1] if history.get('train_loss') else metrics.get('train_loss'),
                    'final_val_loss': history.get('val_loss', [None])[-1] if history.get('val_loss') else metrics.get('val_loss'),
                    'final_train_acc': history.get('train_acc', [None])[-1] if history.get('train_acc') else metrics.get('train_acc'),
                    'final_val_acc': history.get('val_acc', [None])[-1] if history.get('val_acc') else metrics.get('val_acc'),
                    'auc': metrics.get('auc'),
                    'epochs': len(history.get('train_loss', [])) if history.get('train_loss') else None
                }
            }
            comparison_data['models'].append(model_info)

        # 创建可视化
        viz_dir = os.path.join(os.path.dirname(__file__), '..', 'visualizations')
        os.makedirs(viz_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        viz_filename = f'model_comparison_{timestamp}.png'
        viz_path = os.path.join(viz_dir, viz_filename)

        # 创建比较图表 (2x2布局)
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Model Performance Comparison', fontsize=16, fontweight='bold')

        # 准备数据
        model_names = [f"{m['name']}\nv{m['version']}" for m in comparison_data['models']]
        colors = plt.cm.Set3(np.linspace(0, 1, len(models)))

        # 图1: 训练损失比较
        train_losses = [m['metrics']['final_train_loss'] for m in comparison_data['models']]
        valid_train_losses = [x if x is not None else 0 for x in train_losses]
        bars1 = axes[0, 0].bar(range(len(model_names)), valid_train_losses, color=colors, alpha=0.7)
        axes[0, 0].set_xticks(range(len(model_names)))
        axes[0, 0].set_xticklabels(model_names, rotation=15, ha='right', fontsize=9)
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].set_title('Training Loss Comparison')
        axes[0, 0].grid(True, alpha=0.3, axis='y')
        # 添加数值标签
        for i, (bar, val) in enumerate(zip(bars1, train_losses)):
            if val is not None:
                axes[0, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                              f'{val:.4f}', ha='center', va='bottom', fontsize=8)

        # 图2: 验证损失比较
        val_losses = [m['metrics']['final_val_loss'] for m in comparison_data['models']]
        valid_val_losses = [x if x is not None else 0 for x in val_losses]
        bars2 = axes[0, 1].bar(range(len(model_names)), valid_val_losses, color=colors, alpha=0.7)
        axes[0, 1].set_xticks(range(len(model_names)))
        axes[0, 1].set_xticklabels(model_names, rotation=15, ha='right', fontsize=9)
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].set_title('Validation Loss Comparison')
        axes[0, 1].grid(True, alpha=0.3, axis='y')
        # 添加数值标签
        for i, (bar, val) in enumerate(zip(bars2, val_losses)):
            if val is not None:
                axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                              f'{val:.4f}', ha='center', va='bottom', fontsize=8)

        # 图3: 验证准确率比较
        val_accs = [m['metrics']['final_val_acc'] for m in comparison_data['models']]
        valid_val_accs = [x if x is not None else 0 for x in val_accs]
        bars3 = axes[1, 0].bar(range(len(model_names)), valid_val_accs, color=colors, alpha=0.7)
        axes[1, 0].set_xticks(range(len(model_names)))
        axes[1, 0].set_xticklabels(model_names, rotation=15, ha='right', fontsize=9)
        axes[1, 0].set_ylabel('Accuracy (%)')
        axes[1, 0].set_title('Validation Accuracy Comparison')
        axes[1, 0].set_ylim([0, 100])
        axes[1, 0].grid(True, alpha=0.3, axis='y')
        # 添加数值标签
        for i, (bar, val) in enumerate(zip(bars3, val_accs)):
            if val is not None:
                axes[1, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                              f'{val:.2f}%', ha='center', va='bottom', fontsize=8)

        # 图4: AUC比较
        aucs = [m['metrics']['auc'] for m in comparison_data['models']]
        valid_aucs = [x if x is not None else 0 for x in aucs]
        bars4 = axes[1, 1].bar(range(len(model_names)), valid_aucs, color=colors, alpha=0.7)
        axes[1, 1].set_xticks(range(len(model_names)))
        axes[1, 1].set_xticklabels(model_names, rotation=15, ha='right', fontsize=9)
        axes[1, 1].set_ylabel('AUC')
        axes[1, 1].set_title('AUC Comparison')
        axes[1, 1].set_ylim([0, 1])
        axes[1, 1].grid(True, alpha=0.3, axis='y')
        # 添加数值标签
        for i, (bar, val) in enumerate(zip(bars4, aucs)):
            if val is not None:
                axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                              f'{val:.4f}', ha='center', va='bottom', fontsize=8)

        plt.tight_layout()
        plt.savefig(viz_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        # 找出最佳模型
        best_model_by_val_loss = None
        best_val_loss = float('inf')
        best_model_by_val_acc = None
        best_val_acc = 0

        for model_info in comparison_data['models']:
            val_loss = model_info['metrics']['final_val_loss']
            val_acc = model_info['metrics']['final_val_acc']

            if val_loss is not None and val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model_by_val_loss = model_info['id']

            if val_acc is not None and val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_by_val_acc = model_info['id']

        comparison_data['best_models'] = {
            'by_val_loss': best_model_by_val_loss,
            'by_val_acc': best_model_by_val_acc
        }

        comparison_data['visualization_path'] = viz_path
        comparison_data['visualization_url'] = f'/api/models/compare/visualization/{viz_filename}'

        AuditLog.log('model_compare', user_id=session['user_id'],
                    details={'model_ids': model_ids})

        return jsonify({
            'message': 'Model comparison completed',
            'comparison': comparison_data
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/compare/visualization/<filename>')
@login_required
def download_comparison_visualization(filename):
    """下载模型比较可视化图片"""
    try:
        viz_dir = os.path.join(os.path.dirname(__file__), '..', 'visualizations')
        return send_from_directory(viz_dir, filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


# ===== 报告生成 API =====

@app.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """生成报告 (TN-F-031)"""
    try:
        config = request.json

        result = report_generator.generate_report(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id'),
            report_config=config
        )

        if 'error' in result:
            return jsonify(result), 400

        AuditLog.log('report_generate', user_id=session['user_id'],
                    resource_type='report', resource_id=result['report_id'],
                    details={'format': config.get('format')})

        return jsonify(result), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/batch-generate', methods=['POST'])
@login_required
def batch_generate_reports():
    """批量生成报告 (TN-F-040)"""
    try:
        configs = request.json.get('reports', [])

        result = report_generator.batch_generate_reports(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id'),
            reports_config=configs
        )

        AuditLog.log('report_batch_generate', user_id=session['user_id'],
                    details={'count': result['success_count']})

        return jsonify(result), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/<int:report_id>/download', methods=['GET'])
@login_required
def download_report(report_id):
    """下载报告 (TN-F-033)"""
    try:
        report = Report.get_by_id(report_id)

        if not report:
            return jsonify({'error': 'Report not found'}), 404

        # 检查权限
        if report['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        AuditLog.log('report_download', user_id=session['user_id'],
                    resource_type='report', resource_id=report_id)

        filename = os.path.basename(report['file_path'])
        return send_file(report['file_path'], as_attachment=True,
                        download_name=filename)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 报告模板管理 API =====

@app.route('/api/templates', methods=['POST'])
@login_required
def create_report_template():
    """创建报告模板 (TN-F-032)"""
    try:
        config = request.json

        template_id = template_manager.create_template(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id'),
            template_config=config
        )

        AuditLog.log('template_create', user_id=session['user_id'],
                    resource_type='template', resource_id=template_id,
                    details={'name': config.get('name')})

        return jsonify({
            'message': 'Template created successfully',
            'template_id': template_id
        }), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates', methods=['GET'])
@login_required
def list_report_templates():
    """获取报告模板列表"""
    try:
        templates = template_manager.list_templates(
            user_id=session['user_id'],
            tenant_id=session.get('tenant_id')
        )

        return jsonify({
            'templates': templates,
            'count': len(templates)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates/<int:template_id>', methods=['GET'])
@login_required
def get_report_template(template_id):
    """获取报告模板详情"""
    try:
        template = template_manager.get_template(template_id)

        if not template:
            return jsonify({'error': 'Template not found'}), 404

        # 检查权限
        if template['tenant_id'] != session.get('tenant_id'):
            return jsonify({'error': 'Access denied'}), 403

        return jsonify(template), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 用户和角色管理 API =====

@app.route('/api/users', methods=['GET'])
@admin_required
def list_users():
    """获取用户列表 (TN-F-026)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, role, tenant_id, created_at
            FROM users
            WHERE tenant_id = ?
            ORDER BY created_at DESC
        """, (session.get('tenant_id'),))

        users = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'users': users,
            'count': len(users)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>/permissions', methods=['PUT'])
@admin_required
def update_user_permissions(user_id):
    """更新用户权限 (TN-F-026)"""
    try:
        data = request.json
        role = data.get('role', 'user')

        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET role = ?, updated_at = ?
            WHERE id = ? AND tenant_id = ?
        """, (role, datetime.now().isoformat(), user_id, session.get('tenant_id')))
        conn.commit()
        conn.close()

        AuditLog.log('user_permission_update', user_id=session['user_id'],
                    resource_type='user', resource_id=user_id,
                    details={'new_role': role})

        return jsonify({'message': 'Permissions updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roles', methods=['POST'])
@admin_required
def create_role():
    """创建角色 (TN-F-027) - Mock实现"""
    try:
        data = request.json
        role_name = data.get('name')
        permissions = data.get('permissions', [])

        # Mock: 只记录到审计日志
        AuditLog.log('role_create', user_id=session['user_id'],
                    details={'role_name': role_name, 'permissions': permissions})

        return jsonify({
            'message': 'Role created successfully (mock)',
            'role_id': 1,
            'note': 'This is a mock implementation for testing'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 租户管理 API =====

@app.route('/api/tenants', methods=['GET'])
@admin_required
def list_tenants():
    """获取租户列表 (TN-F-028)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tenants ORDER BY created_at DESC")
        tenants = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'tenants': tenants,
            'count': len(tenants)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tenants/<int:tenant_id>/quota', methods=['PUT'])
@admin_required
def update_tenant_quota(tenant_id):
    """更新租户配额 (TN-F-029)"""
    try:
        data = request.json
        quota = data.get('quota', {})

        conn = db.get_connection()
        cursor = conn.cursor()

        # 注意：tenants表中字段名是resource_quota
        cursor.execute("""
            UPDATE tenants SET resource_quota = ?
            WHERE id = ?
        """, (json.dumps(quota), tenant_id))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Tenant not found'}), 404

        conn.commit()
        conn.close()

        AuditLog.log('tenant_quota_update', user_id=session['user_id'],
                    resource_type='tenant', resource_id=tenant_id,
                    details={'quota': quota})

        return jsonify({'message': 'Quota updated successfully'}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ===== 计费管理 API =====

@app.route('/api/billing/records', methods=['GET'])
@login_required
def list_billing_records():
    """获取计费记录 (TN-F-030)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM billing_records
            WHERE tenant_id = ?
            ORDER BY created_at DESC
            LIMIT 100
        """, (session.get('tenant_id'),))

        records = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'records': records,
            'count': len(records)
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/billing/invoice', methods=['POST'])
@login_required
def generate_invoice():
    """生成账单 (TN-F-031)"""
    try:
        data = request.json
        period_start = data.get('period_start')
        period_end = data.get('period_end')

        # Mock计费数据 - 使用正确的字段名
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO billing_records (
                tenant_id, user_id, resource_type, quantity,
                unit_price, total_amount, billing_cycle
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session.get('tenant_id'),
            session['user_id'],
            'monthly_subscription',  # resource_type
            1,  # quantity
            100.00,  # unit_price
            100.00,  # total_amount
            f"{period_start} to {period_end}"  # billing_cycle
        ))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()

        AuditLog.log('billing_invoice_generate', user_id=session['user_id'],
                    resource_type='billing', resource_id=record_id)

        return jsonify({
            'message': 'Invoice generated successfully',
            'invoice_id': record_id,
            'amount': 100.00
        }), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ===== 移动端API =====

@app.route('/api/mobile/detect', methods=['POST'])
@api_key_required
def mobile_detect():
    """移动端异常检测API (TN-F-032)"""
    try:
        data = request.json

        # Mock实现
        result = {
            'status': 'success',
            'detection_id': 'mob_' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'result': {
                'is_anomaly': False,
                'confidence': 0.92,
                'anomaly_score': 0.08
            },
            'note': 'This is a mock implementation for testing'
        }

        AuditLog.log('mobile_detection', user_id=request.api_key_info['user_id'],
                    tenant_id=request.api_key_info['tenant_id'])

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/sync', methods=['POST'])
@api_key_required
def mobile_sync():
    """移动端数据同步 (TN-F-033)"""
    try:
        data = request.json
        offline_data = data.get('offline_data', [])

        # Mock实现
        result = {
            'status': 'success',
            'synced_count': len(offline_data),
            'failed_count': 0,
            'note': 'This is a mock implementation for testing'
        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 第三方系统集成 API =====

@app.route('/api/integration/webhook', methods=['POST'])
@api_key_required
def integration_webhook():
    """第三方系统Webhook (TN-F-034)"""
    try:
        data = request.json
        event_type = data.get('event_type')

        # Mock实现
        AuditLog.log('integration_webhook', user_id=request.api_key_info['user_id'],
                    details={'event_type': event_type})

        return jsonify({
            'status': 'received',
            'message': 'Webhook processed successfully (mock)'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/integration/export', methods=['POST'])
@login_required
def integration_export():
    """数据导出到第三方系统 (TN-F-035)"""
    try:
        data = request.json
        target_system = data.get('target_system')
        export_data = data.get('data', {})

        # Mock实现
        AuditLog.log('integration_export', user_id=session['user_id'],
                    details={'target_system': target_system, 'data_count': len(export_data)})

        return jsonify({
            'status': 'success',
            'message': 'Data exported successfully (mock)',
            'export_id': 'exp_' + datetime.now().strftime('%Y%m%d%H%M%S')
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 高级分析 API =====

@app.route('/api/analytics/advanced', methods=['POST'])
@login_required
def advanced_analytics():
    """高级分析功能 (TN-F-036)"""
    try:
        data = request.json
        analysis_type = data.get('type', 'trend')
        params = data.get('params', {})

        # Mock分析结果
        result = {
            'status': 'success',
            'analysis_type': analysis_type,
            'results': {
                'total_samples': 1000,
                'anomaly_rate': 0.05,
                'trend': 'stable',
                'recommendations': ['Increase monitoring frequency', 'Review model performance']
            },
            'visualization': {
                'chart_data': [10, 20, 15, 30, 25, 35, 40],
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            },
            'note': 'This is a mock implementation for testing'
        }

        AuditLog.log('advanced_analytics', user_id=session['user_id'],
                    details={'type': analysis_type})

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/custom', methods=['POST'])
@login_required
def custom_analytics():
    """自定义分析模型 (TN-F-037)"""
    try:
        data = request.json
        model_config = data.get('config', {})

        # Mock实现
        result = {
            'status': 'success',
            'model_id': 'custom_' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'message': 'Custom analytics model created (mock)'
        }

        return jsonify(result), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== 定时任务 API =====

@app.route('/api/scheduled-tasks', methods=['POST'])
@login_required
def create_scheduled_task():
    """创建定时任务 (TN-F-021)"""
    try:
        data = request.json
        task_type = data.get('type')  # 'report', 'training', etc.
        schedule = data.get('schedule')  # cron expression
        config = data.get('config', {})

        # Mock实现 - 记录到数据库
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tenant_id INTEGER,
                task_type TEXT,
                schedule TEXT,
                config TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)

        cursor.execute("""
            INSERT INTO scheduled_tasks (user_id, tenant_id, task_type, schedule, config, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session['user_id'],
            session.get('tenant_id'),
            task_type,
            schedule,
            json.dumps(config),
            datetime.now().isoformat()
        ))
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()

        AuditLog.log('scheduled_task_create', user_id=session['user_id'],
                    resource_type='scheduled_task', resource_id=task_id)

        return jsonify({
            'message': 'Scheduled task created successfully (mock)',
            'task_id': task_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduled-tasks', methods=['GET'])
@login_required
def list_scheduled_tasks():
    """获取定时任务列表"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='scheduled_tasks'
        """)
        if not cursor.fetchone():
            conn.close()
            return jsonify({'tasks': [], 'count': 0}), 200

        cursor.execute("""
            SELECT * FROM scheduled_tasks
            WHERE tenant_id = ?
            ORDER BY created_at DESC
        """, (session.get('tenant_id'),))

        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'tasks': tasks,
            'count': len(tasks)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== Web页面路由 =====

@app.route('/')
def index():
    """登录页面"""
    from flask import render_template
    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """主控制台页面"""
    from flask import render_template
    return render_template('dashboard.html')


# ===== 错误处理 =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ===== 启动服务器 =====

if __name__ == '__main__':
    print("=" * 60)
    print("音频异常检测系统 - API服务器")
    print("=" * 60)

    print("\n[1/4] 检查路径配置...")
    print(f"  工作目录: {os.getcwd()}")
    print(f"  模板目录: {TEMPLATE_FOLDER}")
    print(f"  静态目录: {STATIC_FOLDER}")
    print(f"  上传目录: {app.config['UPLOAD_FOLDER']}")

    print("\n[2/4] 初始化数据库...")
    db = Database()
    print("  ✅ 数据库初始化成功")

    print("\n[3/4] 服务器配置...")
    print("  主页: http://localhost:5000")
    print("  API文档: http://localhost:5000/api")
    print("  控制台: http://localhost:5000/dashboard")

    print("\n[4/4] 默认管理员账号:")
    print("  用户名: admin")
    print("  密码: admin123")

    print("\n" + "=" * 60)
    print("服务器启动中...")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)