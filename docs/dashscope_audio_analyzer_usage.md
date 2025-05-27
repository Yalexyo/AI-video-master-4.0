# DashScope语音转录分析器使用指南

## 概述

DashScope语音转录分析器是专门处理阿里云DashScope语音转录、热词分析、专业词汇矫正功能的模块。该模块提供了统一的接口，支持音频和视频文件的语音转录，以及智能的词汇处理功能。

## 功能特性

- ✅ **音频转录** - 支持多种音频格式的语音转录
- ✅ **视频转录** - 自动提取音频并进行转录
- ✅ **热词分析** - 智能识别和提取关键词
- ✅ **专业词汇矫正** - 基于相似度的术语标准化
- ✅ **自定义词汇表** - 创建和管理专业词汇库
- ✅ **批量处理** - 支持多文件批量转录
- ✅ **成本估算** - 预估转录成本
- ✅ **格式转换** - 灵活的输出格式支持

## 快速开始

### 1. 环境配置

首先确保设置了DashScope API密钥：

```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

### 2. 基本使用

```python
from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer

# 初始化分析器
analyzer = DashScopeAudioAnalyzer()

# 检查可用性
if analyzer.is_available():
    print("DashScope分析器可用")
else:
    print("请检查API密钥配置")
```

## 详细API参考

### 音频转录

```python
# 转录音频文件
result = analyzer.transcribe_audio(
    audio_path="path/to/audio.wav",
    hotwords=["启赋蕴淳", "A2奶源"],  # 可选：热词列表
    professional_terms=["启赋蕴淳A2", "低聚糖HMO"],  # 可选：专业词汇
    language="zh",  # 语言代码
    format_result=True  # 是否格式化结果
)

if result["success"]:
    print(f"转录文本: {result['transcript']}")
    print(f"时间段数: {len(result['segments'])}")
    for segment in result['segments']:
        print(f"{segment['start_time']}s - {segment['end_time']}s: {segment['text']}")
else:
    print(f"转录失败: {result['error']}")
```

### 视频转录

```python
# 转录视频文件（自动提取音频）
result = analyzer.transcribe_video(
    video_path="path/to/video.mp4",
    hotwords=["启赋蕴淳", "A2奶源"],
    professional_terms=["启赋蕴淳A2", "低聚糖HMO"],
    extract_audio_first=True  # 是否先提取音频
)

if result["success"]:
    print(f"视频转录完成: {result['transcript']}")
```

### 热词分析

```python
# 分析文本中的热词
transcript_text = "启赋蕴淳A2奶粉含有低聚糖HMO营养成分"

hotword_result = analyzer.analyze_hotwords(
    transcript_text=transcript_text,
    domain="general"  # 领域：general, medical, legal, finance等
)

if hotword_result["success"]:
    print(f"识别的热词: {hotword_result['hotwords']}")
    print(f"关键词详情: {hotword_result['keywords']}")
```

### 专业词汇矫正

```python
# 矫正专业术语
original_text = "启赋蕴醇A2奶粉含有低聚塘HMO"
professional_terms = ["启赋蕴淳A2", "低聚糖HMO"]

corrected_text = analyzer.correct_professional_terms(
    text=original_text,
    professional_terms=professional_terms,
    similarity_threshold=0.8  # 相似度阈值
)

print(f"原文: {original_text}")
print(f"矫正后: {corrected_text}")
```

### 自定义词汇表

```python
# 创建自定义词汇表
terms = ["启赋蕴淳A2", "低聚糖HMO", "A2奶源", "OPN蛋白"]

vocab_id = analyzer.create_custom_vocabulary(
    terms=terms,
    vocab_name="infant_formula_terms",
    domain="general"
)

if vocab_id:
    print(f"词汇表创建成功，ID: {vocab_id}")
```

### 批量转录

```python
# 批量处理多个文件
file_paths = [
    "audio1.wav",
    "video1.mp4",
    "audio2.m4a"
]

def progress_callback(progress, message):
    print(f"进度: {progress}% - {message}")

results = analyzer.batch_transcribe(
    file_paths=file_paths,
    hotwords=["启赋蕴淳", "A2奶源"],
    professional_terms=["启赋蕴淳A2", "低聚糖HMO"],
    progress_callback=progress_callback
)

for result in results:
    print(f"文件: {result['file_name']}")
    print(f"状态: {'成功' if result['success'] else '失败'}")
    if result['success']:
        print(f"转录: {result['transcript'][:100]}...")
```

### 成本估算

```python
# 估算转录成本
duration_seconds = 300  # 5分钟

cost_info = analyzer.estimate_cost(duration_seconds)
print(f"时长: {cost_info['duration_minutes']}分钟")
print(f"估算成本: {cost_info['estimated_cost_cny']} {cost_info['currency']}")
```

## 支持的文件格式

### 音频格式
- WAV (.wav)
- MP3 (.mp3)
- M4A (.m4a)
- AAC (.aac)
- FLAC (.flac)

### 视频格式
- MP4 (.mp4)
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)
- WebM (.webm)

### 技术规格
- **采样率**: 8000Hz, 16000Hz, 22050Hz, 44100Hz, 48000Hz
- **声道数**: 单声道(1)、立体声(2)
- **推荐格式**: 16kHz单声道WAV格式

## 集成到现有系统

### 在视频分段器中使用

```python
# 在VideoSegmenter中集成
from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer

class VideoSegmenter:
    def __init__(self):
        self.audio_analyzer = DashScopeAudioAnalyzer()
    
    def analyze_audio(self, audio_path, use_new_analyzer=True):
        if use_new_analyzer and self.audio_analyzer.is_available():
            # 使用DashScope分析器
            result = self.audio_analyzer.transcribe_audio(audio_path)
            
            if result["success"]:
                # 转换格式以兼容现有代码
                return {
                    "transcripts": [{
                        "text": result["transcript"],
                        "sentences": result["segments"]
                    }]
                }
        
        # 回退到原有方法
        return self._legacy_transcribe(audio_path)
```

### 在Streamlit页面中使用

```python
import streamlit as st
from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer

# 页面配置
st.title("语音转录工具")

# 初始化分析器
analyzer = DashScopeAudioAnalyzer()

if not analyzer.is_available():
    st.error("DashScope API不可用，请检查API密钥配置")
    st.stop()

# 文件上传
uploaded_file = st.file_uploader(
    "选择音频或视频文件", 
    type=analyzer.get_supported_formats()["audio"] + 
         analyzer.get_supported_formats()["video"]
)

if uploaded_file:
    # 保存临时文件
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # 转录
    with st.spinner("正在转录..."):
        if uploaded_file.name.endswith(('.mp4', '.avi', '.mov')):
            result = analyzer.transcribe_video(temp_path)
        else:
            result = analyzer.transcribe_audio(temp_path)
    
    # 显示结果
    if result["success"]:
        st.success("转录完成！")
        st.text_area("转录文本", result["transcript"], height=200)
        
        # 显示时间段
        st.subheader("时间段详情")
        for i, segment in enumerate(result["segments"]):
            st.write(f"{i+1}. {segment['start_time']:.2f}s - {segment['end_time']:.2f}s")
            st.write(f"   {segment['text']}")
    else:
        st.error(f"转录失败: {result['error']}")
    
    # 清理临时文件
    os.unlink(temp_path)
```

## 错误处理

### 常见错误及解决方案

1. **API密钥未设置**
   ```python
   if not analyzer.is_available():
       st.error("请设置DASHSCOPE_API_KEY环境变量")
   ```

2. **文件格式不支持**
   ```python
   supported_formats = analyzer.get_supported_formats()
   if file_extension not in supported_formats["audio"] + supported_formats["video"]:
       st.error(f"不支持的文件格式: {file_extension}")
   ```

3. **转录失败处理**
   ```python
   result = analyzer.transcribe_audio(audio_path)
   if not result["success"]:
       logger.error(f"转录失败: {result['error']}")
       # 回退到其他转录方法
       return legacy_transcribe(audio_path)
   ```

## 性能优化建议

1. **音频预处理**
   - 转换为16kHz单声道WAV格式
   - 去除背景噪音
   - 音量标准化

2. **批量处理优化**
   - 使用progress_callback监控进度
   - 分批处理大量文件
   - 异步处理提高效率

3. **成本控制**
   - 预先估算转录成本
   - 音频压缩减少传输时间
   - 缓存转录结果避免重复调用

## 扩展功能

### 自定义后处理

```python
class CustomDashScopeAnalyzer(DashScopeAudioAnalyzer):
    def transcribe_audio(self, audio_path, **kwargs):
        # 调用父类方法
        result = super().transcribe_audio(audio_path, **kwargs)
        
        if result["success"]:
            # 自定义后处理
            result["transcript"] = self.custom_post_process(result["transcript"])
            
        return result
    
    def custom_post_process(self, text):
        # 自定义文本处理逻辑
        # 例如：特殊符号处理、格式标准化等
        return text.strip().replace("。。", "。")
```

### 多语言支持

```python
# 支持不同语言的转录
languages = ["zh", "en", "ja", "ko"]

for lang in languages:
    result = analyzer.transcribe_audio(
        audio_path,
        language=lang
    )
    print(f"{lang}: {result['transcript']}")
```

## 最佳实践

1. **错误处理**: 始终检查转录结果的success状态
2. **资源管理**: 及时清理临时文件
3. **性能监控**: 记录转录时间和成本
4. **用户体验**: 提供进度反馈和错误提示
5. **数据验证**: 验证输入文件格式和大小

## 更新日志

- **v1.0.0**: 初始版本，支持基础转录功能
- 集成到AI分析器模块架构
- 支持热词分析和专业词汇矫正
- 添加批量处理和成本估算功能

## 联系支持

如有问题或建议，请通过以下方式联系：
- 项目Issue: 在GitHub仓库提交问题
- 技术支持: 查看阿里云DashScope官方文档 