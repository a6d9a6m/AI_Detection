"""
测试实时检测脚本是否能正常运行
"""
import subprocess
import sys
import os

def test_realtime_detection():
    """测试实时检测脚本"""
    print("测试实时检测脚本...")
    print(f"Python: {sys.executable}")
    print(f"工作目录: {os.getcwd()}")
    print()

    # 测试命令
    cmd = [
        sys.executable,
        'src/realtime_detection_websocket.py',
        '--checkpoint', 'checkpoints/model_fan_best.pth',
        '--source', 'file',
        '--audio_file', 'data/fan/target_test/section_00_target_test_anomaly_0000.wav',
        '--device', 'cpu',  # 使用CPU避免CUDA问题
        '--threshold', '2.0',
        '--patch_frames', '64',
        '--buffer_duration', '5.0',  # 短一点以便快速测试
        '--hop_duration', '0.5'
    ]

    print(f"执行命令: {' '.join(cmd)}")
    print("=" * 60)
    print()

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # 读取输出
        import threading

        def read_stream(stream, prefix):
            for line in iter(stream.readline, ''):
                if line:
                    print(f"[{prefix}] {line.rstrip()}")

        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, "STDOUT"))
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, "STDERR"))

        stdout_thread.daemon = True
        stderr_thread.daemon = True

        stdout_thread.start()
        stderr_thread.start()

        # 等待3秒
        import time
        time.sleep(3)

        # 终止进程
        process.terminate()
        process.wait(timeout=2)

        print()
        print("=" * 60)
        print(f"测试完成，返回码: {process.returncode}")

        return process.returncode == 0 or process.returncode == -15  # -15是SIGTERM

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_realtime_detection()
    print()
    if success:
        print("✓ 实时检测脚本可以正常运行")
    else:
        print("✗ 实时检测脚本运行失败")
