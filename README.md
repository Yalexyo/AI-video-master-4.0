# AI视频分析大师 3.0

一个功能强大的AI视频内容分析和语义分段系统，支持智能视频分析、内容理解和片段筛选。

## ✨ 主要功能

### 📊 视频内容分析
- **语音转录**：基于DashScope API的高精度语音识别
- **语义分析**：使用Sentence Transformers进行内容语义理解
- **意图匹配**：基于目标人群和产品卖点的智能内容匹配
- **句子完整性修复**：智能边界调整，确保语句完整性

### 🔬 Google Cloud视频智能
- **集成Google Cloud Video Intelligence API**：高精度的视频内容分析
- **对象检测**：识别视频中的物体和场景
- **标签分析**：自动生成内容标签和置信度评分
- **多格式输出**：支持表格、统计和详细视图

### 🔍 内容筛选与可视化
- **多维度筛选**：按语义类型、时长、置信度等条件筛选
- **结果可视化**：直观展示分析结果和匹配度
- **数据导出**：支持CSV、JSON、Excel格式数据导出
- **实时预览**：场景预览和视频片段查看

## 🚀 快速开始

### 环境要求
- Python 3.10+
- FFmpeg (用于视频处理)
- 8GB+ RAM (推荐)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd AI-Video-Master3.0
```

2. **创建虚拟环境**
```bash
python3.10 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或者
.venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **安装FFmpeg**
```bash
# macOS (使用Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# 从 https://ffmpeg.org/download.html 下载并安装
```

5. **配置API密钥**
```bash
cp .env.example .env
# 编辑 .env 文件，添加您的API密钥
```

### 运行应用

```bash
# 启动Streamlit应用
streamlit run streamlit_app/主页.py

# 或指定端口
streamlit run streamlit_app/主页.py --server.port 8501
```

访问 `http://localhost:8501` 开始使用。

## 📁 项目结构

```
AI-video-master-4.0/
├── streamlit_app/                  # Streamlit应用
│   ├── 主页.py                     # 主页面
│   ├── pages/                      # 多页面应用
│   │   ├── 🔍_视频分析.py          # 视频分析页面
│   │   ├── 🔬_Google_Cloud_视频智能测试.py  # Google Cloud测试页面
│   │   ├── ⚙️_设置.py              # 设置页面
│   │   └── 🔧_网络诊断.py          # 网络诊断页面
│   └── utils/                     # 工具函数
├── src/core/                       # 核心功能
│   ├── models/                     # AI模型
│   └── utils/                      # 核心工具
│       ├── video_processor.py      # 视频处理器
│       └── intent_analyzer.py      # 意图分析器
├── data/                           # 数据目录
│   ├── input/                      # 输入视频
│   ├── output/                     # 输出结果
│   ├── processed/                  # 处理后的片段
│   └── temp/                       # 临时文件
├── models/sentence-transformers/   # 本地模型
└── logs/                          # 日志文件
```

## 🛠️ 核心技术

### AI模型集成
- **DashScope API**: 阿里云语音识别和大语言模型
- **Google Cloud Video Intelligence**: 谷歌云视频智能分析
- **Sentence Transformers**: 多语言语义相似度计算
- **Qwen-VL**: 通义千问视觉语言模型

### 视频处理
- **FFmpeg**: 高精度视频切分和格式转换
- **OpenCV**: 视频帧分析和特征提取
- **多格式支持**: MP4, AVI, MOV, MKV, WMV

## ⚙️ 配置说明

### 环境变量配置 (.env)
```bash
# API配置
DASHSCOPE_API_KEY=your_dashscope_api_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json

# 模型配置
DEFAULT_MODEL=qwen-vl-max
SENTENCE_TRANSFORMER_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# 路径配置
DATA_DIR=./data
MODELS_DIR=./models
LOGS_DIR=./logs
```

## 📖 使用指南

### 1. 视频智能分析
1. 访问"🔍 视频分析"页面
2. 上传视频文件（支持多种格式）
3. 选择分析模式和参数
4. 等待语音转录完成
5. 查看分析结果和语义分段

### 2. Google Cloud测试
1. 访问"🔬 Google Cloud 视频智能测试"页面
2. 确保已配置Google Cloud凭据
3. 上传视频进行高精度分析
4. 查看详细的分析结果和置信度评分
5. 导出标准表格格式数据

### 3. 系统设置
1. 访问"⚙️ 设置"页面
2. 配置API密钥和凭据
3. 调整分析参数
4. 测试网络连接

## 🔧 高级功能

### 批量处理
- 支持多视频文件批量处理
- 自动化内容分析和标签生成
- 批量导出和数据整理

### 性能优化
- 多线程视频处理
- 智能缓存机制
- 内存使用优化

### 数据导出
- 标准表格格式（CSV、Excel、JSON）
- 置信度颜色标识
- 自动数据保存和管理

## 🐛 故障排除

### 常见问题

1. **FFmpeg未安装**
   ```bash
   # 检查FFmpeg安装
   ffmpeg -version
   ```

2. **API密钥错误**
   - 检查.env文件配置
   - 验证API密钥有效性

3. **内存不足**
   - 降低检测精度
   - 处理较短的视频片段

4. **视频格式不支持**
   - 使用FFmpeg转换格式
   - 检查编码格式兼容性

### 性能调优

- **高精度模式**: 适合短视频，精确度高但处理慢
- **标准模式**: 平衡精度和速度，推荐日常使用
- **快速模式**: 适合长视频预览，速度快但精度较低

## 📝 更新日志

### v4.0 (当前版本)
- ✅ 新增Google Cloud Video Intelligence集成
- ✅ 优化表格显示和数据导出功能
- ✅ 增强系统状态检查和错误提示
- ✅ 改进用户界面和体验
- ✅ 完善数据保存和管理

### v3.0
- ✅ 语音转录和语义分析优化
- ✅ 意图匹配算法改进
- ✅ 句子完整性修复

### v2.0
- ✅ 语音转录和语义分析
- ✅ 意图匹配算法
- ✅ 句子完整性修复

### v1.0
- ✅ 基础视频分析功能
- ✅ Streamlit界面框架

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📞 支持

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**AI视频分析大师 3.0** - 让视频内容分析更智能、更高效！ 