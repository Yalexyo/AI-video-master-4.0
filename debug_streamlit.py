#!/usr/bin/env python3
"""
带调试日志的Streamlit启动脚本
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

def setup_logging():
    """设置详细的调试日志"""
    # 创建logs目录
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # 设置日志文件名（带时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = logs_dir / f"streamlit_debug_{timestamp}.log"
    
    # 配置日志格式
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"调试日志已启动，日志文件: {log_file}")
    return logger, log_file

def check_environment():
    """检查环境配置"""
    logger = logging.getLogger(__name__)
    
    logger.info("🔍 检查环境配置...")
    
    # 检查Python版本
    logger.info(f"Python版本: {sys.version}")
    
    # 检查工作目录
    logger.info(f"工作目录: {os.getcwd()}")
    
    # 检查关键环境变量
    google_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    dashscope_key = os.environ.get('DASHSCOPE_API_KEY')
    
    logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {google_creds or '未设置'}")
    logger.info(f"DASHSCOPE_API_KEY: {'已设置' if dashscope_key else '未设置'}")
    
    # 检查关键文件
    key_files = [
        "streamlit_app/主页.py",
        "streamlit_app/pages/🔬_Google_Cloud_视频智能测试.py",
        "streamlit_app/modules/ai_analyzers/google_video_analyzer.py"
    ]
    
    for file_path in key_files:
        if os.path.exists(file_path):
            logger.info(f"✅ 文件存在: {file_path}")
        else:
            logger.error(f"❌ 文件缺失: {file_path}")
    
    return google_creds, dashscope_key

def setup_env_variables():
    """设置环境变量"""
    logger = logging.getLogger(__name__)
    
    # 设置Python路径
    current_path = os.getcwd()
    python_path = os.environ.get('PYTHONPATH', '')
    if current_path not in python_path:
        new_python_path = f"{current_path}:{python_path}" if python_path else current_path
        os.environ['PYTHONPATH'] = new_python_path
        logger.info(f"✅ 设置PYTHONPATH: {new_python_path}")
    
    # 设置Google Cloud凭据
    google_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not google_creds:
        default_creds = "data/temp/google_cloud/video-ai-461014-d0c437ff635f.json"
        if os.path.exists(default_creds):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = default_creds
            logger.info(f"✅ 自动设置Google Cloud凭据: {default_creds}")
        else:
            logger.warning("⚠️ Google Cloud凭据未设置")
    
    # 设置Streamlit配置
    streamlit_env = {
        'STREAMLIT_SERVER_PORT': '8501',
        'STREAMLIT_SERVER_HEADLESS': 'true',
        'STREAMLIT_LOGGER_LEVEL': 'debug',
        'STREAMLIT_SERVER_ENABLE_CORS': 'false',
        'STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION': 'false'
    }
    
    for key, value in streamlit_env.items():
        os.environ[key] = value
        logger.debug(f"设置环境变量: {key}={value}")

def main():
    """主函数"""
    logger, log_file = setup_logging()
    
    logger.info("=" * 60)
    logger.info("🚀 启动AI视频分析大师 - 调试模式")
    logger.info("=" * 60)
    
    # 检查环境
    google_creds, dashscope_key = check_environment()
    
    # 设置环境变量
    setup_env_variables()
    
    # 构建启动命令
    cmd = [
        'streamlit', 'run', 'streamlit_app/主页.py',
        '--server.port', '8501',
        '--logger.level', 'debug',
        '--server.headless', 'true'
    ]
    
    logger.info(f"🎯 启动命令: {' '.join(cmd)}")
    logger.info(f"📝 详细日志记录到: {log_file}")
    
    print("\n" + "=" * 60)
    print("🎥 AI视频分析大师 4.0 - 调试模式启动")
    print("=" * 60)
    print(f"📝 日志文件: {log_file}")
    print(f"🌐 访问地址: http://localhost:8501")
    print(f"🔧 Google Cloud凭据: {'已设置' if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') else '未设置'}")
    print(f"🔑 DashScope API: {'已设置' if dashscope_key else '未设置'}")
    print("=" * 60)
    print("💡 在另一个终端运行 'python watch_logs.py' 实时监控日志")
    print("💡 按 Ctrl+C 停止服务")
    print("=" * 60)
    
    try:
        # 启动Streamlit
        logger.info("🚀 正在启动Streamlit...")
        
        # 使用Popen以便可以捕获输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 实时输出日志
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(f"Streamlit: {output.strip()}")
        
        return_code = process.poll()
        logger.info(f"Streamlit进程结束，退出码: {return_code}")
        
    except KeyboardInterrupt:
        logger.info("👋 收到停止信号，正在关闭...")
        if 'process' in locals():
            process.terminate()
        print("\n👋 服务已停止")
        
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 