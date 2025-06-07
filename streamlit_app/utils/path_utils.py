"""
路径工具模块
提供统一的路径解析功能，解决相对路径在不同工作目录下的问题
"""

import os
from pathlib import Path
from typing import Union


def get_project_root() -> Path:
    """获取项目根目录的绝对路径
    
    Returns:
        Path: 项目根目录的绝对路径
    """
    # 从当前文件位置向上查找项目根目录
    current_file = Path(__file__).resolve()
    
    # streamlit_app/utils/path_utils.py -> 项目根目录
    project_root = current_file.parent.parent.parent
    
    return project_root


def get_absolute_path(relative_path: str) -> Path:
    """将相对路径转换为绝对路径
    
    Args:
        relative_path: 相对于项目根目录的路径
        
    Returns:
        Path: 绝对路径
    """
    project_root = get_project_root()
    
    # 清理路径中的 '../' 前缀
    cleaned_path = relative_path.lstrip('../')
    
    return project_root / cleaned_path


def get_google_video_path() -> Path:
    """获取Google Video目录的绝对路径
    
    Returns:
        Path: Google Video目录的绝对路径
    """
    return get_absolute_path("data/output/google_video")


def get_video_pool_path() -> Path:
    """获取Video Pool目录的绝对路径
    
    Returns:
        Path: Video Pool目录的绝对路径
    """
    return get_absolute_path("data/output/google_video/video_pool")


def get_output_path() -> Path:
    """获取输出目录的绝对路径
    
    Returns:
        Path: 输出目录的绝对路径
    """
    return get_absolute_path("data/output")


def ensure_path_exists(path: Path) -> bool:
    """确保路径存在，如果不存在则创建
    
    Args:
        path: 要检查/创建的路径
        
    Returns:
        bool: 路径是否存在（或成功创建）
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        return False


def validate_paths() -> dict:
    """验证所有关键路径是否存在
    
    Returns:
        dict: 路径验证结果
    """
    paths_to_check = {
        "project_root": get_project_root(),
        "google_video": get_google_video_path(),
        "video_pool": get_video_pool_path(),
        "output": get_output_path()
    }
    
    results = {}
    for name, path in paths_to_check.items():
        results[name] = {
            "path": str(path),
            "exists": path.exists(),
            "is_absolute": path.is_absolute()
        }
    
    return results 