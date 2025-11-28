"""
API基本功能测试脚本
测试核心API端点是否正常工作
"""

import requests
import json
import sys
import os

# API基础URL
BASE_URL = "http://localhost:5000"

# 测试结果统计
test_results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}


def log_test(test_name, success, message=""):
    """记录测试结果"""
    if success:
        print(f"✅ {test_name}: PASSED")
        test_results['passed'] += 1
    else:
        print(f"❌ {test_name}: FAILED - {message}")
        test_results['failed'] += 1
        test_results['errors'].append({'test': test_name, 'message': message})


def test_health_check():
    """测试健康检查端点"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        success = response.status_code == 200 and response.json().get('status') == 'ok'
        log_test("Health Check", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("Health Check", False, str(e))
        return False


def test_user_registration():
    """测试用户注册"""
    try:
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com'
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=data)

        # 如果用户已存在，也算成功
        success = response.status_code in [201, 409]
        log_test("User Registration", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("User Registration", False, str(e))
        return False


def test_user_login():
    """测试用户登录"""
    try:
        # 使用默认管理员账号
        data = {
            'username': 'admin',
            'password': 'admin123'
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
        success = response.status_code == 200

        if success:
            # 返回session cookie
            return True, response.cookies
        else:
            log_test("User Login", False, response.text)
            return False, None
    except Exception as e:
        log_test("User Login", False, str(e))
        return False, None


def test_get_current_user(session_cookies):
    """测试获取当前用户信息"""
    try:
        response = requests.get(f"{BASE_URL}/api/auth/me", cookies=session_cookies)
        success = response.status_code == 200
        log_test("Get Current User", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("Get Current User", False, str(e))
        return False


def test_list_voiceprints(session_cookies):
    """测试获取声纹列表"""
    try:
        response = requests.get(f"{BASE_URL}/api/voiceprints", cookies=session_cookies)
        success = response.status_code == 200
        log_test("List Voiceprints", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("List Voiceprints", False, str(e))
        return False


def test_upload_voiceprint(session_cookies):
    """测试上传声纹数据"""
    try:
        # 创建一个测试文件（如果不存在）
        test_file_path = os.path.join(os.path.dirname(__file__), 'test_audio.wav')

        # 如果没有测试文件，跳过此测试
        if not os.path.exists(test_file_path):
            # 尝试使用现有的音频文件
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'fan', 'train')
            if os.path.exists(data_dir):
                # 找到第一个.wav文件
                for file in os.listdir(data_dir):
                    if file.endswith('.wav'):
                        test_file_path = os.path.join(data_dir, file)
                        break

            if not os.path.exists(test_file_path):
                log_test("Upload Voiceprint", False, "No test audio file available")
                return False

        with open(test_file_path, 'rb') as f:
            files = {'file': ('test.wav', f, 'audio/wav')}
            data = {'machine_type': 'fan', 'section': '00'}
            response = requests.post(f"{BASE_URL}/api/voiceprints",
                                    files=files, data=data, cookies=session_cookies)

        success = response.status_code == 201
        log_test("Upload Voiceprint", success, response.text if not success else "")

        if success:
            return True, response.json().get('data_id')
        return False, None
    except Exception as e:
        log_test("Upload Voiceprint", False, str(e))
        return False, None


def test_search_voiceprints(session_cookies):
    """测试搜索声纹"""
    try:
        response = requests.get(f"{BASE_URL}/api/voiceprints/search?q=fan",
                               cookies=session_cookies)
        success = response.status_code == 200
        log_test("Search Voiceprints", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("Search Voiceprints", False, str(e))
        return False


def test_list_models(session_cookies):
    """测试获取模型列表"""
    try:
        response = requests.get(f"{BASE_URL}/api/models", cookies=session_cookies)
        success = response.status_code == 200
        log_test("List Models", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("List Models", False, str(e))
        return False


def test_list_reports(session_cookies):
    """测试获取报告列表"""
    try:
        response = requests.get(f"{BASE_URL}/api/reports", cookies=session_cookies)
        success = response.status_code == 200
        log_test("List Reports", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("List Reports", False, str(e))
        return False


def test_create_api_key(session_cookies):
    """测试创建API密钥"""
    try:
        data = {
            'name': 'Test API Key',
            'permissions': ['read', 'write']
        }
        response = requests.post(f"{BASE_URL}/api/keys", json=data, cookies=session_cookies)
        success = response.status_code == 201
        log_test("Create API Key", success, response.text if not success else "")

        if success:
            return True, response.json().get('api_key')
        return False, None
    except Exception as e:
        log_test("Create API Key", False, str(e))
        return False, None


def test_system_status(session_cookies):
    """测试系统状态"""
    try:
        response = requests.get(f"{BASE_URL}/api/system/status", cookies=session_cookies)
        success = response.status_code == 200
        log_test("System Status", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("System Status", False, str(e))
        return False


def test_generate_report(session_cookies):
    """测试生成报告"""
    try:
        config = {
            'title': 'Test Report',
            'report_type': 'anomaly_detection',
            'format': 'pdf',
            'content': {
                'test': 'This is a test report'
            }
        }
        response = requests.post(f"{BASE_URL}/api/reports/generate",
                                json=config, cookies=session_cookies)
        success = response.status_code == 201
        log_test("Generate Report", success, response.text if not success else "")
        return success
    except Exception as e:
        log_test("Generate Report", False, str(e))
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("API基本功能测试")
    print("=" * 60)
    print(f"\n测试目标: {BASE_URL}\n")

    # 测试1: 健康检查
    print("\n[1] 健康检查测试")
    if not test_health_check():
        print("\n⚠️  API服务器未运行或不可访问！")
        print("请先启动API服务器: python src/api_app.py")
        return

    # 测试2: 用户注册
    print("\n[2] 用户管理测试")
    test_user_registration()

    # 测试3: 用户登录
    success, session_cookies = test_user_login()
    if not success:
        print("\n⚠️  用户登录失败，后续测试无法继续！")
        print_summary()
        return

    log_test("User Login", True)

    # 测试4: 获取当前用户
    test_get_current_user(session_cookies)

    # 测试5: 声纹数据管理
    print("\n[3] 声纹数据管理测试")
    test_list_voiceprints(session_cookies)
    upload_success, data_id = test_upload_voiceprint(session_cookies)
    test_search_voiceprints(session_cookies)

    # 测试6: 模型管理
    print("\n[4] 模型管理测试")
    test_list_models(session_cookies)

    # 测试7: 报告管理
    print("\n[5] 报告管理测试")
    test_list_reports(session_cookies)
    test_generate_report(session_cookies)

    # 测试8: API密钥
    print("\n[6] API密钥管理测试")
    test_create_api_key(session_cookies)

    # 测试9: 系统监控
    print("\n[7] 系统监控测试")
    test_system_status(session_cookies)

    # 打印汇总
    print_summary()


def print_summary():
    """打印测试汇总"""
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"总测试数: {test_results['passed'] + test_results['failed']}")
    print(f"✅ 通过: {test_results['passed']}")
    print(f"❌ 失败: {test_results['failed']}")

    if test_results['failed'] > 0:
        print("\n失败的测试:")
        for error in test_results['errors']:
            print(f"  - {error['test']}: {error['message'][:100]}")

    print("=" * 60)

    # 计算通过率
    total = test_results['passed'] + test_results['failed']
    if total > 0:
        pass_rate = (test_results['passed'] / total) * 100
        print(f"\n通过率: {pass_rate:.1f}%")

        if pass_rate >= 90:
            print("🎉 测试通过率优秀！")
        elif pass_rate >= 70:
            print("👍 测试通过率良好！")
        elif pass_rate >= 50:
            print("⚠️  测试通过率一般，需要改进。")
        else:
            print("❌ 测试通过率较低，需要修复问题。")


if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断。")
        print_summary()
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        print_summary()
