"""
转录工具函数
封装视频转录相关的工具函数
"""

import tempfile
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


def convert_video_to_srt(
    uploaded_video: Any,
    video_id: str,
    output_dir: str,
    use_hotwords: bool = True,
    cleanup_temp: bool = True,
    hotword_id: Optional[str] = None,
    analyze_target_audience: bool = True,
    hotword_mode: str = "use_preset",
    hotwords_text: str = "",
    preset_hotword_id: str = ""
) -> Dict[str, Any]:
    """
    将上传的视频转换为SRT字幕文件，并可选进行人群分析
    
    Args:
        uploaded_video: Streamlit上传的视频文件对象
        video_id: 视频ID（不含扩展名）
        output_dir: 输出目录
        use_hotwords: 是否使用热词优化（向后兼容）
        cleanup_temp: 是否清理临时文件
        hotword_id: 热词ID（向后兼容）
        analyze_target_audience: 是否进行人群分析
        hotword_mode: 热词模式 ("use_preset", "use_custom", "no_hotwords")
        hotwords_text: 自定义热词文本
        preset_hotword_id: 预设热词ID
        
    Returns:
        Dict: 包含转换结果和人群分析的字典
    """
    try:
        # 创建输出目录
        abs_output_dir = Path(output_dir).resolve()
        abs_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置SRT输出路径
        srt_output_path = abs_output_dir / f"{video_id}.srt"
        
        logger.info(f"开始转录视频: {video_id}")
        logger.info(f"🎯 热词模式: {hotword_mode}")
        
        # 🎯 根据热词模式确定最终的热词参数
        final_hotword_id = None
        final_hotwords_list = None
        
        if hotword_mode == "use_preset" and preset_hotword_id:
            final_hotword_id = preset_hotword_id
            logger.info(f"📋 使用预设热词ID: {preset_hotword_id}")
        elif hotword_mode == "use_custom" and hotwords_text:
            # 解析自定义热词
            final_hotwords_list = [
                word.strip() 
                for word in hotwords_text.replace('\n', ',').split(',') 
                if word.strip()
            ]
            logger.info(f"✏️ 使用自定义热词 ({len(final_hotwords_list)} 个): {final_hotwords_list[:5]}...")
        elif hotword_mode == "no_hotwords":
            logger.info("🚫 不使用热词优化")
        else:
            # 向后兼容处理
            if use_hotwords and hotword_id:
                final_hotword_id = hotword_id
                logger.info(f"🔄 向后兼容：使用热词ID: {hotword_id}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_video_path = Path(temp_dir) / f"{video_id}.mp4"
            
            # 保存上传的视频
            with open(temp_video_path, "wb") as f:
                f.write(uploaded_video.getvalue())
            
            logger.info(f"临时视频文件已保存: {temp_video_path}")
            
            # 调用转录功能
            result_srt_path = _perform_transcription(
                video_path=str(temp_video_path),
                output_dir=str(abs_output_dir),
                hotword_id=final_hotword_id,
                custom_hotwords=final_hotwords_list,
                output_srt=str(srt_output_path)
            )
            
            if result_srt_path and Path(result_srt_path).exists():
                logger.info(f"转录成功完成: {result_srt_path}")
                
                # 基础结果
                result = {
                    "success": True,
                    "srt_path": result_srt_path,
                    "video_id": video_id,
                    "output_dir": output_dir,
                    "hotword_mode": hotword_mode,
                    "used_hotword_id": final_hotword_id,
                    "used_custom_hotwords": final_hotwords_list
                }
                
                # 🎯 人群分析（如果启用）
                if analyze_target_audience:
                    logger.info("🎯 开始进行目标人群分析...")
                    target_audience_result = _analyze_target_audience_from_srt(result_srt_path)
                    result.update(target_audience_result)
                
                return result
            else:
                logger.error("转录失败：无法生成精确的SRT文件")
                return {
                    "success": False,
                    "error": "转录服务未返回时间戳信息，无法生成精确的SRT字幕文件。请检查转录服务配置或重试转录。",
                    "error_type": "no_timestamps",
                    "hotword_mode": hotword_mode,
                    "used_hotword_id": final_hotword_id
                }
                
    except ImportError as e:
        logger.error(f"转录模块导入失败: {e}")
        return {
            "success": False,
            "error": f"转录模块导入失败: {str(e)}"
        }
    except Exception as e:
        logger.error(f"转录过程中出错: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def _perform_transcription(
    video_path: str,
    output_dir: str,
    hotword_id: Optional[str] = None,
    custom_hotwords: Optional[list] = None,
    output_srt: Optional[str] = None
) -> Optional[str]:
    """
    执行视频转录
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        hotword_id: 热词ID
        custom_hotwords: 自定义热词列表
        output_srt: 输出SRT文件路径
        
    Returns:
        str: 生成的SRT文件路径，失败时返回None
    """
    try:
        # 🎯 优先尝试使用新的DashScope分析器
        try:
            from streamlit_app.modules.ai_analyzers.dashscope_audio_analyzer import DashScopeAudioAnalyzer
            
            analyzer = DashScopeAudioAnalyzer()
            if analyzer.is_available():
                logger.info("🤖 使用DashScope音频分析器进行转录")
                
                # 转录视频
                result = analyzer.transcribe_video(
            video_path=video_path,
                    hotwords=custom_hotwords,  # 传递自定义热词列表
                    professional_terms=custom_hotwords,  # 也用作专业词汇
                    extract_audio_first=True,
                    preset_vocabulary_id=hotword_id  # 传递预设热词ID
                )
                
                if result.get("success") and result.get("transcript"):
                    try:
                        # 🎯 创建SRT文件，传递时间戳片段
                        segments = result.get("segments", [])
                        srt_content = _create_srt_from_transcript(
                            result.get("transcript", ""), 
                            segments
                        )
                        
                        srt_path = output_srt or f"{output_dir}/{Path(video_path).stem}.srt"
                        with open(srt_path, 'w', encoding='utf-8') as f:
                            f.write(srt_content)
                        
                        logger.info(f"DashScope转录完成，SRT文件已生成: {srt_path}")
                        logger.info(f"🎯 使用的热词模式: {result.get('hotword_mode', 'unknown')}")
                        logger.info(f"📋 词汇表ID: {result.get('vocabulary_id', 'none')}")
                        logger.info(f"⏰ 时间戳片段数: {len(segments)}")
                        return srt_path
        
                    except ValueError as ve:
                        logger.error(f"❌ SRT生成失败: {str(ve)}")
                        # 不使用兜底方案，直接返回None让上层处理错误
                        return None
                else:
                    logger.warning(f"DashScope转录失败: {result.get('error', '未知错误')}")
            else:
                logger.warning("DashScope分析器不可用")
                
        except ImportError:
            logger.warning("DashScope分析器模块不可用")
        except Exception as e:
            logger.warning(f"DashScope转录失败: {str(e)}")
        
        # ❌ 不再使用兜底方案，直接返回None
        logger.error("❌ 所有转录方法都失败，无法生成精确的SRT文件")
        return None
        
    except Exception as e:
        logger.error(f"转录过程异常: {str(e)}")
        return None


def _create_srt_from_transcript(transcript: str, segments: List[Dict[str, Any]] = None) -> str:
    """
    从转录文本和时间戳片段创建SRT格式内容
    
    Args:
        transcript: 转录文本
        segments: 包含时间戳的片段列表
        
    Returns:
        str: SRT格式的字幕内容
        
    Raises:
        ValueError: 当没有时间戳片段时抛出错误
    """
    if not transcript.strip():
        raise ValueError("转录文本为空，无法生成SRT文件")
    
    # 🎯 必须有时间戳片段才能生成精确的SRT
    if not segments or len(segments) == 0:
        logger.error("❌ 没有时间戳片段，无法生成精确的SRT文件")
        raise ValueError("转录服务未返回时间戳信息，无法生成精确的SRT字幕文件。请检查转录服务配置或重试转录。")
    
    logger.info(f"🎯 使用 {len(segments)} 个时间戳片段生成SRT")
    
    srt_content = []
    valid_segments = 0
    
    for i, segment in enumerate(segments):
        if segment.get('text', '').strip():
            # 转换毫秒为SRT格式时间戳
            start_ms = segment.get('start_time', 0)
            end_ms = segment.get('end_time', start_ms + 3000)
            
            # 验证时间戳有效性
            if start_ms < 0 or end_ms <= start_ms:
                logger.warning(f"片段 {i+1} 时间戳无效: {start_ms}ms -> {end_ms}ms，跳过")
                continue
            
            srt_content.append(f"{valid_segments + 1}")
            srt_content.append(f"{_format_timestamp_ms(start_ms)} --> {_format_timestamp_ms(end_ms)}")
            srt_content.append(segment['text'].strip())
            srt_content.append("")
            valid_segments += 1
    
    if valid_segments == 0:
        raise ValueError("所有时间戳片段都无效，无法生成SRT文件")
    
    logger.info(f"✅ 成功生成包含 {valid_segments} 个有效片段的精确SRT文件")
    return "\n".join(srt_content)


def _format_timestamp(seconds: int) -> str:
    """
    格式化时间戳为SRT格式（秒）
    
    Args:
        seconds: 秒数
        
    Returns:
        str: SRT格式的时间戳
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},000"


def _format_timestamp_ms(milliseconds: int) -> str:
    """
    格式化毫秒时间戳为SRT格式
    
    Args:
        milliseconds: 毫秒数
        
    Returns:
        str: SRT格式的时间戳 (HH:MM:SS,mmm)
    """
    # 转换毫秒为秒和毫秒部分
    total_seconds = milliseconds // 1000
    ms = milliseconds % 1000
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def _create_mock_srt(output_path: str) -> str:
    """
    创建模拟SRT文件用于测试
    
    Args:
        output_path: 输出文件路径
        
    Returns:
        str: 生成的SRT文件路径
    """
    mock_srt_content = """1
00:00:01,000 --> 00:00:03,500
这是一个测试字幕文件

2
00:00:03,500 --> 00:00:06,000
专为演示零件工厂功能而创建

3
00:00:06,000 --> 00:00:08,500
请替换为真实的转录模块
"""
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(mock_srt_content)
        
        logger.info(f"模拟SRT文件已创建: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"创建模拟SRT文件失败: {e}")
        return None


def _analyze_target_audience_from_srt(srt_path: str) -> Dict[str, Any]:
    """
    🎯 基于SRT文件内容分析目标人群
    
    Args:
        srt_path: SRT文件路径
        
    Returns:
        Dict: 人群分析结果
    """
    try:
        # 读取SRT文件内容
        full_transcript = _extract_text_from_srt(srt_path)
        
        if not full_transcript.strip():
            logger.warning("SRT文件内容为空，无法进行人群分析")
            return {
                "target_audience_analysis": {
                    "success": False,
                    "error": "SRT文件内容为空"
                }
            }
        
        logger.info(f"📝 从SRT提取到 {len(full_transcript)} 字符的转录文本")
        
        # 🤖 使用DeepSeek进行人群分析
        target_audience_result = _perform_deepseek_audience_analysis(full_transcript)
        
        # 📊 生成人群分析报告
        analysis_report = _generate_audience_analysis_report(
            target_audience_result, 
            full_transcript,
            srt_path
        )
        
        return {
            "target_audience_analysis": {
                "success": True,
                "target_audience": target_audience_result.get("target_audience", "未识别"),
                "confidence": target_audience_result.get("confidence", 0.0),
                "analysis_method": "deepseek_srt_analysis",
                "transcript_length": len(full_transcript),
                "srt_source": srt_path,
                "report": analysis_report
            }
        }
        
    except Exception as e:
        logger.error(f"人群分析失败: {e}")
        return {
            "target_audience_analysis": {
                "success": False,
                "error": str(e)
            }
        }


def _extract_text_from_srt(srt_path: str) -> str:
    """从SRT文件提取纯文本内容"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析SRT格式，提取文本
        lines = content.strip().split('\n')
        text_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过序号行
            if line.isdigit():
                i += 1
                continue
            
            # 跳过时间戳行
            if '-->' in line:
                i += 1
                continue
            
            # 跳过空行
            if not line:
                i += 1
                continue
            
            # 收集文本行
            text_lines.append(line)
            i += 1
        
        full_text = ' '.join(text_lines)
        logger.info(f"从SRT文件提取到 {len(text_lines)} 行文本，总计 {len(full_text)} 字符")
        
        return full_text
        
    except Exception as e:
        logger.error(f"从SRT文件提取文本失败: {e}")
        return ""


def _perform_deepseek_audience_analysis(transcript: str) -> Dict[str, Any]:
    """使用DeepSeek进行目标人群分析"""
    try:
        # 导入DeepSeek分析器
        from streamlit_app.modules.ai_analyzers.deepseek_analyzer import DeepSeekAnalyzer
        
        analyzer = DeepSeekAnalyzer()
        
        # 🔍 详细检查分析器状态
        if not analyzer.is_available():
            logger.warning("DeepSeek分析器不可用，使用兜底分析")
            logger.warning(f"API密钥状态: {bool(analyzer.api_key)}")
            return _fallback_audience_analysis(transcript)
        
        logger.info("🤖 开始DeepSeek目标人群分析")
        logger.info(f"📝 转录文本长度: {len(transcript)} 字符")
        logger.info(f"📝 转录文本预览: {transcript[:200]}...")
        
        # 调用人群分析
        result = analyzer.analyze_video_summary(transcript)
        
        # 🔍 详细记录分析结果
        logger.info(f"🔍 DeepSeek原始返回结果: {result}")
        
        if result.get("error"):
            logger.error(f"❌ DeepSeek分析返回错误: {result['error']}")
            return _fallback_audience_analysis(transcript)
        
        if result.get("target_audience"):
            target_audience = result["target_audience"].strip()
            if target_audience:
                logger.info(f"🎯 人群分析成功: {target_audience}")
                return {
                    "target_audience": target_audience,
                    "confidence": 0.85,  # DeepSeek分析置信度
                    "method": "deepseek_api",
                    "api_response": result  # 保存原始响应用于调试
                }
            else:
                logger.warning("⚠️ DeepSeek返回空的target_audience字段")
        else:
            logger.warning("⚠️ DeepSeek响应中缺少target_audience字段")
        
        logger.warning("DeepSeek分析返回空结果，使用兜底分析")
        return _fallback_audience_analysis(transcript)
            
    except ImportError as e:
        logger.error(f"DeepSeek分析器模块导入失败: {e}")
        return _fallback_audience_analysis(transcript)
    except Exception as e:
        logger.error(f"DeepSeek人群分析异常: {e}")
        logger.error(f"异常类型: {type(e).__name__}")
        return _fallback_audience_analysis(transcript)


def _fallback_audience_analysis(transcript: str) -> Dict[str, Any]:
    """兜底人群分析（基于关键词匹配）"""
    try:
        # 🎯 优化后的人群关键词映射
        audience_keywords = {
            "孕期妈妈": [
                # 孕期相关
                "孕期", "胎儿", "叶酸", "孕妇", "怀孕", "产检", "胎教", "孕早期", "孕中期", "孕晚期",
                # 营养相关  
                "孕期营养", "DHA", "钙片", "维生素", "胎儿发育",
        
            ],
            "新手爸妈": [
                # 新手标识
                "新生儿", "第一次", "新手", "不知道", "怎么办", "初为人母", "初为人父", 
                "刚出生", "新生", "0-6个月", "第一胎", "头胎",
                # 困惑表达
                "不懂", "不会", "学习", "请教", "新手妈妈", "新手爸爸",
                # 婴儿护理
                "怎么喂", "如何冲奶", "吃多少", "睡眠", "哭闹"
            ],
            "二胎妈妈": [
                # 二胎标识
                "二胎", "二宝", "老二", "第二个", "又怀了", "再次", 
                # 经验相关
                "经验", "熟悉", "轻车熟路", "上次", "老大", "大宝",
                # 时间管理
                "忙碌", "省心", "省时", "方便", "简单", "快捷"
            ],
            "混养妈妈": [
                # 混合喂养
                "混喂", "混合喂养", "母乳不够", "奶粉补充", "搭配", "结合", 
                "母乳+奶粉", "白天母乳", "晚上奶粉", "补充喂养",
                # 营养关注
                "营养均衡", "营养补充", "营养不足", "增重", "发育"
            ],
            "贵妇妈妈": [
                # 高端品质
                "有机", "进口", "高端", "品质", "精选", "优质", "奢华", "顶级",
                # 价格不敏感
                "贵一点", "值得", "投资", "最好的", "高档", "专业",
                # 品牌偏好
                "欧洲", "原装进口", "国际品牌"
            ]
        }
        
        # 🔧 改进的置信度计算
        audience_scores = {}
        transcript_lower = transcript.lower()
        total_chars = len(transcript)
        
        for audience, keywords in audience_keywords.items():
            # 计算关键词命中情况
            matched_keywords = []
            for keyword in keywords:
                if keyword in transcript_lower:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                # 基础得分：匹配关键词比例
                base_score = len(matched_keywords) / len(keywords)
                
                # 🎯 权重调整：考虑文本长度和关键词重要性
                length_bonus = min(total_chars / 500, 1.0)  # 文本越长，置信度略微提升
                keyword_weight = len(matched_keywords) * 0.1  # 多个关键词增加权重
                
                # 最终得分
                final_score = min(base_score + length_bonus * 0.1 + keyword_weight, 1.0)
                
                audience_scores[audience] = {
                    "score": final_score,
                    "matched_keywords": matched_keywords,
                    "match_ratio": f"{len(matched_keywords)}/{len(keywords)}"
                }
        
        if audience_scores:
            # 选择得分最高的人群
            best_audience = max(audience_scores, key=lambda x: audience_scores[x]["score"])
            best_result = audience_scores[best_audience]
            confidence = best_result["score"]
            
            logger.info(f"🎯 兜底分析结果: {best_audience} (置信度: {confidence:.2f})")
            logger.info(f"📋 匹配关键词: {best_result['matched_keywords'][:3]}... ({best_result['match_ratio']})")
            
            return {
                "target_audience": best_audience,
                "confidence": confidence,
                "method": "keyword_fallback",
                "matched_keywords": best_result["matched_keywords"],
                "match_details": audience_scores
            }
        else:
            logger.info("🎯 未匹配到明确人群，返回通用人群")
            return {
                "target_audience": "通用妈妈群体", 
                "confidence": 0.3,
                "method": "default_fallback"
            }
            
    except Exception as e:
        logger.error(f"兜底人群分析失败: {e}")
        return {
            "target_audience": "未识别",
            "confidence": 0.0,
            "method": "error",
            "error": str(e)
        }


def _generate_audience_analysis_report(
    analysis_result: Dict[str, Any], 
    transcript: str,
    srt_path: str
) -> Dict[str, Any]:
    """生成人群分析报告"""
    return {
        "analysis_timestamp": Path(srt_path).stat().st_mtime,
        "transcript_stats": {
            "total_length": len(transcript),
            "word_count": len(transcript.split()),
            "has_content": bool(transcript.strip())
        },
        "analysis_method": analysis_result.get("method", "unknown"),
        "confidence_level": "高" if analysis_result.get("confidence", 0) > 0.7 else 
                          "中" if analysis_result.get("confidence", 0) > 0.4 else "低",
        "recommendation": _get_audience_recommendation(analysis_result.get("target_audience", ""))
    }


def _get_audience_recommendation(target_audience: str) -> str:
    """获取针对目标人群的营销建议"""
    recommendations = {
        "孕期妈妈": "强调营养安全、胎儿发育支持，突出专业医学背景",
        "新手爸妈": "提供详细指导、解答常见疑问，强调专业支持和安心感",
        "二胎妈妈": "突出便利性、时间节省，体现实用价值和性价比",
        "混养妈妈": "强调营养均衡、科学配比，提供专业的混合喂养建议",
        "贵妇妈妈": "突出高端品质、进口品牌，强调品质生活和优越选择",
        "通用妈妈群体": "平衡各方面需求，突出产品综合优势"
    }
    
    return recommendations.get(target_audience, "根据目标人群特点定制营销策略")


def validate_transcription_dependencies() -> Dict[str, bool]:
    """
    验证转录功能的依赖
    
    Returns:
        Dict: 验证结果
    """
    checks = {
        "transcribe_core_available": False,
        "deepseek_analyzer_available": False,
        "ffmpeg_available": False
    }
    
    # 检查转录核心模块
    try:
        from src.core.transcribe_core import create_srt_from_video
        checks["transcribe_core_available"] = True
    except ImportError:
        logger.warning("转录核心模块不可用")
    
    # 检查DeepSeek分析器
    try:
        from streamlit_app.modules.ai_analyzers.deepseek_analyzer import DeepSeekAnalyzer
        analyzer = DeepSeekAnalyzer()
        checks["deepseek_analyzer_available"] = analyzer.is_available()
    except ImportError:
        logger.warning("DeepSeek分析器不可用")
    
    # 检查ffmpeg
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        checks["ffmpeg_available"] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("ffmpeg不可用")
    
    return checks 