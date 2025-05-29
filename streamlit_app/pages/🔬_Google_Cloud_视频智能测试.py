"""
Google Cloud Video Intelligence API 测试页面

用于测试 Google Cloud Video Intelligence API 的功能，包括：
- 镜头切分检测
- 视觉标签检测
- 📦 物体跟踪
- ✂️ 自动切分
- 📊 批量分析
"""

import streamlit as st
import os
import tempfile
import json
from pathlib import Path
import time
import logging
import shutil

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
import sys
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# 标签翻译字典
LABEL_TRANSLATIONS = {
    # 动物类
    "animal": "动物",
    "cat": "猫",
    "cats": "猫",
    "kitten": "小猫",
    "kitty": "小猫",
    "tabby": "虎斑猫",
    "persian cat": "波斯猫",
    "maine coon": "缅因猫",
    "siamese cat": "暹罗猫",
    "whiskers": "胡须",
    "paw": "爪子",
    "tail": "尾巴",
    "fur": "毛发",
    "pet": "宠物",
    "pets": "宠物",
    "dog": "狗",
    "puppy": "小狗",
    "bird": "鸟",
    "fish": "鱼",
    "horse": "马",
    "cow": "牛",
    "sheep": "羊",
    "pig": "猪",
    "chicken": "鸡",
    "duck": "鸭",
    "rabbit": "兔子",
    "mouse": "老鼠",
    "elephant": "大象",
    "lion": "狮子",
    "tiger": "老虎",
    "bear": "熊",
    "monkey": "猴子",
    "panda": "熊猫",
    
    # 尺寸描述
    "small": "小",
    "medium": "中等",
    "large": "大",
    "tiny": "微小",
    "huge": "巨大",
    "sized": "大小的",
    "to": "到",
    
    # 食物类
    "food": "食物",
    "fruit": "水果",
    "vegetable": "蔬菜",
    "meat": "肉类",
    "bread": "面包",
    "cake": "蛋糕",
    "pizza": "披萨",
    "hamburger": "汉堡",
    "sandwich": "三明治",
    "noodles": "面条",
    "rice": "米饭",
    "soup": "汤",
    "salad": "沙拉",
    "coffee": "咖啡",
    "tea": "茶",
    "milk": "牛奶",
    "formula": "奶粉",
    "baby formula": "婴儿奶粉",
    "infant formula": "婴幼儿奶粉",
    "powder": "粉末",
    "bottle": "奶瓶",
    "feeding bottle": "奶瓶",
    "baby bottle": "婴儿奶瓶",
    "sippy cup": "学饮杯",
    "pacifier": "奶嘴",
    "bib": "围嘴",
    "high chair": "高脚椅",
    "baby food": "婴儿食品",
    "cereal": "米粉",
    "juice": "果汁",
    "water": "水",
    "beer": "啤酒",
    "wine": "酒",
    
    # 交通工具
    "car": "汽车",
    "bus": "公交车",
    "truck": "卡车",
    "motorcycle": "摩托车",
    "bicycle": "自行车",
    "train": "火车",
    "airplane": "飞机",
    "boat": "船",
    "ship": "轮船",
    "taxi": "出租车",
    
    # 建筑物和场所
    "house": "房子",
    "home": "家",
    "building": "建筑物",
    "room": "房间",
    "bedroom": "卧室",
    "living room": "客厅",
    "kitchen": "厨房",
    "bathroom": "浴室",
    "nursery": "婴儿房",
    "playroom": "游戏室",
    "park": "公园",
    "playground": "游乐场",
    "hospital": "医院",
    "clinic": "诊所",
    "daycare": "托儿所",
    "kindergarten": "幼儿园",
    "school": "学校",
    "church": "教堂",
    "bridge": "桥",
    "tower": "塔",
    "castle": "城堡",
    "temple": "寺庙",
    "museum": "博物馆",
    "store": "商店",
    "supermarket": "超市",
    "mall": "商场",
    
    # 自然景观
    "tree": "树",
    "flower": "花",
    "grass": "草",
    "mountain": "山",
    "river": "河",
    "lake": "湖",
    "sea": "海",
    "beach": "海滩",
    "forest": "森林",
    "sky": "天空",
    "cloud": "云",
    "sun": "太阳",
    "moon": "月亮",
    "star": "星星",
    "snow": "雪",
    "rain": "雨",
    
    # 人物相关
    "person": "人",
    "people": "人们",
    "man": "男人",
    "woman": "女人",
    "child": "孩子",
    "children": "孩子们",
    "baby": "婴儿",
    "babies": "婴儿们",
    "infant": "婴幼儿",
    "toddler": "幼儿",
    "boy": "男孩",
    "girl": "女孩",
    "kid": "小孩",
    "kids": "小孩们",
    "mother": "妈妈",
    "mom": "妈妈",
    "father": "爸爸",
    "dad": "爸爸",
    "parent": "父母",
    "parents": "父母",
    "family": "家庭",
    "face": "脸",
    "hand": "手",
    "hands": "手",
    "eye": "眼睛",
    "eyes": "眼睛",
    "hair": "头发",
    "smile": "微笑",
    "smiling": "微笑",
    "crying": "哭泣",
    "laughing": "大笑",
    
    # 物品
    "book": "书",
    "toy": "玩具",
    "toys": "玩具",
    "doll": "娃娃",
    "teddy bear": "泰迪熊",
    "stuffed animal": "毛绒玩具",
    "ball": "球",
    "blocks": "积木",
    "puzzle": "拼图",
    "stroller": "婴儿车",
    "pram": "婴儿车",
    "car seat": "安全座椅",
    "crib": "婴儿床",
    "cradle": "摇篮",
    "diaper": "尿布",
    "nappy": "尿布",
    "baby carrier": "婴儿背带",
    "baby monitor": "婴儿监视器",
    "phone": "手机",
    "computer": "电脑",
    "television": "电视",
    "camera": "相机",
    "clock": "时钟",
    "chair": "椅子",
    "table": "桌子",
    "bed": "床",
    "door": "门",
    "window": "窗户",
    "bag": "包",
    "diaper bag": "妈咪包",
    "shoes": "鞋子",
    "clothes": "衣服",
    "baby clothes": "婴儿服装",
    "onesie": "连体衣",
    "hat": "帽子",
    "glasses": "眼镜",
    
    # 颜色
    "red": "红色",
    "blue": "蓝色",
    "green": "绿色",
    "yellow": "黄色",
    "black": "黑色",
    "white": "白色",
    "orange": "橙色",
    "purple": "紫色",
    "pink": "粉色",
    "brown": "棕色",
    "gray": "灰色",
    
    # 活动
    "running": "跑步",
    "walking": "走路",
    "jumping": "跳跃",
    "swimming": "游泳",
    "dancing": "跳舞",
    "singing": "唱歌",
    "playing": "玩耍",
    "eating": "吃",
    "drinking": "喝",
    "feeding": "喂食",
    "breastfeeding": "母乳喂养",
    "bottle feeding": "奶瓶喂养",
    "sleeping": "睡觉",
    "napping": "小憩",
    "crawling": "爬行",
    "sitting": "坐着",
    "standing": "站立",
    "walking": "走路",
    "talking": "说话",
    "babbling": "咿呀学语",
    "crying": "哭泣",
    "laughing": "大笑",
    "giggling": "咯咯笑",
    "hugging": "拥抱",
    "kissing": "亲吻",
    "cuddling": "拥抱",
    "bathing": "洗澡",
    "changing": "换尿布",
    "reading": "阅读",
    "writing": "写作",
    "cooking": "烹饪",
    "driving": "开车",
    "flying": "飞行",
    
    # 其他常见词汇
    "indoor": "室内",
    "outdoor": "户外",
    "day": "白天",
    "night": "夜晚",
    "morning": "早晨",
    "evening": "傍晚",
    "summer": "夏天",
    "winter": "冬天",
    "spring": "春天",
    "autumn": "秋天",
    "hot": "热",
    "cold": "冷",
    "warm": "温暖",
    "cool": "凉爽",
    "big": "大",
    "small": "小",
    "tall": "高",
    "short": "短",
    "long": "长",
    "wide": "宽",
    "narrow": "窄",
    "thick": "厚",
    "thin": "薄",
    "heavy": "重",
    "light": "轻",
    "fast": "快",
    "slow": "慢",
    "new": "新",
    "old": "旧",
    "young": "年轻",
    "beautiful": "美丽",
    "ugly": "丑陋",
    "good": "好",
    "bad": "坏",
    "happy": "快乐",
    "sad": "悲伤",
    "angry": "愤怒",
    "surprised": "惊讶",
    "excited": "兴奋",
    "tired": "疲倦",
    "hungry": "饥饿",
    "thirsty": "口渴",
    
    # 广告和品牌相关
    "advertisement": "广告",
    "commercial": "商业广告",
    "brand": "品牌",
    "logo": "标志",
    "product": "产品",
    "package": "包装",
    "packaging": "包装",
    "label": "标签",
    "text": "文字",
    "banner": "横幅",
    "poster": "海报",
    "sign": "标识",
    "nutrition": "营养",
    "healthy": "健康",
    "organic": "有机",
    "natural": "天然",
    "premium": "高端",
    "quality": "质量",
    
    # 视频制作相关
    "video": "视频",
    "vlog": "视频博客",
    "recording": "录制",
    "filming": "拍摄",
    "camera": "摄像机",
    "microphone": "麦克风",
    "lighting": "灯光",
    "studio": "工作室",
    "background": "背景",
    "scene": "场景",
    "shot": "镜头",
    "close up": "特写",
    "wide shot": "远景",
    
    # 情感和表情
    "emotion": "情感",
    "expression": "表情",
    "joy": "喜悦",
    "love": "爱",
    "care": "关爱",
    "gentle": "温柔",
    "peaceful": "平静",
    "comfortable": "舒适",
    "safe": "安全",
    "trust": "信任"
}

def translate_label_to_chinese(english_label, use_deepseek=False):
    """将英文标签翻译成中文"""
    # 转换为小写进行匹配
    label_lower = english_label.lower().strip()
    
    # 直接匹配本地字典
    if label_lower in LABEL_TRANSLATIONS:
        return LABEL_TRANSLATIONS[label_lower]
    
    # 尝试匹配复合词（用空格分隔的词）
    words = label_lower.split()
    if len(words) > 1:
        translated_words = []
        all_translated = True
        
        for word in words:
            if word in LABEL_TRANSLATIONS:
                translated_words.append(LABEL_TRANSLATIONS[word])
            else:
                # 如果有词没有翻译，保留原词但标记为未完全翻译
                translated_words.append(word)
                all_translated = False
        
        # 如果所有词都翻译了，返回翻译结果
        if all_translated:
            return "".join(translated_words)  # 中文不需要空格
        
        # 如果部分翻译且启用DeepSeek，尝试整体翻译
        if use_deepseek and not all_translated:
            try:
                deepseek_translation = translate_with_deepseek(english_label)
                if deepseek_translation and deepseek_translation != english_label:
                    return deepseek_translation
            except Exception as e:
                pass
        
        # 返回部分翻译结果
        return "".join(translated_words)
    
    # 如果本地字典没有找到且启用了DeepSeek翻译，尝试使用DeepSeek翻译
    if use_deepseek:
        try:
            deepseek_translation = translate_with_deepseek(english_label)
            if deepseek_translation and deepseek_translation != english_label:
                return deepseek_translation
        except Exception as e:
            # 静默处理错误，避免在界面上显示太多警告
            pass
    
    # 如果都没有找到翻译，返回原文
    return english_label

def translate_with_deepseek(english_text):
    """使用DeepSeek API翻译英文标签到中文"""
    try:
        from streamlit_app.modules.ai_analyzers import DeepSeekAnalyzer
        
        # 使用DeepSeek分析器
        analyzer = DeepSeekAnalyzer()
        
        if not analyzer.is_available():
            return None
        
        # 翻译英文标签
        translation = analyzer.translate_text(english_text, "中文")
        return translation
        
    except Exception as e:
        # 静默失败，返回None让调用者处理
        return None

# 页面配置
st.set_page_config(
    page_title="Google Cloud Video Intelligence API 测试",
    page_icon="🔬",
    layout="wide"
)

# 初始化会话状态
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'current_video_path' not in st.session_state:
    st.session_state.current_video_path = None
if 'current_video_id' not in st.session_state:
    st.session_state.current_video_id = None
if 'analysis_config' not in st.session_state:
    st.session_state.analysis_config = None

def check_credentials():
    """检查 Google Cloud 凭据是否已设置"""
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        return True, cred_path
    return False, None

def upload_credentials():
    """上传 Google Cloud 服务账号密钥文件"""
    st.subheader("📁 上传服务账号密钥文件")
    
    uploaded_file = st.file_uploader(
        "选择您的 Google Cloud 服务账号密钥文件 (JSON格式)",
        type=['json'],
        help="从 Google Cloud Console 下载的服务账号密钥文件"
    )
    
    if uploaded_file is not None:
        try:
            # 验证JSON格式
            credentials_data = json.loads(uploaded_file.read())
            
            # 检查必要字段
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in credentials_data]
            
            if missing_fields:
                st.error(f"密钥文件缺少必要字段: {', '.join(missing_fields)}")
                return False
            
            # 保存到临时文件
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            cred_file_path = temp_dir / "google_credentials.json"
            with open(cred_file_path, 'w', encoding='utf-8') as f:
                json.dump(credentials_data, f, indent=2)
            
            # 设置环境变量
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_file_path)
            
            st.success(f"✅ 凭据文件已上传并设置！项目ID: {credentials_data.get('project_id', 'Unknown')}")
            st.info(f"凭据文件路径: {cred_file_path}")
            
            return True
            
        except json.JSONDecodeError:
            st.error("❌ 文件格式错误，请确保上传的是有效的JSON文件")
            return False
        except Exception as e:
            st.error(f"❌ 处理凭据文件时出错: {str(e)}")
            return False
    
    return False

def test_video_intelligence(use_deepseek_translation=False):
    """测试 Video Intelligence API"""
    try:
        from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer
        
        st.subheader("🎬 视频分析测试")
        
        # 创建Google Cloud分析器
        analyzer = GoogleVideoAnalyzer()
        
        # 检查凭据
        has_credentials, cred_path = analyzer.check_credentials()
        if not has_credentials:
            st.error("❌ Google Cloud凭据未设置或无效")
            return
        
        st.success("✅ Google Cloud Video Intelligence 分析器准备就绪！")
        
        # 显示存储桶信息
        st.info("📦 **Cloud Storage**: 系统将使用您的 `ai-video-master` 存储桶（asia-east2 香港）进行批量处理")
        
        # 文件上传
        st.markdown("### 📁 选择视频文件")
        
        # 添加快速测试选项
        test_option = st.radio(
            "选择测试方式：",
            ["上传本地视频文件", "使用 Google Cloud 示例视频（快速测试）"],
            help="示例视频可以快速验证API是否正常工作"
        )
        
        uploaded_video = None
        use_sample_video = False
        
        if test_option == "上传本地视频文件":
            uploaded_video = st.file_uploader(
                "选择要分析的视频文件",
                type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
                help="支持常见的视频格式，建议文件大小不超过50MB以获得更快的处理速度"
            )
        else:
            use_sample_video = True
            st.info("🚀 将使用 Google Cloud 公开示例视频进行快速测试")
            st.markdown("示例视频: `gs://cloud-samples-data/video/cat.mp4`")
        
        if uploaded_video is not None or use_sample_video:
            if uploaded_video is not None:
                # 显示视频信息
                st.write(f"**文件名:** {uploaded_video.name}")
                st.write(f"**文件大小:** {uploaded_video.size / (1024*1024):.2f} MB")
            else:
                st.write("**使用示例视频:** cat.mp4")
                st.write("**文件大小:** ~1.5 MB")
            
            # 选择分析功能
            st.subheader("🔧 选择分析功能")
            
            col1, col2 = st.columns(2)
            
            with col1:
                shot_detection = st.checkbox("镜头切分检测", value=True, help="检测视频中的镜头变化")
                label_detection = st.checkbox("标签检测", value=True, help="识别视频中的物体、场景等")
                
            with col2:
                object_tracking = st.checkbox("物体跟踪", help="跟踪视频中移动的对象")
            
            # 开始分析按钮
            if st.button("🚀 开始分析", type="primary"):
                if not any([shot_detection, label_detection, object_tracking]):
                    st.warning("请至少选择一个分析功能！")
                    return
                
                try:
                    # 准备分析参数
                    features = []
                    if shot_detection:
                        features.append("shot_detection")
                    if label_detection:
                        features.append("label_detection")
                    if object_tracking:
                        features.append("object_tracking")
                    
                    # 设置进度回调
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def progress_callback(progress, message):
                        progress_bar.progress(progress)
                        status_text.text(message)
                    
                    # 执行分析
                    if use_sample_video:
                        # 使用示例视频URI
                        video_uri = "gs://cloud-samples-data/video/cat.mp4"
                        st.info("📡 使用云端示例视频进行分析")
                        
                        analysis_result = analyzer.analyze_video(
                            video_uri=video_uri,
                            features=features,
                            progress_callback=progress_callback
                        )
                        
                        current_video_path = None  # 示例视频无法直接切分
                        current_video_id = "google_sample_cat"
                    else:
                        # 保存上传的视频文件
                        from pathlib import Path
                        temp_dir = Path("data/temp/google_cloud")
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        
                        video_filename = uploaded_video.name
                        video_path = temp_dir / video_filename
                        
                        with open(video_path, "wb") as f:
                            f.write(uploaded_video.read())
                        
                        current_video_path = str(video_path)
                        current_video_id = os.path.splitext(video_filename)[0]
                        
                        st.info(f"📊 正在分析 {len(features)} 个功能，视频大小: {uploaded_video.size/(1024*1024):.1f}MB")
                        
                        analysis_result = analyzer.analyze_video(
                            video_path=current_video_path,
                            features=features,
                            progress_callback=progress_callback
                        )
                    
                    if analysis_result.get("success"):
                        result = analysis_result["result"]
                        
                        # 保存到会话状态
                        st.session_state.analysis_result = result
                        st.session_state.current_video_path = current_video_path
                        st.session_state.current_video_id = current_video_id
                        st.session_state.analysis_config = {
                            'shot_detection': shot_detection,
                            'label_detection': label_detection,
                            'object_tracking': object_tracking,
                            'use_deepseek_translation': use_deepseek_translation
                        }
                        
                        # 显示结果
                        display_results(result, shot_detection, label_detection, object_tracking, use_deepseek_translation, current_video_path, current_video_id)
                    else:
                        st.error(f"❌ 分析失败: {analysis_result.get('error', '未知错误')}")
                    
                except Exception as e:
                    st.error(f"❌ 视频分析失败: {str(e)}")
                    st.info("请检查：\n1. 网络连接是否正常\n2. Google Cloud 凭据是否有效\n3. 是否已启用 Video Intelligence API\n4. 视频文件是否损坏")
                
                finally:
                    # 注意：不要立即删除临时文件，因为后续的切分功能需要使用
                    # 临时文件将在用户离开页面或重新上传时自动清理
                    pass
        
    except ImportError as e:
        st.error("❌ 导入Google Cloud Video Intelligence模块时出错")
        st.error(f"错误详情: {str(e)}")
        
        # 调试信息
        import sys
        st.info("调试信息:")
        st.write(f"- Python路径: {sys.executable}")
        st.write(f"- Python版本: {sys.version}")
        st.write(f"- GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '未设置')}")
        
        # 检查是否是库未安装
        try:
            import google.cloud.videointelligence_v1
            st.success("✅ google-cloud-videointelligence 库已安装")
            st.error("❌ 但是GoogleVideoAnalyzer模块导入失败，可能是模块内部错误")
        except ImportError:
            st.error("❌ 未安装 google-cloud-videointelligence 库")
            st.info("请运行以下命令安装：\n```bash\npip install google-cloud-videointelligence\n```")

def get_time_seconds(time_offset):
    """安全地获取时间偏移的秒数"""
    try:
        if hasattr(time_offset, 'total_seconds'):
            return time_offset.total_seconds()
        elif hasattr(time_offset, 'seconds'):
            # 处理 protobuf Duration 对象
            return time_offset.seconds + time_offset.nanos / 1e9
        else:
            # 如果是数字，直接返回
            return float(time_offset)
    except Exception as e:
        st.warning(f"时间解析错误: {e}")
        return 0.0

def analyze_video_segments(segment_files, video_id):
    """
    对视频切片进行二次分析（仅标签检测）
    
    Args:
        segment_files: 切片文件路径列表
        video_id: 视频ID
    """
    try:
        from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer
        
        # 创建分析器
        analyzer = GoogleVideoAnalyzer()
        
        # 检查凭据是否有效
        has_credentials, cred_path = analyzer.check_credentials()
        if not has_credentials:
            st.error("❌ Google Cloud 凭据未设置或无效")
            return
        
        # 仅使用标签检测
        features = ["label_detection"]
        
        st.info(f"🚀 开始分析 {len(segment_files)} 个切片，功能: 标签检测")
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        segment_results = []
        
        for i, segment_file in enumerate(segment_files):
            try:
                segment_name = segment_file.name
                status_text.text(f"正在分析切片 {i+1}/{len(segment_files)}: {segment_name}")
                
                # 分析单个切片
                def progress_callback(progress, message):
                    overall_progress = (i + progress) / len(segment_files)
                    progress_bar.progress(overall_progress)
                    status_text.text(f"切片 {i+1}/{len(segment_files)}: {message}")
                
                result = analyzer.analyze_video(
                    video_path=str(segment_file),
                    features=features,
                    progress_callback=progress_callback
                )
                
                if result.get("success"):
                    annotation = result["result"].annotation_results[0]
                    
                    # 提取分析结果（仅标签）
                    segment_analysis = {
                        'file_name': segment_name,
                        'file_path': str(segment_file),
                        'file_size': segment_file.stat().st_size / (1024*1024),  # MB
                        'labels': []
                    }
                    
                    # 提取标签
                    if hasattr(annotation, 'segment_label_annotations'):
                        for label in annotation.segment_label_annotations[:5]:  # 前5个标签
                            label_name = label.entity.description
                            label_name_cn = translate_label_to_chinese(label_name, use_deepseek=False)
                            confidence = 0.0
                            
                            if label.segments:
                                confidence = label.segments[0].confidence
                            
                            segment_analysis['labels'].append({
                                'name': label_name_cn,
                                'confidence': confidence
                            })
                    
                    segment_results.append(segment_analysis)
                    
                else:
                    st.warning(f"⚠️ 切片 {segment_name} 分析失败: {result.get('error', '未知错误')}")
                
                # 更新进度
                progress = (i + 1) / len(segment_files)
                progress_bar.progress(progress)
                
            except Exception as e:
                st.error(f"❌ 分析切片 {segment_file.name} 时出错: {str(e)}")
                continue
        
        # 显示分析结果
        progress_bar.progress(1.0)
        status_text.text("✅ 切片分析完成！")
        
        if segment_results:
            display_segment_analysis_results(segment_results, video_id)
        else:
            st.error("❌ 没有成功分析的切片")
            
    except Exception as e:
        st.error(f"❌ 切片分析过程中出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")

def display_segment_analysis_results(segment_results, video_id):
    """显示切片分析结果（简化版）"""
    st.markdown("### 📊 切片分析结果")
    
    # 统计信息
    total_segments = len(segment_results)
    total_size = sum(s['file_size'] for s in segment_results)
    total_labels = sum(len(s['labels']) for s in segment_results)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("分析切片数", total_segments)
    with col2:
        st.metric("总大小", f"{total_size:.1f} MB")
    with col3:
        st.metric("检测标签数", total_labels)
    with col4:
        avg_labels = total_labels / total_segments if total_segments > 0 else 0
        st.metric("平均标签数", f"{avg_labels:.1f}")
    
    # 详细结果表格
    st.markdown("### 📋 详细分析结果")
    
    for i, result in enumerate(segment_results):
        with st.expander(f"🎬 {result['file_name']} ({result['file_size']:.1f} MB)", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 标签信息
                if result['labels']:
                    st.write("**🏷️ 检测到的标签:**")
                    for label in result['labels']:
                        confidence_color = "🟢" if label['confidence'] > 0.7 else "🟡" if label['confidence'] > 0.4 else "🔴"
                        st.write(f"  {confidence_color} {label['name']} (置信度: {label['confidence']:.2f})")
                else:
                    st.write("*未检测到标签*")
            
            with col2:
                st.write(f"**文件路径:**")
                st.code(result['file_path'], language="text")
                
                if st.button(f"📂 打开文件", key=f"open_segment_{i}"):
                    import subprocess
                    subprocess.run(["open", "-R", result['file_path']], check=False)
    
    # 保存分析结果
    if st.button("💾 保存分析结果", key="save_segment_analysis"):
        save_segment_analysis_results(segment_results, video_id)

def save_segment_analysis_results(segment_results, video_id):
    """保存切片分析结果到JSON文件"""
    try:
        import json
        from pathlib import Path
        from datetime import datetime
        
        # 创建保存目录
        root_dir = Path(__file__).parent.parent.parent
        results_dir = root_dir / "data" / "output" / "google_video" / str(video_id)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备结果数据
        analysis_data = {
            'video_id': video_id,
            'analysis_time': datetime.now().isoformat(),
            'total_segments': len(segment_results),
            'segments': segment_results
        }
        
        # 保存到文件
        result_file = results_dir / f"segment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        st.success(f"✅ 分析结果已保存到: {result_file}")
        
        if st.button("📂 打开结果文件夹"):
            import subprocess
            try:
                    subprocess.run(["open", str(results_dir)], check=False)
                    st.success("✅ 已打开结果文件夹")
            except Exception as e:
                    st.error(f"❌ 打开文件夹失败: {str(e)}")
                    st.info(f"📁 文件夹路径: {results_dir}")
        
    except Exception as e:
        st.error(f"❌ 保存分析结果时出错: {str(e)}")

def create_video_segments(video_path, segments_data, video_id, is_clustered=False):
    """
    根据分析结果创建视频片段
    
    Args:
        video_path: 原始视频路径
        segments_data: 片段数据列表
        video_id: 视频ID
        is_clustered: 是否为聚类后的场景切分
    
    Returns:
        成功创建的片段列表
    """
    try:
        # 调试信息
        st.info(f"🔍 调试信息:")
        st.write(f"- 视频路径: {video_path}")
        st.write(f"- 视频ID: {video_id}")
        st.write(f"- 片段数量: {len(segments_data)}")
        st.write(f"- 聚类切分: {'是' if is_clustered else '否'}")
        st.write(f"- 视频文件存在: {os.path.exists(video_path) if video_path else 'N/A'}")
        
        # 创建输出目录
        from pathlib import Path
        root_dir = Path(__file__).parent.parent.parent
        
        if is_clustered:
            # 聚类后的场景切分保存到 data/results/{video_id}_merge/
            base_output_dir = root_dir / "data" / "results"
            output_dir = base_output_dir / f"{video_id}_merge"
            st.info("🧠 聚类场景切分：使用专用保存路径")
        else:
            # 原始镜头切分保存到原来的路径
            base_output_dir = root_dir / "data" / "output" / "google_video"
        output_dir = base_output_dir / str(video_id)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        st.write(f"- 输出目录: {output_dir}")
        
        if not video_path:
            st.error("❌ 视频路径为空，无法进行切分")
            return []
        
        if not os.path.exists(video_path):
            st.error(f"❌ 视频文件不存在: {video_path}")
            return []
        
        # 导入视频处理器
        import sys
        sys.path.append(str(root_dir))
        from src.core.utils.video_processor import VideoProcessor
        
        processor = VideoProcessor()
        created_segments = []
        
        # 显示进度条
        cut_type = "聚类场景" if is_clustered else "视频片段"
        st.info(f"🎬 正在切分{cut_type}...")
        progress_bar = st.progress(0)
        
        for i, segment in enumerate(segments_data):
            try:
                start_time = segment['start_time']
                end_time = segment['end_time']
                segment_type = segment['type']
                confidence = segment.get('confidence', 1.0)
                
                # 确保时间有效
                if start_time >= end_time or end_time - start_time < 0.5:
                    st.warning(f"跳过无效片段 {i+1}: 时间范围 {start_time:.2f}s - {end_time:.2f}s")
                    continue
                
                # 使用VideoProcessor提取片段
                extracted_path = processor.extract_segment(
                    video_path=video_path,
                    start_time=start_time,
                    end_time=end_time,
                    segment_index=i,
                    semantic_type=segment_type,
                    video_id=video_id,
                    output_dir=str(output_dir)
                )
                
                if extracted_path and os.path.exists(extracted_path):
                    created_segments.append({
                        'index': i + 1,
                        'type': segment_type,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'confidence': confidence,
                        'file_path': extracted_path,
                        'file_size': os.path.getsize(extracted_path) / (1024*1024),  # MB
                        'is_clustered': is_clustered
                    })
                    
                    st.success(f"✅ 片段 {i+1}: {segment_type} ({start_time:.1f}s-{end_time:.1f}s)")
                else:
                    st.error(f"❌ 片段 {i+1} 创建失败")
                
                # 更新进度
                progress = (i + 1) / len(segments_data)
                progress_bar.progress(progress)
                    
            except Exception as e:
                st.error(f"❌ 处理片段 {i+1} 时出错: {str(e)}")
                continue
        
        progress_bar.progress(1.0)
        save_location = f"data/results/{video_id}_merge/" if is_clustered else f"data/output/google_video/{video_id}/"
        st.success(f"✅ {cut_type}切分完成：成功创建 {len(created_segments)} 个视频片段")
        st.info(f"📁 片段已保存到: {save_location}")
        
        if is_clustered:
            st.success("🧠 聚类场景切片已保存到专用文件夹，便于区分和管理")
        
        return created_segments
        
    except Exception as e:
        st.error(f"创建视频片段时出错: {str(e)}")
        return []

def display_results(result, shot_detection, label_detection, object_tracking, use_deepseek_translation=False, video_path=None, video_id=None):
    """显示分析结果"""
    st.subheader("📊 分析结果")
    
    if not result.annotation_results:
        st.warning("没有获得分析结果")
        return
    
    annotation = result.annotation_results[0]
    
    # 创建Google Video分析器实例用于数据提取
    from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer
    google_analyzer = GoogleVideoAnalyzer()
    
    # 镜头切分结果
    if shot_detection and annotation.shot_annotations:
        st.subheader("🎬 镜头切分结果")
        
        # 显示原始镜头统计
        total_shots = len(annotation.shot_annotations)
        durations = []
        shot_times = []
        
        for shot in annotation.shot_annotations:
            start_time = get_time_seconds(shot.start_time_offset)
            end_time = get_time_seconds(shot.end_time_offset)
            durations.append(end_time - start_time)
            shot_times.append((start_time, end_time))
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # 使用分析器提取镜头信息
        mock_result = {"success": True, "result": result}
        shots = google_analyzer.extract_shots(mock_result)
        
        # 验证镜头连贯性
        continuity = google_analyzer.validate_shot_continuity(shots)
        
        # 使用分析器的连贯性验证结果
        gaps = continuity["gaps"]
        overlaps = continuity["overlaps"]
        total_video_duration = continuity["total_duration"]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("镜头总数", total_shots)
        with col2:
            st.metric("平均时长", f"{avg_duration:.1f}s")
        with col3:
            st.metric("最短时长", f"{min_duration:.1f}s")
        with col4:
            st.metric("最长时长", f"{max_duration:.1f}s")
        
        # 显示连贯性检查结果
        st.markdown("### 🔍 镜头连贯性检查")
        
        if not gaps and not overlaps:
            st.success("✅ 所有镜头时间完全连贯，无空隙或重叠")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("视频总时长", f"{total_video_duration:.2f}s")
            with col2:
                total_cuts_duration = sum(durations)
                st.metric("镜头总时长", f"{total_cuts_duration:.2f}s")
                if abs(total_video_duration - total_cuts_duration) < 0.1:
                    st.success("✅ 时长匹配完美")
        else:
            if gaps:
                st.warning("⚠️ 发现时间空隙:")
                for gap in gaps:
                    st.write(f"  - {gap}")
            
            if overlaps:
                st.error("❌ 发现时间重叠:")
                for overlap in overlaps:
                    st.write(f"  - {overlap}")
            
            st.info("💡 注意：少量误差（<0.1秒）是正常的，可能由于时间精度造成")
        
        # 显示原始镜头表格
        st.markdown("### 📊 镜头切分结果详情")
        
        shots_data = []
        segments_for_cutting = []
        
        for shot in shots:
            shots_data.append({
                "镜头": f"镜头 {shot['index']}",
                "开始时间 (秒)": f"{shot['start_time']:.2f}",
                "结束时间 (秒)": f"{shot['end_time']:.2f}",
                "持续时间 (秒)": f"{shot['duration']:.2f}"
            })
            
            segments_for_cutting.append({
                'start_time': shot['start_time'],
                'end_time': shot['end_time'],
                'type': shot['type'],
                'confidence': shot['confidence']
            })
        
        if shots_data:
            import pandas as pd
            df = pd.DataFrame(shots_data)
            st.dataframe(
                df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "镜头": st.column_config.TextColumn("镜头", width="small"),
                    "开始时间 (秒)": st.column_config.NumberColumn("开始时间 (秒)", width="medium"),
                    "结束时间 (秒)": st.column_config.NumberColumn("结束时间 (秒)", width="medium"),
                    "持续时间 (秒)": st.column_config.NumberColumn("持续时间 (秒)", width="medium")
                }
            )
    
    # 标签检测结果
    if label_detection and annotation.segment_label_annotations:
        st.subheader("🏷️ 标签检测结果")
        
        try:
            # 使用分析器提取标签信息
            mock_result = {"success": True, "result": result}
            labels = google_analyzer.extract_labels(mock_result)
            
            # 准备表格数据
            label_data = []
            
            # 翻译状态统计
            local_translated = 0
            deepseek_translated = 0
            
            for label in labels[:20]:  # 显示前20个标签
                label_name = label['label']
                
                # 先尝试本地翻译
                local_translation = translate_label_to_chinese(label_name, use_deepseek=False)
                if local_translation != label_name:
                    label_name_cn = local_translation
                    local_translated += 1
                elif use_deepseek_translation:
                    # 使用DeepSeek翻译
                    deepseek_translation = translate_with_deepseek(label_name)
                    if deepseek_translation and deepseek_translation != label_name:
                        label_name_cn = deepseek_translation
                        deepseek_translated += 1
                    else:
                        label_name_cn = label_name
                else:
                    label_name_cn = label_name
                
                # 格式化时间显示
                start_time = label['start_time']
                end_time = label['end_time']
                confidence = label['confidence']
                
                start_min = int(start_time // 60)
                start_sec = int(start_time % 60)
                end_min = int(end_time // 60)
                end_sec = int(end_time % 60)
                
                time_range = f"{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}"
                
                label_data.append({
                    "标签": label_name_cn,
                    "时间段": time_range,
                    "置信度": f"{confidence:.2f}"
                })
            
            if label_data:
                # 显示为表格
                import pandas as pd
                df = pd.DataFrame(label_data)
                
                # 设置表格样式
                st.dataframe(
                    df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "标签": st.column_config.TextColumn(
                            "标签",
                            help="检测到的物体或场景标签",
                            width="medium"
                        ),
                        "时间段": st.column_config.TextColumn(
                            "时间段",
                            help="标签出现的时间范围",
                            width="medium"
                        ),
                        "置信度": st.column_config.NumberColumn(
                            "置信度",
                            help="AI识别的置信度（0-1之间）",
                            width="small",
                            format="%.2f"
                        )
                    }
                )
                
                # 统计信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("检测到的标签类型", len(annotation.segment_label_annotations))
                with col2:
                    st.metric("标签实例总数", len(label_data))
                with col3:
                    avg_confidence = sum(float(item["置信度"]) for item in label_data) / len(label_data)
                    st.metric("平均置信度", f"{avg_confidence:.2f}")
                with col4:
                    if use_deepseek_translation:
                        st.metric("AI翻译标签", deepseek_translated)
                    else:
                        st.metric("本地翻译", local_translated)
                
                # 翻译详情
                if use_deepseek_translation and (local_translated > 0 or deepseek_translated > 0):
                    st.info(f"📊 翻译统计: 本地字典翻译 {local_translated} 个，DeepSeek AI翻译 {deepseek_translated} 个")
                
                # 添加标签片段切分功能
                if video_path and video_id:
                    st.markdown("### 🏷️ 标签片段切分")
                    
                    # 可调节的参数设置
                    with st.expander("⚙️ 标签片段参数设置", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            min_duration = st.slider(
                                "最小片段时长（秒）",
                                min_value=0.5,
                                max_value=5.0,
                                value=1.0,
                                step=0.5,
                                help="短于此时长的标签片段将被过滤"
                            )
                        with col2:
                            min_confidence = st.slider(
                                "最小置信度",
                                min_value=0.1,
                                max_value=1.0,
                                value=0.5,
                                step=0.1,
                                help="低于此置信度的标签片段将被过滤"
                            )
                        with col3:
                            max_labels = st.slider(
                                "最大标签数量",
                                min_value=5,
                                max_value=50,
                                value=10,
                                step=5,
                                help="处理的标签数量上限"
                            )
                    
                    # 统计原始标签信息
                    total_labels = len(annotation.segment_label_annotations)
                    all_segments_count = 0
                    filtered_segments_count = 0
                    
                    # 准备标签片段数据
                    label_segments = []
                    label_debug_info = []
                    
                    for i, label in enumerate(annotation.segment_label_annotations[:max_labels]):
                        label_name = label.entity.description
                        label_name_cn = translate_label_to_chinese(label_name, use_deepseek=use_deepseek_translation)
                        
                        for segment in label.segments:
                            try:
                                start_time = get_time_seconds(segment.segment.start_time_offset)
                                end_time = get_time_seconds(segment.segment.end_time_offset)
                                confidence = segment.confidence
                                duration = end_time - start_time
                                
                                all_segments_count += 1
                                
                                # 记录调试信息
                                label_debug_info.append({
                                    'label': label_name_cn,
                                    'duration': duration,
                                    'confidence': confidence,
                                    'start_time': start_time,
                                    'end_time': end_time,
                                    'passed_duration': duration >= min_duration,
                                    'passed_confidence': confidence >= min_confidence
                                })
                                
                                if duration >= min_duration and confidence >= min_confidence:
                                    filtered_segments_count += 1
                                    label_segments.append({
                                        'start_time': start_time,
                                        'end_time': end_time,
                                        'type': f"标签_{label_name_cn}",
                                        'confidence': confidence
                                    })
                            except Exception as e:
                                continue
                    
                    # 显示统计信息
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("检测到的标签", total_labels)
                    with col2:
                        st.metric("原始片段数", all_segments_count)
                    with col3:
                        st.metric("过滤后片段", filtered_segments_count)
                    with col4:
                        filter_rate = (filtered_segments_count / all_segments_count * 100) if all_segments_count > 0 else 0
                        st.metric("通过率", f"{filter_rate:.1f}%")
                    
                    # 显示详细的过滤信息
                    if st.checkbox("显示标签过滤详情", key="show_label_filter_details"):
                        st.markdown("#### 📊 标签片段过滤详情")
                        
                        if label_debug_info:
                            import pandas as pd
                            df_debug = pd.DataFrame(label_debug_info)
                            
                            # 添加状态列
                            df_debug['状态'] = df_debug.apply(
                                lambda row: '✅ 通过' if row['passed_duration'] and row['passed_confidence'] 
                                else f"❌ {'时长不足' if not row['passed_duration'] else ''}{'置信度低' if not row['passed_confidence'] else ''}", 
                                axis=1
                            )
                            
                            # 格式化显示
                            df_display = df_debug[['label', 'duration', 'confidence', '状态']].copy()
                            df_display['duration'] = df_display['duration'].apply(lambda x: f"{x:.2f}s")
                            df_display['confidence'] = df_display['confidence'].apply(lambda x: f"{x:.2f}")
                            df_display.columns = ['标签', '时长', '置信度', '状态']
                            
                            st.dataframe(df_display, use_container_width=True, hide_index=True)
                            
                            # 分析过滤原因
                            duration_filtered = len([x for x in label_debug_info if not x['passed_duration']])
                            confidence_filtered = len([x for x in label_debug_info if not x['passed_confidence']])
                            
                            st.info(f"📈 过滤统计: {duration_filtered} 个因时长不足被过滤，{confidence_filtered} 个因置信度过低被过滤")
                        else:
                            st.warning("没有标签片段数据")
                    
                    if label_segments:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.info(f"将根据 {len(label_segments)} 个标签片段切分视频")
                        with col2:
                            if st.button("🔪 开始切分标签", type="secondary"):
                                with st.spinner("正在切分标签片段..."):
                                    created_segments = create_video_segments(video_path, label_segments, video_id, is_clustered=False)
                                    
                                    if created_segments:
                                        st.success(f"✅ 成功创建 {len(created_segments)} 个标签片段")
                                        
                                        # 显示创建的片段信息
                                        with st.expander("📁 查看创建的标签片段", expanded=True):
                                            for segment in created_segments:
                                                col1, col2, col3 = st.columns([2, 1, 1])
                                                with col1:
                                                    st.write(f"**{segment['type']}** ({segment['duration']:.1f}秒)")
                                                with col2:
                                                    st.write(f"{segment['file_size']:.1f} MB")
                                                with col3:
                                                    if st.button(f"📁 打开", key=f"open_label_{segment['index']}"):
                                                        import subprocess
                                                        subprocess.run(["open", "-R", segment['file_path']], check=False)
                                    else:
                                        st.error("❌ 标签片段创建失败")
                    else:
                        st.info("没有找到适合切分的标签片段（需要至少1秒长度）")
                    
            else:
                st.warning("没有成功解析的标签数据")
                
        except Exception as e:
            st.error(f"标签检测结果显示错误: {e}")
            # 显示原始数据用于调试
            st.write("原始标签数据:")
            st.json(str(annotation.segment_label_annotations[0]) if annotation.segment_label_annotations else "无数据")
    
    # 显示调试信息
    with st.expander("🔍 调试信息"):
        st.write("**分析结果详情:**")
        
        # 检查各种分析结果
        results_summary = []
        
        # 镜头切分
        if hasattr(annotation, 'shot_annotations'):
            if annotation.shot_annotations:
                results_summary.append(f"✅ 镜头切分: {len(annotation.shot_annotations)} 个镜头")
            else:
                results_summary.append("❌ 镜头切分: 无结果")
        else:
            results_summary.append("❌ 镜头切分: 未检测")
            
        # 标签检测
        if hasattr(annotation, 'segment_label_annotations'):
            if annotation.segment_label_annotations:
                results_summary.append(f"✅ 标签检测: {len(annotation.segment_label_annotations)} 个标签")
            else:
                results_summary.append("❌ 标签检测: 无结果")
        else:
            results_summary.append("❌ 标签检测: 未检测")
            
        # 物体跟踪
        if hasattr(annotation, 'object_annotations'):
            if annotation.object_annotations:
                results_summary.append(f"✅ 物体跟踪: {len(annotation.object_annotations)} 个物体")
            else:
                results_summary.append("❌ 物体跟踪: 无结果")
        else:
            results_summary.append("❌ 物体跟踪: 未检测")
        
        for result in results_summary:
            st.write(f"- {result}")
            
        # 显示原始annotation结构（用于高级调试）
        if st.checkbox("显示原始API响应结构"):
            st.write("**原始annotation对象属性:**")
            attrs = [attr for attr in dir(annotation) if not attr.startswith('_')]
            st.write(attrs)
            
            st.write("**annotation对象详情:**")
            st.json({
                "has_shot_annotations": hasattr(annotation, 'shot_annotations'),
                "has_segment_label_annotations": hasattr(annotation, 'segment_label_annotations'),
                "has_object_annotations": hasattr(annotation, 'object_annotations'),
            })
    
    # 添加视频切分功能
    if video_path and video_id and segments_for_cutting:
        st.markdown(f"### 🎬 视频镜头切分")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"将根据 {len(segments_for_cutting)} 个镜头切分视频片段")
            st.write(f"📁 保存路径: `data/output/google_video/{video_id}/`")
        with col2:
            if st.button("🔪 开始切分", type="primary", key="cut_original_shots"):
                with st.spinner("正在切分视频镜头..."):
                    created_segments = create_video_segments(
                        video_path, segments_for_cutting, video_id, is_clustered=False
                    )
                    
                    if created_segments:
                        st.success(f"✅ 成功创建 {len(created_segments)} 个镜头片段")
                        
                        # 显示创建的片段信息
                        with st.expander("📁 查看创建的片段", expanded=True):
                            for segment in created_segments:
                                col1, col2, col3 = st.columns([2, 1, 1])
                                
                                with col1:
                                    st.write(f"**片段 {segment['index']}**: {segment['type']}")
                                    st.write(f"时间: {segment['start_time']:.1f}s - {segment['end_time']:.1f}s")
                                
                                with col2:
                                    st.write(f"📁 {segment['file_size']:.1f}MB")
                                
                                with col3:
                                    if st.button(f"📂 打开", key=f"open_shot_{segment['index']}"):
                                        import subprocess
                                        try:
                                            subprocess.run(["open", "-R", segment['file_path']], check=False)
                                        except Exception as e:
                                            st.error(f"无法打开文件夹: {e}")
                    else:
                        st.error("❌ 视频片段创建失败")

def main():
    """主函数"""
    st.title("🔬 Google Cloud Video Intelligence API 测试")
    
    # 🔥 立即显示凭据状态检查
    st.markdown("### 📊 系统状态检查")
    
    # 检查Google Cloud凭据状态
    has_credentials, cred_path = check_credentials()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if has_credentials:
            try:
                with open(cred_path, 'r', encoding='utf-8') as f:
                    cred_data = json.load(f)
                    project_id = cred_data.get('project_id', 'Unknown')
                st.success(f"✅ **Google Cloud凭据**: 已配置 (项目: {project_id})")
                st.info(f"📁 凭据文件: {cred_path}")
            except Exception:
                st.success("✅ **Google Cloud凭据**: 已配置")
        else:
            st.error("❌ **Google Cloud凭据**: 未设置")
            st.warning("⚠️ **无法使用Google Cloud Video Intelligence功能**")
            
            with st.expander("🔧 如何设置Google Cloud凭据", expanded=True):
                st.markdown("""
                **快速设置步骤:**
                
                1. **在本页面设置标签页上传**
                   - 点击下方 "⚙️ 设置" 标签页
                   - 上传Google Cloud服务账户JSON文件
                
                2. **获取凭据文件步骤:**
                   - 访问 [Google Cloud Console](https://console.cloud.google.com)
                   - 创建项目 → 启用Video Intelligence API
                   - 创建服务账户 → 下载JSON密钥文件
                   - 上传到本页面设置区域
                
                3. **确保API权限:**
                   - Cloud Video Intelligence API
                   - Cloud Storage API (用于文件上传)
                """)
    
    with col2:
        if has_credentials:
            # 显示服务状态
            st.metric("Google Cloud", "已连接", "✅")
        # 删除未配置的错误提示和按钮模块
    
    st.markdown("---")
    
    # 如果未配置凭据，显示主要说明但禁用功能
    if not has_credentials:
        st.warning("🚫 **请先配置Google Cloud凭据才能使用此页面功能**")
        st.markdown("""
        ### 📋 功能介绍（需要凭据配置后使用）:
        - 🎬 **镜头切分检测**：智能检测视频场景变化
        - 🏷️ **标签检测**：识别视频中的物体、场景、动作
        - 📦 **物体跟踪**：跟踪视频中移动的对象
        - ✂️ **自动切分**：根据检测结果自动生成视频片段
        - 📊 **批量分析**：支持多片段并行处理
        """)
        
        # 显示设置标签页，但禁用其他功能
        tab_settings = st.tabs(["⚙️ 设置"])[0]
        with tab_settings:
            st.markdown("### 📋 Google Cloud 凭据设置")
            st.markdown("""
            **首次使用需要配置Google Cloud凭据文件：**
            """)
            
            if upload_credentials():
                st.rerun()
        
        return
    
    # 有凭据时显示完整功能
    st.markdown("""
    这个测试页面可以帮您验证 Google Cloud Video Intelligence API 的各项功能，包括：
    - 🎬 镜头切分检测
    - 🏷️ 标签检测
    - 📦 物体跟踪
    
    **🚀 核心功能**:
    - ✂️ **智能视频切分**: 根据镜头检测结果自动切分视频片段
    - 📁 片段自动保存到 `data/output/google_video/` 目录
    - 📊 提供详细的分析统计和可视化展示
    
    **使用流程**: 上传视频 → Google Cloud AI分析 → 视频切分 → 在'🏷️ 片段标签分析'模块进行AI标注
    """)
    st.markdown("---")
    
    # 功能选择标签页
    tab1, tab2, tab3, tab4 = st.tabs(["🎬 视频分析与切分", "🛍️ 场景聚合", "🏷️ 片段标签分析", "⚙️ 设置"])
    
    with tab1:
            # 保留兼容性
            use_deepseek_translation = False
            
            # 检查是否有保存的分析结果
            if st.session_state.analysis_result and st.session_state.analysis_config:
                st.success("✅ 发现之前的分析结果")
                
                # 显示之前的分析结果
                config = st.session_state.analysis_config
                display_results(
                    st.session_state.analysis_result,
                    config['shot_detection'],
                    config['label_detection'], 
                    config['object_tracking'],
                    config['use_deepseek_translation'],
                    st.session_state.current_video_path,
                    st.session_state.current_video_id
                )
                
                # 添加清除结果按钮
                if st.button("🔄 重新分析", type="secondary"):
                    st.session_state.analysis_result = None
                    st.session_state.current_video_path = None
                    st.session_state.current_video_id = None
                    st.session_state.analysis_config = None
                    st.rerun()
            else:
                # 开始测试
                test_video_intelligence(use_deepseek_translation)
    
    with tab2:
        st.subheader("🛍️ 场景聚合")
        st.markdown("""
        对已切分的视频片段进行智能聚合，生成更有意义的场景：
        - 🧠 **视觉特征聚类**: 基于颜色、纹理、边缘等135维特征进行聚合
        - 📊 **自适应聚类**: 自动确定最佳聚类数量
        - ⏱️ **时间连续性保证**: 确保聚合后的场景在时间上连续
        """)
        
        # 场景聚合功能
        scene_clustering_interface()
    
    with tab3:
        st.subheader("🏷️ 视频片段标签分析")
        st.markdown("""
        针对已切分的视频片段进行AI标签分析，支持多种分析模型：
        - 🌐 **Google Cloud Video Intelligence**: 高精度标签检测
        - 🧠 **Qwen模型**: 本地化视觉理解分析
        """)
        
        # 视频片段标签分析功能
        analyze_existing_segments()
    
    with tab4:
        st.subheader("⚙️ 系统设置")
        
        # Google Cloud凭据设置
        st.markdown("### 📋 Google Cloud 凭据设置")
        
        if has_credentials:
            st.success(f"✅ Google Cloud 凭据已设置: {cred_path}")
            
            # 显示当前项目信息
            try:
                with open(cred_path, 'r', encoding='utf-8') as f:
                    cred_data = json.load(f)
                    st.info(f"当前项目ID: {cred_data.get('project_id', 'Unknown')}")
            except:
                pass
            
            # 提供重新上传选项
            if st.button("🔄 重新上传凭据文件"):
                if upload_credentials():
                    st.rerun()
        else:
            st.markdown("""
            ### 📋 设置步骤：
            
            1. **创建 Google Cloud 项目**
               - 访问 [Google Cloud Console](https://console.cloud.google.com)
               - 创建新项目或选择现有项目
            
            2. **启用 Video Intelligence API**
               - 在导航菜单中选择 "API 和服务" > "库"
               - 搜索并启用 "Cloud Video Intelligence API"
            
            3. **创建服务账号**
               - 在导航菜单中选择 "API 和服务" > "凭据"
               - 点击 "创建凭据" > "服务账号"
               - 填写服务账号信息并完成创建
            
            4. **下载密钥文件**
               - 在服务账号列表中，点击刚创建的账号
               - 选择 "密钥" 标签页
               - 点击 "添加密钥" > "创建新密钥"，选择 JSON 格式
            
            5. **上传密钥文件**
               - 使用下面的文件上传器上传刚下载的 JSON 密钥文件
            """)
            
            # 上传凭据
            if upload_credentials():
                st.rerun()

    # 在main函数最后添加数据存储说明
    st.markdown("---")
    st.markdown("### 📁 数据存储说明")
    
    with st.expander("📂 分析结果存放位置", expanded=False):
        st.markdown("""
        **🎯 分析结果自动保存位置：**
        
        **📊 JSON格式原始数据：**
        - **Google Cloud分析**: `data/output/google_video/{video_id}/google_cloud_analysis_{timestamp}.json`
        - **Qwen模型分析**: `data/output/google_video/{video_id}/qwen_analysis_{timestamp}.json`
        
        **📋 表格导出数据：**
        - **CSV表格**: `data/results/{filename}.csv` (UTF-8格式，Excel可直接打开)
        - **JSON表格**: `data/results/{filename}.json` (结构化数据)
        - **Excel表格**: `data/results/{filename}.xlsx` (如果安装了openpyxl)
        
        **🎬 视频片段文件：**
        - **分割片段**: `data/output/google_video/{video_id}/segments/`
        - **原始视频**: `data/input/` (用户上传的视频)
        
        **💡 快速访问：**
        - 点击分析结果页面的"📂 打开片段文件夹"按钮可直接打开对应目录
        - 点击"💾 导出表格数据"按钮可生成多格式表格文件
        - 所有分析都会自动保存，无需手动操作
        
        **📋 表格格式说明：**
        ```
        video_id | start_time | end_time | visual_label | confidence
        1.mp4    | 00:00:00   | 00:00:04 | baby,chair    | 🟢 0.915
        1.mp4    | 00:00:04   | 00:00:08 | garden,plant  | 🟡 0.650
        ```
        
        **🎨 置信度颜色含义：**
        - 🟢 **高置信度 (0.8-1.0)**: 结果非常可靠，可直接使用
        - 🟡 **中等置信度 (0.5-0.8)**: 结果较可靠，建议人工核查  
        - 🔴 **低置信度 (0.0-0.5)**: 结果不太可靠，需要验证
        """)

def analyze_existing_segments():
    """分析已存在的视频片段"""
    st.markdown("### 📁 选择视频片段目录")
    
    # 扫描可用的视频ID目录
    from pathlib import Path
    root_dir = Path(__file__).parent.parent.parent
    base_output_dir = root_dir / "data" / "output" / "google_video"
    
    if not base_output_dir.exists():
        st.warning("❌ 未找到视频片段目录")
        st.info("请先在 '🎬 视频分析与切分' 标签页中完成视频切分")
        return
    
    # 获取所有视频ID目录
    video_dirs = [d for d in base_output_dir.iterdir() if d.is_dir()]
    
    if not video_dirs:
        st.warning("❌ 未找到任何视频片段")
        st.info("请先在 '🎬 视频分析与切分' 标签页中完成视频切分")
        return
    
    # 选择视频ID
    video_ids = [d.name for d in video_dirs]
    selected_video_id = st.selectbox(
        "选择要分析的视频ID：",
        video_ids,
        help="这些是已经切分过的视频项目"
    )
    
    if selected_video_id:
        segments_dir = base_output_dir / selected_video_id
        
        # 获取片段文件
        segment_files = list(segments_dir.glob("*.mp4"))
        segment_files.sort()
        
        if not segment_files:
            st.warning(f"❌ 在目录 {segments_dir} 中未找到视频片段")
            return
        
        st.success(f"✅ 找到 {len(segment_files)} 个视频片段")
        
        # 显示片段信息
        with st.expander("📋 片段列表", expanded=False):
            for i, segment_file in enumerate(segment_files[:10]):  # 只显示前10个
                file_size = segment_file.stat().st_size / (1024*1024)
                st.write(f"{i+1}. {segment_file.name} ({file_size:.1f} MB)")
            
            if len(segment_files) > 10:
                st.write(f"... 还有 {len(segment_files) - 10} 个片段")
        
        # 选择分析模型
        st.markdown("### 🤖 选择分析模型")
        
        analysis_model = "Qwen视觉模型"
        st.info("🧠 使用Qwen视觉模型进行视频片段标签分析")
        
        # 删除Google Cloud相关的批处理选项
        use_batch_api = False
        cleanup_files = True
        
        # 分析参数设置
        with st.expander("⚙️ 分析参数", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                max_segments = st.slider(
                    "分析片段数量",
                    min_value=1,
                    max_value=min(len(segment_files), 50),
                    value=min(len(segment_files), 50),
                    help="为了节省时间和资源，可以限制分析的片段数量"
                )
            
            with col2:
                batch_size = st.slider(
                    "批处理大小",
                    min_value=1,
                    max_value=5,
                    value=2,
                    help="同时处理的片段数量，影响分析速度"
                )
        
        # 开始分析按钮
        if st.button("🚀 开始片段标签分析", type="primary"):
            if analysis_model == "Qwen视觉模型":
                analyze_segments_with_qwen(segment_files[:max_segments], selected_video_id, batch_size)
            else:
                st.warning("🚫 当前选择的分析模型不支持")

def analyze_segments_with_qwen(segment_files, video_id, batch_size=2):
    """使用Qwen模型分析视频片段（优化版批处理）"""
    st.markdown("### 🧠 Qwen模型片段分析")
    
    try:
        # 检查Qwen分析器是否可用
        from streamlit_app.modules.ai_analyzers import QwenVideoAnalyzer
        
        analyzer = QwenVideoAnalyzer()
        if not analyzer.is_available():
            st.error("❌ Qwen分析器不可用，请检查DASHSCOPE_API_KEY配置")
            return
        
        st.info(f"🚀 开始使用Qwen模型分析 {len(segment_files)} 个片段（批处理大小: {batch_size}）")
        
        # 创建进度条和状态显示
        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics_cols = st.columns(4)
        
        with metrics_cols[0]:
            total_metric = st.metric("总片段", len(segment_files))
        with metrics_cols[1]:
            processed_metric = st.metric("已处理", 0)
        with metrics_cols[2]:
            success_metric = st.metric("成功", 0)
        with metrics_cols[3]:
            error_metric = st.metric("失败", 0)
        
        segment_results = []
        processed_count = 0
        success_count = 0
        error_count = 0
        
        # 优化的批处理分析 - 添加延时和重试机制
        for i in range(0, len(segment_files), batch_size):
            batch_files = segment_files[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(segment_files) + batch_size - 1) // batch_size
            
            status_text.text(f"📦 处理批次 {batch_num}/{total_batches}，包含 {len(batch_files)} 个片段")
            
            # 处理当前批次中的每个文件
            for j, segment_file in enumerate(batch_files):
                current_index = i + j + 1
                
                try:
                    segment_name = segment_file.name
                    status_text.text(f"🔍 正在分析片段 {current_index}/{len(segment_files)}: {segment_name}")
                    
                    # 重试机制
                    max_retries = 2
                    analysis_result = None
                    
                    for retry in range(max_retries + 1):
                        try:
                            # 使用Qwen分析视频内容
                            analysis_result = analyzer.analyze_video_segment(
                                video_path=str(segment_file),
                                tag_language="中文",
                                frame_rate=2.0
                            )
                            
                            if analysis_result.get("success"):
                                break  # 成功则退出重试循环
                            else:
                                if retry < max_retries:
                                    status_text.text(f"⚠️ 片段 {segment_name} 分析失败，正在重试 ({retry + 1}/{max_retries})...")
                                    time.sleep(1)  # 重试前等待1秒
                                    
                        except Exception as e:
                            if retry < max_retries:
                                status_text.text(f"⚠️ 片段 {segment_name} 分析异常，正在重试 ({retry + 1}/{max_retries}): {str(e)}")
                                time.sleep(1)
                            else:
                                raise e
                    
                    processed_count += 1
                    
                    if analysis_result and analysis_result.get("success"):
                        success_count += 1
                        
                        # 提取标签信息
                        labels = []
                        
                        # 从不同分析结果中提取标签
                        objects = analysis_result.get("objects", [])
                        scenes = analysis_result.get("scenes", [])
                        emotions = analysis_result.get("emotions", [])
                        brands = analysis_result.get("brands", [])  # 新增品牌标签
                        
                        # 物体标签
                        for obj in objects:
                            if isinstance(obj, dict):
                                labels.append({
                                    "name": obj.get("name", "未知物体"),
                                    "confidence": obj.get("confidence", 0.8),
                                    "type": "物体"
                                })
                            else:
                                labels.append({
                                    "name": str(obj),
                                    "confidence": 0.8,
                                    "type": "物体"
                                })
                        
                        # 场景标签
                        for scene in scenes:
                            if isinstance(scene, dict):
                                labels.append({
                                    "name": scene.get("name", "未知场景"),
                                    "confidence": scene.get("confidence", 0.8),
                                    "type": "场景"
                                })
                            else:
                                labels.append({
                                    "name": str(scene),
                                    "confidence": 0.8,
                                    "type": "场景"
                                })
                        
                        # 情绪标签
                        for emotion in emotions:
                            if isinstance(emotion, dict):
                                labels.append({
                                    "name": emotion.get("name", "未知情绪"),
                                    "confidence": emotion.get("confidence", 0.8),
                                    "type": "情绪"
                                })
                            else:
                                labels.append({
                                    "name": str(emotion),
                                    "confidence": 0.8,
                                    "type": "情绪"
                                })
                        
                        # 品牌标签
                        for brand in brands:
                            if isinstance(brand, dict):
                                labels.append({
                                    "name": brand.get("name", "未知品牌"),
                                    "confidence": brand.get("confidence", 0.8),
                                    "type": "品牌"
                                })
                            else:
                                labels.append({
                                    "name": str(brand),
                                    "confidence": 0.8,
                                    "type": "品牌"
                                })
                        
                        # 生成内容摘要
                        summary_parts = []
                        if objects:
                            object_names = [obj if isinstance(obj, str) else obj.get("name", "") for obj in objects[:3]]
                            summary_parts.append(f"物体: {', '.join(object_names)}")
                        if scenes:
                            scene_names = [scene if isinstance(scene, str) else scene.get("name", "") for scene in scenes[:2]]
                            summary_parts.append(f"场景: {', '.join(scene_names)}")
                        if emotions:
                            emotion_names = [emotion if isinstance(emotion, str) else emotion.get("name", "") for emotion in emotions[:2]]
                            summary_parts.append(f"情绪: {', '.join(emotion_names)}")
                        if brands:
                            brand_names = [brand if isinstance(brand, str) else brand.get("name", "") for brand in brands[:2]]
                            summary_parts.append(f"品牌: {', '.join(brand_names)}")
                        
                        summary = "; ".join(summary_parts) if summary_parts else "视频片段内容分析"
                        
                        segment_analysis = {
                            'file_name': segment_name,
                            'file_path': str(segment_file),
                            'file_size': segment_file.stat().st_size / (1024*1024),  # MB
                            'model': 'Qwen2.5',
                            'labels': labels,
                            'summary': summary,
                            'emotions': [str(e) for e in emotions] if emotions else [],
                            'quality_score': 0.9  # Qwen分析默认质量分
                        }
                        
                        segment_results.append(segment_analysis)
                        
                    else:
                        error_count += 1
                        error_msg = analysis_result.get('error', '未知错误') if analysis_result else '分析失败'
                        st.warning(f"⚠️ 片段 {segment_name} 分析失败: {error_msg}")
                    
                except Exception as e:
                    error_count += 1
                    processed_count += 1
                    st.error(f"❌ 分析片段 {segment_file.name} 时出错: {str(e)}")
                    continue
                
                # 更新进度和指标
                progress = current_index / len(segment_files)
                progress_bar.progress(progress)
                
                # 更新指标显示
                with metrics_cols[1]:
                    processed_metric.metric("已处理", processed_count)
                with metrics_cols[2]:
                    success_metric.metric("成功", success_count)
                with metrics_cols[3]:
                    error_metric.metric("失败", error_count)
                
                # API限流控制 - 在每个片段分析后添加延时
                if current_index < len(segment_files):  # 不是最后一个片段
                    delay_time = 0.5 if batch_size <= 2 else 1.0  # 根据批处理大小调整延时
                    status_text.text(f"⏳ API限流控制，等待 {delay_time} 秒...")
                    time.sleep(delay_time)
            
            # 批次间延时 - 在每个批次后添加稍长的延时
            if i + batch_size < len(segment_files):  # 不是最后一个批次
                batch_delay = 1.0 if batch_size <= 2 else 2.0
                status_text.text(f"📦 批次 {batch_num} 完成，等待 {batch_delay} 秒后处理下一批...")
                time.sleep(batch_delay)
        
        # 显示分析结果
        progress_bar.progress(1.0)
        status_text.text(f"✅ Qwen模型分析完成！成功分析 {success_count}/{len(segment_files)} 个片段")
        
        if segment_results:
            display_qwen_analysis_results(segment_results, video_id)
        else:
            st.error("❌ 没有成功分析的片段")
            
    except ImportError:
        st.error("❌ 无法导入Qwen分析器，请检查模块是否正确安装")
        st.info("请确保已安装DashScope相关依赖")
    except Exception as e:
        st.error(f"❌ Qwen分析过程中出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")

def analyze_segments_with_google_cloud(segment_files, video_id, use_batch_api=False, cleanup_files=True):
    """使用Google Cloud Video Intelligence分析视频片段（优化版批处理）"""
    st.markdown("### ☁️ Google Cloud Video Intelligence 片段分析")
    
    try:
        from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer
        
        # 创建分析器
        analyzer = GoogleVideoAnalyzer()
        
        # 检查凭据是否有效
        has_credentials, cred_path = analyzer.check_credentials()
        if not has_credentials:
            st.error("❌ Google Cloud 凭据未设置或无效")
            st.info("请在设置页面配置Google Cloud凭据")
            return
        
        if use_batch_api:
            # 使用原生批处理API
            st.info(f"🚀 使用原生批处理API分析 {len(segment_files)} 个片段")
            st.success(f"📦 视频将上传到 `ai-video-master` 存储桶的 `video-analysis/` 文件夹中")
            
            # 转换为路径列表
            video_paths = [str(segment_file) for segment_file in segment_files]
            
            # 创建进度条和状态显示
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 批处理分析
            def progress_callback(progress, message):
                progress_bar.progress(progress / 100.0)
                status_text.text(message)
            
            batch_result = analyzer.analyze_videos_batch(
                video_paths=video_paths,
                features=["label_detection"],
                progress_callback=progress_callback,
                cleanup_cloud_files=cleanup_files
            )
            
            if batch_result.get("success"):
                st.success(f"✅ 批处理分析完成！成功分析 {batch_result['total_videos']} 个视频")
                
                # 显示批处理统计信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总片段", batch_result['total_videos'])
                with col2:
                    st.metric("成功上传", batch_result['successful_uploads'])
                with col3:
                    st.metric("批处理ID", batch_result.get('batch_operation_name', 'N/A')[:8] + "...")
                with col4:
                    st.metric("存储桶", batch_result.get('bucket_name', 'N/A')[:15] + "...")
                
                # 显示个别结果
                individual_results = batch_result.get('individual_results', [])
                display_google_cloud_batch_results(individual_results, video_id)
                
                # 保存结果
                if st.button("💾 保存批处理分析结果"):
                    save_google_cloud_batch_results(batch_result, video_id)
                    st.success("✅ 批处理结果已保存")
            else:
                st.error(f"❌ 批处理分析失败: {batch_result.get('error', '未知错误')}")
        
        else:
            # 使用原有的顺序处理方式
            st.info(f"🔄 使用顺序处理方式分析 {len(segment_files)} 个片段")
            
            # 使用标签检测
            features = ["label_detection"]
            
            # 创建进度条和状态显示
            progress_bar = st.progress(0)
            status_text = st.empty()
            metrics_cols = st.columns(4)
            
            with metrics_cols[0]:
                total_metric = st.metric("总片段", len(segment_files))
            with metrics_cols[1]:
                processed_metric = st.metric("已处理", 0)
            with metrics_cols[2]:
                success_metric = st.metric("成功", 0)
            with metrics_cols[3]:
                error_metric = st.metric("失败", 0)
            
            segment_results = []
            processed_count = 0
            success_count = 0
            error_count = 0
            
            # 优化的顺序处理 - Google Cloud API通常有较好的内置优化
            for i, segment_file in enumerate(segment_files):
                try:
                    segment_name = segment_file.name
                    status_text.text(f"🔍 正在分析片段 {i+1}/{len(segment_files)}: {segment_name}")
                    
                    # Google Cloud分析通常比较稳定，重试次数可以少一些
                    max_retries = 2  # 增加重试次数从1到2
                    analysis_result = None
                    last_error = None
                    
                    for retry in range(max_retries + 1):
                        try:
                            # 分析单个切片
                            def progress_callback(progress, message):
                                overall_progress = (i + progress/100) / len(segment_files)
                                progress_bar.progress(overall_progress)
                                status_text.text(f"片段 {i+1}/{len(segment_files)}: {message}")
                            
                            result = analyzer.analyze_video(
                                video_path=str(segment_file),
                                features=features,
                                progress_callback=progress_callback
                            )
                            
                            if result.get("success"):
                                analysis_result = result
                                break  # 成功则退出重试循环
                            else:
                                last_error = result.get('error', '未知错误')
                                if retry < max_retries:
                                    status_text.text(f"⚠️ 片段 {segment_name} 分析失败，正在重试 ({retry + 1}/{max_retries})...")
                                    time.sleep(3)  # 增加重试等待时间到3秒
                                    
                        except Exception as e:
                            last_error = str(e)
                            if retry < max_retries:
                                status_text.text(f"⚠️ 片段 {segment_name} 分析异常，正在重试 ({retry + 1}/{max_retries}): {str(e)}")
                                time.sleep(3)  # 增加重试等待时间到3秒
                            else:
                                break  # 最后一次重试失败就退出
                    
                    processed_count += 1
                    
                    if analysis_result and analysis_result.get("success"):
                        success_count += 1
                        annotation = analysis_result["result"].annotation_results[0]
                        
                        # 提取分析结果（仅标签）
                        segment_analysis = {
                            'file_name': segment_name,
                            'file_path': str(segment_file),
                            'file_size': segment_file.stat().st_size / (1024*1024),  # MB
                            'model': 'Google Cloud Video Intelligence',
                            'labels': [],
                            'summary': '',
                            'quality_score': 0.95  # Google Cloud 默认质量分
                        }
                        
                        # 提取标签
                        labels = []
                        if hasattr(annotation, 'segment_label_annotations') and annotation.segment_label_annotations:
                            for label in annotation.segment_label_annotations[:10]:  # 前10个标签
                                label_name = label.entity.description
                                confidence = 0.0
                                
                                if label.segments:
                                    confidence = label.segments[0].confidence
                                
                                labels.append({
                                    'name': label_name,
                                    'confidence': confidence
                                })
                        
                        segment_analysis['labels'] = labels
                        
                        # 生成简单摘要
                        if labels:
                            top_labels = [label['name'] for label in labels[:3]]
                            segment_analysis['summary'] = f"主要内容: {', '.join(top_labels)}"
                        else:
                            segment_analysis['summary'] = "未检测到明显内容"
                        
                        segment_results.append(segment_analysis)
                        
                        # 实时显示结果
                        with st.expander(f"📄 {segment_name} - 分析完成", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**文件大小**: {segment_analysis['file_size']:.1f} MB")
                                st.write(f"**质量分**: {segment_analysis['quality_score']:.2f}")
                            with col2:
                                st.write(f"**检测标签**: {len(labels)} 个")
                                if labels:
                                    st.write(f"**主要标签**: {labels[0]['name']} ({labels[0]['confidence']:.2f})")
                            
                            if labels:
                                st.write("**所有标签**:")
                                for label in labels[:5]:  # 显示前5个
                                    confidence_color = "🟢" if label['confidence'] > 0.8 else "🟡" if label['confidence'] > 0.5 else "🔴"
                                    st.write(f"  {confidence_color} {label['name']}: {label['confidence']:.2f}")
                    
                    else:
                        error_count += 1
                        # 显示更详细的错误信息
                        if last_error:
                            st.warning(f"⚠️ 片段 {segment_name} 分析失败: {last_error}")
                        else:
                            st.warning(f"⚠️ 片段 {segment_name} 分析失败: 未知错误")
                    
                    # 更新指标
                    processed_metric.metric("已处理", processed_count)
                    success_metric.metric("成功", success_count)
                    error_metric.metric("失败", error_count)
                    
                    # 适当延迟，避免API限流
                    time.sleep(1)  # 增加延迟到1秒
                    
                except Exception as e:
                    error_count += 1
                    processed_count += 1
                    st.error(f"❌ 处理片段 {segment_file.name} 时发生错误: {str(e)}")
                    continue
            
            # 显示最终结果
            if segment_results:
                st.success(f"✅ 顺序分析完成！成功分析 {len(segment_results)} 个片段")
                display_google_cloud_analysis_results(segment_results, video_id)
                
                # 保存结果
                if st.button("💾 保存分析结果"):
                    save_google_cloud_analysis_results(segment_results, video_id)
                    st.success("✅ 分析结果已保存")
            else:
                st.warning("⚠️ 没有成功分析任何片段")
    
    except Exception as e:
        st.error(f"❌ Google Cloud 片段分析失败: {str(e)}")
        logger.error(f"Google Cloud 片段分析失败: {str(e)}")

def display_google_cloud_batch_results(individual_results, video_id):
    """显示分析结果"""
    if not individual_results:
        st.warning("没有分析结果可显示")
        return
    st.markdown("### 分析结果")
    st.info("功能正在维护中")

def save_google_cloud_batch_results(batch_result, video_id):
    """保存Google Cloud批处理分析结果到JSON文件"""
    try:
        from datetime import datetime
        
        # 创建保存目录
        root_dir = Path(__file__).parent.parent.parent
        results_dir = root_dir / "data" / "output" / "google_video" / str(video_id)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备结果数据
        analysis_data = {
            'video_id': video_id,
            'analysis_type': 'Google Cloud Video Intelligence (Batch)',
            'analysis_time': datetime.now().isoformat(),
            'batch_info': {
                'total_videos': batch_result.get('total_videos', 0),
                'successful_uploads': batch_result.get('successful_uploads', 0),
                'batch_operation_name': batch_result.get('batch_operation_name'),
                'bucket_name': batch_result.get('bucket_name'),
                'features': batch_result.get('features', [])
            },
            'individual_results': batch_result.get('individual_results', []),
            'upload_info': batch_result.get('upload_info', [])
        }
        
        # 保存到文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = results_dir / f"google_cloud_batch_analysis_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        st.info(f"📁 批处理结果已保存到: {result_file}")
        
    except Exception as e:
        st.error(f"保存批处理结果失败: {str(e)}")
        logger.error(f"保存批处理结果失败: {str(e)}")

def analyze_segments_comparison(segment_files, video_id, batch_size=2):
    """对比分析：同时使用Google Cloud和Qwen模型"""
    st.markdown("### 🆚 对比分析")
    st.info("将同时使用Google Cloud和Qwen模型分析相同的视频片段，以便对比两种模型的分析结果")
    
    # 先运行Google Cloud分析
    st.markdown("#### 第一步：Google Cloud Video Intelligence 分析")
    analyze_segments_with_google_cloud(segment_files, video_id)
    
    st.markdown("---")
    
    # 再运行Qwen分析
    st.markdown("#### 第二步：Qwen视觉模型分析")
    analyze_segments_with_qwen(segment_files, video_id, batch_size)
    
    st.markdown("---")
    st.success("🎉 对比分析完成！您可以查看上方两个模型的分析结果进行对比。")

def display_qwen_analysis_results(segment_results, video_id):
    """显示Qwen分析结果 - 简化版：只自动保存文件"""
    if not segment_results:
        st.warning("没有分析结果可显示")
        return
    
    st.markdown("### ✅ Qwen模型分析完成")
    
    # 显示简单统计
    total_segments = len(segment_results)
    total_labels = sum(len(s['labels']) for s in segment_results)
    
    st.success(f"🎉 成功分析 {total_segments} 个视频片段，识别出 {total_labels} 个标签")
    
    # 自动保存JSON文件
    json_file = save_qwen_analysis_results(segment_results, video_id)
    
    # 自动保存CSV文件
    csv_file = export_qwen_results_to_csv(segment_results, video_id)
    
    # 显示保存路径
    st.markdown("#### 💾 文件已自动保存")
    if json_file:
        st.info(f"📄 **JSON详细数据**: `{json_file}`")
    if csv_file:
        st.info(f"📊 **CSV表格数据**: `{csv_file}`")
    
    # 快速访问按钮
    if st.button("📂 打开保存文件夹", key="open_results_folder_simple"):
        import subprocess
        from pathlib import Path
        try:
            root_dir = Path(__file__).parent.parent.parent
            results_dir = root_dir / "data" / "output" / "google_video" / str(video_id)
            subprocess.run(["open", str(results_dir)], check=False)
            st.success("✅ 已打开文件夹")
        except Exception as e:
            st.error(f"❌ 打开文件夹失败: {e}")

def export_qwen_results_to_csv(segment_results, video_id):
    """导出Qwen分析结果为CSV文件 - 返回文件路径"""
    try:
        import pandas as pd
        from datetime import datetime
        from pathlib import Path
        
        # 准备CSV数据
        csv_data = []
        for result in segment_results:
            # 为每个标签创建一行
            for label in result['labels']:
                csv_data.append({
                    'video_id': video_id,
                    'segment_file': result['file_name'],
                    'file_size_mb': result['file_size'],
                    'label_name': label['name'],
                    'label_type': label.get('type', '未知'),
                    'confidence': label['confidence'],
                    'model': result['model'],
                    'quality_score': result.get('quality_score', 0.9),
                    'summary': result.get('summary', ''),
                    'analysis_time': datetime.now().isoformat()
                })
        
        if csv_data:
            df = pd.DataFrame(csv_data)
            
            # 保存到CSV
            root_dir = Path(__file__).parent.parent.parent
            results_dir = root_dir / "data" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_file = results_dir / f"qwen_analysis_{video_id}_{timestamp}.csv"
            
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')  # utf-8-sig for Excel compatibility
            
            return str(csv_file)
        
        return None
        
    except Exception as e:
        st.error(f"❌ 导出CSV失败: {str(e)}")
        return None

def save_qwen_analysis_results(segment_results, video_id):
    """保存Qwen分析结果到JSON文件 - 返回文件路径"""
    try:
        import json
        from pathlib import Path
        from datetime import datetime
        
        # 创建保存目录
        root_dir = Path(__file__).parent.parent.parent
        results_dir = root_dir / "data" / "output" / "google_video" / str(video_id)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备结果数据
        analysis_data = {
            'video_id': video_id,
            'analysis_time': datetime.now().isoformat(),
            'model': 'Qwen',
            'total_segments': len(segment_results),
            'segments': segment_results
        }
        
        # 保存到文件
        result_file = results_dir / f"qwen_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        return str(result_file)
        
    except Exception as e:
        st.error(f"❌ 保存Qwen分析结果时出错: {str(e)}")
        return None

def display_google_cloud_analysis_results(segment_results, video_id):
    """显示分析结果"""
    if not individual_results:
        st.warning("没有分析结果可显示")
        return
    st.markdown("### 分析结果")
    st.info("功能正在维护中")

def save_google_cloud_analysis_results(segment_results, video_id):
    """保存Google Cloud分析结果到JSON文件"""
    try:
        from datetime import datetime
        
        # 创建保存目录
        root_dir = Path(__file__).parent.parent.parent
        results_dir = root_dir / "data" / "output" / "google_video" / str(video_id)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # 准备结果数据
        analysis_data = {
            'video_id': video_id,
            'analysis_type': 'Google Cloud Video Intelligence',
            'analysis_time': datetime.now().isoformat(),
            'total_segments': len(segment_results),
            'segments': segment_results
        }
        
        # 保存到文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = results_dir / f"google_cloud_analysis_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        st.success(f"✅ Google Cloud分析结果已保存到: {result_file}")
        
    except Exception as e:
        st.error(f"❌ 保存Google Cloud分析结果时出错: {str(e)}")

def scene_clustering_interface():
    """场景聚合界面，用于对已切分的视频片段进行聚合"""
    st.markdown("### 📁 选择视频片段目录")
    
    # 扫描可用的视频ID目录
    from pathlib import Path
    root_dir = Path(__file__).parent.parent.parent
    base_output_dir = root_dir / "data" / "output" / "google_video"
    
    if not base_output_dir.exists():
        st.warning("❌ 未找到视频片段目录")
        st.info("请先在 '🎬 视频分析与切分' 标签页中完成视频切分")
        return
    
    # 获取所有视频ID目录
    video_dirs = [d for d in base_output_dir.iterdir() if d.is_dir()]
    
    if not video_dirs:
        st.warning("❌ 未找到任何视频片段")
        st.info("请先在 '🎬 视频分析与切分' 标签页中完成视频切分")
        return
    
    # 选择视频ID
    video_ids = [d.name for d in video_dirs]
    selected_video_id = st.selectbox(
        "选择要聚合的视频ID：",
        video_ids,
        help="这些是已经切分过的视频项目",
        key="scene_clustering_video_id"
    )
    
    if selected_video_id:
        segments_dir = base_output_dir / selected_video_id
        
        # 获取片段文件
        segment_files = list(segments_dir.glob("*.mp4"))
        segment_files.sort()
        
        if not segment_files:
            st.warning(f"❌ 在目录 {segments_dir} 中未找到视频片段")
            return
        
        st.success(f"✅ 找到 {len(segment_files)} 个视频片段")
        
        # 显示片段信息
        with st.expander("📋 片段列表", expanded=False):
            for i, segment_file in enumerate(segment_files[:10]):  # 只显示前10个
                file_size = segment_file.stat().st_size / (1024*1024)
                st.write(f"{i+1}. {segment_file.name} ({file_size:.1f} MB)")
            
            if len(segment_files) > 10:
                st.write(f"... 还有 {len(segment_files) - 10} 个片段")
        
        # 分析片段特征，给出聚合建议
        analyze_segment_fragmentation(segment_files, selected_video_id)
        
        # 聚合参数设置
        st.markdown("### ⚙️ 聚合参数设置")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            similarity_threshold = st.slider(
                "相似度阈值",
                min_value=0.5,
                max_value=0.9,
                value=0.75,
                step=0.05,
                help="越高越严格，只合并非常相似的片段",
                key="scene_clustering_similarity"
            )
        
        with col2:
            min_scene_duration = st.slider(
                "最小场景时长（秒）",
                min_value=2.0,
                max_value=10.0,
                value=3.0,
                step=0.5,
                help="聚合后每个场景的最小持续时间",
                key="scene_clustering_min_duration"
            )
        
        with col3:
            max_scenes = st.selectbox(
                "最大场景数",
                options=[None, 3, 5, 8, 10, 15],
                index=0,
                help="限制最多生成多少个场景（None为自动）",
                key="scene_clustering_max_scenes"
            )
        
        # 开始聚合按钮
        if st.button("🧠 开始场景聚合", type="primary", key="start_scene_clustering"):
            perform_scene_clustering(segment_files, selected_video_id, similarity_threshold, min_scene_duration, max_scenes)

def analyze_segment_fragmentation(segment_files, video_id):
    """分析片段碎片化程度，给出聚合建议"""
    st.markdown("### 📊 片段碎片化分析")
    
    try:
        # 获取片段时长信息
        durations = []
        total_size = 0
        
        for segment_file in segment_files:
            try:
                # 简单估算：文件大小(MB) / 2 ≈ 时长(秒)
                file_size_mb = segment_file.stat().st_size / (1024*1024)
                estimated_duration = file_size_mb / 2  # 粗略估算
                durations.append(estimated_duration)
                total_size += file_size_mb
            except:
                durations.append(2.0)  # 默认值
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            short_segments = len([d for d in durations if d < 3.0])
            fragmentation_ratio = short_segments / len(durations) * 100
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("片段总数", len(segment_files))
            with col2:
                st.metric("平均时长", f"{avg_duration:.1f}s")
            with col3:
                st.metric("短片段数", f"{short_segments}")
            with col4:
                st.metric("碎片化率", f"{fragmentation_ratio:.1f}%")
            
            # 给出聚合建议
            if fragmentation_ratio > 50:
                st.warning(f"⚠️ 碎片化程度高 ({fragmentation_ratio:.1f}%)")
                st.info(f"💡 强烈建议进行场景聚合，可以将 {len(segment_files)} 个片段合并为更少的有意义场景")
            elif fragmentation_ratio > 30:
                st.info(f"📊 中等碎片化程度 ({fragmentation_ratio:.1f}%)")
                st.info("💡 可以考虑进行场景聚合来优化片段结构")
            else:
                st.success(f"✅ 片段长度分布良好 ({fragmentation_ratio:.1f}%)")
                st.info("💡 可以选择性进行聚合，或保持当前片段结构")
            
            # 预估聚合效果
            estimated_scenes = max(3, int(len(segment_files) * 0.3))  # 估算聚合后场景数
            st.info(f"🎯 预估聚合效果: {len(segment_files)} 个片段 → 约 {estimated_scenes} 个场景")
            
    except Exception as e:
        st.error(f"❌ 分析片段信息时出错: {str(e)}")

def perform_scene_clustering(segment_files, video_id, similarity_threshold, min_scene_duration, max_scenes):
    """执行场景聚合"""
    try:
        st.markdown("### 🧠 执行场景聚合")
        
        # 导入聚类模块
        from streamlit_app.modules.video_clustering import cluster_video_segments
        
        with st.spinner("🔍 正在分析视频片段并执行聚合..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_callback(progress, message):
                progress_bar.progress(progress / 100.0)
                status_text.text(message)
            
            # 执行聚合
            clustered_scenes = cluster_video_segments(
                segment_files=segment_files,
                video_id=video_id,
                similarity_threshold=similarity_threshold,
                min_scene_duration=min_scene_duration,
                max_scenes=max_scenes,
                progress_callback=progress_callback
            )
            
            progress_bar.progress(1.0)
            status_text.text("✅ 场景聚合完成！")
            
            if clustered_scenes:
                st.success(f"✅ 聚合完成！{len(segment_files)} 个片段 → {len(clustered_scenes)} 个场景")
                
                # 显示聚合结果
                display_clustering_results(clustered_scenes, video_id, len(segment_files))
                
                # 自动生成聚合场景视频
                auto_generate_clustered_scene_videos(clustered_scenes, video_id, segment_files)
            else:
                st.error("❌ 场景聚合失败")
                
    except ImportError as e:
        st.error("❌ 场景聚合功能不可用，缺少必要依赖")
        st.info("请安装：pip install scikit-learn opencv-python")
    except Exception as e:
        st.error(f"❌ 场景聚合失败: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")

def display_clustering_results(clustered_scenes, video_id, original_segment_count):
    """显示聚合结果"""
    st.markdown("#### 📊 聚合结果详情")
    
    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        reduction_ratio = (original_segment_count - len(clustered_scenes)) / original_segment_count * 100
        st.metric("片段减少", f"{reduction_ratio:.1f}%")
    with col2:
        avg_scene_duration = sum(s['duration'] for s in clustered_scenes) / len(clustered_scenes)
        st.metric("平均场景时长", f"{avg_scene_duration:.1f}s")
    with col3:
        total_segments_in_scenes = sum(s['segment_count'] for s in clustered_scenes)
        st.metric("包含片段数", total_segments_in_scenes)
    with col4:
        longest_scene = max(s['duration'] for s in clustered_scenes)
        st.metric("最长场景", f"{longest_scene:.1f}s")
    
    # 详细场景列表
    st.markdown("#### 🎭 聚合后的场景列表")
    
    scenes_data = []
    for scene in clustered_scenes:
        scenes_data.append({
            "场景": f"场景 {scene['index']}",
            "时长": f"{scene['duration']:.1f}s",
            "包含片段": scene['segment_count'],
            "片段列表": ', '.join([f"片段{i+1}" for i in range(scene['segment_count'])]),
            "质量评分": f"{scene.get('quality_score', 0.8):.2f}"
        })
    
    if scenes_data:
        import pandas as pd
        df_scenes = pd.DataFrame(scenes_data)
        st.dataframe(
            df_scenes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "场景": st.column_config.TextColumn("场景", width="small"),
                "时长": st.column_config.TextColumn("时长", width="small"),
                "包含片段": st.column_config.NumberColumn("包含片段", width="small"),
                "片段列表": st.column_config.TextColumn("片段列表", width="large"),
                "质量评分": st.column_config.TextColumn("质量评分", width="small")
            }
        )

def auto_generate_clustered_scene_videos(clustered_scenes, video_id, segment_files):
    """自动生成聚合场景视频并替换原始切片"""
    st.markdown("#### 🎬 自动生成聚合场景视频")
    
    try:
        # 准备输出目录
        from pathlib import Path
        import shutil
        import os
        
        root_dir = Path(__file__).parent.parent.parent
        
        # 临时聚类输出目录
        temp_output_dir = root_dir / "data" / "results" / f"{video_id}_clustered_scenes"
        temp_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 原始切分目录
        original_dir = root_dir / "data" / "output" / "google_video" / str(video_id)
        
        created_videos = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 创建片段文件映射（按文件名索引）
        segment_file_map = {f.stem: f for f in segment_files}
        
        status_text.text("🔄 第一步：生成聚类场景视频...")
        
        for i, scene in enumerate(clustered_scenes):
            try:
                status_text.text(f"正在生成场景 {scene['index']}: {len(scene['segments'])} 个片段...")
                
                # 收集场景中的所有片段文件
                scene_segment_files = []
                for segment in scene['segments']:
                    # 从segment中获取文件路径
                    if 'file_path' in segment:
                        segment_file = Path(segment['file_path'])
                        if segment_file.exists():
                            scene_segment_files.append(segment_file)
                    elif 'file_name' in segment:
                        # 尝试从文件名匹配
                        file_stem = Path(segment['file_name']).stem
                        if file_stem in segment_file_map:
                            scene_segment_files.append(segment_file_map[file_stem])
                
                if not scene_segment_files:
                    st.warning(f"⚠️ 场景 {scene['index']} 没有找到对应的片段文件")
                    continue
                
                # 生成场景视频文件名
                scene_filename = f"scene_{scene['index']:02d}_{len(scene_segment_files)}segments.mp4"
                scene_output_path = temp_output_dir / scene_filename
                
                # 执行视频合并
                if len(scene_segment_files) == 1:
                    # 单个片段，直接复制
                    shutil.copy2(scene_segment_files[0], scene_output_path)
                    st.info(f"📋 场景 {scene['index']}: 单片段直接复制")
                else:
                    # 多个片段，使用FFmpeg合并
                    success = merge_video_segments(scene_segment_files, scene_output_path)
                    if not success:
                        st.warning(f"⚠️ 场景 {scene['index']} 视频合并失败")
                        continue
                    st.info(f"🔗 场景 {scene['index']}: {len(scene_segment_files)} 个片段已合并")
                
                # 记录创建的视频信息
                scene_info = {
                    'scene_index': scene['index'],
                    'duration': scene['duration'],
                    'segment_count': len(scene_segment_files),
                    'output_path': str(scene_output_path),
                    'filename': scene_filename,
                    'file_size_mb': scene_output_path.stat().st_size / (1024*1024) if scene_output_path.exists() else 0
                }
                created_videos.append(scene_info)
                
                progress = (i + 1) / len(clustered_scenes) * 0.7  # 70%进度用于生成视频
                progress_bar.progress(progress)
                
            except Exception as e:
                st.warning(f"⚠️ 场景 {scene['index']} 视频生成失败: {str(e)}")
                continue
        
        if not created_videos:
            st.error("❌ 没有成功生成任何场景视频")
            return
        
        # 第二步：替换原始文件
        status_text.text("🔄 第二步：备份并替换原始切片文件...")
        progress_bar.progress(0.7)
        
        try:
            # 创建备份目录
            backup_dir = original_dir.parent / f"{video_id}_backup_{int(time.time())}"
            backup_dir.mkdir(exist_ok=True)
            
            # 备份原始文件
            original_files = list(original_dir.glob("*.mp4"))
            st.info(f"📦 备份 {len(original_files)} 个原始文件到: {backup_dir.name}")
            
            for file in original_files:
                shutil.copy2(file, backup_dir / file.name)
            
            progress_bar.progress(0.8)
            
            # 删除原始目录中的mp4文件
            status_text.text("🗑️ 清理原始文件...")
            for file in original_files:
                file.unlink()
            
            progress_bar.progress(0.85)
            
            # 移动聚类后的文件到原始目录
            status_text.text("📁 移动聚类文件到原始目录...")
            moved_count = 0
            
            for video_info in created_videos:
                source_file = Path(video_info['output_path'])
                target_file = original_dir / video_info['filename']
                
                if source_file.exists():
                    shutil.move(str(source_file), str(target_file))
                    moved_count += 1
            
            progress_bar.progress(0.95)
            
            # 清理临时目录
            status_text.text("🧹 清理临时文件...")
            if temp_output_dir.exists():
                shutil.rmtree(temp_output_dir)
            
            progress_bar.progress(1.0)
            status_text.text("✅ 场景聚合和文件替换完成！")
            
            # 显示完成信息
            st.success(f"🎉 场景聚合完成！原始 {len(original_files)} 个片段已被 {moved_count} 个聚类场景替换")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                reduction_ratio = (len(original_files) - moved_count) / len(original_files) * 100
                st.metric("片段减少", f"{reduction_ratio:.1f}%")
            with col2:
                total_size = sum(v['file_size_mb'] for v in created_videos)
                st.metric("新片段总大小", f"{total_size:.1f} MB")
            with col3:
                avg_duration = sum(v['duration'] for v in created_videos) / len(created_videos)
                st.metric("平均场景时长", f"{avg_duration:.1f}s")
            with col4:
                st.metric("备份文件夹", backup_dir.name[:15] + "...")
            
            # 显示文件变化详情
            with st.expander("📋 文件替换详情", expanded=True):
                st.write(f"**📁 目标目录**: `{original_dir}`")
                st.write(f"**🗂️ 备份目录**: `{backup_dir}`")
                st.write(f"**📦 原始文件**: {len(original_files)} 个")
                st.write(f"**🎬 新场景文件**: {moved_count} 个")
                
                st.markdown("**🎭 新的场景文件列表:**")
                for video_info in created_videos:
                    st.write(f"- `{video_info['filename']}` ({video_info['file_size_mb']:.1f} MB, {video_info['duration']:.1f}s)")
            
            # 快速访问按钮
            if st.button("📂 打开更新后的文件夹", type="secondary", key="open_updated_folder"):
                import subprocess
                try:
                    subprocess.run(["open", str(original_dir)], check=False)
                    st.success("✅ 已打开更新后的文件夹")
                except Exception as e:
                    st.error(f"❌ 打开文件夹失败: {e}")
                    st.info(f"📁 文件夹路径: {original_dir}")
            
        except Exception as e:
            st.error(f"❌ 文件替换过程中出错: {str(e)}")
            st.warning("⚠️ 聚类视频已生成，但文件替换失败。请手动处理。")
            st.info(f"📁 聚类文件位置: {temp_output_dir}")
    
    except Exception as e:
        st.error(f"❌ 生成聚合场景视频时出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")

def merge_video_segments(segment_files, output_path):
    """使用FFmpeg合并多个视频片段"""
    try:
        import subprocess
        import tempfile
        
        # 创建临时文件列表
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for segment_file in segment_files:
                f.write(f"file '{segment_file.absolute()}'\n")
            temp_list_file = f.name
        
        # 使用FFmpeg合并
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', temp_list_file,
            '-c', 'copy',
            '-y',  # 覆盖输出文件
            str(output_path)
        ]
        
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60秒超时
        )
        
        # 清理临时文件
        import os
        os.unlink(temp_list_file)
        
        if result.returncode == 0:
            return True
        else:
            logger.error(f"FFmpeg合并失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        st.warning("⚠️ 视频合并超时")
        return False
    except FileNotFoundError:
        st.warning("⚠️ 未找到FFmpeg，请安装FFmpeg")
        return False
    except Exception as e:
        logger.error(f"视频合并失败: {str(e)}")
        return False

if __name__ == "__main__":
    main() 