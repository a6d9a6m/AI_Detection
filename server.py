"""
音频异常检测系统 - Web服务器启动脚本
"""
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web', 'services'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from web.services.api import app

if __name__ == '__main__':
    print("=" * 60)
    print("Audio Anomaly Detection System - API Server")
    print("=" * 60)
    print(f"Server starting at http://0.0.0.0:5000")
    print(f"API Documentation: see API_DOCUMENTATION.md")
    print("=" * 60)

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
