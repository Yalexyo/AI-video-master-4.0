#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试视频片段组织功能
"""

import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler('logs/organize_test.log')  # 输出到文件
    ]
)
logger = logging.getLogger("organize_test")

# 添加项目根目录到系统路径
current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

# 导入视频组织器
from streamlit_app.modules.data_process.video_organizer import organize_segments_by_type

if __name__ == "__main__":
    logger.info("开始测试视频组织功能...")
    
    # 确保data/output目录存在
    output_dir = os.path.join(root_dir, "data", "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")
    
    # 运行组织功能
    try:
        success = organize_segments_by_type()
        if success:
            logger.info("视频片段组织成功完成！")
            print("视频片段已成功按语义类型组织")
        else:
            logger.warning("视频片段组织返回失败！")
            print("视频片段组织失败，请查看日志")
    except Exception as e:
        logger.error(f"视频片段组织出错: {str(e)}", exc_info=True)
        print(f"错误: {str(e)}") 