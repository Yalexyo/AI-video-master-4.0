import os
from dotenv import load_dotenv
import logging
from pathlib import Path
import json

# 加载环境变量
load_dotenv()

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent

# 用户自定义配置文件路径
USER_CONFIG_FILE = os.path.join(ROOT_DIR, "data", "user_config.json")

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 默认配置（作为备选）
DEFAULT_TARGET_GROUPS = [
    "孕期妈妈",
    "二胎妈妈", 
    "混养妈妈",
    "新手爸妈",
    "贵妇妈妈"
]

DEFAULT_PRODUCT_TYPES = [
    "启赋水奶", 
    "启赋蕴淳",
    "启赋蓝钻"
]

DEFAULT_SELLING_POINTS = [
    "HMO & 母乳低聚糖",
    "自愈力",
    "品牌实力",
    "A2奶源",
    "开盖即饮",
    "精准配比"
]

# 默认语义片段类型列表
DEFAULT_SEMANTIC_SEGMENT_TYPES = [
    "广告开场", "问题陈述", "产品介绍", "产品优势", 
    "行动号召", "用户反馈", "专家背书", "品牌理念", "总结收尾", "其他"
]

# 默认语义类型详细定义
DEFAULT_SEMANTIC_TYPE_DEFINITIONS = {
    "广告开场": {
        "name": "广告开场",
        "description": "视频的起始部分，用于吸引观众、引入品牌、Slogan或奠定视频基调。通常是视频的第一个独立语义单元。",
        "keywords": ["开场白", "品牌介绍", "slogan", "吸引注意", "视频开始"],
        "examples": ["大家好，我是xxx", "今天要给大家介绍", "启赋奶粉带来"]
    },
    "问题陈述": {
        "name": "问题陈述", 
        "description": "描绘用户（通常是妈妈）在育儿过程中遇到的痛点、困扰，或宝宝在成长、喂养、健康方面面临的具体问题、挑战。也包括通过场景对比、情景再现等方式引发观众对相关问题的共鸣。",
        "keywords": ["问题", "困扰", "痛点", "挑战", "困难", "担心"],
        "examples": ["宝宝经常哭闹", "奶水不足怎么办", "选择什么奶粉好"]
    },
    "产品介绍": {
        "name": "产品介绍",
        "description": "详细介绍产品的核心特性、主要成分、配方技术、规格参数、设计特点、原料来源等客观信息，并自然过渡到这些特性所带来的直接益处和功效。强调产品\"是什么\"以及它\"能带来什么基础效果\"。",
        "keywords": ["成分", "配方", "技术", "特性", "规格", "设计"],
        "examples": ["含有HMO母乳低聚糖", "A2奶源", "精准配比"]
    },
    "产品优势": {
        "name": "产品优势",
        "description": "强调产品与同类竞品相比的独特之处、核心竞争力或特殊价值。例如\"独有配方\"、\"专利技术\"、\"更好吸收\"、\"更安全\"等对比性或优越性表述。",
        "keywords": ["独有", "专利", "更好", "优于", "领先", "唯一"],
        "examples": ["独有配方技术", "更易吸收", "领先同行"]
    },
    "行动号召": {
        "name": "行动号召",
        "description": "明确引导或鼓励用户采取具体行动，如\"立即购买\"、\"扫码了解更多\"、\"参与活动\"、\"领取优惠\"等直接指令性话语。",
        "keywords": ["购买", "扫码", "了解更多", "参与", "领取", "行动"],
        "examples": ["立即购买", "扫码关注", "点击链接"]
    },
    "用户反馈": {
        "name": "用户反馈",
        "description": "直接或间接展示来自真实用户的评价、使用体验、推荐语或使用前后的对比故事。通常带有主观色彩和用户口吻。",
        "keywords": ["用户说", "体验", "评价", "推荐", "效果好", "满意"],
        "examples": ["用户反馈说", "使用效果很好", "妈妈们都推荐"]
    },
    "专家背书": {
        "name": "专家背书",
        "description": "视频中出现明确的专家身份（如医生、营养师、科学家、育儿博主）或权威机构，并由他们对产品进行推荐、肯定、解释原理或验证效果。强调\"谁说\"的重要性。",
        "keywords": ["专家", "医生", "营养师", "权威", "认证", "推荐"],
        "examples": ["专家推荐", "医生建议", "营养师认证"]
    },
    "品牌理念": {
        "name": "品牌理念",
        "description": "传递品牌的核心价值观、使命、愿景、对消费者的承诺、品牌故事或其在行业中的定位和追求。通常较为抽象和概括性，区别于具体的\"产品介绍\"。可能出现在开场、结尾或穿插于视频中。",
        "keywords": ["理念", "价值观", "使命", "愿景", "承诺", "品牌故事"],
        "examples": ["我们的使命是", "品牌理念", "始终坚持"]
    },
    "总结收尾": {
        "name": "总结收尾",
        "description": "视频的结束部分，对前面内容进行概括、再次强调核心卖点或品牌信息，或给出明确的结束语、感谢语。",
        "keywords": ["总结", "总之", "最后", "感谢", "结束", "再次强调"],
        "examples": ["总之", "最后想说", "感谢大家观看"]
    },
    "其他": {
        "name": "其他",
        "description": "用于标记那些无法明确归入以上任何特定类别的、独立的文本内容。应尽量少用，仅在确实无法分类时使用。",
        "keywords": ["其他", "未分类", "无法归类"],
        "examples": ["过渡性内容", "无明确分类的片段"]
    }
}

def load_user_config():
    """加载用户自定义配置"""
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载用户配置失败: {e}，使用默认配置")
    return {}

def save_config(config_data):
    """保存用户配置到文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(USER_CONFIG_FILE), exist_ok=True)
        
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        logger.info(f"用户配置已保存到: {USER_CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"保存用户配置失败: {e}")
        return False

# 动态加载配置
user_config = load_user_config()

# 定义目标人群列表 (优先使用用户自定义配置)
TARGET_GROUPS = user_config.get("TARGET_GROUPS", DEFAULT_TARGET_GROUPS)

# 定义产品类型列表
PRODUCT_TYPES = user_config.get("PRODUCT_TYPES", DEFAULT_PRODUCT_TYPES)

# 定义核心卖点列表
SELLING_POINTS = user_config.get("SELLING_POINTS", DEFAULT_SELLING_POINTS)

# 定义品牌关键词和产品视觉元素列表 (从video_intent_matcher.py)
BRAND_KEYWORDS = ["启赋", "蕴淳", "水奶", "母乳低聚糖", "HMO", "A2奶源"]
PRODUCT_VISUAL_ELEMENTS = ["奶粉罐", "成分列表", "奶粉勺子", "奶粉罐特写"]

# 定义语义类型详细定义 (优先使用用户自定义配置)
SEMANTIC_TYPE_DEFINITIONS = user_config.get("SEMANTIC_TYPE_DEFINITIONS", DEFAULT_SEMANTIC_TYPE_DEFINITIONS)

# 兼容性：保持原有的静态配置作为默认值
SEMANTIC_SEGMENT_TYPES = DEFAULT_SEMANTIC_SEGMENT_TYPES
# 包含所有SEMANTIC_SEGMENT_TYPES中的类型
SEMANTIC_MODULES = SEMANTIC_SEGMENT_TYPES

def get_semantic_type_definitions():
    """获取语义类型定义"""
    return SEMANTIC_TYPE_DEFINITIONS

def get_semantic_type_definition(semantic_type: str):
    """获取单个语义类型的详细定义
    
    Args:
        semantic_type: 语义类型名称
        
    Returns:
        dict: 包含name, description, keywords, examples的定义字典
    """
    return SEMANTIC_TYPE_DEFINITIONS.get(semantic_type, {
        "name": semantic_type,
        "description": f"用于标记{semantic_type}类型的内容。",
        "keywords": [],
        "examples": []
    })

# 应用配置
def get_config():
    """返回应用的主要配置参数"""
    # 重新加载用户配置以获取最新设置
    current_user_config = load_user_config()
    
    base_config = {
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
        # 添加用户自定义配置
        "TARGET_GROUPS": current_user_config.get("TARGET_GROUPS", DEFAULT_TARGET_GROUPS),
        "PRODUCT_TYPES": current_user_config.get("PRODUCT_TYPES", DEFAULT_PRODUCT_TYPES),
        "SELLING_POINTS": current_user_config.get("SELLING_POINTS", DEFAULT_SELLING_POINTS),
    }
    
    # 合并用户自定义配置
    base_config.update(current_user_config)
    return base_config

# 路径配置
def get_paths_config():
    """返回应用使用的文件路径配置"""
    return {
        "segments_dir": os.path.join(ROOT_DIR, "data", "processed", "segments"),
        "intent_matcher_dir": os.path.join(ROOT_DIR, "data", "processed", "intent_matcher"),
        "transcripts_dir": os.path.join(ROOT_DIR, "data", "processed", "transcripts"),
        "frames_dir": os.path.join(ROOT_DIR, "data", "processed", "frames"),
    }

def get_semantic_segment_types():
    """获取语义分段类型列表（支持用户自定义）"""
    config = get_config()
    return config.get("SEMANTIC_SEGMENT_TYPES", DEFAULT_SEMANTIC_SEGMENT_TYPES)

def get_semantic_modules():
    """获取语义模块列表（与语义分段类型相同）"""
    return get_semantic_segment_types() 