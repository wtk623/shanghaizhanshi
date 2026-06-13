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
    "max_tokens": 800,
    "temperature": 0.1,
    "api_timeout": 60,
    "max_retry": 3
}

# ===================== 上海地标库（带别名，多级匹配）=====================
SHANGHAI_LANDMARKS = {
    "东方明珠": {
        "desc": "东方明珠广播电视塔是上海的标志性文化景观之一，位于浦东新区陆家嘴，塔高约468米，是国家AAAAA级旅游景区，也是上海天际线的核心标志。",
        "aliases": ["东方明珠塔", "东方明珠广播电视塔", "明珠塔"]
    },
    "上海中心大厦": {
        "desc": "上海中心大厦是上海第一高楼，建筑高度632米，中国第一、世界第三高楼，位于陆家嘴金融中心，以螺旋上升的独特造型闻名。",
        "aliases": ["上海中心", "上海中心大楼"]
    },
    "上海环球金融中心": {
        "desc": "上海环球金融中心位于陆家嘴，楼高492米，地上101层，因顶部独特的风洞造型被俗称为“开瓶器”，是上海地标摩天楼之一。",
        "aliases": ["环球金融中心", "开瓶器"]
    },
    "金茂大厦": {
        "desc": "金茂大厦是上海经典摩天大楼，楼高420.5米，地上88层，采用中国传统塔式建筑风格，曾是上海第一高楼。",
        "aliases": ["金茂大楼", "金茂"]
    },
    "外滩": {
        "desc": "外滩是上海标志性景点，位于黄浦江畔，全长1.5公里，拥有52幢风格各异的古典复兴大楼，被誉为“万国建筑博览群”。",
        "aliases": ["外滩建筑群", "上海外滩"]
    },
    "人民英雄纪念塔": {
        "desc": "上海市人民英雄纪念塔位于外滩黄浦公园内，建成于1993年，塔高60米，由三根枪状立柱组成，是为纪念上海革命先烈而建。",
        "aliases": ["人民英雄纪念碑", "上海人民英雄纪念塔"]
    },
    "豫园": {
        "desc": "豫园是上海著名古典园林，始建于明代嘉靖年间，已有四百余年历史，是江南古典园林的代表作品，紧邻上海城隍庙。",
        "aliases": ["上海豫园", "城隍庙豫园"]
    },
    "南京路步行街": {
        "desc": "南京路步行街是上海最繁华的商业街，西起西藏中路，东至河南中路，全长1033米，被誉为“中华商业第一街”。",
        "aliases": ["南京路", "南京东路"]
    },
    "和平饭店": {
        "desc": "和平饭店是上海标志性历史建筑，位于南京东路和外滩交叉口，建于1929年，被誉为“远东第一楼”，见证了上海近百年历史。",
        "aliases": ["上海和平饭店", "和平饭店北楼"]
    },
    "中共一大会址": {
        "desc": "中共一大会址是中国共产党诞生地，位于黄浦区兴业路76号，1921年中国共产党第一次全国代表大会在此召开。",
        "aliases": ["一大会址", "一大会议旧址"]
    },
    "东海大桥": {
        "desc": "东海大桥是中国第一座跨海大桥，连接上海南汇和浙江洋山港，全长32.5公里，2005年建成通车，是世界最长跨海大桥之一。",
        "aliases": ["上海东海大桥"]
    },
    "南浦大桥": {
        "desc": "南浦大桥是上海市区第一座跨越黄浦江的大桥，建成于1991年，全长8346米，采用双塔双索面斜拉桥结构。",
        "aliases": ["上海南浦大桥"]
    },
    "杨浦大桥": {
        "desc": "杨浦大桥是上海跨越黄浦江的斜拉桥，建成于1993年，全长7658米，曾是世界最大跨径的斜拉桥之一。",
        "aliases": ["上海杨浦大桥"]
    },
    "外白渡桥": {
        "desc": "外白渡桥是上海标志性桥梁，位于苏州河汇入黄浦江口，是中国第一座全钢结构铆接桥梁，也是上海经典影视取景地。",
        "aliases": ["上海外白渡桥"]
    },
    "陆家嘴": {
        "desc": "陆家嘴是上海金融中心，位于浦东新区黄浦江畔，聚集了众多跨国银行总部和超高层摩天大楼，是中国金融核心区。",
        "aliases": ["陆家嘴金融区", "上海陆家嘴"]
    },
    "田子坊": {
        "desc": "田子坊是上海著名创意产业聚集区，位于泰康路，由上海特色石库门里弄演变而来，充满文艺气息和老上海风情。",
        "aliases": ["上海田子坊"]
    },
    "新天地": {
        "desc": "上海新天地是具有上海历史文化风貌的都市景点，以上海近代石库门建筑旧区为基础改造，融合了历史与时尚。",
        "aliases": ["上海新天地"]
    },
    "上海迪士尼乐园": {
        "desc": "上海迪士尼乐园是中国内地首座迪士尼主题乐园，位于浦东新区川沙新镇，2016年正式开园，是全球第六座迪士尼乐园。",
        "aliases": ["迪士尼乐园", "上海迪士尼"]
    },
    "武康大楼": {
        "desc": "武康大楼是上海标志性历史建筑，位于淮海中路和武康路交叉口，建于1924年，是上海第一座外廊式公寓大楼。",
        "aliases": ["上海武康大楼"]
    },
    "城隍庙": {
        "desc": "上海城隍庙是上海著名道教宫观，始建于明代永乐年间，周边是上海传统民俗商业区，汇聚了众多上海老字号和特色小吃。",
        "aliases": ["上海城隍庙", "老城隍庙"]
    }
}

# 提取所有地标名称+别名的关键词列表，用于快速匹配
ALL_LANDMARK_KEYWORDS = []
LANDMARK_NAME_MAP = {}
for main_name, info in SHANGHAI_LANDMARKS.items():
    ALL_LANDMARK_KEYWORDS.append(main_name)
    LANDMARK_NAME_MAP[main_name] = main_name
    for alias in info["aliases"]:
        ALL_LANDMARK_KEYWORDS.append(alias)
        LANDMARK_NAME_MAP[alias] = main_name

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
    if not ARK_CONFIG["vision_endpoint_id"] or ARK_CONFIG["vision_endpoint_id"] == "你的视觉模型接入点ID":
        st.error("❌ 请配置ARK_VISION_ENDPOINT_ID（视觉模型接入点ID，ep-开头）")
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
        position: relative;
    }
    
    .main-image {
        max-width: 100%;
        max-height: 70vh;
        width: auto;
        height: auto;
        display: block;
        object-fit: contain;
    }
    
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
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    .stFileUploader {
        max-width: 600px;
        margin: 0 auto;
    }
    
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
    
    .debug-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px;
        margin-top: 10px;
        font-size: 12px;
        color: #666;
        max-width: 1200px;
        width: 100%;
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
        "debug_info": ""
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

# ===================== 📸 图片识别模式（纯文本关键词匹配版）=====================
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
            image_bytes = uploaded_file.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            st.session_state.current_image = image_base64
            
            img = Image.open(io.BytesIO(image_bytes))
            st.session_state.img_width, st.session_state.img_height = img.size
            st.session_state.image_analyzed = False
            st.session_state.hotspots = []
            st.session_state.active_landmark = None
            st.session_state.debug_info = ""
            
            st.rerun()
    
    # 显示图片和识别结果
    else:
        st.markdown('<div class="image-wrapper">', unsafe_allow_html=True)
        
        st.markdown('<div class="image-container">', unsafe_allow_html=True)
        
        st.markdown(f"""
        <img src="data:image/jpeg;base64,{st.session_state.current_image}" class="main-image" id="main-image">
        """, unsafe_allow_html=True)
        
        if not st.session_state.image_analyzed:
            st.markdown("""
            <div class="loading-overlay">
                <div>🔍 AI正在识别图片中的上海地标...</div>
            </div>
            """, unsafe_allow_html=True)
            
            matched_results = []
            debug_logs = []
            
            try:
                # 第一轮：直接让AI列地标名称，纯文本输出，不要求JSON
                response = client.chat.completions.create(
                    model=ARK_CONFIG["vision_endpoint_id"],
                    messages=[
                        {
                            "role": "system",
                            "content": "你是上海地标识别专家。请识别图片中的上海地标建筑，只输出地标名称，多个用中文逗号分隔，不要任何解释、序号、标点符号以外的内容。"
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
                
                ai_output = response.choices[0].message.content.strip()
                debug_logs.append(f"AI原始输出: {ai_output}")
                
                # 清洗输出文本
                ai_output = re.sub(r'[0-9、\.\n\r]', '', ai_output)
                ai_output = ai_output.replace("，", ",").replace("、", ",")
                
                # 分割地标名称
                ai_landmarks = [name.strip() for name in ai_output.split(",") if name.strip()]
                debug_logs.append(f"分割后地标列表: {ai_landmarks}")
                
                # 多级匹配
                matched_names = set()
                
                # 第一级：精确匹配主名称
                for name in ai_landmarks:
                    if name in SHANGHAI_LANDMARKS:
                        matched_names.add(name)
                
                # 第二级：别名匹配
                for name in ai_landmarks:
                    if name in LANDMARK_NAME_MAP:
                        matched_names.add(LANDMARK_NAME_MAP[name])
                
                # 第三级：子串模糊匹配（AI输出不全时也能匹配）
                if not matched_names:
                    for keyword in ALL_LANDMARK_KEYWORDS:
                        for ai_name in ai_landmarks:
                            if keyword in ai_name or ai_name in keyword:
                                matched_names.add(LANDMARK_NAME_MAP[keyword])
                                break
                
                # 第四级：全文本关键词扫描（AI输出带描述时也能提取）
                if not matched_names:
                    full_text = response.choices[0].message.content
                    for keyword in ALL_LANDMARK_KEYWORDS:
                        if keyword in full_text:
                            matched_names.add(LANDMARK_NAME_MAP[keyword])
                
                debug_logs.append(f"匹配到的地标: {list(matched_names)}")
                
                # 生成结果
                for name in matched_names:
                    matched_results.append({
                        "name": name,
                        "description": SHANGHAI_LANDMARKS[name]["desc"]
                    })
                
            except Exception as e:
                debug_logs.append(f"API调用错误: {str(e)}")
                import traceback
                debug_logs.append(f"错误详情: {traceback.format_exc()}")
            
            # 最终后备：如果完全没匹配到
            if not matched_results:
                matched_results.append({
                    "name": "上海城市景观",
                    "description": "这是上海的城市景观。上海是中国最大的城市，也是国际经济、金融、贸易、航运中心，拥有丰富的历史文化和现代化的城市风貌。"
                })
                debug_logs.append("触发后备机制：未匹配到明确地标")
            
            st.session_state.hotspots = matched_results
            st.session_state.debug_info = "\n".join(debug_logs)
            st.session_state.image_analyzed = True
            
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 生成地标按钮和介绍
        if st.session_state.hotspots:
            html_content = """
            <div class="landmark-buttons">
            """
            
            for i, hotspot in enumerate(st.session_state.hotspots):
                html_content += f"""
                <button class="landmark-btn" id="btn-{i}" data-index="{i}">{hotspot['name']}</button>
                """
            
            html_content += """
            </div>
            """
            
            for i, hotspot in enumerate(st.session_state.hotspots):
                html_content += f"""
                <div class="landmark-info" id="info-{i}">
                    <h3>{hotspot['name']}</h3>
                    <p>{hotspot['description']}</p>
                </div>
                """
            
            html_content += """
            <script>
            const buttons = document.querySelectorAll('.landmark-btn');
            const infos = document.querySelectorAll('.landmark-info');
            
            buttons.forEach(button => {
                button.addEventListener('click', () => {
                    const index = button.dataset.index;
                    buttons.forEach(btn => btn.classList.remove('active'));
                    infos.forEach(info => info.classList.remove('active'));
                    
                    setTimeout(() => {
                        button.classList.add('active');
                        document.getElementById(`info-${index}`).classList.add('active');
                        document.getElementById(`info-${index}`).scrollIntoView({
                            behavior: 'smooth',
                            block: 'nearest'
                        });
                    }, 100);
                });
            });
            
            if (buttons.length > 0) {
                buttons[0].click();
            }
            </script>
            """
            
            st.components.v1.html(html_content, height=700, scrolling=True)
            
            # 调试信息（默认显示，方便排查）
            with st.expander("🔧 识别调试信息", expanded=False):
                st.code(st.session_state.debug_info)
        
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
                st.session_state.debug_info = ""
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
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if "shanghai_dialect" in message and message["shanghai_dialect"]:
                st.markdown(f'<div class="shanghai-dialect">🗣️ {message["shanghai_dialect"]}</div>', unsafe_allow_html=True)
            
            if "is_easter_egg" in message and message["is_easter_egg"]:
                st.markdown(f'<div class="easter-egg">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(message["content"])
            
            if "audio" in message and message["audio"]:
                st.audio(message["audio"], format="audio/mp3")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    prompt = st.chat_input("输入你想了解的上海相关内容...")
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            # 彩蛋检测
            easter_egg_triggered = False
            easter_egg_content = ""
            
            for keyword, content in EASTER_EGGS.items():
                if keyword in prompt:
                    easter_egg_triggered = True
                    easter_egg_content = content
                    break
            
            if easter_egg_triggered:
                st.markdown(f'<div class="easter-egg">{easter_egg_content}</div>', unsafe_allow_html=True)
                
                audio_content = None
                try:
                    audio_content = text_to_speech(easter_egg_content, "mandarin")
                except:
                    pass
                
                if audio_content:
                    st.audio(audio_content, format="audio/mp3", autoplay=True)
                
                assistant_data = {
                    "role": "assistant",
                    "content": easter_egg_content,
                    "audio": audio_content,
                    "shanghai_dialect": "",
                    "is_easter_egg": True
                }
                
            else:
                with st.spinner("🤔 正在思考..."):
                    context = ""
                    if st.session_state.last_topic:
                        context = f"上一个话题是：{st.session_state.last_topic}。请关联回答。"
                    
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
                    
                    shanghai_dialect = ""
                    mandarin_content = answer
                    
                    if st.session_state.local_mode:
                        parts = answer.split("\n\n", 1)
                        if len(parts) == 2:
                            shanghai_dialect = parts[0].strip()
                            mandarin_content = parts[1].strip()
                    
                    if st.session_state.local_mode and shanghai_dialect:
                        st.markdown(f'<div class="shanghai-dialect">🗣️ {shanghai_dialect}</div>', unsafe_allow_html=True)
                    
                    st.markdown(mandarin_content)
                    
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
                    
                    assistant_data = {
                        "role": "assistant",
                        "content": mandarin_content,
                        "audio": audio_content,
                        "shanghai_dialect": shanghai_dialect if st.session_state.local_mode else "",
                        "is_easter_egg": False
                    }
            
            st.session_state.messages.append(assistant_data)
            st.session_state.last_topic = prompt
            
            if len(st.session_state.messages) > APP_CONFIG["max_history"]:
                st.session_state.messages = st.session_state.messages[-APP_CONFIG["max_history"]:]
            
            st.rerun()

# 页脚
st.markdown("---")
if st.session_state.local_mode:
    st.caption("🚕 上海老司机智能体 | 阿拉上海宁，为侬带路！")
else:
    st.caption("上海城市智能体 | 基于豆包大模型 | 2026")