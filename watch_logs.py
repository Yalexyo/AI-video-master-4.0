#!/usr/bin/env python3
"""
实时日志监控脚本
"""

import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

def get_latest_log_file():
    """获取最新的日志文件"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return None
    
    log_files = list(logs_dir.glob("streamlit_debug_*.log"))
    if not log_files:
        return None
    
    # 按修改时间排序，返回最新的
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    return latest_log

def monitor_logs():
    """监控日志文件"""
    print("🔍 正在查找最新的日志文件...")
    
    log_file = get_latest_log_file()
    if not log_file:
        print("❌ 没有找到日志文件")
        return
    
    print(f"📝 监控日志文件: {log_file}")
    print("=" * 80)
    print("💡 提示: 按 Ctrl+C 停止监控")
    print("=" * 80)
    
    try:
        # 使用tail命令实时监控日志
        process = subprocess.Popen(
            ['tail', '-f', str(log_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        for line in process.stdout:
            # 添加颜色和格式
            if "ERROR" in line:
                print(f"🔴 {line.strip()}")
            elif "WARNING" in line or "WARN" in line:
                print(f"🟡 {line.strip()}")
            elif "INFO" in line:
                print(f"🔵 {line.strip()}")
            elif "DEBUG" in line:
                print(f"🔷 {line.strip()}")
            else:
                print(f"⚪ {line.strip()}")
                
    except KeyboardInterrupt:
        print("\n👋 日志监控已停止")
        if process:
            process.terminate()
    except Exception as e:
        print(f"❌ 监控出错: {e}")

def show_current_logs():
    """显示当前日志内容"""
    log_file = get_latest_log_file()
    if not log_file:
        print("❌ 没有找到日志文件")
        return
    
    print(f"📖 当前日志内容 ({log_file}):")
    print("=" * 80)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if "ERROR" in line:
                print(f"🔴 {line}")
            elif "WARNING" in line or "WARN" in line:
                print(f"🟡 {line}")
            elif "INFO" in line:
                print(f"🔵 {line}")
            elif "DEBUG" in line:
                print(f"🔷 {line}")
            else:
                print(f"⚪ {line}")
                
    except Exception as e:
        print(f"❌ 读取日志失败: {e}")

if __name__ == "__main__":
    print("🎥 AI视频分析大师 - 日志监控工具")
    print("=" * 80)
    
    # 首先显示当前日志
    show_current_logs()
    
    print("\n" + "=" * 80)
    print("🔄 开始实时监控...")
    print("=" * 80)
    
    # 然后开始实时监控
    monitor_logs() 