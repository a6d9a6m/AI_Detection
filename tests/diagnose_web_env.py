"""
Web界面环境诊断脚本
检查环境配置是否正确
"""

import sys
import os

def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    version = sys.version_info
    print(f"  Python版本: {version.major}.{version.minor}.{version.micro}")
    print(f"  Python路径: {sys.executable}")

    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("  ⚠️  警告: Python版本过低，建议使用3.7+")
        return False
    else:
        print("  ✓ Python版本正常")
        return True

def check_virtual_env():
    """检查是否在虚拟环境中"""
    print("\n检查虚拟环境...")
    in_venv = hasattr(sys, 'prefix') and sys.prefix != sys.base_prefix

    if in_venv:
        print(f"  ✓ 在虚拟环境中: {sys.prefix}")
        return True
    else:
        print("  ⚠️  未在虚拟环境中")
        print("  建议激活虚拟环境: venv\\Scripts\\activate")
        return False

def check_required_packages():
    """检查必需的包"""
    print("\n检查必需的Python包...")

    required_packages = {
        'flask': 'Flask',
        'flask_socketio': 'Flask-SocketIO',
        'torch': 'PyTorch',
        'numpy': 'NumPy',
        'librosa': 'Librosa',
    }

    all_installed = True
    for module_name, display_name in required_packages.items():
        try:
            __import__(module_name)
            print(f"  ✓ {display_name} 已安装")
        except ImportError:
            print(f"  ✗ {display_name} 未安装")
            all_installed = False

    if not all_installed:
        print("\n  安装缺失的包:")
        print("    pip install -r requirements_web.txt")

    return all_installed

def check_files():
    """检查必需的文件"""
    print("\n检查必需的文件...")

    required_files = [
        'src/app.py',
        'src/train.py',
        'tests/test_improved_scoring.py',
        'src/realtime_detection_websocket.py',
        'src/web/templates/index.html',
        'src/web/static/style.css',
        'src/web/static/app.js'
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} 缺失")
            all_exist = False

    return all_exist

def check_directories():
    """检查必需的目录"""
    print("\n检查必需的目录...")

    required_dirs = [
        'src/web/templates',
        'src/web/static',
        'checkpoints',
    ]

    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ⚠️  {dir_path}/ 不存在，将自动创建")
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"     已创建 {dir_path}/")
            except Exception as e:
                print(f"     创建失败: {e}")

    return True

def main():
    print("=" * 60)
    print("音频异常检测 Web 界面 - 环境诊断")
    print("=" * 60)
    print()

    results = []

    results.append(("Python版本", check_python_version()))
    results.append(("虚拟环境", check_virtual_env()))
    results.append(("必需包", check_required_packages()))
    results.append(("必需文件", check_files()))
    results.append(("必需目录", check_directories()))

    print("\n" + "=" * 60)
    print("诊断结果汇总:")
    print("=" * 60)

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有检查通过！")
        print("\n可以启动Web界面:")
        print("  方式1: python src/app.py")
        print("  方式2: start_web_ui_auto.bat (Windows)")
    else:
        print("✗ 部分检查未通过，请根据上述提示修复问题")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == '__main__':
    exit(main())
