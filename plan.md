# 本地智能面试系统 - 技术实现方案

# 一、项目概述

## 1.1 核心目标

基于16GB MacBook本地环境，构建一套“简历解析-岗位匹配-实时面试-评估报告”全链路智能系统，支持语音/文本双模态实时对话，无需依赖外部API，通过知识缓存机制覆盖多领域面试需求，保障交互流畅性与问题精准性。

## 1.2 核心功能清单

- 简历处理：PDF/Word简历→结构化数据（技能、项目、经历）

- 岗位匹配：结构化简历与岗位JD向量匹配，生成技能缺口

- 实时对话：支持语音（ASR→LLM→TTS，含打断）与文本双模态交互

- 知识补充：新领域自动获取知识并缓存（含时间标签），无需重复调用

- 评估报告：面试结束自动生成量化评估报告（专业能力、逻辑表达等）

## 1.3 运行环境要求

16GB内存 MacBook（Apple Silicon M2/M3 优先，Intel i7 适配）、Python 3.8+、无GPU依赖、本地磁盘≥20GB（用于模型缓存）

# 二、整体架构设计

## 2.1 架构分层（从下到上）

|层级|核心组件|核心职责|
|---|---|---|
|基础设施层|本地模型库、缓存管理、音频设备驱动|模型加载与缓存、音频采集/播放、数据持久化|
|核心能力层|ASR模块、TTS模块、LLM模块、简历解析模块、向量匹配模块|语音转文字、文字转语音、面试问题生成/评估、简历结构化、岗位-简历匹配|
|业务逻辑层|面试流程控制器、知识补充管理器、评估报告生成器|控制面试全流程（启动/中断/结束）、新领域知识获取与缓存、生成量化评估报告|
|交互层|语音交互界面、文本Chat界面、简历上传界面、报告展示界面|用户操作入口、实时交互反馈、结果展示|
## 2.2 核心流程闭环

简历上传→结构化解析→岗位JD录入→向量匹配生成技能缺口→启动面试（语音/文本）→实时ASR/TTS/LLM交互（含知识缓存补充）→面试结束→生成量化评估报告

# 三、核心模块技术实现

## 3.1 基础设施层：本地模型与缓存管理

### 3.1.1 本地模型选型（16GB内存适配）

|模块|模型选型|量化方式|内存占用|核心优势|
|---|---|---|---|---|
|ASR（语音转文字）|WhisperX base（中文微调版）|int8|1.8GB|技术术语识别准、流式转写、延迟<1秒、CPU可运行|
|TTS（文字转语音）|Coqui TTS（zh-CN/baker/tacotron2）|轻量版|0.8GB|中文清晰、支持流式合成与打断、轻量无GPU依赖|
|LLM（问题生成/评估）|Qwen-2-7B-Chat|4-bit（GGUF/MLX）|4GB|中文优化、4k上下文、CPU推理≥10token/s、适配技术面试|
|简历解析|Spacy（中文轻量版）+ 正则匹配|-|0.3GB|结构化提取精准、速度快、轻量无依赖|
|向量匹配|Sentence-BERT（all-MiniLM-L6-v2）|int8|0.5GB|1024维向量、语义匹配准、CPU推理快|
### 3.1.2 缓存管理设计

核心目标：新领域知识一次获取、永久缓存，避免重复调用外部资源

- 缓存内容：领域核心技能、典型面试问题、评估标准、岗位向量、简历向量

- 缓存格式：JSON文件（结构化存储），示例：
        `{
  "领域": "AI Agent开发",
  "core_skills": ["LangGraph", "多模态交互", "工具调用"],
  "interview_questions": ["请说明LangGraph构建Agent的核心流程？"],
  "evaluation_criteria": {"专业能力": "能独立开发Agent应用", "逻辑表达": "清晰说明设计思路"},
  "first_fetch_time": "2025-08-01 10:30:00",
  "last_update_time": "2025-08-01 10:30:00",
  "expire_days": 180
}`

- 缓存策略：
        

    - 查询优先：面试前先查缓存，命中且未过期则直接使用

    - 过期更新：缓存过期（新兴领域180天，通用领域365天）自动更新

    - 存储路径：本地`./cache`目录，按“领域/岗位”分类存储

## 3.2 核心能力层：关键模块实现

### 3.2.1 简历解析模块

功能：将PDF/Word简历转为结构化JSON数据（基础信息、技能、项目经历、工作年限等）

#### 实现步骤：

1. 文本提取：用PyMuPDF（PDF）/python-docx（Word）提取简历文本，去除格式干扰

2. 结构化提取：
        

    - 基础信息（姓名、电话、邮箱）：正则匹配（如邮箱正则`[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(.[a-zA-Z0-9_-]+)+`）

    - 技能提取：Spacy实体识别+岗位关键词库匹配（如“Python”“Django”“量子比特”）

    - 项目/工作经历：按“时间范围+公司/项目名称+职责”格式正则提取

3. 数据清洗：去重技能、标准化格式（如“工作年限：3年2个月”→“3.17年”）

#### 核心代码片段：

```python

import fitz  # PyMuPDF
import re
import spacy

# 初始化Spacy中文模型
nlp = spacy.load("zh_core_web_sm")

def extract_resume_text(pdf_path):
    """提取PDF简历文本"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def parse_resume(pdf_path):
    """简历结构化解析"""
    text = extract_resume_text(pdf_path)
    # 1. 基础信息提取
    name = re.search(r"([^\n]{2,4})(?:\s|，|。)", text).group(1) if re.search(r"([^\n]{2,4})(?:\s|，|。)", text) else ""
    phone = re.search(r"1[3-9]\d{9}", text).group() if re.search(r"1[3-9]\d{9}", text) else ""
    email = re.search(r"[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(.[a-zA-Z0-9_-]+)+", text).group() if re.search(r"[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(.[a-zA-Z0-9_-]+)+", text) else ""
    # 2. 技能提取
    doc_nlp = nlp(text)
    skills = set()
    skill_keywords = ["Python", "Django", "LangGraph", "量子比特", "Verilog"]  # 可扩展
    for token in doc_nlp:
        if token.text in skill_keywords:
            skills.add(token.text)
    # 3. 工作年限提取
    work_years = re.search(r"(\d+(?:\.\d+)?)年", text).group(1) if re.search(r"(\d+(?:\.\d+)?)年", text) else "0"
    # 4. 结构化结果
    return {
        "basic_info": {"name": name, "phone": phone, "email": email},
        "skills": list(skills),
        "work_years": float(work_years),
        "raw_text": text
    }
```

### 3.2.2 向量匹配模块

功能：计算结构化简历与岗位JD的语义相似度，生成技能缺口

#### 实现步骤：

1. 文本向量化：用Sentence-BERT将“简历技能+项目经历”与“岗位JD核心技能”转为1024维向量

2. 相似度计算：计算两个向量的余弦相似度（范围0-1，越接近1匹配度越高）

3. 技能缺口分析：对比简历技能与岗位JD技能，找出缺失的核心技能

#### 核心代码片段：

```python

from sentence_transformers import SentenceTransformer, util
import numpy as np

# 初始化向量模型（int8量化，轻量）
vector_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
vector_model.half()  # 内存优化

def get_text_embedding(text):
    """文本转向量"""
    return vector_model.encode(text, convert_to_tensor=True)

def resume_job_matching(resume_data, job_jd):
    """简历-岗位匹配：返回相似度与技能缺口"""
    # 1. 构建匹配文本
    resume_text = " ".join(resume_data["skills"]) + " " + resume_data["raw_text"][:500]  # 取前500字避免冗余
    job_text = job_jd["core_skills"] + " " + job_jd["job_desc"]
    # 2. 向量化
    resume_vec = get_text_embedding(resume_text)
    job_vec = get_text_embedding(job_text)
    # 3. 余弦相似度计算
    similarity = util.cos_sim(resume_vec, job_vec).item()
    # 4. 技能缺口分析
    job_skills = set(job_jd["core_skills"].split(","))
    resume_skills = set(resume_data["skills"])
    skill_gaps = list(job_skills - resume_skills)
    # 5. 结果返回
    return {
        "similarity": round(similarity, 2),
        "skill_gaps": skill_gaps,
        "match_level": "高" if similarity >= 0.7 else "中" if similarity >= 0.5 else "低"
    }
```

### 3.2.3 实时语音对话模块（核心）

功能：实现“麦克风采集→ASR转写→LLM生成问题→TTS播放”实时闭环，支持候选人打断

#### 实现步骤：

1. 音频采集：用sounddevice实时采集麦克风音频，按3072字节分片（≈0.2秒）

2. 实时ASR：WhisperX流式转写音频分片，过滤静音（VAD），输出候选人文本回答

3. LLM问题生成：基于候选人回答、技能缺口、领域知识缓存，生成精准面试问题

4. 实时TTS：Coqui TTS流式合成问题语音，通过扬声器播放，支持打断（检测候选人音量阈值触发）

5. 线程控制：用多线程分离“音频采集”“ASR转写”“LLM推理”“TTS播放”，避免阻塞

#### 核心代码片段：

```python

import sounddevice as sd
import numpy as np
import whisperx
from TTS.api import TTS
from llama_cpp import Llama
import threading
import queue

# 1. 模型初始化（控内存）
asr_model = whisperx.load_model("base", device="cpu", compute_type="int8", language="zh")
tts_model = TTS(model_name="tts_models/zh-CN/baker/tacotron2-DDC_ph", gpu=False)
llm = Llama(model_path="~/.ollama/models/qwen2:7b-chat-q4_K_M", n_ctx=2048, n_threads=8)

# 2. 队列与状态管理（线程通信）
audio_queue = queue.Queue()  # 音频分片队列
text_queue = queue.Queue()   # 转写文本队列
is_speaking = False         # TTS是否正在播放
interrupt_flag = False      # 打断标记

# 3. 音频采集线程
def audio_capture_thread():
    def callback(indata, frames, time, status):
        global interrupt_flag
        if status:
            return
        # 音量检测：候选人说话音量>0.1触发打断
        volume = np.linalg.norm(indata)
        if volume > 0.1 and is_speaking:
            interrupt_flag = True
            tts_model.stop()  # 停止TTS播放
        audio_queue.put(indata.copy())
    # 启动采集（16000采样率，单声道）
    with sd.InputStream(samplerate=16000, channels=1, callback=callback, blocksize=3072):
        while True:
            sd.sleep(100)

# 4. ASR转写线程
def asr_thread():
    audio_buffer = []
    while True:
        if not audio_queue.empty():
            audio_buffer.append(audio_queue.get())
            # 积累3秒音频（平衡实时性与转写准确率）
            if len(audio_buffer) >= int(16000 / 3072 * 3):
                audio_data = np.concatenate(audio_buffer)
                audio_buffer.clear()
                # 实时转写
                result = asr_model.transcribe(audio_data, language="zh", vad=True)
                if result["text"]:
                    text_queue.put(result["text"])

# 5. LLM+TTS线程
def llm_tts_thread(skill_gaps, domain):
    global is_speaking, interrupt_flag
    # 加载领域知识缓存
    domain_knowledge = load_domain_cache(domain)  # 自定义缓存加载函数
    while True:
        if not text_queue.empty() and not is_speaking:
            candidate_text = text_queue.get()
            # LLM生成面试问题（聚焦技能缺口）
            prompt = f"""基于以下信息生成1个精准面试问题，仅返回问题：
            岗位技能缺口：{skill_gaps}
            领域知识：{domain_knowledge['interview_questions'][:2]}
            候选人回答：{candidate_text}
            """
            llm_output = llm.create_completion(prompt=prompt, max_tokens=50, temperature=0.3)
            question = llm_output["choices"][0]["text"].strip()
            # TTS播放问题
            is_speaking = True
            interrupt_flag = False
            tts_model.tts_to_file(text=question, file_path="temp.wav")
            # 播放音频（支持打断）
            data, fs = sd.read("temp.wav")
            for i in range(0, len(data), 1024):
                if interrupt_flag:
                    sd.stop()
                    break
                sd.play(data[i:i+1024], fs)
                sd.wait()
            is_speaking = False

# 6. 启动实时对话
def start_voice_interview(skill_gaps, domain):
    t1 = threading.Thread(target=audio_capture_thread, daemon=True)
    t2 = threading.Thread(target=asr_thread, daemon=True)
    t3 = threading.Thread(target=llm_tts_thread, args=(skill_gaps, domain), daemon=True)
    t1.start()
    t2.start()
    t3.start()
    print("实时语音面试已启动，按Ctrl+C退出...")
    while True:
        sd.sleep(1000)
```

### 3.2.4 知识补充模块

功能：新领域自动获取知识并缓存，避免依赖LLM API高频调用

#### 实现步骤：

1. 领域检测：从简历/岗位JD中提取领域关键词（如“量子计算”“AI Agent开发”）

2. 缓存检查：查询本地缓存，未命中/过期则触发知识获取

3. 知识获取：优先调用权威开源数据源（如ESCO API、GitHub Topic API），未覆盖则用极简LLM API调用（单领域仅1次）

4. 缓存更新：将获取的结构化知识存入本地缓存，添加时间标签

#### 核心代码片段：

```python

import json
import requests
from datetime import datetime, timedelta

CACHE_PATH = "./cache/domain_knowledge.json"

def load_domain_cache(domain):
    """加载领域知识缓存"""
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if domain in cache:
            # 检查缓存是否过期
            last_update = datetime.strptime(cache[domain]["last_update_time"], "%Y-%m-%d %H:%M:%S")
            expire_time = last_update + timedelta(days=cache[domain]["expire_days"])
            if datetime.now() < expire_time:
                return cache[domain]
    except FileNotFoundError:
        return None
    return None

def fetch_domain_knowledge_from_esco(domain):
    """从ESCO API获取领域知识（权威开源，免费）"""
    url = f"https://ec.europa.eu/esco/api/resource/occupation?label={domain}&language=en"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if "_embedded" in data and "occupation" in data["_embedded"]:
            occ = data["_embedded"]["occupation"][0]
            # 提取核心技能
            skills = [skill["title"] for skill in occ["_links"].get("hasSkill", [])]
            # 提取职责描述（作为评估标准）
            description = occ.get("description", "")
            return {
                "core_skills": skills,
                "interview_questions": [f"请说明{skills[0]}的实操经验？" if skills else "请介绍你的项目经验？"],
                "evaluation_criteria": {"专业能力": description, "逻辑表达": "回答层次清晰，重点突出"}
            }
    return None

def fetch_domain_knowledge(domain):
    """获取领域知识：缓存优先，未命中则调用权威API/LLM"""
    # 1. 先查缓存
    cache_data = load_domain_cache(domain)
    if cache_data:
        return cache_data
    # 2. 调用ESCO API
    esco_data = fetch_domain_knowledge_from_esco(domain)
    if esco_data:
        knowledge = esco_data
    else:
        # 3. 极简LLM API调用（仅1次，获取结构化知识）
        knowledge = minimal_llm_api_call(domain)  # 自定义LLM API调用函数
    # 4. 存入缓存
    save_to_cache(domain, knowledge)
    return knowledge

def save_to_cache(domain, knowledge):
    """保存领域知识到缓存，添加时间标签"""
    cache = {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except FileNotFoundError:
        pass
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cache[domain] = {
        **knowledge,
        "first_fetch_time": current_time,
        "last_update_time": current_time,
        "expire_days": 180  # 新兴领域180天过期
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
```

## 3.3 业务逻辑层：面试流程与评估报告

### 3.3.1 面试流程控制器

功能：统一控制面试启动、中断、结束，管理面试状态（如剩余时间、已问问题、技能缺口覆盖情况）

- 核心状态：面试状态（未开始/进行中/已结束）、剩余时间、已问问题列表、技能缺口覆盖进度

- 核心功能：


    - 启动面试：初始化状态，加载领域知识，启动语音/文本对话模块

    - 中断面试：停止音频采集/播放，保存当前面试记录

    - 结束面试：触发评估报告生成，保存完整面试记录（转写文本+语音录音）

### 3.3.2 评估报告生成器

功能：面试结束后，基于候选人回答、技能缺口、领域评估标准，生成量化评估报告

#### 核心评估维度：

- 专业能力（0-10分）：技能缺口覆盖情况、技术术语准确性、项目实操经验

- 逻辑表达（0-10分）：回答层次、重点突出程度、语言流畅性

- 匹配度总结：综合得分、岗位适配建议、后续提升方向

#### 核心代码片段（简化）：

```python

def generate_evaluation_report(interview_records, skill_gaps, domain_knowledge):
    """生成量化评估报告"""
    # 1. 提取面试数据
    candidate_answers = [record["candidate_text"] for record in interview_records]
    asked_questions = [record["question"] for record in interview_records]
    # 2. 专业能力评分（基于技能缺口覆盖）
    covered_gaps = 0
    for gap in skill_gaps:
        if any(gap in answer for answer in candidate_answers):
            covered_gaps += 1
    professional_score = round((covered_gaps / len(skill_gaps)) * 10) if skill_gaps else 8
    # 3. 逻辑表达评分（基于回答长度与层次）
    logic_score = 0
    for answer in candidate_answers:
        if len(answer) > 50 and ("首先" in answer or "其次" in answer or "最后" in answer):
            logic_score += 1
    logic_score = round((logic_score / len(candidate_answers)) * 10) if candidate_answers else 7
    # 4. 综合总结
    total_score = (professional_score + logic_score) / 2
    suggestion = "建议录用" if total_score >= 8 else "可复试" if total_score >= 6 else "不建议录用"
    # 5. 结构化报告
    return {
        "interview_time": interview_records[0]["time"] if interview_records else "",
        "total_score": round(total_score, 1),
        "professional_score": professional_score,
        "logic_score": logic_score,
        "skill_gap_coverage": f"{covered_gaps}/{len(skill_gaps)}" if skill_gaps else "无缺口",
        "suggestion": suggestion,
        "improvement_directions": [f"补充{gap}相关经验" for gap in skill_gaps[:3]] if skill_gaps else ["无明显短板"],
        "interview_records": interview_records
    }
```

## 3.4 交互层：简易界面实现

适配毕设演示需求，用Streamlit快速搭建轻量界面（无需前端开发），核心功能入口：

- 简历上传：支持PDF/Word上传，点击“解析”生成结构化数据

- 岗位JD录入：文本框输入岗位核心技能与职责，点击“匹配”生成技能缺口

- 面试启动：选择“语音面试”或“文本面试”，点击“启动”开始交互

- 报告查看：面试结束后自动展示量化评估报告，支持下载为PDF

#### 界面核心代码片段（Streamlit）：

```python

import streamlit as st

# 页面配置
st.set_page_config(page_title="本地智能面试系统", page_icon="🎤")
st.title("本地智能面试系统")

# 1. 简历上传与解析
st.subheader("1. 简历上传与解析")
resume_file = st.file_uploader("上传简历（PDF/Word）", type=["pdf", "docx"])
if resume_file and st.button("解析简历"):
    resume_data = parse_resume(resume_file)  # 调用前文解析函数
    st.json(resume_data)
    st.session_state["resume_data"] = resume_data

# 2. 岗位JD录入与匹配
st.subheader("2. 岗位JD匹配")
job_jd = st.text_area("输入岗位JD核心信息（如：核心技能：Python,Django；职责：开发后端接口）")
if job_jd and st.button("生成技能缺口"):
    job_data = {"core_skills": job_jd.split("核心技能：")[1].split("；")[0], "job_desc": job_jd}
    matching_result = resume_job_matching(st.session_state["resume_data"], job_data)
    st.write(f"匹配度：{matching_result['similarity']}（{matching_result['match_level']}）")
    st.write(f"技能缺口：{matching_result['skill_gaps']}")
    st.session_state["matching_result"] = matching_result
    st.session_state["domain"] = st.text_input("输入岗位领域（如：Python后端）")

# 3. 启动面试
st.subheader("3. 启动面试")
interview_type = st.radio("选择面试类型", ["语音面试", "文本面试"])
if st.button("启动面试"):
    if "resume_data" in st.session_state and "matching_result" in st.session_state:
        st.info("面试已启动，请开始交互...")
        # 启动对应面试模块
        if interview_type == "语音面试":
            start_voice_interview(
                st.session_state["matching_result"]["skill_gaps"],
                st.session_state["domain"]
            )
        else:
            start_text_interview(...)  # 文本面试启动函数
    else:
        st.error("请先完成简历解析与岗位匹配！")

# 4. 查看评估报告
if "evaluation_report" in st.session_state:
    st.subheader("4. 评估报告")
    report = st.session_state["evaluation_report"]
    st.write(f"综合得分：{report['total_score']}")
    st.write(f"专业能力得分：{report['professional_score']}")
    st.write(f"逻辑表达得分：{report['logic_score']}")
    st.write(f"录用建议：{report['suggestion']}")
    if st.button("下载报告"):
        save_report_to_pdf(report)  # 自定义报告下载函数
        st.success("报告已下载！")
```

# 四、部署与优化指南

## 4.1 本地部署步骤（16GB MacBook）

1. 环境准备：安装Python 3.8+，配置国内pip源（加速依赖安装）
        `pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple`

2. 安装核心依赖：
        `pip install streamlit whisperx TTS llama-cpp-python sentence-transformers pymupdf python-docx spacy sounddevice soundfile
# 下载Spacy中文模型
python -m spacy download zh_core_web_sm
# 下载WhisperX中文模型
whisperx download --model base --language zh
# 下载Coqui TTS中文模型
tts --model_name tts_models/zh-CN/baker/tacotron2-DDC_ph --download_only
# 安装ollama（管理LLM模型）
brew install ollama && ollama pull qwen2:7b-chat-q4_K_M`

3. 代码部署：将上述模块代码整合为项目目录，结构如下：
        `local-interview-system/
├── main.py          # 主程序（Streamlit界面+流程控制）
├── resume_parser.py # 简历解析模块
├── vector_matching.py # 向量匹配模块
├── voice_interview.py # 语音对话模块
├── knowledge_cache.py # 知识补充模块
├── evaluation.py    # 评估报告模块
└── cache/           # 缓存目录（自动生成）`

4. 启动系统：
        `streamlit run main.py`

## 4.2 内存与速度优化（16GB MacBook专属）

- 模型内存优化：
        

    - 所有模型启用量化（WhisperX int8、Qwen-2 4-bit、Sentence-BERT int8）

    - 启动时预加载模型，避免实时加载耗时与内存波动

    - 关闭后台大内存应用（Chrome多标签、Docker等），预留≥6GB系统内存

- 速度优化：
        

    - M系列Mac：用MLX框架加速LLM推理（替换llama.cpp），速度提升30%+

    - Intel Mac：调整LLM线程数为CPU核心数的一半（避免线程过多导致卡顿）

    - ASR/TTS优化：WhisperX启用VAD过滤静音、Coqui TTS用流式合成，降低延迟

    - 缓存复用：岗位向量、领域知识缓存持久化，避免重复计算/获取

## 4.3 常见问题解决方案

|问题|表现|解决方案|
|---|---|---|
|内存溢出（OOM）|程序崩溃，终端提示“MemoryError”|1. 关闭后台应用；2. 将Qwen-2-7B降级为Qwen-2-3B（4-bit，内存2.5GB）；3. 减小LLM上下文长度（n_ctx=1024）|
|语音对话延迟高|端到端延迟>3秒，交互卡顿|1. 调整ASR音频分片为2秒；2. LLM max_tokens设为30-50；3. M系列用MLX加速LLM|
|简历解析不精准|技能提取缺失、基础信息错误|1. 扩展技能关键词库；2. 优化正则表达式；3. 对特殊格式简历（如表格）添加专门解析逻辑|
|TTS播放无声音|生成temp.wav但无声音输出|1. 检查Mac声音设置；2. 用sounddevice重新安装音频驱动；3. 替换TTS模型为pyttsx3（应急）|
# 五、项目验收标准

## 5.1 功能验收

- 简历解析：支持PDF/Word，结构化提取准确率≥85%（核心技能、基础信息无缺失）

- 向量匹配：相似度计算合理，技能缺口识别准确率≥90%

- 实时对话：语音端到端延迟M系列≤2.2秒、Intel≤3.5秒，支持打断，无明显卡顿

- 知识补充：新领域自动获取知识并缓存，后续无重复调用

- 评估报告：量化评分合理，录用建议符合实际，报告内容完整

## 5.2 性能验收

- 内存占用：全流程运行时内存≤10GB（16GB MacBook无OOM）

- 启动速度：系统启动≤30秒，模型预加载完成

- 稳定性：连续面试30分钟无崩溃，交互流畅

# 六、后续扩展方向（可选）

- 多语言支持：添加英文ASR/TTS模型，适配跨国面试场景

- 语音克隆：集成VITS模型，模拟不同风格面试官声音

- 批量面试：支持多候选人简历批量解析与匹配，生成对比报告

- 云端协同：可选对接云模型API，在本地资源不足时兜底（需添加开关控制）
> （注：文档部分内容可能由 AI 生成）