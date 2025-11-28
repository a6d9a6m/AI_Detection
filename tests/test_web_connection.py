"""
测试Web界面连接
快速验证Flask服务器是否正常工作
"""

import requests
import sys

def test_connection():
    """测试服务器连接"""
    try:
        print("正在测试连接到 http://localhost:5000...")
        response = requests.get('http://localhost:5000/api/config', timeout=5)

        if response.status_code == 200:
            data = response.json()
            print("✓ 服务器连接成功!")
            print(f"✓ 状态: {data.get('status')}")
            print(f"✓ 可用checkpoints: {len(data.get('checkpoints', []))}")
            print(f"✓ 可用机器类型: {len(data.get('machine_types', []))}")
            return True
        else:
            print(f"✗ 服务器响应异常: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器")
        print("  请确保已运行: python src/app.py")
        return False
    except Exception as e:
        print(f"✗ 连接测试失败: {str(e)}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("音频异常检测 Web 界面 - 连接测试")
    print("=" * 60)
    print()

    success = test_connection()

    print()
    print("=" * 60)
    if success:
        print("测试通过! 可以在浏览器中打开: http://localhost:5000")
    else:
        print("测试失败! 请检查服务器是否正在运行")
    print("=" * 60)

    sys.exit(0 if success else 1)
