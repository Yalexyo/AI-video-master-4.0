#!/usr/bin/env python3
"""
清除Streamlit缓存脚本
用于解决片段重复和缓存过期问题
"""

import os
import shutil
import sys
from pathlib import Path

def clear_streamlit_cache():
    """清除Streamlit缓存"""
    print("🧹 开始清除Streamlit缓存...")
    
    # 常见的Streamlit缓存目录
    cache_dirs = [
        Path.home() / ".streamlit" / "cache",
        Path.cwd() / ".streamlit" / "cache", 
        Path("/tmp") / "streamlit",
        Path.home() / ".cache" / "streamlit"
    ]
    
    cleared_count = 0
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
                print(f"✅ 已清除: {cache_dir}")
                cleared_count += 1
            except Exception as e:
                print(f"❌ 清除失败: {cache_dir} - {e}")
    
    # 清除项目中的缓存文件
    project_cache_files = [
        "**/__pycache__",
        "**/*.pyc",
        ".pytest_cache"
    ]
    
    for pattern in project_cache_files:
        for path in Path.cwd().glob(pattern):
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
                print(f"✅ 已清除项目缓存: {path.name}")
                cleared_count += 1
            except Exception as e:
                print(f"❌ 清除项目缓存失败: {path} - {e}")
    
    print(f"🎯 缓存清除完成！共清除 {cleared_count} 项")
    print("💡 建议重新启动应用以确保缓存完全刷新")

if __name__ == "__main__":
    clear_streamlit_cache() 