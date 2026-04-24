from __future__ import annotations

import streamlit as st
import base64
import random
import pandas as pd

from supabase import create_client
from datetime import datetime


import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

from config import load_settings
from utils.pdf_parser import Chapter, extract_chapters_from_pdf

SUPABASE_URL = "https://oslxddarixkoycukusvr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zbHhkZGFyaXhrb3ljdWt1c3ZyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1MDg1NzUsImV4cCI6MjA5MjA4NDU3NX0.kvTDceKAYW_MVHto30I4Qfbm9kipcE_DenP2pW0OmSs"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

import smtplib
from email.mime.text import MIMEText

# ================== EMAIL ==================
def send_otp_email(to_email, otp):
    sender_email = "queforge@gmail.com"
    app_password = "vhgxjbhzhohiykhh"

    msg = MIMEText(f"Dear User , \nYour One-Time Password(OTP) is : {otp} \nPlease use this OTP to complete your login process.\n*Do not share this code with anyone.\nThank you QUEFORGE TEAM")
    msg['Subject'] = "Password Reset OTP"
    msg['From'] = sender_email
    msg['To'] = to_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        st.error(f"Email error: {e}")

# ================== SESSION ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "show_forget" not in st.session_state:
    st.session_state.show_forget = False

if "otp_verified" not in st.session_state:
    st.session_state.otp_verified = False

# ================== PAGE ==================



# ================== MAIN FLOW ==================
if not st.session_state.logged_in:

    st.markdown(
    "<div style='text-align: center;'>",
    unsafe_allow_html=True
    )

    st.image("assets/logo.png", width=700)

    tab1, tab2 = st.tabs(["Log In", "Sign Up"])

    # ================== LOGIN ==================
    with tab1:

        st.header("🔐 Welcome Back!")

        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        login_clicked = st.button("Login")

        forgot_clicked = st.button("Forgot Password") 

        # FORGOT CLICK
        if forgot_clicked:
            st.session_state.show_forget = True

        # LOGIN LOGIC
        if login_clicked:
            username = username.strip().lower()
            password = password.strip()

            # ADMIN LOGIN
            if username == "admin" and password == "7777":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = True
                st.success("Admin login successful")
                st.rerun()

            res = supabase.table("users")\
                .select("*")\
                .eq("username", username)\
                .eq("password", password)\
                .execute()

            if res.data:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

        # ================== FORGOT PASSWORD ==================
        if st.session_state.show_forget:

            st.markdown("---")
            st.markdown("## 🔐 Reset Password")

            email = st.text_input("Enter your email", key="reset_email")

            if st.button("Send OTP"):
                res = supabase.table("users").select("*").eq("email", email).execute()

                if not res.data:
                    st.error("Email not registered")
                else:
                    otp = str(random.randint(100000, 999999))
                    st.session_state.otp = otp
                    st.session_state.reset_email_value = email

                    send_otp_email(email, otp)
                    st.success("OTP sent")

            entered_otp = st.text_input("Enter OTP", key="otp_input")

            if st.button("Verify OTP"):
                if entered_otp == st.session_state.get("otp"):
                    st.session_state.otp_verified = True
                    st.success("OTP Verified")
                else:
                    st.error("Wrong OTP")

            if st.session_state.otp_verified:
                new_pass = st.text_input("New Password", type="password")

                if st.button("Reset Password"):
                    supabase.table("users").update({
                        "password": new_pass
                    }).eq("email", st.session_state.reset_email_value).execute()

                    st.success("Password updated!")

                    st.session_state.show_forget = False
                    st.session_state.otp_verified = False
                    st.session_state.otp = None

    # ================== SIGNUP ==================
    with tab2:

        st.header("📝 Let's Get Started")

        new_user = st.text_input("Username", key="reg_user")
        new_pass = st.text_input("Password", type="password", key="reg_pass")
        email = st.text_input("Email", key="reg_email")

        if st.button("Create Account"):
            new_user = new_user.strip().lower()
            new_pass = new_pass.strip()

            supabase.table("users").insert({
                "username": new_user,
                "password": new_pass,
                "email": email
            }).execute()

            st.success("Account created!")
        st.stop()

# ================== AFTER LOGIN ==================
else:
    st.title("🏠 QUEFORGE DASHBOARD")
    st.success(f"Welcome {st.session_state.username}")

if st.session_state.get("show_analytics") and st.session_state.is_admin:

    st.title("📊 User Analytics Dashboard")

    # ===============================
    # 🔥 1. LOGIN ANALYTICS
    # ===============================
    st.subheader("🔐 Login Analytics")
    
    res = supabase.table("login_logs").select("*").execute()
    data = res.data

    df = pd.DataFrame(data)
    df = df["username"].value_counts().reset_index()
    df.columns = ["User", "Login Count"]

    st.bar_chart(df.set_index("User"))


    # ===============================
    # 🔥 2. ACTIVE USERS (TODAY)
    # ===============================
    st.subheader("🟢 Active Users (Today)")

    today = str(datetime.now().date())

    res = supabase.table("login_logs").select("*").execute()

    data = [d for d in res.data if d["time"].startswith(today)]

    active_users = len(set([d["username"] for d in data]))

    st.metric("Active Users Today", active_users)

    # ===============================
    # 🔥 3. QUESTION GENERATION ANALYTICS
    # ===============================
    st.subheader("📝 Question Generation Analytics")
    
    res = supabase.table("question_logs").select("*").execute()

    data = res.data

    if data and "username" in data[0]:
        df = pd.DataFrame(data)

        df = df["username"].value_counts().reset_index()
        df.columns = ["User", "Questions Generated"]

        st.bar_chart(df.set_index("User"))
    else:
        st.warning("No data found for analytics")

    df.columns = ["User", "Questions Generated"]

    # ===============================
    # 🔥 4. MOST USED TOPICS
    # ===============================
    st.subheader("🔥 Most Used Topics")

    data = res.data

    if data and "topic" in data[0]:
        df = pd.DataFrame(data)

        df = df["topic"].value_counts().reset_index()
        df.columns = ["Topic", "Usage Count"]

        st.bar_chart(df.set_index("Topic"))
    else:
        st.warning("No topic data found")
        df.columns = ["Topic", "Usage Count"]

    st.stop() 

CSS = """
<style>
footer {visibility: hidden;}

html, body, [class*="css"]  {
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
}

.block-container { padding-top: 3.5rem; padding-bottom: 2rem; }


/* 🔥 TOP CENTER IMAGE */
.qb-top-img {
  width: 100%;
  text-align: center;
  margin-bottom: 15px;
}

.qb-top-img img {
  width: 120px;
  max-width: 100%;
  height: auto;
  border-radius: 20px;
  box-shadow: 0 0 150px rgba(255,255,255,10);
}

/* 🔥 HERO RESPONSIVE FIX */
.qb-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;  /* ✅ MOBILE FIX */
  gap: 20px;
}

/* LEFT TEXT */
.qb-hero > div:first-child {
  flex: 1 1 300px;
}

/* RIGHT IMAGE */
.qb-hero img {
  max-width: 100%;
  height: auto;
  width: 250px;
  margin-left: auto;
}

/* 🔥 MOBILE VIEW */
@media (max-width: 768px) {
  .qb-hero {
    flex-direction: column;   /* stack */
    align-items: flex-start;
  }

  .qb-hero img {
    width: 180px;
    margin: 25px auto 0 auto;  /* center image */
  }

  .qb-title {
    font-size: 28px !important;  /* prevent break */
    line-height: 1.2;
  }
}

.qb-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255,255,255,0.04);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.35);
}

.qb-hero-left {
  width: 55%;
}

.qb-hero-right {
  width: 40%;
  text-align: center;
}

.qb-hero-right img {
  max-width: 100%;
  margin-right: -270px;
  border-radius: 50px;
  filter: drop-shadow(0px 25px 45px rgba(300,300,257,7));
}

.qb-title {
  font-size: 40px;
  font-weight: 850;
  margin: 0;
  letter-spacing: -0.02em;
}

.qb-title {
  word-break: normal;
  overflow-wrap: break-word;
}

.qb-sub {
  opacity: 0.8;
  margin-top: 6px;
  font-size: 15px;
}

.qb-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(99,102,241,0.18);
  border: 5px solid rgba(99,102,241,0.35);
  font-size: 12px;
  margin-right: 8px;
  margin-bottom: 6px;
}

.qb-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 16px 16px;
}

.qb-step {
  font-size: 17px;
  font-weight: 750;
  margin-bottom: 8px;
}

.qb-hero {
  padding: 20px;
}
.qb-top-img img {
  transition: transform 0.3s ease;
}

.qb-top-img img:hover {
  transform: scale(1.05);
}

.qb-muted { opacity: 0.75; }
</style>
"""

# SIDEBAR
st.sidebar.title("👤 ADMIN PANEL")

if st.session_state.is_admin:
    st.sidebar.success(" ADMIN MODE")
else:
    st.sidebar.info(f"USER : {st.session_state.username}")

if st.session_state.is_admin:
    if st.sidebar.button("View Login History"):
        res = supabase.table("login_logs").select("*").execute()
        data = res.data

        st.subheader("📊 Login History")
        st.table(data)
        

if st.session_state.is_admin:
    if st.sidebar.button("📊 Analytics Dashboard"):
        st.session_state.show_analytics = True

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()


#  ORIGINAL APP START 
st.set_page_config(layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


def load_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

img_base64 = load_image_base64("assets/ai_hero.png")  

from collections import Counter

def extract_topics_with_gpt(client, model, chapter_text):
    prompt = f"""
Extract 7 important topics from the following chapter.

Chapter Content:
{chapter_text[:4000]}

Instructions:
- Return only topic names
- Each topic on a new line
- No numbering
- No explanation
"""

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}]
            }
        ]
    )

    raw = response.output_text.strip()

    # clean topics
    topics = [t.strip("-•1234567890. ") for t in raw.split("\n") if t.strip()]

    return topics if topics else ["General"]

def extract_topics_from_text(text, top_n=7):
    # simple keyword extraction (frequency based)

    # text clean
    text = text.lower()
    text = re.sub(r'[^a-z\s]', ' ', text)

    words = text.split()

    # common useless words remove
    stopwords = set([
        "the", "is", "and", "of", "to", "in", "a", "for", "on", "with",
        "as", "by", "an", "be", "this", "that", "are", "or", "from"
    ])

    words = [w for w in words if w not in stopwords and len(w) > 4]

    freq = Counter(words)

    # top keywords
    topics = [word.capitalize() for word, _ in freq.most_common(top_n)]

    return topics if topics else ["General"]

def load_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

if "chapters" not in st.session_state:
    st.session_state.chapters = []

if "has_toc" not in st.session_state:
    st.session_state.has_toc = False

@st.cache_data(show_spinner=False)
def detect_chapters_cached(file_bytes, heading_patterns, min_chars):
    chapters, has_toc = extract_chapters_from_pdf(
        file_bytes=file_bytes,
        heading_patterns=heading_patterns,
        min_chapter_chars=min_chars
    )
    return chapters, has_toc


# ============================================================
# Page Config + Styles
# ============================================================

st.set_page_config(
    page_title="AI QUESTION BANK GENERATOR",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# Settings
# ============================================================

settings = load_settings()

ENV_KEY = os.getenv("OPENAI_API_KEY")
if ENV_KEY:
    settings["openai"]["api_key"] = ENV_KEY

from openai import OpenAI

client = OpenAI(api_key=settings["openai"]["api_key"])
model = settings["openai"]["model"]

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
if not OPENAI_KEY:
    OPENAI_KEY = str(settings.get("openai", {}).get("api_key", "")).strip()

MODEL = str(settings.get("openai", {}).get("model", "gpt-4o-mini"))
MAX_TOKENS = int(settings.get("openai", {}).get("max_output_tokens", 4096))

HEADING_PATTERNS = settings.get("chapter_split", {}).get("heading_patterns", [])
MIN_CHAPTER_CHARS = int(settings.get("chapter_split", {}).get("min_chapter_chars", 1200))

DEFAULT_Q = int(settings.get("generation", {}).get("default_questions_per_chapter", 8))
MIN_Q = int(settings.get("generation", {}).get("min_questions_per_chapter", 5))
MAX_Q = int(settings.get("generation", {}).get("max_questions_per_chapter", 20))


# ============================================================
# Session State
# ============================================================

def init_state() -> None:
    if "pdf_bytes" not in st.session_state:
        st.session_state.pdf_bytes = None
    if "pdf_name" not in st.session_state:
        st.session_state.pdf_name = None
    if "chapters" not in st.session_state:
        st.session_state.chapters = []
    if "has_toc" not in st.session_state:
        st.session_state.has_toc = False
    if "selected_titles" not in st.session_state:
        st.session_state.selected_titles = []
    if "chat" not in st.session_state:
        st.session_state.chat = []  # list of dicts: {role, content}
    if "topic" not in st.session_state:
        st.session_state.topic = ""
    if "step" not in st.session_state:
        st.session_state.step = 1  # 1 or 2


init_state()


# ============================================================
# Helpers
# ============================================================

def clean_title(title: str) -> str:
    """Make chapter titles shorter & readable."""
    t = (title or "").strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace("\u00a0", " ")
    # hard cut for ugly long titles
    if len(t) > 70:
        t = t[:70].rstrip() + "..."
    return t


def get_selected_chapters() -> List[Chapter]:
    title_set = set(st.session_state.selected_titles)
    return [c for c in st.session_state.chapters if c.title in title_set]

def format_mcq(text):
    import re

    # Questions ke beech extra space
    text = re.sub(r'(Q\d+\.)', r'\n\n\n\1', text)

    # Options separate line me
    text = re.sub(r'(A\.)', r'\nA.', text)
    text = re.sub(r'(B\.)', r'\nB.', text)
    text = re.sub(r'(C\.)', r'\nC.', text)
    text = re.sub(r'(D\.)', r'\nD.', text)

    # Options ke baad thoda gap
    text = re.sub(r'(D\..+)', r'\1\n', text)

    # Clean excessive newlines
    text = re.sub(r'\n{3,}', '\n\n\n', text)

    return text.strip()


def push_chat(role: str, content: str) -> None:
    st.session_state.chat.append({"role": role, "content": content})

def build_questions_prompt(
    chapter_text: str,
    chapter_title: str,
    topic: str,
    num_questions: int,
    mode
) -> str:

    if mode == "MCQ":
        return f"""
You are an expert exam question setter.

Generate EXACTLY {num_questions} MCQs.

Topic:
{topic}

Chapter:
{chapter_title}

Content:
{chapter_text}

Rules:
1) Each question must have 4 options (A, B, C, D)
2) Only ONE correct answer
3) Questions must be tricky and exam-oriented
4) No duplicates
5) Each option MUST be on a NEW LINE
6) DO NOT merge question and options in one line
7) Format must be clean and readable

IMPORTANT:
- Every question MUST start on a new line with Q1, Q2, etc.
- Every option MUST be on a separate line
- DO NOT write multiple questions in one paragraph

Output format:

Q1. Question
A. Option
B. Option
C. Option
D. Option
Answer: Correct option

Q2. ...
""".strip()

    else:
        return f"""
You are an expert exam question setter.

Generate EXACTLY {num_questions} questions.

Topic:
{topic}

Chapter:
{chapter_title}

Content:
{chapter_text}

Rules:
1) Questions must be based ONLY on the chapter content.
2) Make questions refined, exam-oriented, and viva-friendly.
3) Avoid duplicates.
4) Output format must be ONLY a numbered list like:
   1. ...
   2. ...
   ...
No extra text. No headings. No markdown.
""".strip()

def build_answer_prompt(
    chapter_text: str,
    chapter_title: str,
    topic: str,
    questions_text: str,
    user_request: str,
) -> str:
    # Only answer when user asks.
    return f"""
You are a helpful tutor.

You have the chapter content below and a list of questions already generated.

Chapter title:
{chapter_title}

Topic/Focus:
{topic}

Chapter content:
{chapter_text}

Generated questions:
{questions_text}

User request:
{user_request}

Rules:
1) Answer ONLY what the user asked (example: Q3 only, or Q1-Q5).
2) Keep answers short and exam-friendly.
3) Use ONLY chapter content.
4) Do NOT invent anything outside the chapter.
""".strip()


# ============================================================
# Header
# ============================================================

st.markdown(f"""
<div class="qb-hero">

  <div class="qb-top-img">
    <img src="data:image/png;base64,{img_base64}" />
  </div>
     
  <h1 class="qb-title">AI QUESTION BANK GENERATOR</h1>

  <div>
    <span class="qb-pill">📘 AI NLP-BASED</span>
    <span class="qb-pill">🤖 CHATBOT BASED UI</span>
  </div>

</div>

""", unsafe_allow_html=True)

st.write("")


# ============================================================
# Top Controls
# ============================================================

cA, cB = st.columns([0.5, 0.5])

with cA:
    if st.button("🧹 Clear Chat", use_container_width=True):
        st.session_state.chat = []
        st.rerun()

with cB:
    if st.button("📄 New PDF", use_container_width=True):
        st.session_state.pdf_bytes = None
        st.session_state.pdf_name = None
        st.session_state.chapters = []
        st.session_state.has_toc = False
        st.session_state.selected_titles = []
        st.session_state.topic = ""
        st.session_state.step = 1
        st.session_state.chat = []
        st.rerun()


st.write("")


# ============================================================
# Step 1 — Upload + Detect Chapters
# ============================================================

if st.session_state.step == 1:
    st.markdown('<div class="qb-step">Step 1 — Upload PDF </div>', unsafe_allow_html=True)
    st.markdown('<div class="qb-step">Step 2 — Detect Chapters</div>', unsafe_allow_html=True)
    st.markdown('<div class="qb-step">Step 3 — Select Chapters</div>', unsafe_allow_html=True)
    st.markdown('<div class="qb-step">Step 4 — Any Specific Topic / Focus </div>', unsafe_allow_html=True)
    st.markdown('<div class="qb-step">Step 5 — Choose No.of Questions </div>', unsafe_allow_html=True)
    st.markdown('<div class="qb-step">Step 6 — Ask Answers (Integrated Chatbot) </div>', unsafe_allow_html=True)
    
    uploaded = st.file_uploader("UPLOAD PDF", type=["pdf"], accept_multiple_files=False)

    if uploaded is not None:
       st.session_state.pdf_bytes = uploaded.getvalue()
       st.session_state.pdf_name = uploaded.name
       st.success(f"Uploaded: {uploaded.name}")

    st.caption("⚡ Chapter detection is cached.")

detect = st.button(
    "🔎 Detect Chapters",
    type="primary",
    use_container_width=True,
    disabled=st.session_state.pdf_bytes is None
)

if detect:

    if not st.session_state.pdf_bytes:
        st.error("Please upload a PDF first.")
        st.stop()

    with st.spinner("Detecting chapters..."):

        chapters, has_toc = detect_chapters_cached(
            st.session_state.pdf_bytes,
            settings["chapter_split"]["heading_patterns"],
            settings["chapter_split"]["min_chapter_chars"]
        )

    st.session_state.chapters = chapters
    st.session_state.has_toc = has_toc

    if chapters:
                st.session_state.selected_titles = [c.title for c in chapters]
                st.success(f"Detected {len(chapters)} chapters.")
                if has_toc:
                    st.caption("Detected using Table of Contents.")
                else:
                    st.caption("Detected using fallback split (no TOC found).")

                st.session_state.step = 2
                st.rerun()
    else:
                st.error("No chapters detected. Try another PDF.")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# Step 2 — Select + Chat Generate
# ============================================================

elif st.session_state.step == 2:
    left, right = st.columns([0.5, 0.5], gap="large")

    # -------------------------
    # Left: Chapter selection
    # -------------------------
    with left:
        st.markdown('<div class="qb-step">Step 3 — Select Chapters </div>', unsafe_allow_html=True)

        st.caption(f"PDF: {st.session_state.pdf_name}")
        st.success(f"Chapters detected: {len(st.session_state.chapters)}")


        titles_all = [c.title for c in st.session_state.chapters]
        titles_filtered = titles_all

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Select All", use_container_width=True):
                st.session_state.selected_titles = titles_all
                st.rerun()
        with b2:
            if st.button("Deselect All", use_container_width=True):
                st.session_state.selected_titles = []
                st.rerun()

        # Show cleaned titles but keep original mapping
        title_map = {clean_title(t): t for t in titles_filtered}
        cleaned_list = list(title_map.keys())

        cleaned_selected = [clean_title(t) for t in st.session_state.selected_titles if t in titles_filtered]

        chosen_clean = st.multiselect(
            "Choose Chapters",
            options=cleaned_list,
            default=cleaned_selected,
        )

        # map back to original titles
        st.session_state.selected_titles = [title_map[c] for c in chosen_clean if c in title_map]

        st.caption(f"Selected: {len(st.session_state.selected_titles)}")

        st.write("")

        st.markdown('<div class="qb-step">Step 4 — Any Specific Topic / Focus </div>', unsafe_allow_html=True)

        selected_chapter_obj = next(
            (c for c in st.session_state.chapters if c.title in st.session_state.selected_titles),
            None
        )

        if selected_chapter_obj:

        
            if "topics_cache" not in st.session_state:
                st.session_state.topics_cache = {}

            key = selected_chapter_obj.title

            if key not in st.session_state.topics_cache:
                with st.spinner("Extracting topics ..."):
                    topics = extract_topics_with_gpt(
                        client,
                        settings["openai"]["model"],
                        selected_chapter_obj.text
                    )
                    st.session_state.topics_cache[key] = topics

            topics = st.session_state.topics_cache[key]

            selected_topic = st.selectbox(
                "Select Topic",
                topics,
                key=f"topic_{selected_chapter_obj.title}"
            )
                    
            custom_topic = st.text_input("Or type your own topic")

            topic = custom_topic if custom_topic else selected_topic

            st.session_state["topic"] = topic
        
        st.write("")

        st.markdown('<div class="qb-step">Step 5 — Choose No.of Questions </div>', unsafe_allow_html=True)

        num_q = st.number_input(
            "Questions per chapter",
            min_value=MIN_Q,
            max_value=MAX_Q,
            value=DEFAULT_Q,
            step=1,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------
    # Right: Chat area
    # -------------------------
    with right:

        st.markdown('<div class="qb-step">Step 6 — Ask Answers (Integrated Chatbot) </div>', unsafe_allow_html=True)


        # Render chat
        for msg in st.session_state.chat:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(msg["content"].replace("\n", "  \n"))

        st.write("")


        if "generated_questions" in st.session_state:

            text = st.session_state.generated_questions
 
            questions = [q.strip() for q in text.split("\n") if q.strip() != ""]

            df = pd.DataFrame({
                "Questions": questions
            })

            csv = df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇️ Download Questions as CSV",
                data=csv,
                file_name=f"{st.session_state.topic}_questions.csv",
                mime="text/csv"
            )

        # STEP 1: Select Mode (ADD HERE)
        mode = st.radio(
           "Select Question Type",
           ["Descriptive", "MCQ"],
           horizontal=True
        )

        # Main action buttons
        g1, g2 = st.columns([0.6, 0.4])
        with g1:
            generate_btn = st.button("🚀 Generate Questions", type="primary", use_container_width=True)
        with g2:
            back_btn = st.button("← Back to Home Page", use_container_width=True)

        if back_btn:
            st.session_state.step = 1
            st.rerun()

        # Chat input
        
        show_answers = st.toggle("Show Answers", key="show_answers_toggle")
        user_msg = st.chat_input("Ask: Answer Q3 / Explain Q2 / Give answers for Q1-Q5 ...")

        # Generate questions
        if generate_btn:
            if not OPENAI_KEY:
                st.error("OPENAI_API_KEY missing.")
                st.stop()

            if mode == "MCQ":
                user_template = settings["prompts"]["mcq_template"]
            else:
                user_template = settings["prompts"]["user_template"]
            
            if not st.session_state.selected_titles:
                st.error("Select at least one chapter.")
                st.stop()

            if not st.session_state.topic.strip():
                st.error("Write a topic/focus.")
                st.stop()

            selected_chapters = get_selected_chapters()
            client = OpenAI(api_key=OPENAI_KEY)

            push_chat(
                "user",
                f"Generate {int(num_q)} refined questions from selected chapters.\n\nTopic: {st.session_state.topic}",
            )

            with st.spinner("Generating questions..."):
                all_questions_text = []
                for idx, ch in enumerate(selected_chapters, start=1):
                    prompt = build_questions_prompt(
                        chapter_text=ch.text,
                        chapter_title=clean_title(ch.title),
                        topic=st.session_state.topic,
                        num_questions=int(num_q),
                        mode=mode 
                    )

                    # Use Responses API (same as your generator)
                    resp = client.responses.create(
                        model=MODEL,
                        max_output_tokens=MAX_TOKENS,
                        input=[
                            {"role": "system", "content": [{"type": "input_text", "text": "You are a strict exam question generator."}]},
                            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
                        ],
                    )

                    supabase.table("question_logs").insert({
                        "username": st.session_state.username,
                        "topic": st.session_state.topic,
                        "timestamp": str(datetime.now())
                    }).execute()

                    text = (resp.output_text or "").strip()
                    
                    if not text:
                        text = "No questions generated."
                    
                    import re
    
                    if mode == "MCQ":

                        text = re.sub(r'(Q\d+\.)', r'\n\1', text)

                        text = re.sub(r'\s([A-D]\.)', r'\n\1', text)

                        text = re.sub(r'\s(Answer:)', r'\n\1', text)

                        text = re.sub(r'\n+', '\n', text).strip()

                        if not show_answers:
                            text = re.sub(r'Answer:\s*[A-D1-4]', '', text, flags=re.IGNORECASE)

                    formatted = format_mcq(text)

                    all_questions_text.append(f"\n📌 {clean_title(ch.title)}\n\n{formatted}\n")

                final_text = "\n\n".join(all_questions_text)

                final_text = format_mcq(final_text)

                push_chat("assistant", final_text)
                st.session_state.generated_questions = final_text
                st.rerun()

        # Answer on demand
        if user_msg:
            if not OPENAI_KEY:
                st.error("OPENAI_API_KEY missing.")
                st.stop()

            # Find last assistant questions block
            last_questions = ""
            for msg in reversed(st.session_state.chat):
                if msg["role"] == "assistant":
                    last_questions = msg["content"]
                    break

            if not last_questions:
                push_chat("assistant", "Please generate questions first, then ask for answers like: Answer Q3")
                st.rerun()

            selected_chapters = get_selected_chapters()
            combined_text = "\n\n".join([c.text for c in selected_chapters])

            client = OpenAI(api_key=OPENAI_KEY)

            push_chat("user", user_msg)

            with st.spinner("Answering..."):
                ans_prompt = build_answer_prompt(
                    chapter_text=combined_text,
                    chapter_title="Selected Chapters",
                    topic=st.session_state.topic,
                    questions_text=last_questions,
                    user_request=user_msg,
                )

                resp = client.responses.create(
                    model=MODEL,
                    max_output_tokens=min(MAX_TOKENS, 4096),
                    input=[
                        {"role": "system", "content": [{"type": "input_text", "text": "You answer only what the user asks, based strictly on provided text."}]},
                        {"role": "user", "content": [{"type": "input_text", "text": ans_prompt}]},
                    ],
                )

                answer_text = (resp.output_text or "").strip()
                if not answer_text:
                    answer_text = "Sorry, I could not generate an answer."

            push_chat("assistant", answer_text)
            st.rerun()
