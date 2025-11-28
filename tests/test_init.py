"""
初始化并测试系统
"""

import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 60)
print("音频异常检测系统 - 初始化测试")
print("=" * 60)

# 步骤1: 测试导入
print("\n[1/4] 测试模块导入...")
try:
    from models import Database, User, VoiceprintData, Model
    print("✅ models.py 导入成功")
except Exception as e:
    print(f"❌ models.py 导入失败: {e}")
    sys.exit(1)

try:
    from training_service import training_manager, feature_manager, evaluation_manager
    print("✅ training_service.py 导入成功")
except Exception as e:
    print(f"❌ training_service.py 导入失败: {e}")
    sys.exit(1)

try:
    from report_service import report_generator, template_manager
    print("✅ report_service.py 导入成功")
except Exception as e:
    print(f"❌ report_service.py 导入失败: {e}")
    sys.exit(1)

# 步骤2: 初始化数据库
print("\n[2/4] 初始化数据库...")
try:
    db = Database()
    print("✅ 数据库初始化成功")
    print(f"   数据库路径: {db.db_path}")
except Exception as e:
    print(f"❌ 数据库初始化失败: {e}")
    sys.exit(1)

# 步骤3: 验证默认用户
print("\n[3/4] 验证默认管理员账号...")
try:
    admin = User.authenticate('admin', 'admin123')
    if admin:
        print("✅ 默认管理员账号验证成功")
        print(f"   用户名: admin")
        print(f"   角色: {admin['role']}")
    else:
        print("❌ 默认管理员账号验证失败")
        sys.exit(1)
except Exception as e:
    print(f"❌ 用户验证失败: {e}")
    sys.exit(1)

# 步骤4: 检查API应用
print("\n[4/4] 检查API应用...")
try:
    from api_app import app
    print("✅ API应用加载成功")
    print(f"   Flask应用: {app.name}")
except Exception as e:
    print(f"❌ API应用加载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 总结
print("\n" + "=" * 60)
print("初始化测试完成！")
print("=" * 60)
print("\n下一步:")
print("1. 启动API服务器: python src/api_app.py")
print("2. 运行API测试: python tests/test_api_basic.py")
print("\n默认管理员账号:")
print("  用户名: admin")
print("  密码: admin123")
print("=" * 60)
