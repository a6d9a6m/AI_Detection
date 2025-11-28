"""
Flask Web Application for Audio Anomaly Detection
Provides UI interface for training, testing, and real-time detection
"""

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import subprocess
import os
import json
import threading
import queue
import time
from datetime import datetime
import glob
import sys  # 添加sys模块

app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
app.config['SECRET_KEY'] = 'audio_anomaly_detection_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for process management
current_processes = {}
realtime_queue = queue.Queue()
realtime_thread = None
realtime_active = False


def get_available_checkpoints():
    """Get list of available model checkpoints"""
    checkpoint_dir = "checkpoints"
    if not os.path.exists(checkpoint_dir):
        return []

    checkpoints = glob.glob(os.path.join(checkpoint_dir, "*.pth"))
    return [os.path.basename(cp) for cp in checkpoints]


def get_data_directories():
    """Get list of available data directories"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        return []

    machine_types = [d for d in os.listdir(data_dir)
                     if os.path.isdir(os.path.join(data_dir, d))]
    return machine_types


@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get configuration data for UI"""
    return jsonify({
        'checkpoints': get_available_checkpoints(),
        'machine_types': get_data_directories(),
        'status': 'ready'
    })


@app.route('/api/train', methods=['POST'])
def train_model():
    """Start training process"""
    data = request.json

    # Build command - 使用当前Python解释器
    cmd = [
        sys.executable, 'src/train.py',  # 使用sys.executable，从项目根目录访问src目录
        '--train_dir', data['train_dir'],
        '--machine_type', data['machine_type']
    ]

    # 基本参数
    if data.get('output_dir'):
        cmd.extend(['--output_dir', data['output_dir']])
    if data.get('seed'):
        cmd.extend(['--seed', str(data['seed'])])

    # 训练参数
    cmd.extend([
        '--epochs', str(data.get('epochs', 150)),
        '--batch_size', str(data.get('batch_size', 32)),
        '--lr', str(data.get('lr', 0.001)),
        '--weight_decay', str(data.get('weight_decay', 0.0001))
    ])

    if data.get('optimizer'):
        cmd.extend(['--optimizer', data['optimizer']])
    if data.get('scheduler') and data['scheduler'] != 'none':
        cmd.extend(['--scheduler', data['scheduler']])
    if data.get('warmup_epochs'):
        cmd.extend(['--warmup_epochs', str(data['warmup_epochs'])])
    if data.get('num_workers'):
        cmd.extend(['--num_workers', str(data['num_workers'])])
    if data.get('save_interval'):
        cmd.extend(['--save_interval', str(data['save_interval'])])

    # 特征提取参数
    if data.get('sr'):
        cmd.extend(['--sr', str(data['sr'])])
    if data.get('n_mels'):
        cmd.extend(['--n_mels', str(data['n_mels'])])
    if data.get('n_fft'):
        cmd.extend(['--n_fft', str(data['n_fft'])])
    if data.get('hop_length'):
        cmd.extend(['--hop_length', str(data['hop_length'])])
    if data.get('fmin') is not None:
        cmd.extend(['--fmin', str(data['fmin'])])
    if data.get('fmax'):
        cmd.extend(['--fmax', str(data['fmax'])])
    if data.get('patch_frames'):
        cmd.extend(['--patch_frames', str(data['patch_frames'])])

    # 模型参数
    if data.get('width_mult'):
        cmd.extend(['--width_mult', str(data['width_mult'])])
    if data.get('dropout_rate') is not None:
        cmd.extend(['--dropout_rate', str(data['dropout_rate'])])

    # 数据增强参数
    if data.get('augmentation') is False:
        cmd.append('--no-augmentation')
    else:
        if data.get('aug_volume_min') is not None:
            cmd.extend(['--aug_volume_min', str(data['aug_volume_min'])])
        if data.get('aug_volume_max'):
            cmd.extend(['--aug_volume_max', str(data['aug_volume_max'])])
        if data.get('aug_time_shift') is not None:
            cmd.extend(['--aug_time_shift', str(data['aug_time_shift'])])
        if data.get('aug_freq_mask') is not None:
            cmd.extend(['--aug_freq_mask', str(data['aug_freq_mask'])])
        if data.get('aug_time_mask') is not None:
            cmd.extend(['--aug_time_mask', str(data['aug_time_mask'])])

    try:
        # 打印命令用于调试
        print(f"执行命令: {' '.join(cmd)}")
        socketio.emit('training_log', {'message': f"执行命令: {' '.join(cmd)}"})

        # Start training in background thread
        def run_training():
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                text=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 设置工作目录为项目根目录
            )
            current_processes['train'] = process

            # Stream output
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(line.strip())  # 同时打印到控制台
                    socketio.emit('training_log', {'message': line.strip()})

            process.wait()

            # 获取返回码
            returncode = process.returncode
            print(f"训练进程退出，返回码: {returncode}")

            socketio.emit('training_complete', {
                'returncode': returncode,
                'message': '训练完成' if returncode == 0 else f'训练失败 (退出码: {returncode})'
            })

            if 'train' in current_processes:
                del current_processes['train']

        thread = threading.Thread(target=run_training)
        thread.daemon = True
        thread.start()

        return jsonify({'status': 'started', 'message': '训练进程已启动'})

    except Exception as e:
        print(f"启动训练失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/test', methods=['POST'])
def test_model():
    """Start testing process"""
    data = request.json

    # Build command - 使用当前Python解释器
    cmd = [
        sys.executable, 'tests/test_improved_scoring.py',  # 使用sys.executable，从项目根目录访问tests目录
        '--checkpoint', data['checkpoint'],
        '--train_dir', data['train_dir'],
        '--test_dir', data['test_dir'],
        '--machine_type', data['machine_type']
    ]

    # Optional parameters
    if data.get('patch_frames'):
        cmd.extend(['--patch_frames', str(data['patch_frames'])])
    if data.get('hop_frames'):
        cmd.extend(['--hop_frames', str(data['hop_frames'])])

    try:
        # 打印命令用于调试
        print(f"执行命令: {' '.join(cmd)}")
        socketio.emit('testing_log', {'message': f"执行命令: {' '.join(cmd)}"})

        # Start testing in background thread
        def run_testing():
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                text=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 设置工作目录为项目根目录
            )
            current_processes['test'] = process

            output_buffer = []
            # Stream output
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(line.strip())  # 同时打印到控制台
                    output_buffer.append(line.strip())
                    socketio.emit('testing_log', {'message': line.strip()})

            process.wait()

            # 获取返回码
            returncode = process.returncode
            print(f"测试进程退出，返回码: {returncode}")

            # Parse results
            results = parse_test_results(output_buffer)

            socketio.emit('testing_complete', {
                'returncode': returncode,
                'message': '测试完成' if returncode == 0 else f'测试失败 (退出码: {returncode})',
                'results': results
            })

            if 'test' in current_processes:
                del current_processes['test']

        thread = threading.Thread(target=run_testing)
        thread.daemon = True
        thread.start()

        return jsonify({'status': 'started', 'message': '测试进程已启动'})

    except Exception as e:
        print(f"启动测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


def parse_test_results(output_lines):
    """Parse test output to extract AUC scores"""
    results = {}
    for line in output_lines:
        if 'Baseline' in line and 'AUC' not in line:
            parts = line.split('.')
            if len(parts) > 1:
                try:
                    results['baseline'] = float(parts[-1].strip())
                except:
                    pass
        elif 'Mean Based' in line:
            parts = line.split('.')
            if len(parts) > 1:
                try:
                    results['mean_based'] = float(parts[-1].strip())
                except:
                    pass
        elif 'Comprehensive' in line:
            parts = line.split('.')
            if len(parts) > 1:
                try:
                    results['comprehensive'] = float(parts[-1].strip())
                except:
                    pass
        elif 'Best AUC' in line:
            parts = line.split(':')
            if len(parts) > 1:
                try:
                    results['best_auc'] = float(parts[-1].strip())
                except:
                    pass
    return results


@socketio.on('start_realtime')
def handle_start_realtime(data):
    """Start real-time detection"""
    global realtime_thread, realtime_active

    if realtime_active:
        emit('realtime_status', {'status': 'error', 'message': '实时检测已在运行中'})
        return

    realtime_active = True

    # Build command - 使用当前Python解释器
    cmd = [
        sys.executable, 'src/realtime_detection_websocket.py',  # 使用sys.executable，从项目根目录访问src目录
        '--checkpoint', data['checkpoint'],
        '--source', data['source'],
        '--device', data.get('device', 'cuda'),
        '--threshold', str(data.get('threshold', 2.0)),
        '--patch_frames', str(data.get('patch_frames', 64)),
        '--buffer_duration', str(data.get('buffer_duration', 10.0)),
        '--hop_duration', str(data.get('hop_duration', 0.5))
    ]

    # 音频播放
    if data.get('enable_playback', False):
        cmd.append('--enable_playback')

    if data['source'] == 'file' and data.get('audio_file'):
        cmd.extend(['--audio_file', data['audio_file']])
        # 添加realtime参数
        if data.get('realtime', False):
            cmd.append('--realtime')
    if data.get('device_id') is not None:
        cmd.extend(['--device_id', str(data['device_id'])])

    # 打印命令用于调试
    print(f"执行实时检测命令: {' '.join(cmd)}")

    def run_realtime():
        global realtime_active
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # 保持分离，因为stderr有日志信息
                text=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # 设置工作目录为项目根目录
                universal_newlines=True  # 确保文本模式
            )
            current_processes['realtime'] = process

            print("实时检测进程已启动")
            socketio.emit('realtime_status', {'status': 'started', 'message': '实时检测已启动'})

            # 读取stderr日志的线程
            def read_stderr():
                try:
                    for line in iter(process.stderr.readline, ''):
                        if line.strip():
                            log_msg = line.strip()
                            print(f"[STDERR] {log_msg}")
                            socketio.emit('realtime_log', {'message': log_msg})
                except Exception as e:
                    print(f"stderr读取错误: {e}")

            stderr_thread = threading.Thread(target=read_stderr)
            stderr_thread.daemon = True
            stderr_thread.start()

            # Stream output
            output_count = 0
            for line in iter(process.stdout.readline, ''):
                if not realtime_active:
                    print("收到停止信号，终止进程")
                    process.terminate()
                    break

                if line.strip():
                    output_count += 1
                    try:
                        # Try to parse as JSON
                        data_json = json.loads(line.strip())
                        print(f"[JSON数据 #{output_count}] 检测结果")
                        socketio.emit('realtime_data', data_json)
                    except json.JSONDecodeError:
                        # Regular log message
                        log_msg = line.strip()
                        print(f"[STDOUT] {log_msg}")
                        socketio.emit('realtime_log', {'message': log_msg})

            process.wait()
            socketio.emit('realtime_stopped', {
                'message': '实时检测已停止',
                'returncode': process.returncode
            })

        except Exception as e:
            socketio.emit('realtime_status', {'status': 'error', 'message': str(e)})
        finally:
            realtime_active = False
            if 'realtime' in current_processes:
                del current_processes['realtime']

    realtime_thread = threading.Thread(target=run_realtime)
    realtime_thread.daemon = True
    realtime_thread.start()


@socketio.on('stop_realtime')
def handle_stop_realtime():
    """Stop real-time detection"""
    global realtime_active

    realtime_active = False

    if 'realtime' in current_processes:
        process = current_processes['realtime']
        process.terminate()
        emit('realtime_status', {'status': 'stopped', 'message': '实时检测已停止'})
    else:
        emit('realtime_status', {'status': 'error', 'message': '没有运行中的实时检测'})


@app.route('/api/stop/<task>', methods=['POST'])
def stop_task(task):
    """Stop a running task"""
    if task in current_processes:
        current_processes[task].terminate()
        del current_processes[task]
        return jsonify({'status': 'stopped', 'message': f'{task} 已停止'})
    return jsonify({'status': 'error', 'message': f'{task} 未运行'}), 404


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get status of all tasks"""
    return jsonify({
        'training': 'train' in current_processes,
        'testing': 'test' in current_processes,
        'realtime': realtime_active
    })


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('web/templates', exist_ok=True)
    os.makedirs('web/static', exist_ok=True)
    os.makedirs('checkpoints', exist_ok=True)
    os.makedirs('results_step1', exist_ok=True)

    print("=" * 60)
    print("音频异常检测 Web 界面")
    print("=" * 60)
    print(f"Python解释器: {sys.executable}")
    print(f"工作目录: {os.path.abspath('.')}")
    print("服务器启动地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
