# 视频分析大师 1.0

一个用于视频内容分析、意图匹配和片段筛选的AI应用。

## 主要功能

- **视频分段与分析**：自动将视频分割成句子级别的片段，提取语音内容。
- **意图匹配**：基于目标人群和产品卖点，匹配相关视频片段。
- **内容筛选**：从大量视频中快速找到符合特定营销需求的内容片段。
- **结果可视化**：展示匹配结果，并提供文本内容查看。

## 使用方法

### 安装依赖

```bash
# 创建虚拟环境
python3.10 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或者
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 设置API密钥

1. 复制示例环境文件：
```bash
cp .env.example .env
```

2. 编辑`.env`文件，添加您的DashScope API密钥：
```
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

### 运行应用

```bash
# 方法1 (使用根目录的包装器脚本)
python app.py
```

或者直接使用Streamlit运行：

```bash
# 方法2 (直接运行Streamlit应用)
streamlit run streamlit_app/app.py
```

## 目录结构

```
AI-Video-Master3.0/
├── app.py                  # 启动应用的包装器脚本
├── streamlit_app/          # Streamlit应用目录
│   ├── app.py              # Streamlit应用主文件
│   ├── config/             # 配置文件目录
│   ├── modules/            # 功能模块目录
│   │   ├── data_loader/    # 数据加载模块
│   │   ├── data_process/   # 数据处理模块
│   │   ├── analysis/       # 分析模块
│   │   └── visualization/  # 数据可视化模块
│   ├── tests/              # 测试目录
│   ├── pages/              # 多页面应用的页面
│   ├── utils/              # 工具函数
│   └── assets/             # 静态资源
├── scripts/                # 实用脚本目录
├── data/                   # 数据目录
│   ├── input/              # 输入数据
│   ├── output/             # 输出结果
│   ├── processed/          # 处理后的数据
│   └── temp/               # 临时文件
├── src/                    # 项目核心Python代码
│   └── core/               # 核心功能模块
├── models/                 # AI模型存放目录
├── logs/                   # 日志文件目录
├── requirements.txt        # 依赖包列表
├── Makefile                # 项目管理命令
└── README.md               # 项目说明
```

## 技术栈

- Python 3.10+
- Streamlit
- FFmpeg (用于视频处理)
- DashScope API (用于语音识别和AI模型)
- Sentence Transformers (用于语义分析)

## 配置

核心配置通过环境变量或 `.env` 文件提供，主要包括：

- API密钥 (DASHSCOPE_API_KEY)
- 默认数据目录
- 模型参数

## 注意事项

- 确保安装了FFmpeg，它用于视频处理和分段。你可以从[FFmpeg官网](https://ffmpeg.org/download.html)下载并安装。
- 处理大型视频文件可能需要较长时间。
- 分析结果的准确性取决于输入视频的质量和语音清晰度。
- 首次运行时，如果未设置API密钥，应用将无法进行语音识别和视频分析。 