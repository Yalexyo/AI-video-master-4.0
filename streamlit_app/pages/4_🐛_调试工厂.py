import streamlit as st
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

# 设置日志
logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="🐛 调试工厂 - AI视频混剪系统",
    page_icon="🐛",
    layout="wide"
)

def main():
    """调试工厂主界面"""
    
    st.title("🐛 调试工厂")
    st.markdown("**实时查看映射机制、过滤规则和选片过程的详细信息**")
    
    # 侧边栏 - 调试选项
    with st.sidebar:
        st.header("🔧 调试选项")
        
        debug_mode = st.selectbox(
            "选择调试模式",
            ["映射规则检查", "过滤机制测试", "选片决策日志"]
        )
        
        st.markdown("---")
    
    # 主要内容区域
    if debug_mode == "映射规则检查":
        render_mapping_rules_debug()
    elif debug_mode == "过滤机制测试":
        render_filter_mechanism_debug()
    elif debug_mode == "选片决策日志":
        render_selection_decision_log()

def render_mapping_rules_debug():
    """渲染映射规则调试界面"""
    st.header("📋 映射规则详细检查")
    
    # 显示当前工作目录和配置文件路径信息
    current_dir = os.getcwd()
    st.info(f"🔍 当前工作目录: {current_dir}")
    
    # 尝试两个可能的配置文件路径
    config_paths = [
        "../config/matching_rules.json",  # 项目根目录
        "config/matching_rules.json"      # streamlit_app目录
    ]
    
    config_file = None
    for path in config_paths:
        abs_path = os.path.abspath(path)
        st.info(f"📁 检查配置文件: {path} -> {abs_path} (存在: {os.path.exists(path)})")
        if os.path.exists(path):
            config_file = path
            break
    
    if not config_file:
        st.error("❌ 配置文件不存在，请检查 config/matching_rules.json")
        return
    
    # 加载配置文件
    try:        
        with open(config_file, 'r', encoding='utf-8') as f:
            matching_rules = json.load(f)
    except Exception as e:
        st.error(f"加载配置文件失败: {e}")
        st.info("使用默认配置继续运行...")
        # 显示默认配置示例
        st.code("""
{
  "痛点": {
    "object_keywords": ["妈妈", "宝宝"],
    "negative_keywords": ["高速公路", "红绿灯", "驾驶"]
  }
}
        """, language="json")
        return
    
    # 配置加载成功，继续处理
    try:
            
        st.success(f"✅ 使用配置文件: {config_file}")
        
        # 显示文件状态信息
        try:
            file_stat = os.stat(config_file)
            mod_time = datetime.fromtimestamp(file_stat.st_mtime)
            st.info(f"📅 配置文件最后修改: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.info(f"📦 文件大小: {file_stat.st_size} bytes")
        except Exception as e:
            st.warning(f"无法获取文件信息: {e}")
            
        # 添加实时验证按钮
        if st.button("🔄 刷新配置文件状态", key="refresh_config_status"):
            st.rerun()
            
        # 显示各模块的规则
        modules = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
        
        for module in modules:
            if module in matching_rules:
                with st.expander(f"📋 **{module}** 完整规则", expanded=True):
                    rules = matching_rules[module]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("✅ 正面规则")
                        
                        # 🔧 可编辑的关键词配置
                        keyword_types = [
                            ("object_keywords", "对象关键词"),
                            ("sence_keywords", "场景关键词"), 
                            ("emotion_keywords", "情感关键词"),
                            ("required_keywords", "必需关键词")
                        ]
                        
                        for kw_type, kw_name in keyword_types:
                            st.write(f"**{kw_name}:**")
                            current_keywords = rules.get(kw_type, [])
                            
                            keywords_str = ", ".join(current_keywords)
                            new_keywords_str = st.text_area(
                                f"编辑 {module} {kw_name}",
                                value=keywords_str,
                                key=f"edit_{kw_type}_{module}",
                                height=80
                            )
                            
                            if st.button(f"💾 保存 {kw_name}", key=f"save_{kw_type}_{module}"):
                                new_keywords_list = [kw.strip() for kw in new_keywords_str.split(",") if kw.strip()]
                                
                                # 更新配置
                                matching_rules[module][kw_type] = new_keywords_list
                                
                                # 保存到文件
                                try:
                                    # 记录保存前的文件时间
                                    old_time = os.path.getmtime(config_file) if os.path.exists(config_file) else 0
                                    
                                    with open(config_file, 'w', encoding='utf-8') as f:
                                        json.dump(matching_rules, f, ensure_ascii=False, indent=2)
                                    
                                    # 验证保存是否成功
                                    if os.path.exists(config_file):
                                        new_time = os.path.getmtime(config_file)
                                        time_str = datetime.fromtimestamp(new_time).strftime("%H:%M:%S")
                                        
                                        if new_time > old_time:
                                            st.balloons()  # 添加气球动画
                                            st.success(f"🎉 {module} {kw_name} 保存成功!")
                                            st.success(f"⏰ 文件更新时间: {time_str}")
                                            st.success(f"📊 新关键词数量: {len(new_keywords_list)}")
                                        else:
                                            st.warning("⚠️ 文件时间未更新，可能保存失败")
                                    else:
                                        st.error(f"❌ 配置文件不存在: {config_file}")
                                    
                                    # 短暂延迟后刷新
                                    import time
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"💥 保存失败: {e}")
                                    st.error(f"📁 配置文件路径: {config_file}")
                                    st.error(f"🔍 文件是否存在: {os.path.exists(config_file)}")
                                    st.error(f"✍️ 尝试写入的内容长度: {len(str(matching_rules))}")
                    
                    with col2:
                        st.subheader("❌ 负面规则")
                        
                        if rules.get("negative_keywords"):
                            st.write("**排除关键词:**")
                            negative_list = rules["negative_keywords"]
                            
                            # 🔧 添加编辑功能
                            negative_str = ", ".join(negative_list)
                            new_negative_str = st.text_area(
                                f"编辑 {module} 排除关键词",
                                value=negative_str,
                                key=f"edit_negative_{module}",
                                height=80,
                                help="修改后点击保存按钮"
                            )
                            
                            # 保存按钮
                            if st.button(f"💾 保存 {module} 排除关键词", key=f"save_negative_{module}"):
                                new_negative_list = [kw.strip() for kw in new_negative_str.split(",") if kw.strip()]
                                
                                # 更新配置
                                matching_rules[module]["negative_keywords"] = new_negative_list
                                
                                # 保存到文件
                                try:
                                    with open(config_file, 'w', encoding='utf-8') as f:
                                        json.dump(matching_rules, f, ensure_ascii=False, indent=2)
                                    st.success(f"✅ {module} 排除关键词已保存!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"保存失败: {e}")
                            
                            # 🔥 重点突出排除关键词
                            if "高速公路" in negative_list or "红绿灯" in negative_list:
                                st.error("⚠️ **发现高速公路/红绿灯排除规则!**")
                                st.write("这些关键词应该被过滤，如果仍然出现请检查过滤逻辑!")
                        else:
                            st.info("该模块没有配置排除关键词")
                            
                            # 为没有排除关键词的模块添加新增功能
                            new_negative_str = st.text_area(
                                f"添加 {module} 排除关键词",
                                value="",
                                key=f"add_negative_{module}",
                                height=80,
                                placeholder="输入要排除的关键词，用逗号分隔"
                            )
                            
                            if st.button(f"➕ 添加 {module} 排除关键词", key=f"add_save_negative_{module}"):
                                if new_negative_str.strip():
                                    new_negative_list = [kw.strip() for kw in new_negative_str.split(",") if kw.strip()]
                                    
                                    # 更新配置
                                    matching_rules[module]["negative_keywords"] = new_negative_list
                                    
                                    # 保存到文件
                                    try:
                                        with open(config_file, 'w', encoding='utf-8') as f:
                                            json.dump(matching_rules, f, ensure_ascii=False, indent=2)
                                        st.success(f"✅ {module} 排除关键词已添加!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"保存失败: {e}")
                                else:
                                    st.warning("请输入要添加的关键词")
                        
                        # 显示权重和阈值
                        st.write("**权重配置:**")
                        if rules.get("weights"):
                            for weight_type, value in rules["weights"].items():
                                st.write(f"- {weight_type}: {value}")
                        
                        st.write("**质量阈值:**")
                        st.write(f"- 最小质量: {rules.get('min_quality', '未设置')}")
                        st.write(f"- 最小分数: {rules.get('min_score_threshold', '未设置')}")
        
        # 全局过滤规则
        if "GLOBAL_SETTINGS" in matching_rules:
            st.header("🌐 全局过滤规则")
            
            global_settings = matching_rules["GLOBAL_SETTINGS"]
            
            # 🔧 新增：显示全局排除关键词
            if "global_exclusion_keywords" in global_settings:
                st.subheader("🚫 全局排除关键词")
                current_global_keywords = global_settings["global_exclusion_keywords"]
                st.code(", ".join(current_global_keywords))
                st.warning("⚠️ 这些关键词会导致片段被全局过滤，不分模块")
                
                # 编辑全局排除关键词
                global_exclusion_str = ", ".join(current_global_keywords)
                new_global_exclusion_str = st.text_area(
                    "编辑全局排除关键词",
                    value=global_exclusion_str,
                    key="edit_global_exclusion",
                    help="包含这些关键词的片段将被完全过滤"
                )
                
                if st.button("💾 保存全局排除关键词", key="save_global_exclusion"):
                    new_keywords = [kw.strip() for kw in new_global_exclusion_str.split(",") if kw.strip()]
                    matching_rules["GLOBAL_SETTINGS"]["global_exclusion_keywords"] = new_keywords
                    
                    try:
                        with open(config_file, 'w', encoding='utf-8') as f:
                            json.dump(matching_rules, f, ensure_ascii=False, indent=2)
                        st.success("✅ 全局排除关键词已保存!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存失败: {e}")
            
            # 🔧 新增：显示分段约束
            if "max_segments_per_module" in global_settings:
                st.subheader("🔢 分段约束设置")
                current_max = global_settings["max_segments_per_module"]
                st.info(f"每个模块最大片段数: **{current_max}** 个")
                st.caption("这个设置防止单个模块有过多片段拼接，保持视频流畅性")
                
                new_max = st.number_input(
                    "设置每模块最大片段数",
                    min_value=1,
                    max_value=10,
                    value=current_max,
                    key="max_segments_input"
                )
                
                if st.button("💾 保存分段约束", key="save_max_segments"):
                    matching_rules["GLOBAL_SETTINGS"]["max_segments_per_module"] = new_max
                    
                    try:
                        with open(config_file, 'w', encoding='utf-8') as f:
                            json.dump(matching_rules, f, ensure_ascii=False, indent=2)
                        st.success(f"✅ 分段约束已保存: 每模块最多 {new_max} 个片段!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存失败: {e}")
            
            # 不相关场景分类
            st.subheader("🌐 不相关场景分类")
            irrelevant_categories = global_settings.get("irrelevant_scene_categories", {})
            
            for category, keywords in irrelevant_categories.items():
                with st.expander(f"🚫 {category} (全局排除)", expanded=False):
                    # 显示当前关键词
                    keywords_str = ", ".join(keywords)
                    new_global_keywords_str = st.text_area(
                        f"编辑 {category} 全局排除关键词",
                        value=keywords_str,
                        key=f"edit_global_{category}",
                        height=80
                    )
                    
                    if st.button(f"💾 保存 {category} 全局排除", key=f"save_global_{category}"):
                        new_global_keywords_list = [kw.strip() for kw in new_global_keywords_str.split(",") if kw.strip()]
                        
                        # 更新配置
                        matching_rules["GLOBAL_SETTINGS"]["irrelevant_scene_categories"][category] = new_global_keywords_list
                        
                        # 保存到文件
                        try:
                            with open(config_file, 'w', encoding='utf-8') as f:
                                json.dump(matching_rules, f, ensure_ascii=False, indent=2)
                            st.success(f"✅ {category} 全局排除关键词已保存!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"保存失败: {e}")
                    
                    # 检查关键词
                    if any(kw in ["高速公路", "红绿灯", "高速", "马路", "道路", "交通"] for kw in keywords):
                        st.error("🚨 **包含交通相关排除词!** 这些应该被全局过滤!")
        
        # 📋 配置文件验证区域
        st.markdown("---")
        st.header("📋 配置文件验证")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📁 文件状态检查")
            if st.button("🔍 检查配置文件", key="check_config_file"):
                try:
                    # 检查两个可能的配置文件位置
                    configs = [
                        ("项目根目录", "../config/matching_rules.json"),
                        ("Streamlit目录", "config/matching_rules.json")
                    ]
                    
                    for name, path in configs:
                        if os.path.exists(path):
                            stat = os.stat(path)
                            mod_time = datetime.fromtimestamp(stat.st_mtime)
                            st.success(f"✅ {name}: {path}")
                            st.info(f"   📅 修改时间: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            st.info(f"   📦 文件大小: {stat.st_size} bytes")
                        else:
                            st.error(f"❌ {name}: {path} 不存在")
                except Exception as e:
                    st.error(f"检查失败: {e}")
        
        with col2:
            st.subheader("📝 配置备份")
            if st.button("💾 创建配置备份", key="backup_config"):
                try:
                    import shutil
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = f"../config/matching_rules_backup_{timestamp}.json"
                    shutil.copy2(config_file, backup_path)
                    st.success(f"✅ 备份已创建: {backup_path}")
                except Exception as e:
                    st.error(f"备份失败: {e}")
        
        # 🧪 快速测试区域
        st.markdown("---")
        st.header("🧪 规则测试验证")
        st.info("修改规则后，立即测试效果")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 快速测试")
            quick_test_tags = st.text_input(
                "输入测试标签 (逗号分隔)",
                value="高速公路, 红绿灯",
                key="quick_test_input"
            )
            
            if st.button("⚡ 快速测试", key="quick_test_btn"):
                if quick_test_tags.strip():
                    test_tags = [tag.strip() for tag in quick_test_tags.split(",") if tag.strip()]
                    st.write("**测试结果:**")
                    
                    # 执行测试
                    try:
                        from streamlit_app.modules.mapper import VideoSegmentMapper
                        mapper = VideoSegmentMapper()
                        
                        result = mapper.classify_segment(test_tags)
                        tags_text = " ".join(test_tags).lower()
                        excluded = mapper._is_excluded_by_negative_keywords(tags_text)
                        
                        if excluded:
                            st.error(f"🚫 被排除过滤: **{result}**")
                        else:
                            st.success(f"✅ 分类结果: **{result}**")
                    
                    except Exception as e:
                        st.error(f"测试失败: {e}")
        
        with col2:
            st.subheader("📊 配置状态")
            st.metric("配置模块", len(modules))
            st.metric("全局排除类别", len(irrelevant_categories) if "GLOBAL_SETTINGS" in matching_rules else 0)
            
            # 显示最近修改时间
            try:
                if os.path.exists(config_file):
                    mtime = os.path.getmtime(config_file)
                    mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    st.info(f"配置文件最后修改: {mod_time}")
            except Exception as e:
                st.warning(f"无法获取文件修改时间: {e}")
    
    except Exception as e:
        st.error(f"处理配置文件时出现错误: {e}")
        st.info("请检查配置文件格式和权限...")

# 实时片段分析功能已删除 - 存在路径识别问题

def analyze_single_segment(tags_list: List[str]):
    """分析单个片段的详细过程"""
    st.subheader("🔬 详细分析过程")
    
    # 显示输入标签
    st.write("**输入标签:**")
    st.code(", ".join(tags_list))
    
    # 执行分类
    try:
        from streamlit_app.modules.mapper import VideoSegmentMapper
        mapper = VideoSegmentMapper()
        
        # 分步骤分析
        st.markdown("---")
        st.subheader("📊 分类步骤")
        
        # 第一步：检查排除关键词
        st.write("**🚫 第一步：排除关键词检查**")
        
        # 加载排除规则
        config_file = "../config/matching_rules.json"  # 使用项目根目录的配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            matching_rules = json.load(f)
        
        exclusion_hits = []
        tags_text = " ".join(tags_list).lower()
        
        # 检查每个模块的排除关键词
        for module in ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]:
            if module in matching_rules:
                negative_keywords = matching_rules[module].get("negative_keywords", [])
                module_hits = []
                
                for neg_kw in negative_keywords:
                    if neg_kw.lower() in tags_text:
                        module_hits.append(neg_kw)
                
                if module_hits:
                    exclusion_hits.append((module, module_hits))
                    st.error(f"❌ **{module}** 被排除 - 命中关键词: {', '.join(module_hits)}")
                else:
                    st.success(f"✅ **{module}** 通过排除检查")
        
        # 检查全局排除
        st.write("**🌐 全局排除检查:**")
        global_exclusions = []
        if "GLOBAL_SETTINGS" in matching_rules:
            irrelevant_categories = matching_rules["GLOBAL_SETTINGS"].get("irrelevant_scene_categories", {})
            
            for category, keywords in irrelevant_categories.items():
                category_hits = []
                for kw in keywords:
                    if kw.lower() in tags_text:
                        category_hits.append(kw)
                
                if category_hits:
                    global_exclusions.append((category, category_hits))
                    st.error(f"🚨 **全局排除 - {category}** 命中: {', '.join(category_hits)}")
        
        if not global_exclusions:
            st.success("✅ 通过全局排除检查")
        
        # 第二步：关键词分类
        st.markdown("---")
        st.write("**🎯 第二步：关键词分类**")
        
        keyword_result = mapper.classify_segment_by_tags(tags_list)
        if keyword_result:
            st.success(f"✅ 关键词分类结果: **{keyword_result}**")
        else:
            st.warning("⚠️ 关键词分类无结果，将使用AI分类")
        
        # 第三步：AI分类 (如果关键词分类失败)
        if not keyword_result:
            st.write("**🤖 第三步：AI分类**")
            ai_result = mapper.classify_segment_by_deepseek(tags_list)
            st.info(f"🤖 AI分类结果: **{ai_result}**")
        
        # 最终结果
        st.markdown("---")
        st.subheader("🎯 最终分类结果")
        
        final_result = mapper.classify_segment(tags_list)
        
        # 根据排除情况给出警告
        if exclusion_hits or global_exclusions:
            st.error(f"⚠️ **警告**: 片段被分类为 **{final_result}**，但存在排除关键词冲突!")
            st.error("**这表明排除关键词过滤机制没有正常工作!**")
            
            # 详细说明问题
            st.markdown("**🐛 发现的问题:**")
            for module, hits in exclusion_hits:
                st.write(f"- {module} 应该被排除，但仍可能被选中 (排除词: {', '.join(hits)})")
            
            for category, hits in global_exclusions:
                st.write(f"- 全局排除 {category} 命中 (排除词: {', '.join(hits)})")
        else:
            st.success(f"🎉 最终分类结果: **{final_result}**")
    
    except Exception as e:
        st.error(f"分析过程出错: {e}")
        st.exception(e)

def analyze_segment_detailed(segment: Dict[str, Any]):
    """详细分析已有片段"""
    st.subheader(f"🔍 片段详细分析: {segment.get('file_name', '未知')}")
    
    # 显示片段基本信息
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("当前分类", segment.get('category', '未分类'))
        st.metric("质量分数", f"{segment.get('combined_quality', 0):.2f}")
    
    with col2:
        st.metric("时长", f"{segment.get('duration', 0):.1f}s")
        st.metric("置信度", f"{segment.get('confidence', 0):.2f}")
    
    with col3:
        st.metric("人脸特写", "是" if segment.get('is_face_close_up') else "否")
        st.metric("不可用", "是" if segment.get('unusable') else "否")
    
    # 显示标签
    st.subheader("🏷️ 片段标签")
    all_tags = segment.get('all_tags', [])
    if all_tags:
        st.code(", ".join(all_tags))
        
        # 重新分析这些标签
        if st.button("🔄 重新分析这些标签"):
            analyze_single_segment(all_tags)
    else:
        st.warning("没有标签信息")
    
    # 显示转录文本
    if segment.get('transcription'):
        st.subheader("📝 转录文本")
        st.text_area("", segment['transcription'], height=100, disabled=True)

def render_filter_mechanism_debug():
    """渲染过滤机制调试界面"""
    st.header("🔬 过滤机制测试")
    
    st.info("测试排除关键词和过滤规则是否正常工作")
    
    # 测试配置
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 选择测试场景")
        
        test_scenarios = {
            "高速公路场景": ["汽车", "高速公路", "驾驶", "方向盘", "车内"],
            "红绿灯场景": ["红绿灯", "交通", "马路", "等待", "车辆"],
            "医院场景": ["医院", "病房", "打点滴", "医生", "病床"],
            "正常育儿场景": ["妈妈", "宝宝", "奶粉", "客厅", "温馨"],
            "品牌展示场景": ["启赋", "奶粉罐", "营养表", "配方", "品质"]
        }
        
        selected_scenario = st.selectbox("选择测试场景", list(test_scenarios.keys()))
        scenario_tags = test_scenarios[selected_scenario]
        
        st.write("**场景标签:**")
        st.code(", ".join(scenario_tags))
    
    with col2:
        st.subheader("⚙️ 自定义测试")
        
        custom_tags = st.text_area(
            "自定义标签 (逗号分隔)",
            value="",
            height=100
        )
        
        use_custom = st.checkbox("使用自定义标签")
    
    # 执行测试
    if st.button("🧪 执行过滤测试", type="primary"):
        test_tags = custom_tags.split(",") if use_custom and custom_tags.strip() else scenario_tags
        test_tags = [tag.strip() for tag in test_tags if tag.strip()]
        
        st.markdown("---")
        st.subheader("🧪 测试结果")
        
        # 加载规则并测试
        try:
            config_file = "../config/matching_rules.json"  # 使用项目根目录的配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                matching_rules = json.load(f)
            
            tags_text = " ".join(test_tags).lower()
            
            # 测试每个模块的过滤
            st.write("**📋 各模块过滤测试:**")
            
            for module in ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]:
                if module in matching_rules:
                    negative_keywords = matching_rules[module].get("negative_keywords", [])
                    
                    blocked = False
                    blocking_keywords = []
                    
                    for neg_kw in negative_keywords:
                        if neg_kw.lower() in tags_text:
                            blocked = True
                            blocking_keywords.append(neg_kw)
                    
                    if blocked:
                        st.error(f"❌ **{module}** - 被阻止 (关键词: {', '.join(blocking_keywords)})")
                    else:
                        st.success(f"✅ **{module}** - 通过过滤")
            
            # 测试全局过滤
            st.write("**🌐 全局过滤测试:**")
            
            if "GLOBAL_SETTINGS" in matching_rules:
                irrelevant_categories = matching_rules["GLOBAL_SETTINGS"].get("irrelevant_scene_categories", {})
                
                any_global_blocked = False
                
                for category, keywords in irrelevant_categories.items():
                    blocked_by_category = []
                    
                    for kw in keywords:
                        if kw.lower() in tags_text:
                            blocked_by_category.append(kw)
                    
                    if blocked_by_category:
                        any_global_blocked = True
                        st.error(f"🚨 **{category}** - 全局阻止 (关键词: {', '.join(blocked_by_category)})")
                
                if not any_global_blocked:
                    st.success("✅ 通过所有全局过滤")
            
            # 实际分类测试
            st.markdown("---")
            st.write("**🎯 实际分类测试:**")
            
            from streamlit_app.modules.mapper import VideoSegmentMapper
            mapper = VideoSegmentMapper()
            
            actual_result = mapper.classify_segment(test_tags)
            
            st.info(f"🤖 实际分类结果: **{actual_result}**")
            
            # 分析结果
            expected_blocked = any("高速" in tag or "红绿灯" in tag or "医院" in tag for tag in test_tags)
            
            if expected_blocked and actual_result not in ["其他", None]:
                st.error("🚨 **过滤机制失效!** 应该被排除的内容仍然被分类")
            elif not expected_blocked and actual_result:
                st.success("✅ 过滤机制正常工作")
            else:
                st.info("ℹ️ 测试结果需要进一步验证")
        
        except Exception as e:
            st.error(f"测试失败: {e}")

def render_selection_decision_log():
    """渲染选片决策日志界面"""
    st.header("🎬 选片决策日志分析")
    
    st.markdown("""
    **🎯 选片决策日志的价值:**
    
    1. **🔍 决策透明化** - 详细记录每个片段的选择理由
    2. **🚫 排除原因追踪** - 明确显示片段被排除的具体原因  
    3. **🎯 关键词匹配分析** - 查看哪些关键词触发了分类
    4. **🤖 AI分类过程** - 监控AI分类的决策过程和置信度
    5. **📊 质量评估详情** - 了解质量评分的具体计算过程
    
    **💡 核心功能: 回答"为什么选择这个片段"的问题**
    """)
    
    # 日志会话管理
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 启动新的选片日志会话", type="primary"):
            try:
                # 兼容不同的运行环境
                try:
                    from modules.selection_logger import start_new_session
                except ImportError:
                    from streamlit_app.modules.selection_logger import start_new_session
                
                logger = start_new_session()
                st.success(f"✅ 新日志会话已启动: {logger.session_id}")
                st.info("💡 现在去混剪工厂生成视频，所有选片决策都会被详细记录")
            except Exception as e:
                st.error(f"启动选片日志失败: {e}")
                st.info("💡 请确保selection_logger模块已正确配置")
    
    with col2:
        if st.button("📊 查看当前会话状态"):
            try:
                # 兼容不同的运行环境
                try:
                    from modules.selection_logger import get_selection_logger
                except ImportError:
                    from streamlit_app.modules.selection_logger import get_selection_logger
                
                logger = get_selection_logger()
                summary = logger.get_session_summary()
                st.success(f"📋 当前会话: {summary['session_id']}")
                st.info(f"📊 已分析片段: {summary['segments_analyzed']} 个")
            except Exception as e:
                st.error(f"获取会话状态失败: {e}")
                st.info("💡 请确保selection_logger模块已正确配置")
    
    # 专注于选片决策日志
    st.markdown("---")
    st.subheader("📋 选片决策日志文件")
    
    # 查找选片决策日志 - 智能路径检测
    # 获取当前工作目录，确定正确的路径
    current_dir = os.getcwd()
    
    # 🔧 智能检测路径：根据当前工作目录动态计算
    current_work_dir = os.getcwd()
    st.info(f"🔍 当前工作目录: {current_work_dir}")
    
    if current_work_dir.endswith("streamlit_app"):
        # 如果已经在streamlit_app目录中
        possible_log_dirs = [
            "logs/selection",  # 当前目录
            "../logs/selection",  # 上级目录
        ]
    else:
        # 如果在项目根目录
        possible_log_dirs = [
            "logs/selection",  # 项目根目录
            "streamlit_app/logs/selection",  # streamlit_app子目录
        ]
    
    # 寻找存在的日志目录
    selection_log_dir = None
    for log_dir in possible_log_dirs:
        if os.path.exists(log_dir):
            try:
                files = os.listdir(log_dir)
                log_files_count = len([f for f in files if f.endswith(('.jsonl', '.log'))])
                if log_files_count > 0:
                    selection_log_dir = log_dir
                    st.success(f"✅ 找到选片日志目录: {log_dir} (包含 {log_files_count} 个日志文件)")
                    break
            except Exception as e:
                continue
    
    # 如果没有找到任何日志目录
    if not selection_log_dir:
        st.warning("📁 未找到包含日志文件的目录")
        st.info("💡 可能的原因：日志目录为空或权限问题")
    
    if selection_log_dir:
        # 查找 .jsonl 和 .log 文件
        jsonl_files = [f for f in os.listdir(selection_log_dir) if f.endswith('.jsonl')]
        log_files = [f for f in os.listdir(selection_log_dir) if f.endswith('.log')]
        
        if jsonl_files or log_files:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📊 结构化决策日志 (.jsonl)**")
                if jsonl_files:
                    selected_jsonl = st.selectbox(
                        "选择决策日志文件",
                        sorted(jsonl_files, reverse=True),
                        key="jsonl_selector"
                    )
                    
                    if st.button("📊 分析决策过程", key="analyze_decisions"):
                        _analyze_decision_log(os.path.join(selection_log_dir, selected_jsonl))
                else:
                    st.info("暂无结构化决策日志")
            
            with col2:
                st.write("**📝 文本日志 (.log)**")
                if log_files:
                    selected_log = st.selectbox(
                        "选择文本日志文件",
                        sorted(log_files, reverse=True),
                        key="log_selector"
                    )
                    
                    if st.button("📖 查看详细日志", key="view_detailed_log"):
                        _show_detailed_log(os.path.join(selection_log_dir, selected_log))
                else:
                    st.info("暂无文本日志")
        else:
            st.warning("📁 选片日志目录为空")
            st.info("💡 请先运行混剪工厂生成视频，系统会自动记录选片决策过程")
    else:
        st.warning("📁 未找到选片日志目录")
        st.info("💡 日志目录会在第一次运行选片时自动创建")
        
        # 显示调试信息
        if st.checkbox("🔍 显示路径调试信息", key="debug_log_paths"):
            st.subheader("🔧 路径调试信息")
            st.write(f"🔍 当前工作目录: `{current_work_dir}`")
            
            st.write("**检查的日志路径:**")
            for i, log_dir in enumerate(possible_log_dirs):
                exists = os.path.exists(log_dir)
                st.write(f"{i+1}. `{log_dir}` → {'✅ 存在' if exists else '❌ 不存在'}")
                if exists:
                    try:
                        files = os.listdir(log_dir)
                        log_files = [f for f in files if f.endswith(('.jsonl', '.log'))]
                        st.write(f"   📁 包含 {len(log_files)} 个日志文件")
                        for log_file in log_files[:3]:  # 只显示前3个
                            file_path = os.path.join(log_dir, log_file)
                            file_size = os.path.getsize(file_path)
                            st.write(f"   📄 {log_file} ({file_size:,} bytes)")
                    except Exception as e:
                        st.write(f"   ⚠️ 无法读取目录: {e}")
    
    # 实时监控和帮助
    st.markdown("---")
    st.subheader("🔧 实时监控建议")
    
    st.markdown("""
    **🖥️ 最佳调试方式:**
    
    1. **终端实时输出** - 运行混剪工厂时观察控制台，有实时的选片决策信息
    2. **启动日志会话** - 点击上方"启动新的选片日志会话"按钮
    3. **生成视频** - 去混剪工厂页面生成视频，所有决策都会被记录
    4. **分析结果** - 回到这里查看详细的选片决策分析
    
    **📋 有用的日志标记:**
    - 🎯 关键词分类成功
    - 🤖 AI分类结果  
    - 🚫 片段被排除
    - ✅ 质量检查通过
    - 📊 质量评分详情
    """)

def _analyze_decision_log(log_path: str):
    """分析选片决策日志文件"""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        segment_analyses = []
        module_selections = []
        
        for line in lines:
            if line.strip():
                data = json.loads(line)
                if data.get("segment_id"):
                    segment_analyses.append(data)
                elif data.get("log_type") == "module_selection":
                    module_selections.append(data)
        
        st.success(f"📊 日志分析完成: {os.path.basename(log_path)}")
        
        # 统计信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("片段分析", len(segment_analyses))
        with col2:
            st.metric("模块选片", len(module_selections))
        with col3:
            st.metric("决策步骤", sum(len(s.get("analysis_steps", [])) for s in segment_analyses))
        
        # 显示最近的几个决策
        if segment_analyses:
            st.subheader("🔍 最近的片段决策")
            for analysis in segment_analyses[-5:]:  # 显示最后5个
                with st.expander(f"🎬 {analysis['segment_info']['file_name']} → {analysis['final_result']}"):
                    st.write(f"**决策原因:** {analysis['decision_reason']}")
                    st.write(f"**标签:** {', '.join(analysis['segment_info']['all_tags'])}")
                    st.write(f"**分析步骤:** {len(analysis['analysis_steps'])} 步")
                    
                    for step in analysis['analysis_steps']:
                        step_type = step['step_type']
                        if step_type == "exclusion_check":
                            if step['exclusion_results']['is_excluded']:
                                st.error(f"🚫 排除检查: {step['exclusion_results']['exclusion_reasons']}")
                            else:
                                st.success("✅ 通过排除检查")
                        elif step_type == "keyword_classification":
                            if step['classification_result']:
                                st.info(f"🎯 关键词分类: {step['classification_result']}")
                            else:
                                st.warning("⚠️ 关键词分类无结果")
                        elif step_type == "ai_classification":
                            st.info(f"🤖 AI分类: {step['ai_result']} (耗时: {step['api_call_info'].get('duration', 0):.2f}s)")
        
        # 显示模块选片结果
        if module_selections:
            st.subheader("🎬 模块选片结果")
            for selection in module_selections[-3:]:  # 显示最后3个
                st.write(f"**{selection['module_name']}:** {selection['selected_count']}/{selection['candidates_count']} 片段被选中")
            
    except Exception as e:
        st.error(f"分析日志失败: {e}")

def _show_detailed_log(log_path: str):
    """显示详细的文本日志"""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 过滤相关的选片决策日志
        lines = content.split('\n')
        decision_lines = []
        
        keywords = ["🎯", "🤖", "🚫", "✅", "📊", "⚠️", "片段分析", "分类", "排除", "质量"]
        
        for line in lines:
            if any(keyword in line for keyword in keywords):
                decision_lines.append(line)
        
        if decision_lines:
            st.subheader(f"📋 选片决策日志 (共 {len(decision_lines)} 条)")
            st.text_area(
                "决策日志内容",
                "\n".join(decision_lines[-100:]),  # 显示最后100条
                height=400,
                key="decision_log_content"
            )
            st.info(f"📊 从 {len(lines)} 行日志中筛选出 {len(decision_lines)} 条相关决策记录")
        else:
            st.warning("未找到选片决策相关的日志内容")
            
    except Exception as e:
        st.error(f"读取日志失败: {e}")
    
    # 实时日志监控
    st.markdown("---")
    st.subheader("🔴 实时日志监控")
    
    if st.checkbox("开启实时监控"):
        st.info("实时监控功能需要进一步开发...")

# show_all_segments_table 函数已删除 - 存在复杂的路径识别问题

def _show_fallback_srt_based_table(video_filename: str, video_duration: float, selected_segments: Dict[str, List[Dict]] = None):
    """显示基于SRT的表格 - 优先使用实际合成片段，回退到视频池匹配"""
    if selected_segments:
        st.subheader(f"📋 {video_filename} - 基于标杆视频SRT时间轴的合成片段映射")
    else:
        st.subheader(f"📋 {video_filename} - 基于标杆视频SRT的实际片段构成")
    
    try:
        # 读取标杆视频的SRT文件 - 使用绝对路径
        current_file_dir = os.path.dirname(os.path.abspath(__file__))  # streamlit_app/pages
        streamlit_app_dir = os.path.dirname(current_file_dir)  # streamlit_app
        project_root = os.path.dirname(streamlit_app_dir)  # 项目根目录
        srt_file_path = os.path.join(project_root, "data", "input", "test_videos", "通用-保护薄弱期-HMO&自御力-启赋-CTA7.srt")
        
        if not os.path.exists(srt_file_path):
            st.error(f"标杆视频SRT文件不存在: {srt_file_path}")
            return
        
        # 解析SRT文件
        srt_segments = []
        with open(srt_file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # 分割SRT片段
        srt_blocks = content.split('\n\n')
        
        for block in srt_blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                index = lines[0]
                time_range = lines[1]
                text = ' '.join(lines[2:])
                
                srt_segments.append({
                    'index': int(index),
                    'time_range': time_range,
                    'text': text
                })
        
        # 定义模块映射
        srt_module_mapping = {
            1: {"module": "痛点", "icon": "🔴"},
            2: {"module": "痛点", "icon": "🔴"},
            3: {"module": "解决方案导入", "icon": "🟢"},
            4: {"module": "卖点·成分&配方", "icon": "🟡"},
            5: {"module": "促销机制", "icon": "🟠"}
        }
        
        # 🔧 优先使用传入的合成片段数据，否则加载视频池数据
        if selected_segments:
            # 使用实际合成的片段数据
            pool_by_module = selected_segments.copy()
            pool_segments = []
            for segments_list in selected_segments.values():
                pool_segments.extend(segments_list)
            st.success(f"✅ 使用实际合成片段数据: {len(pool_segments)} 个片段")
        else:
            # 回退到加载视频池数据
            video_pool_path = "data/output/google_video/video_pool"
            pool_segments = []
        
            if os.path.exists(video_pool_path):
                with st.spinner("加载视频池数据..."):
                    try:
                        from streamlit_app.modules.mapper import VideoSegmentMapper
                        mapper = VideoSegmentMapper()
                        pool_segments = mapper.scan_video_pool(video_pool_path)
                        st.success(f"✅ 成功加载 {len(pool_segments)} 个视频池片段")
                    except Exception as e:
                        st.warning(f"⚠️ 加载视频池失败: {e}")
            else:
                st.warning("⚠️ 视频池目录不存在，将显示理论片段名")
        
            # 🎯 按模块分组视频池片段
            pool_by_module = {
                "痛点": [],
                "解决方案导入": [],
                "卖点·成分&配方": [],
                "促销机制": []
            }
        
        for segment in pool_segments:
            category = segment.get('category', '未分类')
            if category in pool_by_module:
                pool_by_module[category].append(segment)
        
        # 创建表格表头
        header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([0.8, 2.5, 2, 2.5, 0.8])
        
        with header_col1:
            st.markdown("**模块**")
        with header_col2:
            st.markdown("**SRT时间**")
        with header_col3:
            st.markdown("**实际匹配片段**")
        with header_col4:
            st.markdown("**内容描述**")
        with header_col5:
            st.markdown("**质量评估**")
        
        st.markdown("---")
        
        # 为每个模块维护已使用的片段索引
        module_usage_count = {
            "痛点": 0,
            "解决方案导入": 0,
            "卖点·成分&配方": 0,
            "促销机制": 0
        }
        
        # 显示每个SRT片段
        for srt_seg in srt_segments:
            index = srt_seg['index']
            time_range = srt_seg['time_range']
            text = srt_seg['text']
            
            # 获取模块信息
            module_info = srt_module_mapping.get(index, {"module": "其他", "icon": "⚪"})
            module = module_info["module"]
            icon = module_info["icon"]
            
            # 🎯 获取该模块所有匹配的片段
            module_segments = pool_by_module.get(module, [])

            # 创建一个容器来展示整个SRT模块
            with st.container():
                # 第一行：显示模块、SRT时间和内容描述
                col1, col2, col4 = st.columns([0.8, 2.5, 2.5])
                with col1:
                    st.markdown(f"{icon} **{module}**")
                with col2:
                    st.markdown(f"**{time_range}**")
                with col4:
                    display_text = text[:50] + "..." if len(text) > 50 else text
                    st.markdown(f"**{display_text}**")
            
                # 后续行：显示该模块下的所有片段
                if not module_segments:
                     # 如果没有匹配的片段
                    _, _, seg_col3, _, seg_col5 = st.columns([0.8, 2.5, 2, 2.5, 0.8])
                    with seg_col3:
                        st.markdown("*理论-无匹配片段*")
                    with seg_col5:
                        st.markdown("N/A")
                else:
                    for segment_in_module in module_segments:
                        video_id = segment_in_module.get('video_id', 'unknown')
                        file_name = segment_in_module.get('file_name', 'segment.mp4')
                        quality = segment_in_module.get('combined_quality', 0.75)
                        
                        if video_id != 'unknown' and not file_name.startswith(f"{video_id}-"):
                            actual_filename = f"{video_id}-{file_name}"
                        else:
                            actual_filename = file_name
                        
                        # 为每个片段创建一行
                        _, _, seg_col3, _, seg_col5 = st.columns([0.8, 2.5, 2, 2.5, 0.8])
                        with seg_col3:
                            st.markdown(f"**{actual_filename}**")
                        with seg_col5:
                            st.markdown(f"**{quality:.2f}**")
            
            # 清除该模块的片段，防止在其他SRT条目中重复显示
            if module in pool_by_module:
                pool_by_module[module] = []

            st.markdown("---")
        
        # 显示统计信息
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("SRT片段数", len(srt_segments))
        
        with col2:
            actual_matches = sum(len(segments) for segments in pool_by_module.values())
            st.metric("可用池片段", actual_matches)
        
        with col3:
            st.metric("视频时长", f"{video_duration:.1f}秒")
        
        # 显示模块匹配统计
        st.subheader("📊 模块匹配统计")
        
        module_stats = []
        for module, segments in pool_by_module.items():
            srt_count = sum(1 for seg in srt_segments 
                           if srt_module_mapping.get(seg['index'], {}).get('module') == module)
            
            module_stats.append({
                "模块": f"{srt_module_mapping.get(1, {}).get('icon', '⚪')} {module}" if module == "痛点" 
                       else f"{srt_module_mapping.get(3, {}).get('icon', '⚪')} {module}" if module == "解决方案导入"
                       else f"{srt_module_mapping.get(4, {}).get('icon', '⚪')} {module}" if module == "卖点·成分&配方"
                       else f"{srt_module_mapping.get(5, {}).get('icon', '⚪')} {module}",
                "SRT需求": srt_count,
                "池中可用": len(segments),
                "匹配状态": "✅ 充足" if len(segments) >= srt_count else f"⚠️ 不足({len(segments)}/{srt_count})"
            })
        
        if module_stats:
            import pandas as pd
            df = pd.DataFrame(module_stats)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 提示信息
        if pool_segments:
            st.info("ℹ️ 此表格基于标杆视频SRT的时间轴，显示实际从视频池匹配的片段文件名")
        else:
            st.warning("⚠️ 未加载视频池数据，显示的是理论片段构成。请先在混剪工厂中完成映射。")
        
    except Exception as e:
        st.error(f"显示回退表格失败: {e}")

def _show_real_composition_table(comp_result: Dict[str, Any], selected_segments: Dict[str, List[Dict]], metadata: Dict[str, Any]) -> None:
    """显示真实的合成视频片段表格 - 基于JSON文件数据"""
    st.header("📋 混剪工厂合成视频片段表 (真实数据)")
    
    # 显示基本信息
    st.success(f"✅ 合成视频: **{metadata.get('video_filename', '未知文件名')}**")
    
    # 添加显示方式选择
    display_mode = st.radio(
        "🎯 选择显示方式：",
        ["📄 基于SRT标杆视频时间轴", "🎬 基于合成视频时间轴"],
        index=0,  # 默认选择SRT方式
        horizontal=True
    )
    
    if display_mode == "📄 基于SRT标杆视频时间轴":
        # 调用SRT基础的显示函数，传入实际合成的片段
        video_filename = metadata.get('video_filename', '未知文件名')
        video_duration = comp_result.get('duration', 0)
        _show_fallback_srt_based_table(video_filename, video_duration, selected_segments)
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎬 总时长", f"{comp_result.get('duration', 0):.1f}秒")
    with col2:
        total_segments = sum(len(segs) for segs in selected_segments.values())
        st.metric("📦 总片段数", total_segments)
    with col3:
        st.metric("🎯 合成策略", metadata.get('strategy', '未知'))
    with col4:
        file_size_mb = comp_result.get('file_size', 0) / (1024*1024) if comp_result.get('file_size') else 0
        st.metric("📁 文件大小", f"{file_size_mb:.1f}MB")
    
    # 定义模块图标
    module_icons = {
        "痛点": "🔴",
        "解决方案导入": "🟢", 
        "卖点·成分&配方": "🟡",
        "促销机制": "🟠"
    }
    
    # 创建表格表头
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([0.8, 2.5, 2, 2.5, 0.8])
    
    with header_col1:
        st.markdown("**模块**")
    with header_col2:
        st.markdown("**时间位置**")
    with header_col3:
        st.markdown("**选中片段名称**")
    with header_col4:
        st.markdown("**片段标签**")
    with header_col5:
        st.markdown("**质量分数**")
    
    st.markdown("---")
    
    # 按模块顺序显示片段
    modules = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
    current_time = 0.0
    
    for module in modules:
        if module not in selected_segments:
            continue
            
        module_segments = selected_segments[module]
        if not module_segments:
            continue
        
        icon = module_icons.get(module, "⚪")
        
        # 为每个模块的片段显示信息
        for segment_idx, segment in enumerate(module_segments):
            # 获取片段信息
            file_name = segment.get('file_name', f'segment_{segment_idx+1}.mp4')
            video_id = segment.get('video_id', 'unknown')
            duration = segment.get('duration', 0)
            all_tags = segment.get('all_tags', [])
            quality = segment.get('combined_quality', 0.75)
            transcription = segment.get('transcription', '')
            
            # 计算时间范围
            start_time = current_time
            end_time = current_time + duration
            time_range = f"{int(start_time//60):02d}:{int(start_time%60):02d} - {int(end_time//60):02d}:{int(end_time%60):02d}"
            
            # 构建显示文件名（添加视频ID前缀）
            if video_id != 'unknown' and not file_name.startswith(f"{video_id}-"):
                display_filename = f"{video_id}-{file_name}"
            else:
                display_filename = file_name
            
            # 处理标签 - 优先使用真实标签
            if all_tags:
                main_tags = all_tags[:4]  # 显示前4个标签
                tags_display = ", ".join(main_tags)
            elif transcription:
                # 如果有转录文本，提取关键词作为标签
                keywords = transcription.split()[:4]
                tags_display = ", ".join(keywords)
            else:
                # 根据模块生成默认标签
                module_default_tags = {
                    "痛点": ["妈妈", "宝宝", "担忧", "问题"],
                    "解决方案导入": ["妈妈", "宝宝", "奶粉", "解决"],
                    "卖点·成分&配方": ["奶粉", "营养", "配方", "成分"],
                    "促销机制": ["优惠", "促销", "活动", "试喝"]
                }
                tags_display = ", ".join(module_default_tags.get(module, ["妈妈", "宝宝", "奶粉"]))
            
            # 创建5列表格布局
            col1, col2, col3, col4, col5 = st.columns([0.8, 2.5, 2, 2.5, 0.8])
            
            with col1:
                if segment_idx == 0:  # 只在第一个片段显示模块名
                    st.markdown(f"{icon} **{module}**")
                else:
                    st.markdown("")  # 空白，保持对齐
            
            with col2:
                st.markdown(f"**{time_range}**")
                # 显示片段时长
                st.markdown(f"<div style='color: #666; font-size: 12px; margin-top: 2px;'>⏱ {duration:.1f}秒</div>", unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"**{display_filename}**")
                # 如果有转录文本，显示预览
                if transcription:
                    preview = transcription[:30] + "..." if len(transcription) > 30 else transcription
                    st.markdown(f"<div style='color: #999; font-size: 11px; margin-top: 2px;'>💬 {preview}</div>", unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"**{tags_display}**")
            
            with col5:
                # 质量分数彩色显示
                if quality >= 0.8:
                    color = "#22c55e"  # 绿色
                elif quality >= 0.6:
                    color = "#f59e0b"  # 黄色
                else:
                    color = "#ef4444"  # 红色
                st.markdown(f"<div style='color: {color}; font-weight: bold;'>{quality:.2f}</div>", unsafe_allow_html=True)
            
            # 更新当前时间
            current_time = end_time
    
    # 显示详细统计信息
    st.markdown("---")
    st.subheader("📊 详细统计")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**模块分布:**")
        for module in modules:
            if module in selected_segments:
                count = len(selected_segments[module])
                duration_total = sum(seg.get('duration', 0) for seg in selected_segments[module])
                st.write(f"• {module}: {count}片段, {duration_total:.1f}秒")
    
    with col2:
        st.write("**质量分析:**")
        all_qualities = []
        for segments in selected_segments.values():
            for seg in segments:
                quality = seg.get('combined_quality', 0)
                if quality > 0:
                    all_qualities.append(quality)
        
        if all_qualities:
            avg_quality = sum(all_qualities) / len(all_qualities)
            max_quality = max(all_qualities)
            min_quality = min(all_qualities)
            st.write(f"• 平均质量: {avg_quality:.3f}")
            st.write(f"• 最高质量: {max_quality:.3f}")
            st.write(f"• 最低质量: {min_quality:.3f}")
    
    with col3:
        st.write("**合成信息:**")
        timestamp = metadata.get('timestamp', '')
        if timestamp:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                st.write(f"• 合成时间: {dt.strftime('%Y-%m-%d %H:%M')}")
            except:
                st.write(f"• 合成时间: {timestamp}")
        
        audio_strategy = comp_result.get('audio_strategy', '未知')
        st.write(f"• 音频策略: {audio_strategy}")
        
        quality_settings = metadata.get('quality_settings', {})
        if quality_settings:
            resolution = quality_settings.get('resolution', '未知')
            st.write(f"• 输出分辨率: {resolution}")


if __name__ == "__main__":
    main() 