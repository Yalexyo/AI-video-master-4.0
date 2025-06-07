"""
工厂通用配置文件
为零件工厂和组装工厂提供集中配置管理
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class FactoryConfig:
    """工厂通用配置类"""
    
    # 零件工厂配置
    class PartsFactory:
        """零件工厂配置"""
        APP_NAME = "🧫 零件工厂"
        PAGE_ICON = "🧫"
        LAYOUT = "wide"
        
        # 路径配置
        DEFAULT_OUTPUT_DIR = "data/input/test_videos"
        SUPPORTED_VIDEO_FORMATS = ['mp4', 'avi', 'mov', 'wmv', 'mkv']
        
        # 转录配置
        DEFAULT_HOTWORD_ID = "vocab-aivideo-4d73bdb1b5ef496d94f5104a957c012b"  # 🔧 使用实际的预设热词ID
        ENABLE_HOTWORDS_DEFAULT = True
        CLEANUP_TEMP_DEFAULT = True
    
    # 组装工厂配置
    class AssemblyFactory:
        """组装工厂配置"""
        APP_NAME = "🧱 组装工厂"
        PAGE_ICON = "🧱"
        LAYOUT = "wide"
        
        # 路径配置 - 使用绝对路径
        @classmethod
        def get_video_pool_path(cls) -> str:
            """获取video pool路径"""
            from streamlit_app.utils.path_utils import get_google_video_path
            return str(get_google_video_path())
        
        @classmethod
        def get_output_path(cls) -> str:
            """获取输出路径"""
            from streamlit_app.utils.path_utils import get_output_path
            return str(get_output_path())
        
        DEFAULT_VIDEO_POOL_PATH = None  # 动态获取
        DEFAULT_OUTPUT_PATH = None  # 动态获取
        
        # API配置
        DEEPSEEK_ENABLED = True
        DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
        GOOGLE_CLOUD_ENABLED = True
        QWEN_ENABLED = True
        
        # 分析配置
        DEFAULT_BATCH_SIZE = 2
        MIN_EMPTY_TAGS = 2
        AUTO_MERGE_RESULTS = True
        
        # 聚类配置
        DEFAULT_SIMILARITY_THRESHOLD = 0.8
        DEFAULT_MIN_SCENE_DURATION = 3.0
        DEFAULT_MAX_SCENES = 10
        
        # 支持的视频格式
        SUPPORTED_VIDEO_FORMATS = ['mp4', 'avi', 'mov', 'wmv', 'mkv']
        
        # 支持的图片格式
        SUPPORTED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'bmp']
    
    # 通用配置
    CACHE_TTL = 3600  # 缓存时间(秒)
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = "DEBUG" if DEBUG_MODE else "INFO"
    
    # 视觉分析配置
    VISUAL_ANALYSIS_CONFIG = {
        "default_frame_rate": 2.0,
        "max_frames_per_video": 10,
        "image_quality": 85,
        "max_image_size": (1024, 1024),
        "analysis_timeout": 30,
        # 🎯 NEW: 人脸特写检测配置
        "face_close_up_detection": {
            "enabled": True,
            "face_area_threshold": 0.3,  # 人脸占画面30%以上认为是特写
            "frame_sampling_count": 3,   # 采样帧数
            "detection_confidence": 0.5, # 检测阈值
            "keywords": [
                "人脸", "面部", "头像", "特写", "肖像", "脸部",
                "眼睛", "嘴唇", "鼻子", "面孔", "头部特写"
            ]
        }
    }
    
    @classmethod
    def get_parts_config(cls) -> Dict[str, Any]:
        """获取零件工厂配置"""
        return {
            "app_name": cls.PartsFactory.APP_NAME,
            "page_icon": cls.PartsFactory.PAGE_ICON,
            "layout": cls.PartsFactory.LAYOUT,
            "default_output_dir": cls.PartsFactory.DEFAULT_OUTPUT_DIR,
            "supported_video_formats": cls.PartsFactory.SUPPORTED_VIDEO_FORMATS,
            "default_hotword_id": cls.PartsFactory.DEFAULT_HOTWORD_ID,
            "enable_hotwords_default": cls.PartsFactory.ENABLE_HOTWORDS_DEFAULT,
            "cleanup_temp_default": cls.PartsFactory.CLEANUP_TEMP_DEFAULT,
            "cache_ttl": cls.CACHE_TTL,
            "debug_mode": cls.DEBUG_MODE,
            "log_level": cls.LOG_LEVEL
        }
    
    @classmethod
    def get_assembly_config(cls) -> Dict[str, Any]:
        """获取组装工厂配置"""
        return {
            "app_name": cls.AssemblyFactory.APP_NAME,
            "page_icon": cls.AssemblyFactory.PAGE_ICON,
            "layout": cls.AssemblyFactory.LAYOUT,
            "default_video_pool_path": cls.AssemblyFactory.get_video_pool_path(),
            "default_output_path": cls.AssemblyFactory.get_output_path(),
            "deepseek_enabled": cls.AssemblyFactory.DEEPSEEK_ENABLED,
            "deepseek_api_key": cls.AssemblyFactory.DEEPSEEK_API_KEY,
            "google_cloud_enabled": cls.AssemblyFactory.GOOGLE_CLOUD_ENABLED,
            "qwen_enabled": cls.AssemblyFactory.QWEN_ENABLED,
            "default_batch_size": cls.AssemblyFactory.DEFAULT_BATCH_SIZE,
            "min_empty_tags": cls.AssemblyFactory.MIN_EMPTY_TAGS,
            "auto_merge_results": cls.AssemblyFactory.AUTO_MERGE_RESULTS,
            "default_similarity_threshold": cls.AssemblyFactory.DEFAULT_SIMILARITY_THRESHOLD,
            "default_min_scene_duration": cls.AssemblyFactory.DEFAULT_MIN_SCENE_DURATION,
            "default_max_scenes": cls.AssemblyFactory.DEFAULT_MAX_SCENES,
            "supported_video_formats": cls.AssemblyFactory.SUPPORTED_VIDEO_FORMATS,
            "supported_image_formats": cls.AssemblyFactory.SUPPORTED_IMAGE_FORMATS,
            "cache_ttl": cls.CACHE_TTL,
            "debug_mode": cls.DEBUG_MODE,
            "log_level": cls.LOG_LEVEL
        }
    
    @classmethod
    def validate_parts_config(cls) -> Dict[str, bool]:
        """验证零件工厂配置"""
        checks = {
            "output_dir_writable": os.access(
                os.path.dirname(cls.PartsFactory.DEFAULT_OUTPUT_DIR), os.W_OK
            ) if os.path.exists(os.path.dirname(cls.PartsFactory.DEFAULT_OUTPUT_DIR)) else False,
            "transcribe_module_available": True  # 稍后检查
        }
        return checks
    
    @classmethod
    def validate_assembly_config(cls) -> Dict[str, bool]:
        """验证组装工厂配置"""
        video_pool_path = cls.AssemblyFactory.get_video_pool_path()
        output_path = cls.AssemblyFactory.get_output_path()
        
        checks = {
            "video_pool_path_exists": os.path.exists(video_pool_path),
            "deepseek_api_key_set": bool(cls.AssemblyFactory.DEEPSEEK_API_KEY),
            "output_path_writable": os.access(
                os.path.dirname(output_path), os.W_OK
            ) if os.path.exists(os.path.dirname(output_path)) else False
        }
        return checks 