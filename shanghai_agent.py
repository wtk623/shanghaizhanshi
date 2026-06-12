import streamlit as st
import os
import openai
import base64
import plotly.express as px
import pandas as pd
from datetime import datetime
import requests
import json
import uuid
from dotenv import load_dotenv
from PIL import Image
import io
import time
import re

# ===================== 🔧 全局配置 =====================
load_dotenv()
ARK_CONFIG = {
    "api_key": st.secrets.get("ARK_API_KEY", os.getenv("ARK_API_KEY", "")),
    "endpoint_id": st.secrets.get("ARK_ENDPOINT_ID", os.getenv("ARK_ENDPOINT_ID", "bot-20260608181219-tlqzx")),
    "vision_endpoint_id": st.secrets.get("ARK_VISION_ENDPOINT_ID", os.getenv("ARK_VISION_ENDPOINT_ID", "你的视觉模型接入点ID")),
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "tts_model": "speech-tts-v1"
}
APP_CONFIG = {
    "page_title": "上海城市智能体 🗺️",
    "page_icon": "🏙️",
    "layout": "wide",
    "max_history": 15,
    "max_tokens": 1500,
    "temperature": 0.05,  # 降低温度，提高识别准确性
    "api_timeout": 60,
    "max_retry": 5  # 增加重试次数
}

# 预定义上海常见地标（终极后备机制）
SHANGHAI_LANDMARKS = {
    "东方明珠": "东方明珠广播电视塔是上海的标志性文化景观之一，位于浦东新区陆家嘴，塔高约468米，是国家AAAAA级旅游景区。",
    "上海中心大厦": "上海中心大厦是上海的第一高楼，建筑高度632米，是中国第一、世界第三高楼，位于陆家嘴金融中心。",
    "外滩": "外滩是上海的标志性景点，位于黄浦江畔，全长1.5公里，拥有52幢风格各异的古典复兴大楼，被誉为万国建筑博览群。",
    "豫园": "豫园是上海著名的古典园林，始建于明代嘉靖、万历年间，已有四百余年历史，是江南古典园林的代表作品。",
    "南京路步行街": "南京路步行街是上海最繁华的商业街，西起西藏中路，东至河南中路，全长1033米，被誉为中华商业第一街。",
    "上海迪士尼乐园": "上海迪士尼乐园是中国内地首座迪士尼主题乐园，位于浦东新区川沙新镇，于2016年6月16日正式开园。",
    "田子坊": "田子坊是上海著名的创意产业聚集区，位于泰康路，由上海最具特色的石库门里弄演变而来。",
    "新天地": "上海新天地是一个具有上海历史文化风貌的都市旅游景点，以上海近代建筑石库门建筑旧区为基础改造而成。",
    "东海大桥": "东海大桥是中国第一座跨海大桥，连接上海南汇和浙江洋山港，全长32.5公里，2005年建成通车，是世界上最长的跨海大桥之一。",
    "南浦大桥": "南浦大桥是上海市区第一座跨越黄浦江的大桥，建成于1991年，全长8346米，采用斜拉桥结构。",
    "杨浦大桥": "杨浦大桥是上海的一座跨越黄浦江的斜拉桥，建成于1993年，全长7658米，曾是世界上最大的斜拉桥之一。",
    "陆家嘴": "陆家嘴是上海的金融中心，位于浦东新区黄浦江畔，聚集了众多跨国银行的大中华区及东亚总部。",
    "中共一大会址": "中共一大会址是中国共产党的诞生地，位于上海市黄浦区兴业路76号，1921年中国共产党第一次全国代表大会在此召开。",
    "和平饭店": "和平饭店是上海的标志性历史建筑，位于南京东路和外滩的交叉口，建于1929年，被誉为远东第一楼。",
    "上海环球金融中心": "上海环球金融中心是位于陆家嘴的摩天大楼，楼高492米，地上101层，以其独特的开瓶器造型闻名。",
    "金茂大厦": "金茂大厦是上海的经典摩天大楼，楼高420.5米，地上88层，采用中国传统塔式建筑风格。",
    "外白渡桥": "外白渡桥是上海的标志性桥梁，位于苏州河汇入黄浦江口，是中国第一座全钢结构铆接桥梁。",
    "上海火车站": "上海站是上海的主要铁路客运站之一，位于静安区秣陵路，始建于1908年，是上海铁路枢纽的重要组成部分。",
    "虹桥机场": "上海虹桥国际机场是上海的两大国际机场之一，位于长宁区和闵行区交界处，是中国主要的航空枢纽之一。",
    "浦东机场": "上海浦东国际机场是上海的两大国际机场之一，位于浦东新区，是中国最大的航空枢纽之一。"
}

# ===================== 🥚 彩蛋配置 =====================
EASTER_EGGS = {
    "和平饭店": "上海有个规矩，只要进了和平饭店，黑白两道的人都不敢动你，只因饭店的老板姓杜",
    "蜜雪冰城": "检测到有人使用安卓手机拍摄东方明珠",
    "沪爷": "随便整整888卖给沪爷",
    "空悲切": "我能打上海major！，到时候全场欢呼 danking！danking！danking！"
}

# ===================== ✅ 配置校验 =====================
def validate_config():
    if not ARK_CONFIG["api_key"]:
        st.error("❌ 请配置ARK_API_KEY！")
        st.markdown("""
        配置方式：
        1. 本地开发：项目根目录新建`.env`，写入`ARK_API_KEY=你的密钥`
        2. 云端部署：在Streamlit Secrets中添加`ARK_API_KEY`
        """)
        st.stop()
    if not ARK_CONFIG["endpoint_id"]:
        st.error("❌ 请配置ARK_ENDPOINT_ID（推理接入点ID）")
        st.stop()
    if not ARK_CONFIG["vision_endpoint_id"]:
        st.error("❌ 请配置ARK_VISION_ENDPOINT_ID（视觉模型接入点ID）")
        st.stop()

validate_config()

# ===================== 🚀 初始化客户端 =====================
@st.cache_resource
def get_ark_client():
    return openai.OpenAI(
        api_key=ARK_CONFIG["api_key"],
        base_url=ARK_CONFIG["base_url"]
    )

client = get_ark_client()

# ===================== 🎙️ 语音合成 =====================
def text_to_speech(text, language="mandarin"):
    url = f"{ARK_CONFIG['base_url']}/audio/speech"
    headers = {"Authorization": f"Bearer {ARK_CONFIG['api_key']}", "Content-Type": "application/json"}
    
    voice_config = {
        "shanghai": {"voice": "zh-CN-XiaoxiaoNeural", "speed": 1.05},
        "mandarin": {"voice": "zh-CN-YunxiNeural", "speed": 1.0}
    }
    config = voice_config.get(language, voice_config["mandarin"])
    
    data = {
        "model": ARK_CONFIG["tts_model"],
        "input": text[:300],
        "voice": config["voice"],
        "speed": config["speed"],
        "format": "mp3"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.content
    except:
        return None

# ===================== 🎨 UI样式 =====================
def set_styles():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding-top: 0;
    }
    
    .stApp[data-local="true"] {
        background: linear-gradient(135deg, #f5f0e6 0%, #e8dcc8 100%);
        background-image: url('https://images.unsplash.com/photo-1558618666-fcd25c85cd64?ixlib=rb-4.0.3&auto=format&fit=crop&w=1950&q=80');
        background-size: cover;
        background-attachment: fixed;
        background-blend-mode: overlay;
    }
    
    .top-nav {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 60px;
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 20px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    .nav-title {
        font-size: 1.5em;
        font-weight: bold;
        color: #333;
    }
    
    .chat-container {
        margin-top: 80px;
        margin-bottom: 80px;
        padding: 0 20px;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
        margin-bottom: 20px;
    }
    
    .stChatMessage[data-testid="stChatMessage-user"] {
        background-color: rgba(220, 240, 255, 0.95) !important;
    }
    
    .shanghai-dialect {
        background-color: #fff3cd;
        padding: 10px 15px;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin-bottom: 15px;
        font-family: "Microsoft YaHei", sans-serif;
        font-size: 1.1em;
        font-weight: 500;
    }
    
    /* 彩蛋回复特殊样式 */
    .easter-egg {
        background-color: #fff3cd !important;
        border: 3px solid #dc3545 !important;
        border-radius: 15px !important;
        padding: 20px !important;
        font-size: 1.2em !important;
        font-weight: bold !important;
        color: #dc3545 !important;
        text-align: center !important;
        animation: shake 0.5s ease-in-out;
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    /* 图片识别模式 */
    .image-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        min-height: calc(100vh - 200px);
        padding: 20px;
        margin-top: 70px;
    }
    
    .image-container {
        max-width: 1200px;
        max-height: 70vh;
        border-radius: 15px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        overflow: hidden;
        margin-bottom: 25px;
    }
    
    .main-image {
        max-width: 100%;
        max-height: 70vh;
        width: auto;
        height: auto;
        display: block;
        object-fit: contain;
    }
    
    /* 地标按钮组 */
    .landmark-buttons {
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
        justify-content: center;
        max-width: 1200px;
        margin-bottom: 20px;
    }
    
    .landmark-btn {
        background-color: #ffffff;
        color: #333333;
        border: 2px solid #667eea;
        padding: 12px 24px;
        border-radius: 25px;
        font-size: 16px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .landmark-btn:hover {
        background-color: #667eea;
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .landmark-btn.active {
        background-color: #667eea;
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    /* 平滑展开的介绍内容 */
    .landmark-info {
        background-color: white;
        padding: 0 20px;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        max-width: 1200px;
        width: 100%;
        margin-bottom: 20px;
        max-height: 0;
        opacity: 0;
        overflow: hidden;
        transition: all 0.4s ease-in-out;
    }
    
    .landmark-info.active {
        max-height: 500px;
        opacity: 1;
        padding: 20px;
    }
    
    .landmark-info h3 {
        margin-top: 0;
        margin-bottom: 10px;
        color: #667eea;
        font-size: 20px;
    }
    
    .landmark-info p {
        margin: 0;
        line-height: 1.6;
        font-size: 16px;
        color: #333;
    }
    
    .bottom-input {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        padding: 15px 20px;
        box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
        z-index: 1000;
    }
    
    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* 修复文件上传器样式 */
    .stFileUploader {
        max-width: 600px;
        margin: 0 auto;
    }
    
    /* 加载状态样式 */
    .loading-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        color: white;
        font-size: 1.2em;
        z-index: 500;
        border-radius: 15px;
    }
    
    /* 错误提示样式 */
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #f5c6cb;
        margin-bottom: 20px;
        max-width: 600px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

set_styles()

# ===================== 📊 会话状态初始化 =====================
def init_session_state():
    defaults = {
        "messages": [],
        "mode": "对话模式",
        "last_topic": None,
        "local_mode": False,
        "audio_counter": 0,
        "current_image": None,
        "hotspots": [],
        "active_landmark": None,
        "image_history": [],
        "img_width": 0,
        "img_height": 0,
        "image_analyzed": False,
        "debug_mode": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ===================== 🧭 顶部导航 =====================
st.markdown(f"""
<div class="top-nav">
    <div class="nav-title">{APP_CONFIG['page_title']}</div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("💬 对话模式", key="chat_mode_btn", use_container_width=True, 
                 type="primary" if st.session_state.mode == "对话模式" else "secondary"):
        st.session_state.mode = "对话模式"
        st.session_state.active_landmark = None
        st.rerun()
with col2:
    if st.button("🖼️ 图片识别", key="image_mode_btn", use_container_width=True,
                 type="primary" if st.session_state.mode == "图片识别模式" else "secondary"):
        st.session_state.mode = "图片识别模式"
        st.rerun()
with col3:
    if st.button("🚕 本地人模式", key="local_mode_btn", use_container_width=True,
                 type="primary" if st.session_state.local_mode else "secondary"):
        st.session_state.local_mode = not st.session_state.local_mode
        st.rerun()

# ===================== 📸 图片识别模式（终极优化版）=====================
if st.session_state.mode == "图片识别模式":
    # 上传图片区域
    if not st.session_state.current_image:
        st.markdown("""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: calc(100vh - 200px);">
            <h2>上传上海相关图片</h2>
            <p>支持JPG、JPEG、PNG格式，AI自动识别地标并生成按钮</p>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("上传上海地标图片", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        
        if uploaded_file:
            # 立即处理并显示图片
            image_bytes = uploaded_file.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            st.session_state.current_image = image_base64
            
            # 获取图片尺寸
            img = Image.open(io.BytesIO(image_bytes))
            st.session_state.img_width, st.session_state.img_height = img.size
            st.session_state.image_analyzed = False
            st.session_state.hotspots = []
            st.session_state.active_landmark = None
            
            st.rerun()
    
    # 显示图片和按钮
    else:
        st.markdown('<div class="image-wrapper">', unsafe_allow_html=True)
        
        # 图片容器
        st.markdown('<div class="image-container">', unsafe_allow_html=True)
        
        # 显示主图片
        st.markdown(f"""
        <img src="data:image/jpeg;base64,{st.session_state.current_image}" class="main-image" id="main-image">
        """, unsafe_allow_html=True)
        
        # 显示加载状态
        if not st.session_state.image_analyzed:
            st.markdown("""
            <div class="loading-overlay">
                <div>🔍 AI正在分析图片中的上海地标...</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 自动分析图片（终极优化版）
            retry_count = 0
            success = False
            error_messages = []
            
            while retry_count < APP_CONFIG["max_retry"] and not success:
                try:
                    # 强化版系统提示词
                    system_prompt = f"""你是上海城市智能体的首席图片分析专家，专门识别上海的地标建筑。
                    
                    重要规则：
                    1. 这张图片100%拍摄于上海，必须识别出至少1个上海地标
                    2. 即使地标只露出一部分、距离很远、角度特殊，也要尽力识别
                    3. 常见上海地标包括：{', '.join(list(SHANGHAI_LANDMARKS.keys())[:15])}
                    4. 严格按照以下JSON格式输出，不要添加任何其他文字、解释或markdown
                    5. 识别3-5个最重要的地标，按重要性排序
                    
                    输出格式：
                    {{"hotspots":[{{"name":"地标名称","description":"100字左右详细介绍"}}]}}
                    
                    示例：
                    {{"hotspots":[{{"name":"东海大桥","description":"东海大桥是中国第一座跨海大桥，连接上海南汇和浙江洋山港，全长32.5公里，2005年建成通车，是世界上最长的跨海大桥之一。"}}]}}
                    """
                    
                    response = client.chat.completions.create(
                        model=ARK_CONFIG["vision_endpoint_id"],
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{st.session_state.current_image}"}}
                                ]
                            }
                        ],
                        temperature=APP_CONFIG["temperature"],
                        max_tokens=APP_CONFIG["max_tokens"],
                        timeout=APP_CONFIG["api_timeout"]
                    )
                    
                    # 超级增强版JSON解析
                    content = response.choices[0].message.content.strip()
                    
                    # 移除所有markdown标记和多余内容
                    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
                    content = re.sub(r'`', '', content)
                    content = content.strip()
                    
                    # 提取JSON部分
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(0)
                        # 修复常见JSON语法错误
                        json_str = json_str.replace("'", "\"")
                        json_str = re.sub(r',\s*}', '}', json_str)
                        json_str = re.sub(r',\s*]', ']', json_str)
                        
                        try:
                            hotspot_data = json.loads(json_str)
                            st.session_state.hotspots = hotspot_data.get("hotspots", [])
                            
                            # 验证识别结果
                            valid_hotspots = []
                            for hotspot in st.session_state.hotspots:
                                if "name" in hotspot and "description" in hotspot:
                                    # 检查是否是上海地标
                                    name = hotspot["name"].strip()
                                    # 模糊匹配预定义地标
                                    for landmark_name, landmark_desc in SHANGHAI_LANDMARKS.items():
                                        if landmark_name in name or name in landmark_name:
                                            hotspot["name"] = landmark_name
                                            hotspot["description"] = landmark_desc
                                            break
                                    valid_hotspots.append(hotspot)
                            
                            st.session_state.hotspots = valid_hotspots
                            
                            if len(st.session_state.hotspots) > 0:
                                success = True
                            else:
                                raise ValueError("未识别到有效的上海地标")
                        except json.JSONDecodeError as e:
                            error_messages.append(f"JSON解析失败: {str(e)}")
                            error_messages.append(f"原始内容: {content}")
                    else:
                        error_messages.append(f"未找到JSON数据: {content}")
                
                except Exception as e:
                    error_messages.append(f"第{retry_count+1}次尝试失败: {str(e)}")
                    retry_count += 1
                    if retry_count < APP_CONFIG["max_retry"]:
                        time.sleep(2)
            
            # 终极后备机制：如果AI完全失败，使用预定义地标
            if not success:
                # 尝试使用关键词匹配
                image_text = ""
                try:
                    # 这里可以添加OCR识别，但为了简化，我们直接使用后备
                    pass
                except:
                    pass
                
                # 使用通用后备
                st.session_state.hotspots = [
                    {
                        "name": "上海城市景观",
                        "description": "这是上海的城市景观，上海是中国最大的城市，也是国际经济、金融、贸易、航运中心，拥有丰富的历史文化和现代化的城市风貌。"
                    }
                ]
            
            st.session_state.image_analyzed = True
            
            # 调试模式：显示错误信息
            if st.session_state.debug_mode and error_messages:
                st.error("调试信息：")
                for msg in error_messages:
                    st.code(msg)
            
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 生成地标按钮和介绍
        if st.session_state.hotspots:
            html_content = """
            <div class="landmark-buttons">
            """
            
            # 生成按钮
            for i, hotspot in enumerate(st.session_state.hotspots):
                html_content += f"""
                <button class="landmark-btn" id="btn-{i}" data-index="{i}">{hotspot['name']}</button>
                """
            
            html_content += """
            </div>
            """
            
            # 生成介绍内容
            for i, hotspot in enumerate(st.session_state.hotspots):
                html_content += f"""
                <div class="landmark-info" id="info-{i}">
                    <h3>{hotspot['name']}</h3>
                    <p>{hotspot['description']}</p>
                </div>
                """
            
            # 添加交互逻辑（平滑展开）
            html_content += """
            <script>
            const buttons = document.querySelectorAll('.landmark-btn');
            const infos = document.querySelectorAll('.landmark-info');
            
            buttons.forEach(button => {
                button.addEventListener('click', () => {
                    const index = button.dataset.index;
                    
                    // 移除所有活跃状态（触发平滑收起）
                    buttons.forEach(btn => btn.classList.remove('active'));
                    infos.forEach(info => info.classList.remove('active'));
                    
                    // 延迟后添加当前活跃状态（实现先收起再展开）
                    setTimeout(() => {
                        button.classList.add('active');
                        document.getElementById(`info-${index}`).classList.add('active');
                        
                        // 滚动到介绍内容
                        document.getElementById(`info-${index}`).scrollIntoView({
                            behavior: 'smooth',
                            block: 'nearest'
                        });
                    }, 100);
                });
            });
            
            // 自动点击第一个按钮
            if (buttons.length > 0) {
                buttons[0].click();
            }
            </script>
            """
            
            # 渲染HTML
            st.components.v1.html(html_content, height=700, scrolling=True)
            
        else:
            # 无热点提示
            st.markdown("""
            <div class="error-box">
                <h3>😕 未识别到上海地标</h3>
                <p>请尝试上传更清晰的上海地标图片，或者直接在对话模式中询问相关信息</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 底部操作栏
        st.markdown('<div class="bottom-input">', unsafe_allow_html=True)
        col_clear, col_tip, col_chat = st.columns(3)
        with col_clear:
            if st.button("🗑️ 清除图片", use_container_width=True):
                st.session_state.current_image = None
                st.session_state.hotspots = []
                st.session_state.active_landmark = None
                st.session_state.img_width = 0
                st.session_state.img_height = 0
                st.session_state.image_analyzed = False
                st.rerun()
        with col_tip:
            st.markdown("<p style='text-align: center; margin-top: 8px;'>点击下方按钮查看对应地标介绍</p>", unsafe_allow_html=True)
        with col_chat:
            if st.button("💬 切换到对话模式", use_container_width=True):
                st.session_state.mode = "对话模式"
                st.session_state.active_landmark = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ===================== 💬 对话模式 =====================
else:
    # 侧边栏
    with st.sidebar:
        st.title(APP_CONFIG["page_title"])
        if st.session_state.local_mode:
            st.markdown('<span style="background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 20px; font-size: 0.8em;">🚕 上海老司机在线</span>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### 功能说明")
        st.markdown("""
        - **对话模式**：查询上海历史、建筑、美食、交通
        - **图片识别**：上传图片，点击下方按钮查看介绍
        - 🎙️ 自动语音回复，本地人模式讲上海话
        - 🥚 隐藏彩蛋：试试输入"和平饭店"、"蜜雪冰城"等关键词
        """)
        st.markdown("---")
        if st.button("清空对话历史", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_topic = None
            st.rerun()
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # 显示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if "shanghai_dialect" in message and message["shanghai_dialect"]:
                st.markdown(f'<div class="shanghai-dialect">🗣️ {message["shanghai_dialect"]}</div>', unsafe_allow_html=True)
            
            # 显示彩蛋或普通内容
            if "is_easter_egg" in message and message["is_easter_egg"]:
                st.markdown(f'<div class="easter-egg">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(message["content"])
            
            if "audio" in message and message["audio"]:
                st.audio(message["audio"], format="audio/mp3")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 用户输入
    prompt = st.chat_input("输入你想了解的上海相关内容...")
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            # 彩蛋检测（优先触发）
            easter_egg_triggered = False
            easter_egg_content = ""
            
            for keyword, content in EASTER_EGGS.items():
                if keyword in prompt:
                    easter_egg_triggered = True
                    easter_egg_content = content
                    break
            
            if easter_egg_triggered:
                # 显示彩蛋回复（特殊样式）
                st.markdown(f'<div class="easter-egg">{easter_egg_content}</div>', unsafe_allow_html=True)
                
                # 生成语音
                audio_content = None
                try:
                    audio_content = text_to_speech(easter_egg_content, "mandarin")
                except:
                    pass
                
                if audio_content:
                    st.audio(audio_content, format="audio/mp3", autoplay=True)
                
                # 保存到历史
                assistant_data = {
                    "role": "assistant",
                    "content": easter_egg_content,
                    "audio": audio_content,
                    "shanghai_dialect": "",
                    "is_easter_egg": True
                }
                
            else:
                # 正常回答
                with st.spinner("🤔 正在思考..."):
                    # 构建上下文
                    context = ""
                    if st.session_state.last_topic:
                        context = f"上一个话题是：{st.session_state.last_topic}。请关联回答。"
                    
                    # 系统提示词
                    if st.session_state.local_mode:
                        system_prompt = f"""你是一位热情幽默的上海出租车司机，开了20年出租车，对上海了如指掌。
                        {context}
                        回答规则：
                        1. 首先用上海话写一段生动的开场白（不超过50字）
                        2. 然后用标准普通话详细介绍
                        3. 加入本地小知识或实用建议
                        4. 语气亲切自然，带点上海人的幽默
                        """
                    else:
                        system_prompt = f"""你是专业的上海城市智能体。{context}
                        请提供准确、通俗、简洁的介绍。
                        优先使用结构化格式（标题、列表）。
                        回答要全面但不冗长，突出重点。
                        """
                    
                    try:
                        # 调用API
                        response = client.chat.completions.create(
                            model=ARK_CONFIG["endpoint_id"],
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=APP_CONFIG["temperature"],
                            max_tokens=APP_CONFIG["max_tokens"],
                            timeout=APP_CONFIG["api_timeout"]
                        )
                        
                        answer = response.choices[0].message.content.strip()
                        
                    except Exception as e:
                        answer = "抱歉，暂时无法回答您的问题。您可以尝试询问：\n- 上海著名景点\n- 本帮菜推荐\n- 交通出行\n- 历史事件"
                    
                    # 分离上海话和普通话
                    shanghai_dialect = ""
                    mandarin_content = answer
                    
                    if st.session_state.local_mode:
                        parts = answer.split("\n\n", 1)
                        if len(parts) == 2:
                            shanghai_dialect = parts[0].strip()
                            mandarin_content = parts[1].strip()
                    
                    # 显示内容
                    if st.session_state.local_mode and shanghai_dialect:
                        st.markdown(f'<div class="shanghai-dialect">🗣️ {shanghai_dialect}</div>', unsafe_allow_html=True)
                    
                    st.markdown(mandarin_content)
                    
                    # 生成语音
                    audio_content = None
                    try:
                        if st.session_state.local_mode:
                            audio_content = text_to_speech(shanghai_dialect + " " + mandarin_content[:200], "shanghai")
                        else:
                            audio_content = text_to_speech(mandarin_content[:300], "mandarin")
                    except:
                        pass
                    
                    if audio_content:
                        if st.session_state.local_mode:
                            st.audio(audio_content, format="audio/mp3", autoplay=True)
                        else:
                            st.audio(audio_content, format="audio/mp3")
                    
                    # 保存到历史
                    assistant_data = {
                        "role": "assistant",
                        "content": mandarin_content,
                        "audio": audio_content,
                        "shanghai_dialect": shanghai_dialect if st.session_state.local_mode else "",
                        "is_easter_egg": False
                    }
            
            st.session_state.messages.append(assistant_data)
            st.session_state.last_topic = prompt
            
            # 限制历史记录长度
            if len(st.session_state.messages) > APP_CONFIG["max_history"]:
                st.session_state.messages = st.session_state.messages[-APP_CONFIG["max_history"]:]
            
            st.rerun()

# 页脚
st.markdown("---")
if st.session_state.local_mode:
    st.caption("🚕 上海老司机智能体 | 阿拉上海宁，为侬带路！")
else:
    st.caption("上海城市智能体 | 基于豆包大模型 | 2026")