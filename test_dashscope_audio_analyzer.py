#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试DashScope语音转录分析器模块

验证语音转录、热词分析、专业词汇矫正等功能
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_module_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
        print("✅ DashScopeAudioAnalyzer 导入成功")
        return DashScopeAudioAnalyzer
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return None

def test_analyzer_initialization():
    """测试分析器初始化"""
    print("\n🔍 测试分析器初始化...")
    
    try:
        from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
        
        analyzer = DashScopeAudioAnalyzer()
        
        print(f"✅ 分析器初始化成功")
        print(f"   API可用性: {analyzer.is_available()}")
        
        if analyzer.is_available():
            print("   ✅ DashScope API 可用")
        else:
            print("   ⚠️ DashScope API 不可用 (可能缺少API密钥)")
        
        return analyzer
        
    except Exception as e:
        print(f"❌ 分析器初始化失败: {e}")
        return None

def test_supported_formats():
    """测试支持的格式"""
    print("\n🔍 测试支持的格式...")
    
    try:
        from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
        
        analyzer = DashScopeAudioAnalyzer()
        formats = analyzer.get_supported_formats()
        
        print("✅ 支持的格式:")
        print(f"   音频格式: {formats['audio']}")
        print(f"   视频格式: {formats['video']}")
        print(f"   采样率: {formats['sample_rates']}")
        print(f"   声道数: {formats['channels']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试支持格式失败: {e}")
        return False

def test_professional_terms_correction():
    """测试专业词汇矫正"""
    print("\n🔍 测试专业词汇矫正...")
    
    try:
        from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
        
        analyzer = DashScopeAudioAnalyzer()
        
        # 测试文本
        test_text = "启赋蕴醇A2奶粉含有低聚塘HMO，适合新生儿饮用。"
        professional_terms = ["启赋蕴淳A2", "低聚糖HMO", "新生儿"]
        
        corrected_text = analyzer.correct_professional_terms(
            test_text, professional_terms
        )
        
        print("✅ 专业词汇矫正测试:")
        print(f"   原文: {test_text}")
        print(f"   矫正后: {corrected_text}")
        
        if corrected_text != test_text:
            print("   ✅ 检测到词汇矫正")
        else:
            print("   ℹ️ 未检测到需要矫正的词汇")
        
        return True
        
    except Exception as e:
        print(f"❌ 专业词汇矫正测试失败: {e}")
        return False

def test_cost_estimation():
    """测试成本估算"""
    print("\n🔍 测试成本估算...")
    
    try:
        from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
        
        analyzer = DashScopeAudioAnalyzer()
        
        # 测试不同时长的成本估算
        durations = [60, 300, 600, 1800]  # 1分钟、5分钟、10分钟、30分钟
        
        print("✅ 成本估算:")
        for duration in durations:
            cost_info = analyzer.estimate_cost(duration)
            print(f"   {cost_info['duration_minutes']}分钟: {cost_info['estimated_cost_cny']} {cost_info['currency']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 成本估算测试失败: {e}")
        return False

def test_audio_transcription_simulation():
    """模拟音频转录测试"""
    print("\n🔍 模拟音频转录测试...")
    
    try:
        from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
        
        analyzer = DashScopeAudioAnalyzer()
        
        # 模拟音频文件路径（不存在的文件，测试错误处理）
        fake_audio_path = "test_audio.wav"
        
        result = analyzer.transcribe_audio(fake_audio_path)
        
        print("✅ 转录接口测试:")
        print(f"   成功状态: {result['success']}")
        
        if not result['success']:
            print(f"   错误信息: {result['error']}")
            print("   ✅ 错误处理正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 转录接口测试失败: {e}")
        return False

def test_environment_check():
    """测试环境检查"""
    print("\n🔍 检查环境配置...")
    
    # 检查环境变量
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    
    print("✅ 环境变量检查:")
    if dashscope_key:
        print(f"   DASHSCOPE_API_KEY: 已设置 (长度: {len(dashscope_key)})")
    else:
        print("   DASHSCOPE_API_KEY: 未设置")
    
    # 检查依赖包
    try:
        import dashscope
        print("   ✅ dashscope 包可用")
    except ImportError:
        print("   ❌ dashscope 包未安装")
    
    try:
        import difflib
        print("   ✅ difflib 包可用")
    except ImportError:
        print("   ❌ difflib 包不可用")
    
    return True

def main():
    """主测试函数"""
    print("🚀 开始测试 DashScope语音转录分析器模块")
    print("=" * 60)
    
    # 运行各项测试
    tests = [
        ("环境检查", test_environment_check),
        ("模块导入", test_module_imports),
        ("分析器初始化", test_analyzer_initialization),
        ("支持格式", test_supported_formats),
        ("专业词汇矫正", test_professional_terms_correction),
        ("成本估算", test_cost_estimation),
        ("转录接口", test_audio_transcription_simulation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 测试完成: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！DashScope语音转录分析器模块运行正常。")
    else:
        print("⚠️ 部分测试失败，请检查配置和依赖。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 