"""
Google Cloud Video Intelligence API 测试页面

用于测试 Google Cloud Video Intelligence API 的功能，包括：
- 镜头切分检测
- 视觉标签检测
- 文本检测
- 人脸检测等
"""

import streamlit as st
import os
import tempfile
import json
from pathlib import Path
import time

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
    page_title="Google Cloud 视频智能测试",
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
                text_detection = st.checkbox("文本检测", help="检测视频中的文字内容")
                
            with col2:
                face_detection = st.checkbox("人脸检测", help="检测视频中的人脸")
                object_tracking = st.checkbox("物体跟踪", help="跟踪视频中的特定物体")
            
            # 开始分析按钮
            if st.button("🚀 开始分析", type="primary"):
                if not any([shot_detection, label_detection, text_detection, face_detection, object_tracking]):
                    st.warning("请至少选择一个分析功能！")
                    return
                
                try:
                    # 准备分析参数
                    features = []
                    if shot_detection:
                        features.append("shot_detection")
                    if label_detection:
                        features.append("label_detection")
                    if text_detection:
                        features.append("text_detection")
                    if face_detection:
                        features.append("face_detection")
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
                            'text_detection': text_detection,
                            'face_detection': face_detection,
                            'object_tracking': object_tracking,
                            'use_deepseek_translation': use_deepseek_translation
                        }
                        
                        # 显示结果
                        display_results(result, shot_detection, label_detection, text_detection, face_detection, object_tracking, use_deepseek_translation, current_video_path, current_video_id)
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





def create_video_segments(video_path, segments_data, video_id):
    """
    根据分析结果创建视频片段
    
    Args:
        video_path: 原始视频路径
        segments_data: 片段数据列表
        video_id: 视频ID
    
    Returns:
        成功创建的片段列表
    """
    try:
        # 调试信息
        st.info(f"🔍 调试信息:")
        st.write(f"- 视频路径: {video_path}")
        st.write(f"- 视频ID: {video_id}")
        st.write(f"- 片段数量: {len(segments_data)}")
        st.write(f"- 视频文件存在: {os.path.exists(video_path) if video_path else 'N/A'}")
        
        if not video_path:
            st.error("❌ 视频路径为空，无法进行切分")
            return []
        
        if not os.path.exists(video_path):
            st.error(f"❌ 视频文件不存在: {video_path}")
            return []
            
        # 创建输出目录
        from pathlib import Path
        root_dir = Path(__file__).parent.parent.parent
        output_dir = root_dir / "data" / "output" / "google_video"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 导入视频处理器
        import sys
        sys.path.append(str(root_dir))
        from src.core.utils.video_processor import VideoProcessor
        
        processor = VideoProcessor()
        created_segments = []
        
        # 显示进度条
        st.info("🎬 正在切分视频片段...")
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
                        'file_size': os.path.getsize(extracted_path) / (1024*1024)  # MB
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
        st.success(f"✅ 视频切分完成：成功创建 {len(created_segments)} 个视频片段")
        
        return created_segments
        
    except Exception as e:
        st.error(f"创建视频片段时出错: {str(e)}")
        return []

def display_results(result, shot_detection, label_detection, text_detection, face_detection, object_tracking, use_deepseek_translation=False, video_path=None, video_id=None):
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
        
        # 准备表格数据
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
            
                        # 添加视频切分功能
            if video_path and video_id and segments_for_cutting:
                st.markdown("### 🎬 视频片段切分")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info(f"将根据 {len(segments_for_cutting)} 个镜头切分视频片段")
                with col2:
                    if st.button("🔪 开始切分", type="primary"):
                        with st.spinner("正在切分视频片段..."):
                            created_segments = create_video_segments(
                                video_path, segments_for_cutting, video_id
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
                                                subprocess.run(["open", "-R", segment['file_path']], check=False)
                            else:
                                st.error("❌ 视频片段创建失败")
    
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
                                    created_segments = create_video_segments(video_path, label_segments, video_id)
                                    
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
    
    # 文本检测结果
    if text_detection and annotation.text_annotations:
        st.subheader("📝 文本检测结果")
        
        try:
            for text_annotation in annotation.text_annotations:
                st.write(f"**检测到的文本:** {text_annotation.text}")
                
                for segment in text_annotation.segments:
                    try:
                        start_time = get_time_seconds(segment.segment.start_time_offset)
                        end_time = get_time_seconds(segment.segment.end_time_offset)
                        confidence = segment.confidence
                        
                        st.write(f"  - 时间段: {start_time:.2f}s - {end_time:.2f}s, 置信度: {confidence:.2f}")
                    except Exception as e:
                        st.write(f"  - 时间段解析错误: {e}")
        except Exception as e:
            st.error(f"文本检测结果显示错误: {e}")
    
    # 人脸检测结果
    if face_detection and annotation.face_annotations:
        st.subheader("👤 人脸检测结果")
        
        # 使用分析器提取人脸信息
        mock_result = {"success": True, "result": result}
        faces = google_analyzer.extract_faces(mock_result)
        
        st.info(f"检测到 {len(annotation.face_annotations)} 个人脸轨迹")
        
        face_segments = []  # 用于视频切分的人脸片段数据
        
        try:
            # 按人脸ID分组显示
            face_groups = {}
            for face in faces:
                face_id = face['face_id']
                if face_id not in face_groups:
                    face_groups[face_id] = []
                face_groups[face_id].append(face)
            
            for face_id, segments in list(face_groups.items())[:5]:  # 显示前5个人脸
                st.write(f"**人脸 {face_id}:**")
                
                for face in segments:
                    start_time = face['start_time']
                    end_time = face['end_time']
                    
                    st.write(f"  - 出现时间: {start_time:.2f}s - {end_time:.2f}s")
                    
                    # 准备切分数据（只处理1秒以上的片段）
                    if face['duration'] >= 1.0:
                        face_segments.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'type': face['type'],
                            'confidence': face['confidence']
                        })
            
            # 添加人脸片段切分功能
            if video_path and video_id and face_segments:
                st.markdown("### 👤 人脸片段切分")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info(f"将根据 {len(face_segments)} 个人脸片段切分视频")
                with col2:
                    if st.button("🔪 开始切分人脸", type="secondary"):
                        with st.spinner("正在切分人脸片段..."):
                            created_segments = create_video_segments(video_path, face_segments, video_id)
                            
                            if created_segments:
                                st.success(f"✅ 成功创建 {len(created_segments)} 个人脸片段")
                                
                                # 显示创建的片段信息
                                with st.expander("📁 查看创建的人脸片段", expanded=True):
                                    for segment in created_segments:
                                        col1, col2, col3 = st.columns([2, 1, 1])
                                        with col1:
                                            st.write(f"**{segment['type']}** ({segment['duration']:.1f}秒)")
                                        with col2:
                                            st.write(f"{segment['file_size']:.1f} MB")
                                        with col3:
                                            if st.button(f"📁 打开", key=f"open_face_{segment['index']}"):
                                                import subprocess
                                                subprocess.run(["open", "-R", segment['file_path']], check=False)
                            else:
                                st.error("❌ 人脸片段创建失败")
            elif video_path and video_id and not face_segments:
                st.info("没有找到适合切分的人脸片段（需要至少1秒长度）")
                
        except Exception as e:
            st.error(f"人脸检测结果显示错误: {e}")
    

    
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
            
        # 文本检测
        if hasattr(annotation, 'text_annotations'):
            if annotation.text_annotations:
                results_summary.append(f"✅ 文本检测: {len(annotation.text_annotations)} 个文本")
            else:
                results_summary.append("❌ 文本检测: 无结果")
        else:
            results_summary.append("❌ 文本检测: 未检测")
            
        # 人脸检测
        if hasattr(annotation, 'face_annotations'):
            if annotation.face_annotations:
                results_summary.append(f"✅ 人脸检测: {len(annotation.face_annotations)} 个人脸")
            else:
                results_summary.append("❌ 人脸检测: 无结果")
        else:
            results_summary.append("❌ 人脸检测: 未检测")
            

            
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
                "has_text_annotations": hasattr(annotation, 'text_annotations'),
                "has_face_annotations": hasattr(annotation, 'face_annotations'),
                "has_object_annotations": hasattr(annotation, 'object_annotations'),
            })
    
    # 综合切分功能
    if video_path and video_id:
        st.markdown("---")
        st.subheader("🎬 综合视频切分")
        st.markdown("一次性根据所有检测结果创建视频片段")
        
        # 收集所有可切分的片段
        all_segments = []
        
        # 镜头片段
        if shot_detection and annotation.shot_annotations:
            for i, shot in enumerate(annotation.shot_annotations):
                try:
                    start_time = get_time_seconds(shot.start_time_offset)
                    end_time = get_time_seconds(shot.end_time_offset)
                    if end_time - start_time >= 0.5:
                        all_segments.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'type': f"镜头{i+1}",
                            'confidence': 1.0,
                            'category': '镜头切分'
                        })
                except:
                    continue
        
        # 标签片段
        if label_detection and annotation.segment_label_annotations:
            for label in annotation.segment_label_annotations[:5]:  # 限制前5个标签
                label_name = label.entity.description
                label_name_cn = translate_label_to_chinese(label_name, use_deepseek=use_deepseek_translation)
                
                for segment in label.segments:
                    try:
                        start_time = get_time_seconds(segment.segment.start_time_offset)
                        end_time = get_time_seconds(segment.segment.end_time_offset)
                        confidence = segment.confidence
                        
                        if end_time - start_time >= 1.0:
                            all_segments.append({
                                'start_time': start_time,
                                'end_time': end_time,
                                'type': f"标签_{label_name_cn}",
                                'confidence': confidence,
                                'category': '标签检测'
                            })
                    except:
                        continue
        
        # 人脸片段
        if face_detection and annotation.face_annotations:
            for i, face in enumerate(annotation.face_annotations[:3]):  # 限制前3个人脸
                for j, segment in enumerate(face.segments):
                    try:
                        start_time = get_time_seconds(segment.segment.start_time_offset)
                        end_time = get_time_seconds(segment.segment.end_time_offset)
                        
                        if end_time - start_time >= 1.0:
                            all_segments.append({
                                'start_time': start_time,
                                'end_time': end_time,
                                'type': f"人脸{i+1}_片段{j+1}",
                                'confidence': 1.0,
                                'category': '人脸检测'
                            })
                    except:
                        continue
        
        if all_segments:
            # 按时间排序
            all_segments.sort(key=lambda x: x['start_time'])
            
            # 显示统计信息
            col1, col2, col3, col4 = st.columns(4)
            
            shot_count = len([s for s in all_segments if s['category'] == '镜头切分'])
            label_count = len([s for s in all_segments if s['category'] == '标签检测'])
            face_count = len([s for s in all_segments if s['category'] == '人脸检测'])
            
            with col1:
                st.metric("镜头片段", shot_count)
            with col2:
                st.metric("标签片段", label_count)
            with col3:
                st.metric("人脸片段", face_count)
            with col4:
                st.metric("总片段数", len(all_segments))
            
            # 切分按钮
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"将创建 {len(all_segments)} 个视频片段，保存到 data/output/google_video/ 目录")
            with col2:
                if st.button("🚀 开始综合切分", type="primary", key="comprehensive_cut"):
                    with st.spinner("正在创建所有视频片段..."):
                        created_segments = create_video_segments(video_path, all_segments, video_id)
                        
                        if created_segments:
                            st.success(f"✅ 成功创建 {len(created_segments)} 个视频片段")
                            
                            # 按类别统计
                            category_stats = {}
                            total_size = 0
                            total_duration = 0
                            
                            for segment in created_segments:
                                category = next((s['category'] for s in all_segments if s['type'] == segment['type']), '未知')
                                if category not in category_stats:
                                    category_stats[category] = {'count': 0, 'size': 0, 'duration': 0}
                                
                                category_stats[category]['count'] += 1
                                category_stats[category]['size'] += segment['file_size']
                                category_stats[category]['duration'] += segment['duration']
                                
                                total_size += segment['file_size']
                                total_duration += segment['duration']
                            
                            # 显示统计结果
                            st.markdown("### 📊 切分结果统计")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**按类别统计:**")
                                for category, stats in category_stats.items():
                                    st.write(f"- {category}: {stats['count']} 个片段, {stats['size']:.1f} MB, {stats['duration']:.1f} 秒")
                            
                            with col2:
                                st.write("**总计:**")
                                st.write(f"- 总片段数: {len(created_segments)}")
                                st.write(f"- 总大小: {total_size:.1f} MB")
                                st.write(f"- 总时长: {total_duration:.1f} 秒")
                            
                            # 显示输出目录
                            from pathlib import Path
                            root_dir = Path(__file__).parent.parent.parent
                            output_dir = root_dir / "data" / "output" / "google_video"
                            
                            st.info(f"📁 所有片段已保存到: {output_dir}")
                            
                            if st.button("📂 打开输出文件夹"):
                                import subprocess
                                subprocess.run(["open", str(output_dir)], check=False)
                        else:
                            st.error("❌ 视频片段创建失败")
        else:
            st.info("没有找到可切分的片段数据")

def main():
    """主函数"""
    st.title("🔬 Google Cloud Video Intelligence API 测试")
    st.markdown("""
    这个测试页面可以帮您验证 Google Cloud Video Intelligence API 的各项功能，包括：
    - 🎬 镜头切分检测
    - 🏷️ 标签检测
    - 📝 文本检测
    - 👤 人脸检测
    - 📦 物体跟踪
    
    **🚀 核心功能**:
    - ✂️ **智能视频切分**: 根据Google Cloud分析结果自动切分视频片段
    - 📁 片段自动保存到 `data/output/google_video/` 目录
    - 📊 提供详细的分析统计和可视化展示
    - 🔍 支持镜头、标签、人脸等多种切分模式
    
    **使用流程**: 上传视频 → Google Cloud AI分析 → 自动切分视频片段 → 查看结果
    """)
    st.markdown("---")
    
    # 检查凭据状态
    has_credentials, cred_path = check_credentials()
    
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
                config['text_detection'],
                config['face_detection'],
                config.get('object_tracking', False),
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
        
    else:
        st.warning("⚠️ 未检测到 Google Cloud 凭据")
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

if __name__ == "__main__":
    main() 