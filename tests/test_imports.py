"""
快速验证实时检测脚本导入是否正常
"""

import sys
import os

def test_imports():
    """测试所有必需的导入"""
    print("=" * 60)
    print("测试实时检测脚本导入")
    print("=" * 60)
    print()

    try:
        print("1. 测试 features.LogMelExtractor...")
        from src.features import LogMelExtractor
        print("   ✓ LogMelExtractor 导入成功")
    except ImportError as e:
        print(f"   ✗ LogMelExtractor 导入失败: {e}")
        return False

    try:
        print("2. 测试 model.MobileNetV2...")
        from src.model import MobileNetV2
        print("   ✓ MobileNetV2 导入成功")
    except ImportError as e:
        print(f"   ✗ MobileNetV2 导入失败: {e}")
        return False

    try:
        print("3. 测试实例化 MobileNetV2...")
        model = MobileNetV2(num_classes=3, width_mult=1.0, dropout_rate=0.2)
        print("   ✓ MobileNetV2 实例化成功")
        print(f"   模型类型: {type(model)}")
    except Exception as e:
        print(f"   ✗ MobileNetV2 实例化失败: {e}")
        return False

    try:
        print("4. 测试导入 realtime_detection_websocket...")
        from src.realtime_detection_websocket import RealtimeAnomalyDetectorWebSocket
        print("   ✓ RealtimeAnomalyDetectorWebSocket 导入成功")
    except ImportError as e:
        print(f"   ✗ RealtimeAnomalyDetectorWebSocket 导入失败: {e}")
        return False

    print()
    print("=" * 60)
    print("✓ 所有导入测试通过！")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)
