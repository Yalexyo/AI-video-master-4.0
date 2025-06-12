"""
混剪工厂配置文件
集中管理所有配置参数，避免硬编码
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class MixingConfig:
    """混剪工厂配置类"""
    
    # 应用基本配置
    APP_NAME = "🧪 混剪工厂"
    PAGE_ICON = "🧪"
    LAYOUT = "wide"
    
    # 默认路径配置 - 使用绝对路径
    @classmethod
    def get_video_pool_path(cls) -> str:
        """获取video pool路径"""
        from utils.path_utils import get_video_pool_path
        return str(get_video_pool_path())
    
    @classmethod
    def get_output_path(cls) -> str:
        """获取输出路径"""
        from utils.path_utils import get_output_path
        return str(get_output_path())
    
    DEFAULT_VIDEO_POOL_PATH = None  # 动态获取
    DEFAULT_OUTPUT_PATH = None  # 动态获取
    
    # 视频处理配置
    DEFAULT_TARGET_DURATION = 60  # 默认目标时长(秒)
    DEFAULT_RESOLUTION = "1920x1080"  # 默认分辨率
    DEFAULT_BITRATE = "5000k"  # 默认比特率
    DEFAULT_FPS = 30  # 默认帧率
    
    # 质量预设
    QUALITY_PRESETS = {
        "高清 (1080p)": {"resolution": "1920x1080", "bitrate": "5000k", "fps": 30},
        "标清 (720p)": {"resolution": "1280x720", "bitrate": "3000k", "fps": 30},
        "竖屏高清 (1080p)": {"resolution": "1080x1920", "bitrate": "5000k", "fps": 30}
    }
    
    # 时长比例模板
    DURATION_RATIO_TEMPLATES = {
        "均衡模式": {"痛点": 0.25, "解决方案": 0.25, "卖点": 0.25, "促销": 0.25},
        "痛点导向": {"痛点": 0.4, "解决方案": 0.3, "卖点": 0.2, "促销": 0.1},
        "产品优势": {"痛点": 0.2, "解决方案": 0.2, "卖点": 0.4, "促销": 0.2},
        "促销重点": {"痛点": 0.2, "解决方案": 0.2, "卖点": 0.2, "促销": 0.4}
    }
    
    # 模块分类
    MODULES = ["痛点", "解决方案", "卖点", "促销"]
    
    # 缓存配置
    CACHE_TTL = 3600  # 缓存时间(秒)
    
    # AI配置
    DEEPSEEK_ENABLED = True
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    # 调试配置
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = "DEBUG" if DEBUG_MODE else "INFO"
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """获取完整配置字典"""
        return {
            "app_name": cls.APP_NAME,
            "page_icon": cls.PAGE_ICON,
            "layout": cls.LAYOUT,
            "default_video_pool_path": cls.get_video_pool_path(),
            "default_output_path": cls.get_output_path(),
            "default_target_duration": cls.DEFAULT_TARGET_DURATION,
            "default_resolution": cls.DEFAULT_RESOLUTION,
            "default_bitrate": cls.DEFAULT_BITRATE,
            "default_fps": cls.DEFAULT_FPS,
            "quality_presets": cls.QUALITY_PRESETS,
            "duration_ratio_templates": cls.DURATION_RATIO_TEMPLATES,
            "modules": cls.MODULES,
            "cache_ttl": cls.CACHE_TTL,
            "deepseek_enabled": cls.DEEPSEEK_ENABLED,
            "deepseek_api_key": cls.DEEPSEEK_API_KEY,
            "debug_mode": cls.DEBUG_MODE,
            "log_level": cls.LOG_LEVEL
        }
    
    @classmethod
    def validate_config(cls) -> Dict[str, bool]:
        """验证配置是否正确"""
        video_pool_path = cls.get_video_pool_path()
        output_path = cls.get_output_path()
        
        checks = {
            "video_pool_path_exists": os.path.exists(video_pool_path),
            "deepseek_api_key_set": bool(cls.DEEPSEEK_API_KEY),
            "output_path_writable": os.access(
                os.path.dirname(output_path), os.W_OK
            ) if os.path.exists(os.path.dirname(output_path)) else False
        }
        return checks 