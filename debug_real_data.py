#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
真实数据调试脚本 - 测试真实JSON文件的分类情况
"""

import sys
import os
import json

# 添加路径
sys.path.append('streamlit_app')

def test_real_json_file():
    """测试真实的JSON文件"""
    print("🧪 测试真实JSON文件...")
    
    # 使用第一个JSON文件
    json_file = "data/output/google_video/video_pool/1_analysis_intelligent_strategy_20250605_162906.json"
    
    if not os.path.exists(json_file):
        print(f"❌ JSON文件不存在: {json_file}")
        return
    
    # 导入mapper
    from modules.mapper import VideoSegmentMapper
    mapper = VideoSegmentMapper()
    
    # 读取JSON文件
    with open(json_file, 'r', encoding='utf-8') as f:
        video_data = json.load(f)
    
    segments = video_data.get('segments', [])
    print(f"📋 找到 {len(segments)} 个片段")
    
    # 测试前5个片段
    for i, segment in enumerate(segments[:5]):
        print(f"\n🔍 测试片段 {i+1}: {segment.get('file_name', 'unknown')}")
        
        # 提取基本信息
        all_tags = segment.get('all_tags', [])
        file_name = segment.get('file_name', '')
        
        print(f"   原始all_tags: {all_tags}")
        
        # 如果all_tags为空，尝试从旧格式构建
        if not all_tags:
            print("   🔧 all_tags为空，从旧格式构建...")
            raw_fields = [
                segment.get('object', ''),
                segment.get('scene', ''),
                segment.get('emotion', ''),
                segment.get('brand_elements', '')
            ]
            
            print(f"   旧格式字段: object='{segment.get('object', '')}', scene='{segment.get('scene', '')}', emotion='{segment.get('emotion', '')}', brand_elements='{segment.get('brand_elements', '')}'")
            
            all_tags = []
            for raw_field in raw_fields:
                if not raw_field:
                    continue
                    
                # 处理逗号分隔的情况
                if ',' in raw_field:
                    tags = raw_field.split(',')
                else:
                    tags = [raw_field]
                
                # 清理和添加标签
                for tag in tags:
                    clean_tag = tag.strip()
                    if clean_tag and clean_tag not in all_tags:
                        all_tags.append(clean_tag)
            
            print(f"   构建的all_tags: {all_tags}")
        
        # 跳过空标签片段
        if not all_tags:
            print("   ❌ 标签为空，跳过")
            continue
        
        # 模拟时长检查（简化版）
        duration = 5.0  # 假设5秒，在10秒限制内
        
        # 进行分类
        try:
            category = mapper.classify_segment_by_tags(all_tags)
            print(f"   🎯 分类结果: {category}")
            
            # 如果分类为None，进行详细调试
            if not category:
                print("   🔍 分类为None，进行详细分析...")
                
                tags_text = " ".join(all_tags).lower()
                
                # 检查排除关键词
                is_excluded = mapper._is_excluded_by_negative_keywords(tags_text)
                print(f"      排除检查: {is_excluded}")
                
                if not is_excluded:
                    # 检查各模块匹配
                    modules_priority = ["痛点", "卖点·成分&配方", "解决方案导入", "促销机制"]
                    
                    for module in modules_priority:
                        if module not in mapper.rules:
                            continue
                            
                        module_config = mapper.rules[module]
                        if not isinstance(module_config, dict):
                            continue
                        
                        # 检查negative_keywords
                        negative_keywords = module_config.get("negative_keywords", [])
                        has_negative = False
                        matched_negative = []
                        for neg_kw in negative_keywords:
                            if neg_kw.lower() in tags_text:
                                has_negative = True
                                matched_negative.append(neg_kw)
                        
                        if has_negative:
                            print(f"      🚫 模块 {module} 被排除: {matched_negative}")
                            continue
                        
                        # 检查正面关键词
                        match_score = 0
                        matched_keywords = []
                        
                        for keyword_type in ["object_keywords", "scene_keywords", "emotion_keywords"]:
                            keywords = module_config.get(keyword_type, [])
                            for kw in keywords:
                                if kw.lower() in tags_text:
                                    match_score += 1
                                    matched_keywords.append(f"{keyword_type}:{kw}")
                        
                        min_score_threshold = module_config.get("min_score_threshold", 0.3)
                        print(f"      📊 模块 {module}: 分数={match_score}, 阈值={min_score_threshold}, 匹配={matched_keywords}")
            
        except Exception as e:
            print(f"   ❌ 分类失败: {e}")

def main():
    print("🚀 开始真实数据调试...")
    test_real_json_file()
    print("\n✅ 调试完成!")

if __name__ == "__main__":
    main() 