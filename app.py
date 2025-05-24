"""
视频分析大师 1.0 - 主入口

启动方式: streamlit run app.py
"""

import os
import subprocess
import sys

# 确保当前工作目录是项目根目录
if __name__ == "__main__":
    # 设置环境变量
    os.environ["PYTHONPATH"] = os.getcwd()
    
    # 使用subprocess启动Streamlit应用
    streamlit_app_path = os.path.join(os.path.dirname(__file__), "streamlit_app", "🔍_分析.py")
    
    try:
        subprocess.run(["streamlit", "run", streamlit_app_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"启动Streamlit应用失败: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("找不到streamlit命令，请确保已安装Streamlit")
        print("可以使用命令安装: pip install streamlit")
        sys.exit(1) 