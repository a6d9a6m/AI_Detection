"""
路径配置
统一管理项目输出路径
"""
import os

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 核心目录
SRC = os.path.join(ROOT, 'src')
WEB = os.path.join(ROOT, 'web')

# 结果输出目录
RESULTS = os.path.join(SRC, 'results')
MODELS = os.path.join(RESULTS, 'models')
CHECKPOINTS = os.path.join(RESULTS, 'checkpoints')
VISUALIZATIONS = os.path.join(RESULTS, 'visualizations')
REPORTS = os.path.join(RESULTS, 'reports')
FEATURES = os.path.join(RESULTS, 'features')

# checkpoint子目录
FEATURE_EXTRACTION_CHECKPOINTS = os.path.join(CHECKPOINTS, 'feature_extraction')

# 数据库
DATABASE = os.path.join(ROOT, 'database.db')


def init():
    """初始化所有输出目录"""
    dirs = [
        RESULTS, MODELS, CHECKPOINTS, VISUALIZATIONS,
        REPORTS, FEATURES, FEATURE_EXTRACTION_CHECKPOINTS
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print(f"[Paths] Initialized: {RESULTS}")


def model_path(machine_type: str, task_id: str) -> str:
    """获取模型路径"""
    return os.path.join(MODELS, f"model_{machine_type}_{task_id}.pth")


def checkpoint_path(machine_type: str, name: str) -> str:
    """获取checkpoint路径"""
    return os.path.join(CHECKPOINTS, f"{machine_type}_{name}")


def viz_path(filename: str) -> str:
    """获取可视化文件路径"""
    return os.path.join(VISUALIZATIONS, filename)


def report_path(filename: str) -> str:
    """获取报告路径"""
    return os.path.join(REPORTS, filename)


def feature_path(filename: str) -> str:
    """获取特征路径"""
    return os.path.join(FEATURES, filename)


def feature_checkpoint_path(task_id: str) -> str:
    """获取特征提取checkpoint路径"""
    return os.path.join(FEATURE_EXTRACTION_CHECKPOINTS, f"{task_id}.json")
