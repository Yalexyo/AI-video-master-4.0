import os
from dotenv import load_dotenv
import logging
from pathlib import Path

# 加载环境变量
load_dotenv()

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义目标人群列表 (从targetANDsellingpoints.py)
TARGET_GROUPS = [
    "孕期妈妈",
    "二胎妈妈",
    "混养妈妈",
    "新手爸妈",
    "贵妇妈妈"
]

# 定义产品类型列表
PRODUCT_TYPES = [
    "启赋水奶", 
    "启赋蕴淳",
    "启赋蓝钻"
]

# 定义核心卖点列表 (从targetANDsellingpoints.py)
SELLING_POINTS = [
    "HMO & 母乳低聚糖",
    "自愈力",
    "品牌实力",
    "A2奶源",
    "开盖即饮",
    "精准配比"
]

# 定义品牌关键词和产品视觉元素列表 (从video_intent_matcher.py)
BRAND_KEYWORDS = ["启赋", "蕴淳", "水奶", "母乳低聚糖", "HMO", "A2奶源"]
PRODUCT_VISUAL_ELEMENTS = ["奶粉罐", "成分列表", "奶粉勺子", "奶粉罐特写"]

# 新增：定义语义分段类型
SEMANTIC_SEGMENT_TYPES = [
    "广告开场",  # 品牌介绍、开场白
    "问题陈述",  # 描绘用户痛点、宝宝面临的挑战或引发焦虑的场景
    "产品介绍",  # 介绍奶粉产品的特性和成分，及其直接带来的功效
    "产品优势",  # 比较优势或独特卖点
    "行动号召",  # 鼓励购买或尝试
    "用户反馈",  # 用户评价、使用体验
    "专家背书",  # 医生、营养师等推荐
    "品牌理念",  # 介绍品牌故事、理念、价值观等
    "总结收尾",  # 对视频内容进行总结或再次强调核心信息
    "其他"      # 未能明确归类的其他内容
]

# 核心语义模块类型（用于UI展示）
# 包含所有SEMANTIC_SEGMENT_TYPES中的类型
SEMANTIC_MODULES = SEMANTIC_SEGMENT_TYPES

# 应用配置
def get_config():
    """返回应用的主要配置参数"""
    return {
        "app_name": "AI 视频分析与合成系统",
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY"),
        "aliyun_access_key_id": os.getenv("OSS_ACCESS_KEY_ID"),
        "aliyun_access_key_secret": os.getenv("OSS_ACCESS_KEY_SECRET"),
        "hotword_id": os.getenv("HOTWORD_ID", "vocab-aivideo-4d73bdb1b5ef496d94f5104a957c012b"),
        "data_dir": os.path.join(ROOT_DIR, "data"),
        "input_dir": os.path.join(ROOT_DIR, "data", "input"),
        "output_dir": os.path.join(ROOT_DIR, "data", "output"),
        "temp_dir": os.path.join(ROOT_DIR, "data", "temp"),
        "processed_dir": os.path.join(ROOT_DIR, "data", "processed"),
        "ref_video_dir": os.path.join(ROOT_DIR, "data", "input", "ref_video"),
        "target_video_dir": os.path.join(ROOT_DIR, "data", "input", "target_video"),
        "debug_mode": os.getenv("DEBUG", "False").lower() == "true",
        "use_sentence_transformer": True,  # 启用SentenceTransformer
        "sentence_transformer_local_path": os.path.join(ROOT_DIR, "models", "sentence-transformers"),  # 本地模型路径
    }

# 路径配置
def get_paths_config():
    """返回应用使用的文件路径配置"""
    return {
        "segments_dir": os.path.join(ROOT_DIR, "data", "processed", "segments"),
        "intent_matcher_dir": os.path.join(ROOT_DIR, "data", "processed", "intent_matcher"),
        "transcripts_dir": os.path.join(ROOT_DIR, "data", "processed", "transcripts"),
        "frames_dir": os.path.join(ROOT_DIR, "data", "processed", "frames"),
    } 