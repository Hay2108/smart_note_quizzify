"""
Smart Note & Quizzify — Trợ lý Học tập Tốc độ
================================================
Giao diện Streamlit theo triết lý Google Material Design:
  • Bề mặt vật lý số (Digital surfaces) với hệ thống Elevation 3 tầng.
  • Chuyển động phản hồi vật lý (cubic-bezier(0.4, 0, 0.2, 1)).
  • Bảng màu Google Material + phông Plus Jakarta Sans.
  • Bố cục lưới thích ứng theo bội số 8px.

Kiến trúc 6 màn hình wireframe:
  Trang "Tạo mới"  : Màn 1 (Tải lên) + Màn 2 (Xem & sửa văn bản)
                     → Màn 3 (Kết quả) → Màn 4 (Ôn flashcard) / Màn 5 (Trắc nghiệm)
  Trang "Thư viện" : Màn 6 (Thư viện) → "Mở" nạp thẳng Màn 3 (FR10)

Chạy: streamlit run app.py
"""

import copy
import html
import json
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

# ==========================================================
# 0. CẤU HÌNH TRANG
# ==========================================================
st.set_page_config(
    page_title="Smart Note & Quizzify · Trợ lý Học tập Tốc độ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Smart Note & Quizzify — biến ảnh bảng/slide và file ghi âm bài giảng "
                 "thành tóm tắt, flashcard và trắc nghiệm ôn tập bằng AI."
    },
)

# ==========================================================
# 1. MATERIAL DESIGN SYSTEM (CSS INJECTION)
#    Tách bạch toàn bộ design tokens + component styles ở đầu file.
# ==========================================================
MATERIAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400..700,0..1,0&display=swap');

/* ---------- 1.1 DESIGN TOKENS ---------- */
:root {
  /* Primary · Google Blue */
  --md-primary: #1A73E8;
  --md-primary-hover: #1557B0;
  --md-primary-tint: #E8F0FE;
  --md-on-primary-tint: #0B57D0;
  /* Secondary / Accent */
  --md-indigo: #6366F1;
  --md-indigo-hover: #4F46E5;
  --md-indigo-tint: #EEF0FF;
  --md-amber: #F59E0B;
  --md-amber-ink: #B45309;
  --md-amber-tint: #FEF3C7;
  /* Status */
  --md-success: #1E8E3E;
  --md-success-hover: #137333;
  --md-success-tint: #E6F4EA;
  --md-error: #D93025;
  --md-error-hover: #B3261E;
  --md-error-tint: #FCE8E6;
  /* Text & outline */
  --md-text: #1F2937;
  --md-text-2: #5F6368;
  --md-text-3: #80868B;
  --md-outline: #DADCE0;
  --md-outline-soft: #E8EAED;
  /* Surfaces */
  --md-bg: #F4F6F9;
  --md-surface: #FFFFFF;
  --md-surface-dim: #F8FAFC;
  /* Elevation */
  --md-elev-1: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
  --md-elev-2: 0 4px 12px rgba(26,115,232,0.15), 0 2px 4px rgba(0,0,0,0.12);
  --md-elev-3: 0 10px 20px rgba(0,0,0,0.10), 0 6px 6px rgba(0,0,0,0.08);
  /* Motion */
  --md-ease: cubic-bezier(0.4, 0, 0.2, 1);
  --md-motion: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  /* Shape (bội số 8px) */
  --md-r-sm: 8px;
  --md-r-md: 12px;
  --md-r-lg: 16px;
  --md-r-xl: 24px;
  --md-r-full: 999px;
}

/* ---------- 1.2 NỀN & TYPOGRAPHY ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stSidebar"], [data-testid="stMarkdownContainer"],
button, input, textarea, select, label {
  font-family: 'Plus Jakarta Sans', 'Roboto', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stApp, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(900px 360px at 85% -80px, rgba(26,115,232,0.10), transparent 70%),
    radial-gradient(700px 300px at -10% 10%, rgba(99,102,241,0.06), transparent 70%),
    var(--md-bg);
  color: var(--md-text);
}
[data-testid="stHeader"] {
  background: rgba(244,246,249,0.72);
  backdrop-filter: saturate(180%) blur(12px);
  -webkit-backdrop-filter: saturate(180%) blur(12px);
}
[data-testid="stDecoration"], footer { display: none !important; }
[data-testid="stHeaderActionElements"] { display: none !important; }

.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 1120px !important;
  padding: 64px 32px 64px !important;
  margin: 0 auto;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li { color: var(--md-text); line-height: 1.65; }
[data-testid="stCaptionContainer"], .stCaption { color: var(--md-text-2) !important; }
h1, h2, h3, h4 { color: var(--md-text); letter-spacing: -0.01em; }
hr { border-color: var(--md-outline-soft) !important; margin: 24px 0 !important; }

/* Material Symbols dùng trong HTML tuỳ biến */
.msr {
  font-family: 'Material Symbols Rounded';
  font-weight: normal; font-style: normal;
  font-size: 20px; line-height: 1;
  display: inline-block; vertical-align: middle;
  letter-spacing: normal; text-transform: none; white-space: nowrap;
  -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga';
  -webkit-font-smoothing: antialiased;
  font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;
}

/* ---------- 1.3 ELEVATED CARDS · st.container(border=True, key="card_*") ---------- */
[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlock"][class*="st-key-card"] {
  background: var(--md-surface) !important;
  border: none !important;
  border-radius: var(--md-r-lg) !important;
  box-shadow: var(--md-elev-1);
  padding: 24px !important;
  transition: var(--md-motion);
}
[data-testid="stVerticalBlockBorderWrapper"]:hover,
div[data-testid="stVerticalBlock"][class*="st-key-card"]:hover {
  box-shadow: var(--md-elev-2);
}
/* Thẻ tương tác (Thư viện / preview) — nổi lên vật lý khi hover */
div[data-testid="stVerticalBlock"][class*="st-key-card_lib_"]:hover,
div[data-testid="stVerticalBlock"][class*="st-key-card_stat"]:hover {
  transform: translateY(-2px);
}
div[data-testid="stVerticalBlock"][class*="st-key-card_lib_"] { height: 100%; }

/* ---------- 1.4 MATERIAL BUTTONS ---------- */
.stButton > button,
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-tertiary"] {
  font-family: inherit;
  font-weight: 600;
  letter-spacing: 0.01em;
  min-height: 44px;
  padding: 8px 24px;
  border-radius: var(--md-r-full) !important;
  transition: var(--md-motion) !important;
  will-change: transform, box-shadow;
}
.stButton > button p { font-weight: 600 !important; color: inherit !important; font-size: 0.95rem; }

/* Filled (Primary) */
button[data-testid="stBaseButton-primary"] {
  background: var(--md-primary) !important;
  border: 1px solid var(--md-primary) !important;
  color: #FFFFFF !important;
  box-shadow: 0 1px 2px rgba(60,64,67,0.30), 0 1px 3px 1px rgba(60,64,67,0.15);
}
button[data-testid="stBaseButton-primary"]:hover {
  background: var(--md-primary-hover) !important;
  border-color: var(--md-primary-hover) !important;
  box-shadow: var(--md-elev-2);
  transform: translateY(-1px);
}
/* Outlined (Secondary) */
button[data-testid="stBaseButton-secondary"] {
  background: var(--md-surface) !important;
  border: 1px solid var(--md-outline) !important;
  color: var(--md-primary) !important;
}
button[data-testid="stBaseButton-secondary"]:hover {
  background: var(--md-primary-tint) !important;
  border-color: var(--md-primary) !important;
  color: var(--md-primary-hover) !important;
  box-shadow: var(--md-elev-2);
  transform: translateY(-1px);
}
/* Text (Tertiary) */
button[data-testid="stBaseButton-tertiary"] {
  background: transparent !important;
  border: none !important;
  color: var(--md-primary) !important;
}
button[data-testid="stBaseButton-tertiary"]:hover {
  background: var(--md-primary-tint) !important;
  transform: translateY(-1px);
}
/* Tactile realism — nhấn xuống lún vào bề mặt */
.stButton > button:active,
button[data-testid^="stBaseButton-"]:active {
  transform: scale(0.98) !important;
  box-shadow: var(--md-elev-1) !important;
}
.stButton > button:focus-visible {
  outline: 3px solid rgba(26,115,232,0.35) !important;
  outline-offset: 2px;
}
.stButton > button:disabled {
  background: #F1F3F4 !important; border-color: #F1F3F4 !important;
  color: #9AA0A6 !important; box-shadow: none !important; transform: none !important;
}

/* Biến thể nút theo ngữ cảnh (bọc trong st.container(key="btn_*")) */
[class*="st-key-btn_success"] button {
  background: var(--md-success) !important; border-color: var(--md-success) !important; color: #fff !important;
}
[class*="st-key-btn_success"] button:hover {
  background: var(--md-success-hover) !important; border-color: var(--md-success-hover) !important;
  box-shadow: 0 4px 12px rgba(30,142,62,0.22), 0 2px 4px rgba(0,0,0,0.12) !important;
}
[class*="st-key-btn_indigo"] button {
  background: var(--md-indigo) !important; border-color: var(--md-indigo) !important; color: #fff !important;
}
[class*="st-key-btn_indigo"] button:hover {
  background: var(--md-indigo-hover) !important; border-color: var(--md-indigo-hover) !important;
  box-shadow: 0 4px 12px rgba(99,102,241,0.25), 0 2px 4px rgba(0,0,0,0.12) !important;
}
[class*="st-key-btn_outline_error"] button {
  background: #fff !important; border: 1px solid var(--md-outline) !important; color: var(--md-error) !important;
}
[class*="st-key-btn_outline_error"] button:hover {
  background: var(--md-error-tint) !important; border-color: var(--md-error) !important;
  box-shadow: 0 4px 12px rgba(217,48,37,0.15), 0 2px 4px rgba(0,0,0,0.10) !important;
}
[class*="st-key-btn_tonal"] button {
  background: var(--md-primary-tint) !important; border: 1px solid transparent !important;
  color: var(--md-on-primary-tint) !important;
}
[class*="st-key-btn_tonal"] button:hover {
  background: #D3E3FD !important; box-shadow: var(--md-elev-2) !important;
}
[class*="st-key-btn_retry"] button {
  background: var(--md-error) !important; border-color: var(--md-error) !important; color: #fff !important;
}
[class*="st-key-btn_retry"] button:hover {
  background: var(--md-error-hover) !important; border-color: var(--md-error-hover) !important;
  box-shadow: 0 4px 12px rgba(217,48,37,0.22), 0 2px 4px rgba(0,0,0,0.12) !important;
}
[class*="st-key-btn_lg"] button { min-height: 56px; font-size: 1rem; }
[class*="st-key-btn_lg"] button p { font-size: 1rem !important; }

/* ---------- 1.5 SIDEBAR · MATERIAL NAVIGATION DRAWER ---------- */
[data-testid="stSidebar"] {
  background: var(--md-surface) !important;
  border-right: 1px solid var(--md-outline-soft);
  box-shadow: 1px 0 3px rgba(0,0,0,0.04);
}
[data-testid="stSidebarUserContent"] { padding: 8px 16px 32px; }
.st-key-nav_drawer { gap: 4px !important; }
.st-key-nav_drawer button {
  justify-content: flex-start !important;
  width: 100%;
  min-height: 52px !important;
  padding: 0 24px !important;
  box-shadow: none !important;
}
.st-key-nav_drawer button > div { justify-content: flex-start !important; gap: 12px; }
.st-key-nav_drawer button p { font-size: 0.95rem !important; }
.st-key-nav_drawer button[data-testid="stBaseButton-primary"] {
  background: var(--md-primary-tint) !important;
  border: 1px solid transparent !important;
  color: var(--md-on-primary-tint) !important;
}
.st-key-nav_drawer button[data-testid="stBaseButton-primary"] p { font-weight: 700 !important; }
.st-key-nav_drawer button[data-testid="stBaseButton-tertiary"] { color: #3C4043 !important; }
.st-key-nav_drawer button[data-testid="stBaseButton-tertiary"]:hover {
  background: #F1F3F4 !important; transform: none;
}
.md-brand { display: flex; align-items: center; gap: 12px; padding: 8px 8px 16px; }
.md-brand-logo {
  width: 44px; height: 44px; border-radius: 14px; flex-shrink: 0;
  display: grid; place-items: center; color: #fff;
  background: linear-gradient(135deg, #1A73E8 0%, #6366F1 100%);
  box-shadow: 0 4px 12px rgba(26,115,232,0.35);
}
.md-brand-logo .msr { font-size: 26px; }
.md-brand-name { font-weight: 800; font-size: 1.05rem; color: var(--md-text); line-height: 1.2; }
.md-brand-sub { font-size: 0.78rem; color: var(--md-text-2); font-weight: 500; }
.md-nav-label {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--md-text-3); padding: 16px 8px 8px;
}
.md-side-card {
  background: var(--md-surface-dim); border: 1px solid var(--md-outline-soft);
  border-radius: var(--md-r-lg); padding: 16px; margin-top: 8px;
}
.md-side-card .t { font-size: 0.72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--md-text-3); }
.md-side-card .v { font-size: 0.9rem; font-weight: 700; color: var(--md-text); margin-top: 4px; line-height: 1.4; }
.md-side-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
.md-side-stat { background: #fff; border-radius: var(--md-r-md); padding: 8px 12px; box-shadow: var(--md-elev-1); }
.md-side-stat b { display: block; font-size: 1.15rem; color: var(--md-primary); }
.md-side-stat small { color: var(--md-text-2); font-size: 0.72rem; font-weight: 600; }

/* ---------- 1.6 EXPANDER ---------- */
[data-testid="stExpander"] details {
  background: var(--md-surface);
  border: none !important;
  border-radius: var(--md-r-md) !important;
  box-shadow: var(--md-elev-1);
  overflow: hidden;
  transition: var(--md-motion);
}
[data-testid="stExpander"] details:hover { box-shadow: var(--md-elev-2); }
[data-testid="stExpander"] summary {
  padding: 16px !important; font-weight: 600; transition: var(--md-motion);
}
[data-testid="stExpander"] summary:hover { background: var(--md-surface-dim); color: var(--md-primary); }
[data-testid="stExpander"] summary p { font-weight: 600 !important; }
[data-testid="stExpanderDetails"] { padding: 0 16px 16px !important; }

/* ---------- 1.7 FILE UPLOADER · bề mặt tiếp nhận vật lý ---------- */
[data-testid="stFileUploader"] { transition: var(--md-motion); }
[data-testid="stFileUploader"] > label p { font-weight: 600 !important; }
[data-testid="stFileUploaderDropzone"] {
  border: 2px dashed var(--md-primary) !important;
  background: #F8FBFF !important;
  border-radius: var(--md-r-lg) !important;
  padding: 32px 24px !important;
  min-height: 136px;
  transition: var(--md-motion) !important;
  cursor: pointer;
}
[data-testid="stFileUploaderDropzone"]:hover {
  background: var(--md-primary-tint) !important;
  border-color: var(--md-primary-hover) !important;
  box-shadow: var(--md-elev-2);
  transform: translateY(-1px);
}
[data-testid="stFileUploaderDropzoneInstructions"] * { font-size: 0 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] svg { width: 0; height: 0; }
[data-testid="stFileUploaderDropzoneInstructions"]::before {
  content: "Kéo thả file vào đây";
  display: block; font-size: 1rem; font-weight: 700; color: var(--md-text);
}
[data-testid="stFileUploaderDropzoneInstructions"]::after {
  content: "JPG · PNG · WEBP · PDF · MP3 · WAV · M4A  —  tối đa 25MB";
  display: block; font-size: 0.82rem; font-weight: 500; color: var(--md-text-2); margin-top: 4px;
}
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"] {
  border-color: var(--md-primary) !important;
}
[data-testid="stFileUploaderFile"] {
  background: var(--md-surface); border-radius: var(--md-r-md);
  box-shadow: var(--md-elev-1); padding: 8px 12px;
}

/* ---------- 1.8 INPUTS (text_input / selectbox / text_area) ---------- */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
  border-radius: var(--md-r-md) !important;
  background: var(--md-surface) !important;
  transition: var(--md-motion);
}
[data-baseweb="input"]:hover, [data-baseweb="select"] > div:hover, [data-baseweb="textarea"]:hover {
  border-color: #9AA0A6 !important;
}
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within,
[data-baseweb="textarea"]:focus-within {
  border-color: var(--md-primary) !important;
  box-shadow: 0 0 0 3px rgba(26,115,232,0.18) !important;
}
.stTextArea textarea {
  font-size: 0.95rem !important; line-height: 1.7 !important; color: var(--md-text) !important;
  font-family: 'Plus Jakarta Sans', 'Roboto', sans-serif !important;
}
[data-testid="stWidgetLabel"] p { font-weight: 600 !important; color: var(--md-text) !important; }

/* ---------- 1.9 PROGRESS ---------- */
[data-testid="stProgress"] [role="progressbar"] > div,
[data-testid="stProgress"] > div > div > div {
  border-radius: var(--md-r-full) !important;
}
[data-testid="stProgress"] [role="progressbar"] { height: 8px !important; }
[data-testid="stProgress"] p { font-weight: 600 !important; color: var(--md-text-2) !important; font-size: 0.85rem !important; }

/* ---------- 1.10 MATERIAL TABS ---------- */
[data-testid="stTabs"] [role="tablist"] {
  gap: 4px !important;
  border-bottom: 1px solid var(--md-outline-soft);
}
[data-testid="stTabs"] [role="tablist"]::after { display: none; }
[data-testid="stTab"], button[data-baseweb="tab"] {
  height: 52px !important;
  padding: 0 24px !important;
  border-radius: var(--md-r-md) var(--md-r-md) 0 0 !important;
  color: var(--md-text-2) !important;
  transition: var(--md-motion) !important;
}
[data-testid="stTab"] p, button[data-baseweb="tab"] p {
  font-weight: 600 !important; font-size: 0.95rem !important; color: inherit !important;
}
[data-testid="stTab"]:hover, [data-testid="stTab"][data-hovered], button[data-baseweb="tab"]:hover {
  background: rgba(232,240,254,0.7) !important; color: var(--md-primary) !important;
}
[data-testid="stTab"][data-selected], [data-testid="stTab"][aria-selected="true"],
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--md-primary) !important;
}
[data-testid="stTab"] .react-aria-SelectionIndicator {
  height: 3px !important; border-radius: 3px 3px 0 0 !important;
}
[data-testid="stTab"][data-selected] .react-aria-SelectionIndicator,
[data-baseweb="tab-highlight"] { background-color: var(--md-primary) !important; height: 3px !important; }
[data-baseweb="tab-border"] { background-color: var(--md-outline-soft) !important; }
[data-testid="stTabs"] [role="tabpanel"] { padding-top: 24px !important; }

/* ---------- 1.11 RADIO → thẻ lựa chọn (Màn 5) ---------- */
.st-key-card_quiz [data-testid="stRadioGroup"],
.st-key-card_quiz [role="radiogroup"] { gap: 8px !important; width: 100%; }
.st-key-card_quiz [data-testid="stRadioGroup"] > div { width: 100%; }
.st-key-card_quiz [data-testid="stRadioOption"],
.st-key-card_quiz label[data-baseweb="radio"] {
  display: flex !important; align-items: center;
  width: 100%;
  margin: 0 !important;
  padding: 16px !important;
  background: var(--md-surface);
  border: 1px solid var(--md-outline);
  border-radius: var(--md-r-md);
  transition: var(--md-motion);
  cursor: pointer;
}
.st-key-card_quiz [data-testid="stRadioOption"] p,
.st-key-card_quiz label[data-baseweb="radio"] p { font-size: 0.98rem !important; font-weight: 500; }
.st-key-card_quiz [data-testid="stRadioOption"]:hover,
.st-key-card_quiz [data-testid="stRadioOption"][data-hovered],
.st-key-card_quiz label[data-baseweb="radio"]:hover {
  border-color: var(--md-primary);
  background: #F8FBFF;
  box-shadow: var(--md-elev-2);
  transform: translateY(-2px);
}
.st-key-card_quiz [data-testid="stRadioOption"][data-selected],
.st-key-card_quiz label[data-baseweb="radio"]:has(input:checked) {
  border: 2px solid var(--md-primary);
  background: var(--md-primary-tint);
  padding: 15px !important;
}
.st-key-card_quiz [data-testid="stRadioOption"][data-selected] p { font-weight: 700 !important; color: var(--md-on-primary-tint) !important; }

/* ---------- 1.12 METRIC CARDS ---------- */
[data-testid="stMetric"] {
  background: var(--md-surface);
  border-radius: var(--md-r-lg);
  padding: 16px 24px !important;
  box-shadow: var(--md-elev-1);
  border-top: 4px solid var(--md-primary);
  transition: var(--md-motion);
}
[data-testid="stMetric"]:hover { box-shadow: var(--md-elev-2); transform: translateY(-2px); }
[data-testid="stMetricLabel"] p {
  font-size: 0.75rem !important; font-weight: 700 !important; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--md-text-2) !important;
}
[data-testid="stMetricValue"] { font-weight: 800 !important; color: var(--md-text) !important; font-size: 1.9rem !important; }
[class*="st-key-metric_success"] [data-testid="stMetric"] { border-top-color: var(--md-success); }
[class*="st-key-metric_error"] [data-testid="stMetric"] { border-top-color: var(--md-error); }
[class*="st-key-metric_indigo"] [data-testid="stMetric"] { border-top-color: var(--md-indigo); }
[class*="st-key-metric_amber"] [data-testid="stMetric"] { border-top-color: var(--md-amber); }

/* ---------- 1.13 ALERTS, SPINNER & TOAST (DYNAMIC UI COMPONENTS) ---------- */
[data-testid="stAlertContainer"] {
  border-radius: var(--md-r-md) !important; border: none !important;
  box-shadow: var(--md-elev-1);
  animation: md-rise .28s var(--md-ease) both;
}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {
  background: var(--md-error-tint) !important; color: var(--md-error-hover) !important;
  border-left: 4px solid var(--md-error) !important;
}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {
  background: var(--md-success-tint) !important; color: var(--md-success-hover) !important;
  border-left: 4px solid var(--md-success) !important;
}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {
  background: var(--md-primary-tint) !important; color: var(--md-on-primary-tint) !important;
  border-left: 4px solid var(--md-primary) !important;
}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
  background: var(--md-amber-tint) !important; color: var(--md-amber-ink) !important;
  border-left: 4px solid var(--md-amber) !important;
}
[data-testid="stAlertContainer"] p { color: inherit !important; font-weight: 500; }

/* Material Spinner & Live AI Processing Surface */
[data-testid="stSpinner"] {
  background: linear-gradient(135deg, #E8F0FE 0%, #EEF0FF 100%);
  border: 1px solid #D3E3FD;
  border-radius: var(--md-r-md);
  padding: 16px 20px;
  margin: 8px 0;
  box-shadow: var(--md-elev-1);
  animation: md-rise .25s var(--md-ease) both;
}
[data-testid="stSpinner"] p {
  color: var(--md-on-primary-tint) !important;
  font-weight: 600 !important;
  font-size: 0.94rem !important;
}

/* Material Snackbar / Toast */
[data-testid="stToast"] {
  background: var(--md-surface) !important;
  border-radius: var(--md-r-lg) !important;
  box-shadow: var(--md-elev-3) !important;
  border-left: 4px solid var(--md-primary) !important;
  padding: 12px 16px !important;
  transition: var(--md-motion) !important;
}
[data-testid="stToast"] p {
  font-weight: 600 !important;
  color: var(--md-text) !important;
}

/* ---------- 1.14 CUSTOM COMPONENTS (HTML) ---------- */
@keyframes md-rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes md-flip {
  0%   { transform: perspective(1400px) rotateY(-90deg); opacity: 0.2; }
  100% { transform: perspective(1400px) rotateY(0deg);   opacity: 1; }
}
@keyframes md-enter {
  0%   { transform: translateX(32px) scale(0.98); opacity: 0; }
  100% { transform: none; opacity: 1; }
}

/* Hero / Top app bar */
.md-hero {
  position: relative; overflow: hidden;
  background: var(--md-surface);
  border-radius: var(--md-r-xl);
  box-shadow: var(--md-elev-1);
  padding: 32px;
  margin-bottom: 24px;
  animation: md-rise .4s var(--md-ease) both;
}
.md-hero::before, .md-hero::after {
  content: ""; position: absolute; border-radius: 50%; pointer-events: none;
}
.md-hero::before {
  width: 280px; height: 280px; right: -60px; top: -120px;
  background: radial-gradient(circle, rgba(26,115,232,0.20), rgba(26,115,232,0) 70%);
}
.md-hero::after {
  width: 220px; height: 220px; right: 140px; bottom: -150px;
  background: radial-gradient(circle, rgba(99,102,241,0.16), rgba(99,102,241,0) 70%);
}
.md-hero-row { position: relative; z-index: 1; display: flex; gap: 24px; align-items: center; justify-content: space-between; }
.md-hero-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 0.78rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--md-primary); background: var(--md-primary-tint);
  padding: 4px 12px 4px 8px; border-radius: var(--md-r-full);
}
.md-hero-eyebrow .msr { font-size: 18px; }
.md-hero h1 {
  font-size: 2rem !important; font-weight: 800 !important; line-height: 1.25 !important;
  margin: 16px 0 8px !important; padding: 0 !important; color: var(--md-text) !important;
}
.md-hero p.md-hero-sub { color: var(--md-text-2) !important; font-size: 1rem; margin: 0; max-width: 640px; }
.md-hero-art {
  flex-shrink: 0; width: 120px; height: 120px; border-radius: 32px;
  display: grid; place-items: center; color: #fff;
  background: linear-gradient(135deg, #1A73E8 0%, #6366F1 60%, #8B5CF6 100%);
  box-shadow: var(--md-elev-3);
  transform: rotate(-6deg);
}
.md-hero-art .msr { font-size: 56px; font-variation-settings: 'FILL' 1, 'wght' 600, 'GRAD' 0, 'opsz' 48; }
.md-hero-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }

/* Chips */
.md-chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 0.8rem; font-weight: 600; line-height: 1;
  padding: 6px 12px; border-radius: var(--md-r-full);
  background: #F1F3F4; color: #3C4043; white-space: nowrap;
}
.md-chip .msr { font-size: 16px; }
.chip-primary { background: var(--md-primary-tint); color: var(--md-on-primary-tint); }
.chip-indigo  { background: var(--md-indigo-tint);  color: #4338CA; }
.chip-success { background: var(--md-success-tint); color: var(--md-success-hover); }
.chip-error   { background: var(--md-error-tint);   color: var(--md-error-hover); }
.chip-amber   { background: var(--md-amber-tint);   color: var(--md-amber-ink); }
.chip-outline { background: #fff; border: 1px solid var(--md-outline); color: var(--md-text-2); }

/* Stepper */
.md-stepper {
  display: flex; align-items: center; gap: 8px;
  background: var(--md-surface); border-radius: var(--md-r-full);
  box-shadow: var(--md-elev-1); padding: 8px; margin-bottom: 24px;
  animation: md-rise .45s var(--md-ease) both;
}
.md-step {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 8px 12px; border-radius: var(--md-r-full);
  color: var(--md-text-3); font-weight: 600; font-size: 0.85rem;
  transition: var(--md-motion);
}
.md-step-dot {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  display: grid; place-items: center; font-size: 0.8rem; font-weight: 700;
  background: #F1F3F4; color: var(--md-text-2);
}
.md-step-dot .msr { font-size: 18px; }
.md-step.done { color: var(--md-success); }
.md-step.done .md-step-dot { background: var(--md-success-tint); color: var(--md-success); }
.md-step.active { background: var(--md-primary-tint); color: var(--md-on-primary-tint); }
.md-step.active .md-step-dot { background: var(--md-primary); color: #fff; box-shadow: 0 2px 6px rgba(26,115,232,0.4); }
.md-step-sep { width: 24px; height: 2px; background: var(--md-outline-soft); border-radius: 2px; flex-shrink: 0; }

/* Section header trong card */
.md-section { display: flex; align-items: flex-start; gap: 16px; margin-bottom: 8px; }
.md-section-badge {
  width: 40px; height: 40px; border-radius: var(--md-r-md); flex-shrink: 0;
  display: grid; place-items: center;
  background: var(--md-primary-tint); color: var(--md-primary);
}
.md-section-badge.indigo { background: var(--md-indigo-tint); color: var(--md-indigo); }
.md-section-badge.success { background: var(--md-success-tint); color: var(--md-success); }
.md-section-badge .msr { font-size: 22px; }
.md-section-kicker { font-size: 0.72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--md-text-3); }
.md-section-title { font-size: 1.2rem; font-weight: 800; color: var(--md-text); line-height: 1.3; }
.md-section-sub { font-size: 0.9rem; color: var(--md-text-2); margin-top: 4px; line-height: 1.5; }

/* File pill */
.md-file-pill {
  display: flex; align-items: center; gap: 16px;
  background: var(--md-surface-dim); border: 1px solid var(--md-outline-soft);
  border-radius: var(--md-r-md); padding: 12px 16px; margin: 8px 0;
  animation: md-rise .3s var(--md-ease) both;
}
.md-file-icon {
  width: 44px; height: 44px; border-radius: var(--md-r-md); flex-shrink: 0;
  display: grid; place-items: center;
}
.md-file-icon.image { background: var(--md-primary-tint); color: var(--md-primary); }
.md-file-icon.audio { background: var(--md-indigo-tint); color: var(--md-indigo); }
.md-file-icon.bad { background: var(--md-error-tint); color: var(--md-error); }
.md-file-name { font-weight: 700; color: var(--md-text); word-break: break-all; }
.md-file-meta { font-size: 0.82rem; color: var(--md-text-2); margin-top: 2px; }

/* Flashcard 3D surface (Elevation 3) */
.fc-card {
  position: relative;
  min-height: 300px;
  padding: 48px 40px 40px;
  border-radius: var(--md-r-xl);
  background: var(--md-surface);
  box-shadow: var(--md-elev-3);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center;
  transition: var(--md-motion);
  transform-style: preserve-3d;
  margin-bottom: 16px;
  overflow: hidden;
}
.fc-card:hover { box-shadow: 0 14px 28px rgba(0,0,0,0.12), 0 10px 10px rgba(0,0,0,0.08); }
.fc-card.anim-flip  { animation: md-flip .5s var(--md-ease) both; }
.fc-card.anim-enter { animation: md-enter .4s var(--md-ease) both; }
.fc-card.front { border-top: 6px solid var(--md-primary); }
.fc-card.back {
  border-top: 6px solid var(--md-indigo);
  background: linear-gradient(160deg, #EEF0FF 0%, #F5F3FF 45%, #FFFFFF 100%);
}
.fc-card::after {
  content: ""; position: absolute; right: -40px; bottom: -40px; width: 160px; height: 160px; border-radius: 50%;
  background: radial-gradient(circle, rgba(26,115,232,0.08), transparent 70%);
}
.fc-card.back::after { background: radial-gradient(circle, rgba(99,102,241,0.14), transparent 70%); }
.fc-side {
  position: absolute; top: 20px; left: 24px;
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 0.75rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  padding: 6px 12px; border-radius: var(--md-r-full);
}
.fc-card.front .fc-side { background: var(--md-primary-tint); color: var(--md-on-primary-tint); }
.fc-card.back  .fc-side { background: #fff; color: #4338CA; box-shadow: var(--md-elev-1); }
.fc-count { position: absolute; top: 24px; right: 24px; font-size: 0.82rem; font-weight: 700; color: var(--md-text-3); }
.fc-content { font-size: 1.45rem; font-weight: 700; color: var(--md-text); line-height: 1.55; max-width: 680px; position: relative; z-index: 1; }
.fc-card.back .fc-content { font-size: 1.2rem; font-weight: 600; color: #312E81; }
.fc-hint { margin-top: 24px; font-size: 0.85rem; color: var(--md-text-3); font-weight: 500; display: inline-flex; gap: 6px; align-items: center; }
.fc-tally { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 16px; }

/* Flashcard preview grid (Màn 3) */
.fc-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.fc-mini {
  background: var(--md-surface); border-radius: var(--md-r-lg); box-shadow: var(--md-elev-1);
  overflow: hidden; transition: var(--md-motion); animation: md-rise .35s var(--md-ease) both;
}
.fc-mini:hover { box-shadow: var(--md-elev-2); transform: translateY(-2px); }
.fc-mini-front { padding: 16px; border-bottom: 1px dashed var(--md-outline); }
.fc-mini-back { padding: 16px; background: linear-gradient(160deg, #F5F6FF, #FFFFFF); }
.fc-mini-q { font-weight: 700; color: var(--md-text); margin-top: 8px; line-height: 1.5; }
.fc-mini-a { color: #3730A3; margin-top: 8px; line-height: 1.55; font-size: 0.93rem; }

/* Quiz */
.q-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.q-text { font-size: 1.25rem; font-weight: 700; color: var(--md-text); line-height: 1.5; margin-bottom: 8px; }
.q-preview { background: var(--md-surface); border-radius: var(--md-r-lg); box-shadow: var(--md-elev-1); padding: 16px 24px; margin-bottom: 8px; transition: var(--md-motion); }
.q-preview:hover { box-shadow: var(--md-elev-2); }
.q-preview .q-text { font-size: 1.02rem; }
.q-opt { display: flex; gap: 8px; padding: 8px 12px; border-radius: var(--md-r-sm); background: var(--md-surface-dim); margin-top: 6px; color: var(--md-text); font-size: 0.93rem; }

/* Score hero */
.score-hero {
  display: flex; align-items: center; gap: 32px;
  background: var(--md-surface); border-radius: var(--md-r-xl); box-shadow: var(--md-elev-3);
  padding: 32px; margin-bottom: 24px; animation: md-rise .45s var(--md-ease) both;
}
.score-ring {
  --p: 0; --ring: var(--md-primary);
  width: 140px; height: 140px; border-radius: 50%; flex-shrink: 0;
  background: conic-gradient(var(--ring) calc(var(--p) * 1%), #E8EAED 0);
  display: grid; place-items: center;
}
.score-ring-inner {
  width: 112px; height: 112px; border-radius: 50%; background: #fff;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);
}
.score-ring-inner b { font-size: 1.9rem; font-weight: 800; color: var(--md-text); line-height: 1; }
.score-ring-inner small { font-size: 0.72rem; color: var(--md-text-2); font-weight: 600; margin-top: 4px; text-transform: uppercase; letter-spacing: .06em; }
.score-title { font-size: 1.5rem; font-weight: 800; color: var(--md-text); }
.score-sub { color: var(--md-text-2); margin-top: 4px; }

/* Answer rows */
.ans-row { display: flex; gap: 12px; align-items: flex-start; padding: 12px 16px; border-radius: var(--md-r-md); margin-bottom: 8px; }
.ans-row .msr { margin-top: 2px; }
.ans-row small { display: block; font-size: 0.72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; opacity: .8; }
.ans-row div.v { font-weight: 600; margin-top: 2px; }
.ans-ok { background: var(--md-success-tint); color: var(--md-success-hover); }
.ans-bad { background: var(--md-error-tint); color: var(--md-error-hover); }
.ans-key { background: var(--md-primary-tint); color: var(--md-on-primary-tint); }

/* Library card */
.lib-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.lib-src { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; }
.lib-src.image { background: var(--md-primary-tint); color: var(--md-primary); }
.lib-src.audio { background: var(--md-indigo-tint); color: var(--md-indigo); }
.lib-title { font-size: 1.08rem; font-weight: 800; color: var(--md-text); line-height: 1.4; margin: 16px 0 4px; min-height: 3em; }
.lib-file { font-size: 0.82rem; color: var(--md-text-2); display: flex; align-items: center; gap: 6px; }
.lib-file .msr { font-size: 16px; }
.lib-stats { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 8px; margin: 16px 0 8px; }
.lib-stat { background: var(--md-surface-dim); border-radius: var(--md-r-md); padding: 8px 12px; }
.lib-stat b { display: block; font-size: 1.05rem; font-weight: 800; color: var(--md-text); }
.lib-stat small { font-size: 0.72rem; color: var(--md-text-2); font-weight: 600; }
.lib-stat.good b { color: var(--md-success); }
.lib-stat.mid b { color: var(--md-amber-ink); }
.lib-stat.bad b { color: var(--md-error); }
.lib-stat.none b { color: var(--md-text-3); }
.md-stats-row { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 16px; margin-bottom: 24px; }
.md-stat-tile {
  background: var(--md-surface); border-radius: var(--md-r-lg); box-shadow: var(--md-elev-1);
  padding: 16px 24px; display: flex; align-items: center; gap: 16px; transition: var(--md-motion);
  animation: md-rise .4s var(--md-ease) both;
}
.md-stat-tile:hover { box-shadow: var(--md-elev-2); transform: translateY(-2px); }
.md-stat-tile .ic { width: 44px; height: 44px; border-radius: var(--md-r-md); display: grid; place-items: center; }
.md-stat-tile b { display: block; font-size: 1.5rem; font-weight: 800; color: var(--md-text); line-height: 1.1; }
.md-stat-tile small { color: var(--md-text-2); font-weight: 600; font-size: 0.8rem; }

.md-empty { text-align: center; padding: 48px 24px; color: var(--md-text-2); }
.md-empty .msr { font-size: 56px; color: var(--md-outline); }
.md-empty b { display: block; color: var(--md-text); font-size: 1.1rem; margin: 8px 0 4px; }
.md-results-label { font-size: 0.85rem; font-weight: 600; color: var(--md-text-2); margin: 8px 0 16px; }

.md-meta-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 16px; }
.md-summary [data-testid="stMarkdownContainer"] li { margin-bottom: 8px; }

/* ---------- 1.15 RESPONSIVE (Mobile ≤ 640px, Tablet ≤ 960px) ---------- */
@media (max-width: 960px) {
  .md-hero-art { width: 96px; height: 96px; border-radius: 24px; }
  .md-hero-art .msr { font-size: 44px; }
  .md-step-label { display: none; }
  .md-step { flex: 0 0 auto; }
  .md-stepper { justify-content: space-between; }
}
@media (max-width: 640px) {
  .block-container, [data-testid="stMainBlockContainer"] { padding: 56px 16px 48px !important; }
  .md-hero { padding: 24px; border-radius: var(--md-r-lg); }
  .md-hero h1 { font-size: 1.5rem !important; }
  .md-hero-art { display: none; }
  div[data-testid="stVerticalBlock"][class*="st-key-card"] { padding: 16px !important; }
  .fc-card { min-height: 260px; padding: 56px 20px 32px; }
  .fc-content { font-size: 1.15rem; }
  .fc-card.back .fc-content { font-size: 1.02rem; }
  .fc-grid { grid-template-columns: 1fr; }
  .score-hero { flex-direction: column; text-align: center; gap: 16px; padding: 24px; }
  .md-stats-row { grid-template-columns: 1fr; gap: 8px; }
  .lib-stats { grid-template-columns: repeat(3, minmax(0,1fr)); }
  [data-testid="stTab"], button[data-baseweb="tab"] { padding: 0 12px !important; }
  .md-step-sep { width: 8px; }
}
</style>
"""
st.markdown(MATERIAL_CSS, unsafe_allow_html=True)


# ==========================================================
# 2. HẰNG SỐ, HELPER RENDER & SESSION STATE
# ==========================================================
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
DOC_EXTENSIONS = ["pdf"]
AUDIO_EXTENSIONS = ["mp3", "wav", "m4a"]
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS + DOC_EXTENSIONS + AUDIO_EXTENSIONS
BACKEND_NATIVE_EXTENSIONS = set(IMAGE_EXTENSIONS + DOC_EXTENSIONS)
BACKEND_MIME_MAP = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "pdf": "application/pdf",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
}
MAX_FILE_SIZE_MB = 25  # Ngưỡng dung lượng của luồng ngoại lệ FR14
SUBJECT_LIST = ["Trí tuệ nhân tạo (AI)", "Cơ học kỹ thuật", "Kinh tế vĩ mô", "Đồ họa máy tính", "Môn học khác"]
BACKEND_SQLITE_PATH = Path(__file__).parent / "smart_note_backend" / "smart_note.db"
FASTAPI_BASE_URL = "http://127.0.0.1:8000"
FASTAPI_UPLOAD_ENDPOINT = "/api/v1/upload"
FASTAPI_HEALTH_ENDPOINT = "/health"
DEFAULT_FLASHCARD_COUNT = 5
DEFAULT_QUIZ_COUNT = 5

# Màu chip theo môn học (Material tonal palette)
SUBJECT_STYLE = {
    "Trí tuệ nhân tạo (AI)": ("chip-indigo", "psychology"),
    "Cơ học kỹ thuật": ("chip-amber", "precision_manufacturing"),
    "Kinh tế vĩ mô": ("chip-success", "monitoring"),
    "Đồ họa máy tính": ("chip-error", "palette"),
    "Môn học khác": ("chip-outline", "category"),
}


def render_html(markup: str) -> None:
    """Render HTML tuỳ biến. Gộp thành 1 dòng để Markdown không biến dòng thụt lề thành code block."""
    compact = " ".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(compact, unsafe_allow_html=True)


def esc(text) -> str:
    return html.escape(str(text))


def icon(name: str, extra_style: str = "") -> str:
    style = f' style="{extra_style}"' if extra_style else ""
    return f'<span class="msr"{style}>{name}</span>'


def subject_chip(subject: str) -> str:
    cls, ic = SUBJECT_STYLE.get(subject, ("chip-outline", "category"))
    return f'<span class="md-chip {cls}">{icon(ic)}{esc(subject)}</span>'


def file_kind(file_name: str) -> str:
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in IMAGE_EXTENSIONS or ext in DOC_EXTENSIONS:
        return "image"
    return "other"


def canonical_mime_type(file_name: str, fallback_type: str = "") -> str:
    """Chuẩn hoá MIME type khớp tuyệt đối với bảng EXTENSIONS của smart_note_backend/app/files.py."""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext in BACKEND_MIME_MAP:
        return BACKEND_MIME_MAP[ext]
    return fallback_type or "application/octet-stream"


def score_level(score_text: str) -> str:
    """Phân loại điểm 'a/b ...' → good / mid / bad / none để tô màu."""
    try:
        frac = score_text.split(" ")[0]
        a, b = frac.split("/")
        ratio = int(a) / int(b)
        return "good" if ratio >= 0.8 else ("mid" if ratio >= 0.5 else "bad")
    except (ValueError, ZeroDivisionError, AttributeError):
        return "none"


def render_hero(eyebrow_icon: str, eyebrow: str, title: str, subtitle: str = "",
                art_icon: str = "", chips_html: str = "") -> None:
    """Top app bar dạng Material Surface — chứa thẻ <h1> duy nhất của trang."""
    art = f'<div class="md-hero-art">{icon(art_icon)}</div>' if art_icon else ""
    sub = f'<p class="md-hero-sub">{subtitle}</p>' if subtitle else ""
    chips = f'<div class="md-hero-chips">{chips_html}</div>' if chips_html else ""
    render_html(f"""
    <header class="md-hero"><div class="md-hero-row"><div>
      <span class="md-hero-eyebrow">{icon(eyebrow_icon)}{esc(eyebrow)}</span>
      <h1>{esc(title)}</h1>{sub}{chips}
    </div>{art}</div></header>
    """)


def render_stepper(screen: int) -> None:
    """Material stepper cho luồng Tạo mới (Màn 1 → 5)."""
    steps = [(1, "Tải lên", "upload"), (2, "Sửa văn bản", "edit_note"),
             (3, "Kết quả", "auto_awesome"), (4, "Ôn luyện", "school")]
    current = 4 if screen in (4, 5) else screen
    parts = []
    for i, (num, label, _ic) in enumerate(steps):
        state = "done" if num < current else ("active" if num == current else "")
        dot = icon("check") if state == "done" else str(num)
        parts.append(f'<div class="md-step {state}"><span class="md-step-dot">{dot}</span>'
                     f'<span class="md-step-label">{label}</span></div>')
        if i < len(steps) - 1:
            parts.append('<span class="md-step-sep"></span>')
    render_html(f'<nav class="md-stepper" aria-label="Tiến trình tạo học liệu">{"".join(parts)}</nav>')


def render_section(badge_icon: str, kicker: str, title: str, subtitle: str = "", tone: str = "") -> None:
    sub = f'<div class="md-section-sub">{subtitle}</div>' if subtitle else ""
    render_html(f"""
    <div class="md-section"><div class="md-section-badge {tone}">{icon(badge_icon)}</div>
    <div><div class="md-section-kicker">{esc(kicker)}</div>
    <div class="md-section-title">{esc(title)}</div>{sub}</div></div>
    """)


def go_to(nav: str, screen: int | None = None) -> None:
    st.session_state.nav_menu = nav
    if screen is not None:
        st.session_state.current_screen = screen
    st.rerun()


def start_flashcards(order=None) -> None:
    total = len(st.session_state.current_study_set["flashcards"])
    st.session_state.fc_order = list(order) if order is not None else list(range(total))
    st.session_state.fc_pos = 0
    st.session_state.fc_flipped = False
    st.session_state.fc_known = []
    st.session_state.fc_unknown = []
    st.session_state.fc_anim = "enter"
    st.session_state.current_screen = 4


def flip_flashcard_state() -> bool:
    """Logic lật thẻ Mặt trước ↔ Mặt sau trên Màn 4, kích hoạt animation 3D flip."""
    st.session_state.fc_flipped = not st.session_state.fc_flipped
    st.session_state.fc_anim = "flip"
    return st.session_state.fc_flipped


def record_flashcard_review(card_idx: int, is_known: bool) -> None:
    """Logic đánh giá thẻ 'Đã nhớ' / 'Chưa nhớ' và chuyển sang thẻ kế tiếp."""
    if is_known:
        st.session_state.fc_known.append(card_idx)
    else:
        st.session_state.fc_unknown.append(card_idx)
    st.session_state.fc_pos += 1
    st.session_state.fc_flipped = False
    st.session_state.fc_anim = "enter"


def start_quiz() -> None:
    st.session_state.quiz_index = 0
    st.session_state.quiz_answers = {}
    st.session_state.quiz_finished = False
    st.session_state.quiz_attempt += 1
    st.session_state.quiz_warning = False
    st.session_state.current_screen = 5


def resolve_correct_option(raw_correct, options: list[str]) -> str:
    """Chuẩn hoá đáp án đúng từ JSON (hỗ trợ cả nguyên chuỗi 'B. ...', ký tự 'A'-'D' hoặc chỉ số 0-3)."""
    if not options:
        return str(raw_correct or "")
    if isinstance(raw_correct, int) and 0 <= raw_correct < len(options):
        return options[raw_correct]
    ans_str = str(raw_correct or "").strip()
    if not ans_str:
        return options[0]
    for opt in options:
        if opt.strip() == ans_str or opt.strip().lower() == ans_str.lower():
            return opt
    letter = ans_str.rstrip(".) ").upper()
    if len(letter) == 1 and letter in "ABCD":
        idx = ord(letter) - ord("A")
        for opt in options:
            if opt.strip().upper().startswith((f"{letter}.", f"{letter})", f"{letter} ")):
                return opt
        if 0 <= idx < len(options):
            return options[idx]
    for opt in options:
        if ans_str.lower() in opt.lower():
            return opt
    return ans_str


def is_option_match(user_choice: str | None, correct_answer: str, options: list[str] | None = None) -> bool:
    """So khớp lựa chọn của người dùng với đáp án đúng chuẩn hoá."""
    if not user_choice:
        return False
    u = user_choice.strip()
    target = resolve_correct_option(correct_answer, options or []).strip()
    if u == target or u.lower() == target.lower():
        return True
    u_prefix = u.split(".", 1)[0].strip().upper()
    t_prefix = target.split(".", 1)[0].strip().upper()
    if len(u_prefix) == 1 and u_prefix in "ABCD" and u_prefix == t_prefix:
        return True
    return False


def calculate_quiz_score(quizzes: list[dict], user_answers: dict[int, str]) -> dict:
    """
    Logic tính điểm bài Trắc nghiệm (Màn 5) dựa trên cấu trúc JSON chuẩn của Leader.
    Trả về tổng điểm, số câu đúng/sai, phần trăm chính xác, chuỗi last_score và chi tiết từng câu.
    """
    total = len(quizzes)
    correct = 0
    details = []
    for i, q in enumerate(quizzes):
        opts = q.get("options", [])
        canonical_correct = resolve_correct_option(q.get("correct_answer", ""), opts)
        user_ans = user_answers.get(i, "Chưa chọn")
        ok = is_option_match(user_ans if user_ans != "Chưa chọn" else None, canonical_correct, opts)
        if ok:
            correct += 1
        details.append({
            "index": i,
            "question": q.get("question", ""),
            "user_answer": user_ans,
            "correct_answer": canonical_correct,
            "is_correct": ok,
            "explanation": q.get("explanation", ""),
        })
    wrong = total - correct
    pct = int(round((correct / total) * 100)) if total else 0
    return {
        "correct": correct,
        "wrong": wrong,
        "total": total,
        "pct": pct,
        "last_score": f"{correct}/{total} ({pct}%)",
        "details": details,
    }


def synthesize_summary_from_ai_data(extracted_text: str, flashcards: list[dict]) -> str:
    """
    Tự động tổng hợp bản Tóm tắt Markdown có cấu trúc từ dữ liệu thật của Backend /api/v1/upload
    (do schema UploadResponse của Backend trả về extracted_text + flashcards + quizzes).
    """
    bullets: list[str] = []
    for fc in flashcards:
        front = str(fc.get("front_text", "")).strip()
        back = str(fc.get("back_text", "")).strip()
        if front and back:
            bullets.append(f"- **{front}** — {back}")
    if bullets:
        header = "### Trọng tâm kiến thức từ AI (`/api/v1/upload`)\n"
        text_preview = [line.strip() for line in extracted_text.splitlines() if len(line.strip()) > 25][:3]
        overview = ""
        if text_preview:
            overview = "\n**Nội dung trích xuất chính:**\n" + "\n".join(
                f"- {line.lstrip('-•* ')}" for line in text_preview
            ) + "\n\n**Các khái niệm & ý chính cần nhớ:**\n"
        return header + overview + "\n".join(bullets)
    lines = [line.strip().lstrip("-•* ") for line in extracted_text.splitlines() if line.strip()]
    if lines:
        return "\n".join(f"- {line}" for line in lines[:8])
    return "- Tài liệu đã được trích xuất thành công từ hệ thống AI."


def normalize_study_set(payload: dict, fallback_subject: str = "", fallback_file_name: str = "") -> dict:
    """
    Chuẩn hoá JSON trả về từ Mock Data hoặc Endpoint POST /api/v1/upload của Backend
    về đúng schema chuẩn hiển thị trên 6 màn hình Streamlit.
    Hỗ trợ linh hoạt cả response phẳng hoặc bọc trong {"data": {...}} / {"result": {...}},
    cũng như các biến thể tên trường (front/back, front_text/back_text, answer/correct_answer...).
    """
    if not isinstance(payload, dict):
        payload = {}
    inner = payload.get("data") if isinstance(payload.get("data"), dict) else (
        payload.get("result") if isinstance(payload.get("result"), dict) else payload
    )

    file_name = (
        inner.get("file_name")
        or inner.get("filename")
        or payload.get("file_name")
        or payload.get("filename")
        or fallback_file_name
        or "tai_lieu_moi.png"
    )
    subject = (
        inner.get("subject")
        or payload.get("subject")
        or fallback_subject
        or SUBJECT_LIST[0]
    )
    stem = file_name.rsplit(".", 1)[0].replace("_", " ").strip() or "Tài liệu mới"
    title = inner.get("title") or payload.get("title") or f"{subject} - {stem}"

    extracted_text = (
        inner.get("extracted_text")
        or inner.get("raw_text")
        or inner.get("text")
        or inner.get("transcript")
        or payload.get("extracted_text")
        or payload.get("raw_text")
        or payload.get("text")
        or ""
    )

    raw_cards = inner.get("flashcards") or inner.get("cards") or payload.get("flashcards") or []
    flashcards = []
    for idx, c in enumerate(raw_cards, 1):
        if not isinstance(c, dict):
            continue
        front = c.get("front_text") or c.get("front") or c.get("question") or c.get("term") or f"Thẻ {idx}"
        back = c.get("back_text") or c.get("back") or c.get("answer") or c.get("definition") or ""
        flashcards.append({
            "card_id": str(c.get("card_id") or c.get("id") or f"fc_{idx}"),
            "front_text": str(front),
            "back_text": str(back),
        })

    raw_summary = inner.get("summary") or payload.get("summary") or ""
    if isinstance(raw_summary, list):
        summary = "\n".join(f"- {item}" if not str(item).lstrip().startswith("-") else str(item) for item in raw_summary)
    else:
        summary = str(raw_summary).strip()
    if not summary:
        summary = synthesize_summary_from_ai_data(str(extracted_text), flashcards)

    raw_quizzes = inner.get("quizzes") or inner.get("quiz") or inner.get("questions") or payload.get("quizzes") or []
    quizzes = []
    for idx, q in enumerate(raw_quizzes, 1):
        if not isinstance(q, dict):
            continue
        question = q.get("question") or q.get("prompt") or q.get("q") or f"Câu hỏi {idx}"
        raw_opts = q.get("options") or q.get("choices") or q.get("answers") or []
        options = [str(o) for o in raw_opts] if isinstance(raw_opts, list) else []
        raw_ans = (
            q.get("correct_answer")
            if q.get("correct_answer") is not None
            else (q.get("answer") if q.get("answer") is not None else q.get("correct"))
        )
        correct_answer = resolve_correct_option(raw_ans, options)
        explanation = (
            q.get("explanation")
            or q.get("reason")
            or q.get("rationale")
            or f"Đáp án chính xác là “{correct_answer}” — được AI trích xuất trực tiếp từ nội dung bài giảng."
        )
        quizzes.append({
            "quiz_id": str(q.get("quiz_id") or q.get("id") or f"q_{idx}"),
            "question": str(question),
            "options": options,
            "correct_answer": str(correct_answer),
            "explanation": str(explanation),
        })

    meta = inner.get("meta") or payload.get("meta")
    if not isinstance(meta, dict):
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext == "pdf":
            engine_default = "PDF Vision OCR"
        elif file_kind(file_name) == "audio":
            engine_default = "Speech-to-Text"
        else:
            engine_default = "Vision OCR"
        meta = {"engine": engine_default, "detail": f"Từ /api/v1/upload · {len(flashcards)} thẻ · {len(quizzes)} câu hỏi"}

    return {
        "doc_id": str(inner.get("doc_id") or inner.get("id") or payload.get("doc_id") or uuid.uuid4()),
        "user_id": str(inner.get("user_id") or payload.get("user_id") or "00000000-0000-4000-8000-000000000001"),
        "title": str(title),
        "subject": str(subject),
        "file_name": str(file_name),
        "created_at": str(inner.get("created_at") or payload.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M")),
        "last_score": str(inner.get("last_score") or payload.get("last_score") or "Chưa làm"),
        "meta": meta,
        "extracted_text": str(extracted_text),
        "summary": summary,
        "flashcards": flashcards,
        "quizzes": quizzes,
    }


def load_sqlite_library(db_path: Path = BACKEND_SQLITE_PATH) -> list[dict]:
    """
    Đọc trực tiếp các bộ học liệu thật đã được Backend lưu trong SQLite (smart_note.db)
    để đồng bộ vào Màn 6 (Thư viện).
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        docs = cur.execute(
            "SELECT doc_id, user_id, file_name, extracted_text, created_at FROM documents ORDER BY created_at DESC"
        ).fetchall()
        items: list[dict] = []
        for doc in docs:
            doc_id = doc["doc_id"]
            cards = cur.execute(
                "SELECT card_id, front_text, back_text FROM flashcards WHERE doc_id = ? ORDER BY created_at ASC",
                (doc_id,),
            ).fetchall()
            quizzes_rows = cur.execute(
                "SELECT quiz_id, question, options, correct_answer FROM quizzes WHERE doc_id = ? ORDER BY created_at ASC",
                (doc_id,),
            ).fetchall()
            parsed_quizzes = []
            for q in quizzes_rows:
                raw_opts = q["options"]
                if isinstance(raw_opts, str):
                    try:
                        opts = json.loads(raw_opts)
                    except Exception:  # noqa: BLE001
                        opts = []
                elif isinstance(raw_opts, list):
                    opts = raw_opts
                else:
                    opts = []
                parsed_quizzes.append({
                    "quiz_id": q["quiz_id"],
                    "question": q["question"],
                    "options": opts,
                    "correct_answer": q["correct_answer"],
                })
            created_str = str(doc["created_at"] or "")[:16]
            items.append(normalize_study_set({
                "doc_id": doc_id,
                "user_id": doc["user_id"],
                "file_name": doc["file_name"] or "tai_lieu_ai.png",
                "extracted_text": doc["extracted_text"] or "",
                "created_at": created_str or datetime.now().strftime("%Y-%m-%d %H:%M"),
                "flashcards": [dict(c) for c in cards],
                "quizzes": parsed_quizzes,
            }))
        conn.close()
        return items
    except Exception:  # noqa: BLE001
        return []


def build_seed_library() -> list[dict]:
    """Khởi tạo Thư viện 100% từ dữ liệu thật trong SQLite của Backend (smart_note.db)."""
    return load_sqlite_library()


def queue_toast(message: str, icon_name: str = ":material/info:") -> None:
    """Hiển thị Toast ngay lập tức và lưu vào hàng đợi để không bị mất sau khi st.rerun()."""
    st.session_state.pending_toast = (message, icon_name)
    st.toast(message, icon=icon_name)


def flush_pending_toast() -> None:
    """Hiển thị Toast đã xếp hàng sau khi trang vừa rerun."""
    toast_item = st.session_state.pop("pending_toast", None)
    if toast_item and isinstance(toast_item, tuple) and len(toast_item) == 2:
        st.toast(toast_item[0], icon=toast_item[1])


def init_session_state() -> None:
    defaults = {
        # Điều hướng: "Tạo mới" (Màn 1→5) | "Thư viện" (Màn 6)
        "nav_menu": "Tạo mới",
        "current_screen": 1,  # 1 Tải lên · 2 Sửa văn bản · 3 Kết quả · 4 Flashcard · 5 Trắc nghiệm
        # Luồng xử lý hiện tại
        "selected_subject": SUBJECT_LIST[0],
        "uploader_key": 0,
        "pending_file": None,        # {"name","size","type","bytes"} — giữ file để "Thử lại"
        "uploaded_file_name": None,
        "extract_meta": None,
        "extracted_text": "",        # Bản đã lưu
        "draft_text": "",            # Bản nháp đang sửa trong text_area
        "pending_study_set": None,   # Bộ học liệu AI trả về từ /api/v1/upload
        "last_raw_json": None,       # JSON gốc gần nhất từ /api/v1/upload
        "current_study_set": None,
        "api_error_state": None,     # ("extract"|"generate", message, code)
        "pending_toast": None,
        "backend_base_url": FASTAPI_BASE_URL,
        "flashcard_count": DEFAULT_FLASHCARD_COUNT,
        "quiz_count": DEFAULT_QUIZ_COUNT,
        "backend_health": None,
        # Màn 4 · Flashcard
        "fc_order": [],
        "fc_pos": 0,
        "fc_flipped": False,
        "fc_known": [],
        "fc_unknown": [],
        "fc_anim": "enter",
        # Màn 5 · Trắc nghiệm
        "quiz_index": 0,
        "quiz_answers": {},
        "quiz_finished": False,
        "quiz_attempt": 0,
        "quiz_warning": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "library_db" not in st.session_state:
        st.session_state.library_db = build_seed_library()


init_session_state()
flush_pending_toast()


# ==========================================================
# 3. DỊCH VỤ API TRỰC TIẾP (BACKEND POST /api/v1/upload)
# ==========================================================
def check_backend_health(base_url: str = FASTAPI_BASE_URL) -> dict:
    """Kiểm tra trạng thái hoạt động của Backend FastAPI qua GET /health."""
    health_url = f"{base_url.rstrip('/')}{FASTAPI_HEALTH_ENDPOINT}"
    try:
        res = requests.get(health_url, timeout=2.0)
        if res.ok:
            data = res.json()
            return {
                "online": True,
                "status": data.get("status", "ok"),
                "database": data.get("database", "ok"),
                "ai_provider": data.get("ai_provider", "gemini"),
                "ai_configured": bool(data.get("ai_configured", False)),
            }
        return {"online": False, "error": f"HTTP {res.status_code}"}
    except Exception as exc:  # noqa: BLE001
        return {"online": False, "error": str(exc)}


def extract_backend_error(res_or_body) -> tuple[str, str]:
    """
    Trích xuất mã lỗi (code) và thông báo tiếng Việt (message) theo chuẩn ErrorResponse của smart_note_backend:
    {"status": "error", "error": {"code": "...", "message": "..."}}
    """
    body = res_or_body
    status_code = getattr(res_or_body, "status_code", 500)
    if hasattr(res_or_body, "json"):
        try:
            body = res_or_body.json()
        except Exception:  # noqa: BLE001
            body = {}
    if isinstance(body, dict):
        err_obj = body.get("error") if isinstance(body.get("error"), dict) else {}
        code = str(err_obj.get("code") or body.get("code") or f"HTTP_{status_code}")
        msg = str(
            err_obj.get("message")
            or body.get("message")
            or body.get("detail")
            or f"Backend trả về mã lỗi HTTP {status_code}."
        )
        return code, msg
    return f"HTTP_{status_code}", f"Backend trả về lỗi HTTP {status_code}."


def api_upload(
    file_info: dict,
    subject: str,
    simulate_error: bool = False,
    base_url: str = FASTAPI_BASE_URL,
    flashcard_count: int = DEFAULT_FLASHCARD_COUNT,
    quiz_count: int = DEFAULT_QUIZ_COUNT,
) -> dict:
    """
    Nối trực tiếp Endpoint POST /api/v1/upload từ Backend (smart_note_backend) vào Streamlit.
    Gửi multipart/form-data gồm file nhị phân (với MIME chuẩn) + flashcard_count + quiz_count
    tới {base_url}/api/v1/upload (nhận HTTP 201 Created), trích xuất dữ liệu thật từ AI (extracted_text,
    flashcards, quizzes) và chuẩn hoá hiển thị cho cả 6 màn hình.
    """
    if simulate_error:
        time.sleep(0.5)
        return {
            "status": "error",
            "code": "SIMULATED_QA_ERROR",
            "message": "[SIMULATED_QA_ERROR] Lỗi kết nối tới Endpoint /api/v1/upload (Giả lập lỗi QA 504). File của bạn vẫn được giữ nguyên — hãy bấm “Thử lại”.",
        }

    endpoint_url = f"{base_url.rstrip('/')}{FASTAPI_UPLOAD_ENDPOINT}"
    mime_type = canonical_mime_type(file_info["name"], file_info.get("type", ""))
    form_data = {
        "flashcard_count": str(max(1, min(20, int(flashcard_count)))),
        "quiz_count": str(max(1, min(20, int(quiz_count)))),
    }
    try:
        res = requests.post(
            endpoint_url,
            files={"file": (file_info["name"], file_info["bytes"], mime_type)},
            data=form_data,
            timeout=125,
        )
        body = {}
        try:
            body = res.json()
        except Exception:  # noqa: BLE001
            body = {}

        is_http_ok = getattr(res, "ok", True) and getattr(res, "status_code", 201) < 400
        if not is_http_ok or (isinstance(body, dict) and body.get("status") == "error"):
            code, msg = extract_backend_error(body if body else res)
            return {
                "status": "error",
                "code": code,
                "message": f"[{code}] {msg}",
                "raw_json": body,
            }

        study_set = normalize_study_set(body, fallback_subject=subject, fallback_file_name=file_info["name"])
        study_set["meta"] = body.get("meta") if isinstance(body.get("meta"), dict) else {
            "engine": "AI Backend (/api/v1/upload)",
            "detail": f"HTTP {getattr(res, 'status_code', 201)} · {len(study_set['flashcards'])} thẻ · {len(study_set['quizzes'])} câu hỏi",
        }
        return {
            "status": "success",
            "extracted_text": study_set["extracted_text"],
            "meta": study_set["meta"],
            "data": study_set,
            "raw_json": body,
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "code": "BACKEND_UNREACHABLE",
            "message": (
                f"[BACKEND_UNREACHABLE] Không kết nối được tới máy chủ FastAPI tại `{endpoint_url}`. "
                "Vui lòng bật Backend (`run_backend.bat` hoặc `uvicorn app.main:app --reload`) rồi bấm **Thử lại**."
            ),
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "code": "AI_TIMEOUT",
            "message": f"[AI_TIMEOUT] Quá thời gian chờ phản hồi từ `{endpoint_url}` (Timeout 125s). File vẫn được giữ nguyên — hãy bấm **Thử lại**.",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "code": type(exc).__name__,
            "message": f"[{type(exc).__name__}] Không gọi được Backend `{endpoint_url}` ({exc}). Hãy kiểm tra server FastAPI hoặc bấm “Thử lại”.",
        }


def api_finalize_study_set(
    raw_text: str,
    subject: str,
    file_name: str,
    simulate_error: bool = False,
    base_url: str = FASTAPI_BASE_URL,
) -> dict:
    """
    Hoàn tất bộ học liệu ở Màn 2 (Sinh nội dung):
    - Sử dụng trực tiếp dữ liệu AI thật trọn gói đã nhận từ POST /api/v1/upload (flashcards, quizzes)
      và cập nhật lại văn bản + bản tóm tắt theo nội dung người dùng vừa chỉnh sửa ở Màn 2.
    - Nếu bộ học liệu chưa có trong phiên, gọi trực tiếp POST /api/v1/upload từ Backend (tuyệt đối không dùng dữ liệu giả).
    """
    time.sleep(0.35)
    if simulate_error:
        return {
            "status": "error",
            "code": "SIMULATED_QA_ERROR",
            "message": "[SIMULATED_QA_ERROR] Lỗi từ dịch vụ AI khi sinh bộ câu hỏi. Văn bản của bạn vẫn được giữ nguyên — hãy bấm “Thử lại”.",
        }

    pending = copy.deepcopy(st.session_state.get("pending_study_set") or {})
    text_changed = raw_text.strip() != (st.session_state.get("extracted_text") or "").strip()

    if not pending or (not pending.get("flashcards") and not pending.get("quizzes")):
        if st.session_state.get("pending_file"):
            retry_res = api_upload(
                st.session_state.pending_file,
                subject,
                simulate_error=False,
                base_url=base_url,
                flashcard_count=st.session_state.get("flashcard_count", DEFAULT_FLASHCARD_COUNT),
                quiz_count=st.session_state.get("quiz_count", DEFAULT_QUIZ_COUNT),
            )
            if retry_res["status"] == "error":
                return retry_res
            pending = retry_res["data"]
        else:
            return {
                "status": "error",
                "code": "MISSING_UPLOAD_DATA",
                "message": "[MISSING_UPLOAD_DATA] Chưa có dữ liệu từ Endpoint /api/v1/upload. Vui lòng tải file lên và bấm “Bắt đầu xử lý”.",
            }

    pending["extracted_text"] = raw_text
    pending["subject"] = subject
    stem = file_name.rsplit(".", 1)[0].replace("_", " ").strip() or "Tài liệu mới"
    pending["title"] = f"{subject} - {stem}"
    if text_changed or not pending.get("summary"):
        pending["summary"] = synthesize_summary_from_ai_data(raw_text, pending.get("flashcards", []))
    return {"status": "success", "data": pending}


def render_error_alert_with_hint(error_state: tuple) -> None:
    """
    Component UI động hiển thị Alert lỗi từ Backend kèm hướng dẫn khắc phục theo mã lỗi.
    """
    msg = error_state[1] if len(error_state) > 1 else "Đã xảy ra lỗi khi gọi API."
    code = error_state[2] if len(error_state) > 2 else "API_ERROR"
    st.error(msg, icon=":material/cloud_off:")
    if code == "BACKEND_UNREACHABLE":
        st.warning(
            "**Gợi ý khắc phục:** Hãy mở Terminal chạy `.\\run_backend.bat` (hoặc `uvicorn app.main:app --reload` tại `smart_note_backend`) "
            "để bật máy chủ ở cổng `8000`, sau đó bấm **Thử lại**.",
            icon=":material/terminal:",
        )
    elif code in {"AI_NOT_CONFIGURED", "AI_AUTH_ERROR"}:
        st.warning(
            "**Gợi ý khắc phục:** Kiểm tra lại khoá `GEMINI_API_KEY` hoặc `OPENAI_API_KEY` trong file `smart_note_backend/.env`, "
            "sau đó bấm **Thử lại**.",
            icon=":material/key:",
        )
    elif code in {"NO_TEXT_DETECTED", "INVALID_IMAGE", "INVALID_PDF", "UNSUPPORTED_FILE_TYPE", "CONTENT_TYPE_MISMATCH"}:
        st.info(
            "**Gợi ý khắc phục:** Hãy chọn một ảnh chụp bảng/slide hoặc file PDF rõ nét, có chứa văn bản đọc được.",
            icon=":material/lightbulb:",
        )


# ==========================================================
# 4. SIDEBAR · MATERIAL NAVIGATION DRAWER
# ==========================================================
with st.sidebar:
    render_html(f"""
    <div class="md-brand"><div class="md-brand-logo">{icon("bolt")}</div>
    <div><div class="md-brand-name">Smart Note &amp; Quizzify</div>
    <div class="md-brand-sub">Trợ lý Học tập Tốc độ</div></div></div>
    """)
    render_html('<div class="md-nav-label">Điều hướng</div>')

    with st.container(key="nav_drawer"):
        is_create = st.session_state.nav_menu == "Tạo mới"
        if st.button("Tạo mới", key="nav_create", icon=":material/add_circle:",
                     type="primary" if is_create else "tertiary", width="stretch"):
            if not is_create:
                go_to("Tạo mới")
        lib_count = len(st.session_state.library_db)
        if st.button(f"Thư viện  ·  {lib_count}", key="nav_library", icon=":material/local_library:",
                     type="tertiary" if is_create else "primary", width="stretch"):
            if is_create:
                go_to("Thư viện")

    if st.session_state.nav_menu == "Tạo mới" and st.session_state.current_screen > 1:
        st.write("")
        if st.button("Tạo học liệu mới từ đầu", key="nav_reset", icon=":material/restart_alt:", width="stretch"):
            st.session_state.update({
                "current_screen": 1, "extracted_text": "", "draft_text": "", "pending_file": None,
                "uploaded_file_name": None, "extract_meta": None, "pending_study_set": None,
                "api_error_state": None, "uploader_key": st.session_state.uploader_key + 1,
            })
            st.session_state.pop("editor_text", None)
            st.rerun()

    current = st.session_state.current_study_set
    total_cards = sum(len(x["flashcards"]) for x in st.session_state.library_db)
    total_qs = sum(len(x["quizzes"]) for x in st.session_state.library_db)
    current_html = (f'<div class="md-side-card"><div class="t">Đang học</div>'
                    f'<div class="v">{esc(current["title"])}</div></div>') if current else ""
    render_html(f"""
    <div class="md-nav-label">Tổng quan</div>
    <div class="md-side-stats">
      <div class="md-side-stat"><b>{total_cards}</b><small>Flashcard</small></div>
      <div class="md-side-stat"><b>{total_qs}</b><small>Câu hỏi</small></div>
    </div>{current_html}
    <div class="md-nav-label">Công cụ</div>
    """)

    # Cấu hình kết nối trực tiếp Backend FastAPI (/api/v1/upload) & QA Test
    with st.expander("Cấu hình Dev / QA Test", icon=":material/build:", expanded=False):
        st.caption("Kết nối trực tiếp `POST /api/v1/upload` từ FastAPI Backend.")
        backend_base_url = st.text_input(
            "Backend Base URL",
            value=st.session_state.backend_base_url,
            key="input_backend_url",
            help="Địa chỉ máy chủ FastAPI cung cấp POST /api/v1/upload (mặc định http://127.0.0.1:8000)",
        )
        st.session_state.backend_base_url = backend_base_url.strip() or FASTAPI_BASE_URL
        st.caption(f"Endpoint: `{st.session_state.backend_base_url.rstrip('/')}{FASTAPI_UPLOAD_ENDPOINT}`")

        col_cnt1, col_cnt2 = st.columns(2)
        with col_cnt1:
            st.session_state.flashcard_count = st.number_input(
                "Số Flashcard", min_value=1, max_value=20, value=int(st.session_state.flashcard_count), key="num_fc_count"
            )
        with col_cnt2:
            st.session_state.quiz_count = st.number_input(
                "Số Quiz", min_value=1, max_value=20, value=int(st.session_state.quiz_count), key="num_quiz_count"
            )

        if st.button("Kiểm tra /health", key="btn_check_health", icon=":material/monitor_heart:", width="stretch"):
            st.session_state.backend_health = check_backend_health(st.session_state.backend_base_url)
            if st.session_state.backend_health.get("online"):
                st.toast("Kết nối Backend /health thành công!", icon=":material/check_circle:")
            else:
                st.toast("Không kết nối được Backend /health!", icon=":material/error:")
        if st.button("Đồng bộ SQLite", key="btn_sync_sqlite", icon=":material/sync:", width="stretch"):
            st.session_state.library_db = build_seed_library()
            queue_toast(f"Đã đồng bộ {len(st.session_state.library_db)} bộ học liệu từ smart_note.db!", ":material/check_circle:")
            st.rerun()

        if st.session_state.backend_health:
            bh = st.session_state.backend_health
            if bh.get("online"):
                ai_state = "AI Key: Sẵn sàng" if bh.get("ai_configured") else "AI Key: Chưa cấu hình (.env)"
                st.success(f"Backend OK · Provider: `{bh.get('ai_provider')}` · {ai_state}", icon=":material/cloud_done:")
            else:
                st.warning(f"Backend Offline ({bh.get('error')})", icon=":material/cloud_off:")

        simulate_api_error = st.checkbox("Giả lập lỗi kết nối API (Test nút Thử lại)", value=False,
                                         key="simulate_api_error")

        if st.session_state.last_raw_json:
            with st.popover("Xem JSON Response gần nhất", icon=":material/data_object:", use_container_width=True):
                st.json(st.session_state.last_raw_json)

        screen_no = st.session_state.current_screen if st.session_state.nav_menu == "Tạo mới" else 6
        st.caption(f"Màn hình hiện tại: **Màn {screen_no}**")


# ==========================================================
# 5. CÁC MÀN HÌNH THEO WIREFRAME
# ==========================================================

# ----------------------------------------------------------
# 5.1 · MÀN 1 (TẢI LÊN) & MÀN 2 (XEM VÀ SỬA VĂN BẢN)
# ----------------------------------------------------------
def validate_upload(file_obj):
    """Luồng ngoại lệ FR14 — kiểm tra định dạng & dung lượng. Trả về (hợp lệ, thông báo lỗi)."""
    ext = file_obj.name.rsplit(".", 1)[-1].lower() if "." in file_obj.name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, (f"Định dạng file “.{ext or '?'}” không hợp lệ! Chỉ chấp nhận JPG, PNG, WEBP, PDF, MP3, WAV, M4A. "
                       f"Vui lòng chọn lại file (Mã lỗi: FR14).")
    size_mb = file_obj.size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, (f"Dung lượng file ({size_mb:.1f} MB) vượt quá giới hạn {MAX_FILE_SIZE_MB} MB. "
                       f"Vui lòng chọn lại file nhẹ hơn (Mã lỗi: FR14).")
    return True, ""


def handle_extraction(progress_slot) -> None:
    """
    Gửi file trực tiếp lên POST /api/v1/upload kèm Progress Bar động + Spinner khi chờ AI xử lý
    và Toast + Alert khi có lỗi hoặc thành công.
    """
    file_info = st.session_state.pending_file
    if file_info is None:
        st.toast("Vui lòng chọn file học liệu hợp lệ trước khi xử lý!", icon=":material/warning:")
        st.error("Vui lòng chọn một file ảnh, PDF hoặc ghi âm hợp lệ trước khi bấm **Bắt đầu xử lý**.", icon=":material/upload_file:")
        return

    engine = "Speech-to-Text" if file_kind(file_info["name"]) == "audio" else "Vision OCR"
    fc_cnt = st.session_state.get("flashcard_count", DEFAULT_FLASHCARD_COUNT)
    qz_cnt = st.session_state.get("quiz_count", DEFAULT_QUIZ_COUNT)
    bar = progress_slot.progress(5, text=f"Đang khởi tạo kết nối tới {FASTAPI_UPLOAD_ENDPOINT} ({engine})…")

    with st.spinner(f"AI đang đọc file “{file_info['name']}”, trích xuất văn bản ({engine}) và biên soạn {fc_cnt} Flashcard & {qz_cnt} câu Quiz…"):
        time.sleep(0.15)
        bar.progress(25, text=f"Đang tải file lên POST {FASTAPI_UPLOAD_ENDPOINT}… 25%")
        time.sleep(0.15)
        bar.progress(55, text="AI đang nhận diện văn bản (OCR) và phân tích kiến thức trọng tâm… 55%")
        res = api_upload(
            file_info=file_info,
            subject=st.session_state.selected_subject,
            simulate_error=simulate_api_error,
            base_url=st.session_state.backend_base_url,
            flashcard_count=fc_cnt,
            quiz_count=qz_cnt,
        )

    if res["status"] == "error":
        progress_slot.empty()
        err_code = res.get("code", "API_ERROR")
        st.session_state.api_error_state = ("extract", res["message"], err_code)
        queue_toast(f"Lỗi xử lý ({err_code}): Vui lòng kiểm tra thông báo lỗi bên dưới!", ":material/error:")
        st.rerun()

    bar.progress(100, text="Hoàn tất nhận dữ liệu thật từ AI qua /api/v1/upload (HTTP 201)!")
    time.sleep(0.2)
    progress_slot.empty()

    # Lưu luôn vào Thư viện ngay khi nhận dữ liệu từ /api/v1/upload (đồng bộ với SQLite của Backend)
    if res.get("data"):
        existing_ids = [item.get("doc_id") for item in st.session_state.library_db]
        if res["data"].get("doc_id") in existing_ids:
            idx = existing_ids.index(res["data"]["doc_id"])
            st.session_state.library_db[idx] = res["data"]
        else:
            st.session_state.library_db.insert(0, res["data"])

    queue_toast(
        f"Trích xuất thành công! Đã tạo {len(res['data']['flashcards'])} Flashcard & {len(res['data']['quizzes'])} Quiz.",
        ":material/check_circle:",
    )
    st.session_state.update({
        "api_error_state": None,
        "uploaded_file_name": file_info["name"],
        "extract_meta": res.get("meta"),
        "extracted_text": res["extracted_text"],
        "draft_text": res["extracted_text"],
        "editor_text": res["extracted_text"],
        "pending_study_set": res.get("data"),
        "last_raw_json": res.get("raw_json"),
        "current_screen": 2,
    })
    st.rerun()


def handle_generation(progress_slot, text_to_process: str) -> None:
    """
    Đồng bộ văn bản đã kiểm tra ở Màn 2 và chuyển sang Màn 3 kèm Progress Bar + Spinner + Toast/Alert.
    """
    if not text_to_process.strip():
        st.toast("Văn bản trích xuất không được để trống!", icon=":material/error:")
        st.error("Văn bản trích xuất không được để trống!", icon=":material/error:")
        return

    bar = progress_slot.progress(10, text="AI đang phân tích ý chính từ văn bản…")
    with st.spinner("Đang tổng hợp bản Tóm tắt, đồng bộ Flashcard và câu hỏi Trắc nghiệm…"):
        for pct, msg in (
            (35, "Đang tổng hợp bản tóm tắt trọng tâm…"),
            (65, "Đang đồng bộ bộ thẻ Flashcard…"),
            (85, "Đang hoàn thiện bộ câu hỏi Trắc nghiệm…"),
        ):
            time.sleep(0.12)
            bar.progress(pct, text=f"{msg} {pct}%")
        res = api_finalize_study_set(
            raw_text=text_to_process,
            subject=st.session_state.selected_subject,
            file_name=st.session_state.uploaded_file_name or "Tai_lieu_moi.png",
            simulate_error=simulate_api_error,
            base_url=st.session_state.backend_base_url,
        )

    if res["status"] == "error":
        progress_slot.empty()
        err_code = res.get("code", "GENERATE_ERROR")
        st.session_state.api_error_state = ("generate", res["message"], err_code)
        queue_toast(f"Lỗi sinh nội dung ({err_code}) — hãy bấm Thử lại!", ":material/error:")
        st.rerun()

    bar.progress(100, text="Đã sinh học liệu thành công!")
    time.sleep(0.2)
    progress_slot.empty()
    st.session_state.api_error_state = None
    st.session_state.current_study_set = res["data"]
    # Cập nhật hoặc thêm mới vào Thư viện (tránh trùng lặp doc_id nếu sinh lại)
    existing_ids = [item.get("doc_id") for item in st.session_state.library_db]
    if res["data"].get("doc_id") in existing_ids:
        idx = existing_ids.index(res["data"]["doc_id"])
        st.session_state.library_db[idx] = res["data"]
    else:
        st.session_state.library_db.insert(0, res["data"])
    st.session_state.current_screen = 3
    queue_toast("Đã hoàn tất bộ học liệu và lưu vào Thư viện!", ":material/check_circle:")
    st.rerun()


def persist_draft() -> None:
    st.session_state.draft_text = st.session_state.editor_text


def render_create_upload_and_edit() -> None:
    render_hero(
        "add_circle", "Tạo mới",
        "Biến bài giảng thành bộ ôn tập",
        "Tải ảnh chụp bảng đen, slide hoặc PDF bài giảng — AI trích xuất văn bản qua /api/v1/upload, rồi tự động soạn "
        "tóm tắt, flashcard và câu hỏi trắc nghiệm cho bạn.",
        art_icon="auto_awesome",
        chips_html=(f'<span class="md-chip chip-primary">{icon("document_scanner")}OCR ảnh &amp; PDF</span>'
                    f'<span class="md-chip chip-indigo">{icon("cloud_upload")}POST /api/v1/upload</span>'
                    f'<span class="md-chip chip-amber">{icon("bolt")}Sinh nội dung bằng AI</span>'),
    )
    render_stepper(st.session_state.current_screen)

    # ---------------- MÀN 1 · TẢI LÊN ----------------
    with st.container(border=True, key="card_upload"):
        render_section("upload_file", "Màn 1 · Tải lên", "Chọn học liệu của bạn",
                       "Hỗ trợ ảnh/tài liệu <b>JPG, PNG, WEBP, PDF</b> và ghi âm <b>MP3, WAV, M4A</b> — dung lượng tối đa <b>25MB</b>.")

        uploaded_file = st.file_uploader(
            "Ảnh hoặc file ghi âm bài giảng",
            type=None,  # Không giới hạn ở widget để chủ động bắt lỗi FR14 bằng st.error
            key=f"uploader_{st.session_state.uploader_key}",
            label_visibility="collapsed",
        )

        upload_error = None
        if uploaded_file is not None:
            ok, upload_error = validate_upload(uploaded_file)
            if ok:
                if (st.session_state.pending_file is None
                        or st.session_state.pending_file["name"] != uploaded_file.name
                        or st.session_state.pending_file["size"] != uploaded_file.size):
                    st.session_state.pending_file = {
                        "name": uploaded_file.name, "size": uploaded_file.size,
                        "type": uploaded_file.type or "application/octet-stream",
                        "bytes": uploaded_file.getvalue(),
                    }
                    st.session_state.api_error_state = None
                    st.toast(f"Đã nhận file “{uploaded_file.name}” hợp lệ!", icon=":material/check_circle:")
            else:
                st.session_state.pending_file = None
                st.toast("File không hợp lệ (FR14) — vui lòng chọn lại!", icon=":material/error:")

        # Hiển thị file đã nhận / lỗi FR14 ngay lập tức
        if upload_error:
            st.error(upload_error, icon=":material/block:")
        elif st.session_state.pending_file:
            pf = st.session_state.pending_file
            kind = file_kind(pf["name"])
            ic, engine = ("graphic_eq", "Speech-to-Text") if kind == "audio" else ("image", "Vision OCR")
            render_html(f"""
            <div class="md-file-pill"><div class="md-file-icon {kind}">{icon(ic)}</div>
            <div style="flex:1;min-width:0"><div class="md-file-name">{esc(pf["name"])}</div>
            <div class="md-file-meta">{pf["size"] / (1024 * 1024):.2f} MB · Sẽ gửi trực tiếp tới /api/v1/upload ({engine})</div></div>
            <span class="md-chip chip-success">{icon("check_circle")}Hợp lệ</span></div>
            """)

        col_subj, col_btn = st.columns([3, 2], vertical_alignment="bottom")
        with col_subj:
            st.session_state.selected_subject = st.selectbox(
                "Môn học", options=SUBJECT_LIST,
                index=SUBJECT_LIST.index(st.session_state.selected_subject),
            )
        with col_btn:
            with st.container(key="btn_lg_upload"):
                start_clicked = st.button("Bắt đầu xử lý", type="primary", icon=":material/rocket_launch:",
                                          width="stretch", key="btn_start")

        progress_slot = st.empty()
        if start_clicked:
            if upload_error:
                st.toast("Không thể xử lý vì file vi phạm quy định FR14!", icon=":material/error:")
            else:
                handle_extraction(progress_slot)

        # Luồng ngoại lệ: API trích xuất lỗi → Alert chi tiết + nút Thử lại, giữ nguyên file đã tải
        if st.session_state.api_error_state and st.session_state.api_error_state[0] == "extract":
            render_error_alert_with_hint(st.session_state.api_error_state)
            with st.container(key="btn_retry_extract"):
                if st.button("Thử lại", icon=":material/refresh:", key="retry_extract"):
                    handle_extraction(progress_slot)

    # ---------------- MÀN 2 · XEM VÀ SỬA VĂN BẢN ----------------
    if st.session_state.current_screen == 2:
        st.write("")
        with st.container(border=True, key="card_edit"):
            render_section("edit_note", "Màn 2 · Xem và sửa văn bản", "Kiểm tra văn bản trích xuất",
                           "Sửa trực tiếp các từ/công thức nhận diện sai, hoặc bấm <b>Sinh nội dung</b> ngay nếu văn bản đã chuẩn.",
                           tone="indigo")

            if "editor_text" not in st.session_state:
                st.session_state.editor_text = st.session_state.draft_text or st.session_state.extracted_text

            meta = st.session_state.extract_meta or {}
            text_now = st.session_state.editor_text
            unsaved = text_now != st.session_state.extracted_text
            save_chip = (f'<span class="md-chip chip-amber">{icon("edit")}Có thay đổi chưa lưu</span>' if unsaved
                         else f'<span class="md-chip chip-success">{icon("cloud_done")}Đã lưu</span>')
            pending_set = st.session_state.get("pending_study_set") or {}
            ai_ready_chip = (
                f'<span class="md-chip chip-indigo">{icon("auto_awesome")}'
                f'AI đã soạn sẵn {len(pending_set.get("flashcards", []))} thẻ &amp; {len(pending_set.get("quizzes", []))} câu hỏi</span>'
                if pending_set.get("flashcards") or pending_set.get("quizzes") else ""
            )
            render_html(f"""
            <div class="md-meta-row">
              <span class="md-chip chip-primary">{icon("memory")}{esc(meta.get("engine", "AI"))}</span>
              <span class="md-chip chip-outline">{icon("info")}{esc(meta.get("detail", ""))}</span>
              <span class="md-chip chip-outline">{icon("notes")}{len(text_now.split())} từ</span>
              {ai_ready_chip}
              {save_chip}
            </div>
            """)

            st.text_area("Văn bản trích xuất (có thể sửa trực tiếp)", key="editor_text",
                         height=260, on_change=persist_draft)

            col_save, col_gen = st.columns([1, 2])
            with col_save:
                if st.button("Lưu", icon=":material/save:", width="stretch", key="btn_save"):
                    st.session_state.extracted_text = st.session_state.editor_text
                    st.session_state.draft_text = st.session_state.editor_text
                    queue_toast("Đã lưu nội dung chỉnh sửa!", ":material/check_circle:")
                    st.rerun()
            with col_gen:
                gen_clicked = st.button("Sinh nội dung", type="primary", icon=":material/auto_awesome:",
                                        width="stretch", key="btn_generate")

            gen_slot = st.empty()
            if gen_clicked:
                # Cho phép sinh ngay cả khi không sửa văn bản — dùng nội dung hiện có trong ô soạn thảo
                handle_generation(gen_slot, st.session_state.editor_text)

            # Luồng ngoại lệ: API sinh nội dung lỗi → Alert + nút Thử lại, giữ nguyên văn bản
            if st.session_state.api_error_state and st.session_state.api_error_state[0] == "generate":
                render_error_alert_with_hint(st.session_state.api_error_state)
                with st.container(key="btn_retry_generate"):
                    if st.button("Thử lại", icon=":material/refresh:", key="retry_generate"):
                        handle_generation(gen_slot, st.session_state.editor_text)


# ----------------------------------------------------------
# 5.2 · MÀN 3 · KẾT QUẢ
# ----------------------------------------------------------
def render_results() -> None:
    study_set = st.session_state.current_study_set
    kind = file_kind(study_set["file_name"])
    src_icon = "graphic_eq" if kind == "audio" else "image"
    render_hero(
        "task_alt", "Màn 3 · Kết quả · Đã lưu vào Thư viện",
        study_set["title"],
        chips_html=(subject_chip(study_set["subject"])
                    + f'<span class="md-chip chip-outline">{icon(src_icon)}{esc(study_set["file_name"])}</span>'
                    + f'<span class="md-chip chip-outline">{icon("schedule")}{esc(study_set["created_at"])}</span>'
                    + f'<span class="md-chip chip-primary">{icon("style")}{len(study_set["flashcards"])} thẻ</span>'
                    + f'<span class="md-chip chip-indigo">{icon("quiz")}{len(study_set["quizzes"])} câu hỏi</span>'),
    )
    render_stepper(3)

    with st.container(border=True, key="card_results"):
        tab_sum, tab_fc, tab_quiz = st.tabs([
            ":material/summarize: Tóm tắt",
            f":material/style: Flashcard ({len(study_set['flashcards'])})",
            f":material/quiz: Trắc nghiệm ({len(study_set['quizzes'])})",
        ])

        with tab_sum:
            render_section("summarize", "Tóm tắt", "Ý chính cần nhớ", tone="success")
            with st.container(key="md_summary"):
                st.markdown(study_set["summary"])

        with tab_fc:
            cards_html = []
            for idx, card in enumerate(study_set["flashcards"], 1):
                cards_html.append(f"""
                <div class="fc-mini" style="animation-delay:{idx * 60}ms">
                  <div class="fc-mini-front"><span class="md-chip chip-primary">{icon("help")}Thẻ {idx} · Mặt trước</span>
                  <div class="fc-mini-q">{esc(card["front_text"])}</div></div>
                  <div class="fc-mini-back"><span class="md-chip chip-indigo">{icon("lightbulb")}Mặt sau</span>
                  <div class="fc-mini-a">{esc(card["back_text"])}</div></div>
                </div>""")
            render_html(f'<div class="fc-grid">{"".join(cards_html)}</div>')

        with tab_quiz:
            for idx, q in enumerate(study_set["quizzes"], 1):
                opts = "".join(f'<div class="q-opt">{esc(o)}</div>' for o in q["options"])
                render_html(f"""
                <div class="q-preview"><div class="q-head"><span class="md-chip chip-indigo">{icon("quiz")}Câu {idx}</span></div>
                <div class="q-text">{esc(q["question"])}</div>{opts}</div>
                """)
                with st.expander("Xem đáp án & giải thích", icon=":material/visibility:"):
                    st.success(f"**Đáp án:** {q['correct_answer']}", icon=":material/check_circle:")
                    st.caption(f"Giải thích: {q['explanation']}")

    st.write("")
    render_section("school", "Bước tiếp theo", "Chọn chế độ ôn tập", "Ghi nhớ bằng flashcard hoặc tự kiểm tra bằng trắc nghiệm.")
    col_fc, col_quiz = st.columns(2)
    with col_fc:
        with st.container(key="btn_indigo"):
            with st.container(key="btn_lg_fc"):
                if st.button("Ôn flashcard", icon=":material/style:", width="stretch", key="btn_go_fc"):
                    start_flashcards()
                    st.rerun()
    with col_quiz:
        with st.container(key="btn_lg_quiz"):
            if st.button("Làm trắc nghiệm", type="primary", icon=":material/edit_square:",
                         width="stretch", key="btn_go_quiz"):
                start_quiz()
                st.rerun()


# ----------------------------------------------------------
# 5.3 · MÀN 4 · ÔN FLASHCARD
# ----------------------------------------------------------
def render_flashcards() -> None:
    study_set = st.session_state.current_study_set
    cards = study_set["flashcards"]
    if not st.session_state.fc_order:
        st.session_state.fc_order = list(range(len(cards)))
    order = st.session_state.fc_order
    total = len(order)
    pos = st.session_state.fc_pos

    render_hero("style", "Màn 4 · Ôn flashcard", "Ôn tập flashcard", esc(study_set["title"]), art_icon="style")
    render_stepper(4)

    if pos < total:
        st.progress((pos + 1) / total, text=f"Thẻ {pos + 1}/{total}")
        render_html(f"""
        <div class="fc-tally">
          <span class="md-chip chip-success">{icon("check_circle")}Đã nhớ: {len(st.session_state.fc_known)}</span>
          <span class="md-chip chip-error">{icon("replay")}Chưa nhớ: {len(st.session_state.fc_unknown)}</span>
          <span class="md-chip chip-outline">{icon("hourglass_top")}Còn lại: {total - pos}</span>
        </div>
        """)

        card = cards[order[pos]]
        flipped = st.session_state.fc_flipped
        side_cls = "back" if flipped else "front"
        anim_cls = "anim-flip" if st.session_state.fc_anim == "flip" else "anim-enter"
        label = f'{icon("lightbulb")}Mặt sau · Đáp án' if flipped else f'{icon("help")}Mặt trước · Câu hỏi'
        content = card["back_text"] if flipped else card["front_text"]
        hint = "Tự đánh giá: bạn đã nhớ thẻ này chưa?" if flipped else "Nhớ lại câu trả lời, rồi bấm “Lật thẻ”"
        render_html(f"""
        <div class="fc-card {side_cls} {anim_cls}" role="region" aria-label="Flashcard">
          <span class="fc-side">{label}</span><span class="fc-count">{pos + 1} / {total}</span>
          <div class="fc-content">{esc(content)}</div>
          <div class="fc-hint">{icon("touch_app", "font-size:18px")}{hint}</div>
        </div>
        """)

        with st.container(key="btn_tonal_flip"):
            if st.button("Lật về mặt trước" if flipped else "Lật thẻ", icon=":material/flip:",
                         width="stretch", key="btn_flip"):
                flip_flashcard_state()
                st.rerun()

        col_no, col_yes = st.columns(2)
        with col_no:
            with st.container(key="btn_outline_error"):
                if st.button("Chưa nhớ", icon=":material/replay:", width="stretch", key="btn_unknown"):
                    record_flashcard_review(order[pos], is_known=False)
                    st.rerun()
        with col_yes:
            with st.container(key="btn_success"):
                if st.button("Đã nhớ", type="primary", icon=":material/check_circle:", width="stretch", key="btn_known"):
                    record_flashcard_review(order[pos], is_known=True)
                    st.rerun()
    else:
        known, unknown = len(st.session_state.fc_known), len(st.session_state.fc_unknown)
        pct = int(known / total * 100) if total else 0
        ring = "var(--md-success)" if pct >= 80 else ("var(--md-amber)" if pct >= 50 else "var(--md-error)")
        render_html(f"""
        <div class="score-hero"><div class="score-ring" style="--p:{pct};--ring:{ring}">
        <div class="score-ring-inner"><b>{pct}%</b><small>Đã nhớ</small></div></div>
        <div><div class="score-title">Hoàn thành lượt ôn!</div>
        <div class="score-sub">Bạn đã ôn {total} thẻ của bộ “{esc(study_set["title"])}”.</div></div></div>
        """)
        c1, c2, c3 = st.columns(3)
        with c1, st.container(key="metric_success_fc"):
            st.metric("Đã nhớ", f"{known} thẻ")
        with c2, st.container(key="metric_error_fc"):
            st.metric("Chưa nhớ", f"{unknown} thẻ")
        with c3, st.container(key="metric_indigo_fc"):
            st.metric("Tổng số thẻ", f"{total}")

        st.write("")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if unknown:
                with st.container(key="btn_tonal_retry"):
                    if st.button(f"Ôn lại {unknown} thẻ chưa nhớ", icon=":material/replay:", width="stretch", key="fc_re_unknown"):
                        start_flashcards(st.session_state.fc_unknown)
                        st.rerun()
            elif st.button("Ôn lại cả bộ", icon=":material/restart_alt:", width="stretch", key="fc_re_all"):
                start_flashcards()
                st.rerun()
        with col_b:
            if st.button("Làm trắc nghiệm", type="primary", icon=":material/edit_square:", width="stretch", key="fc_to_quiz"):
                start_quiz()
                st.rerun()
        with col_c:
            if st.button("Về Thư viện", icon=":material/local_library:", width="stretch", key="fc_to_lib"):
                go_to("Thư viện")

    st.divider()
    if st.button("Quay lại Kết quả", type="tertiary", icon=":material/arrow_back:", key="fc_back"):
        go_to("Tạo mới", 3)


# ----------------------------------------------------------
# 5.4 · MÀN 5 · LÀM TRẮC NGHIỆM
# ----------------------------------------------------------
def render_quiz() -> None:
    study_set = st.session_state.current_study_set
    quizzes = study_set["quizzes"]
    total = len(quizzes)
    q_idx = st.session_state.quiz_index

    render_hero("edit_square", "Màn 5 · Làm trắc nghiệm", "Tự kiểm tra kiến thức", esc(study_set["title"]), art_icon="quiz")
    render_stepper(5)

    if not st.session_state.quiz_finished and q_idx < total:
        st.progress((q_idx + 1) / total, text=f"Câu {q_idx + 1}/{total}")
        q = quizzes[q_idx]
        with st.container(border=True, key="card_quiz"):
            render_html(f"""
            <div class="q-head"><span class="md-chip chip-primary">{icon("quiz")}Câu {q_idx + 1}/{total}</span>
            {subject_chip(study_set["subject"])}</div>
            <div class="q-text">{esc(q["question"])}</div>
            """)
            selected = st.radio("Chọn đáp án đúng nhất:", options=q["options"], index=None,
                                key=f"quiz_{st.session_state.quiz_attempt}_{q_idx}")
            if st.session_state.quiz_warning and selected is None:
                st.warning("Vui lòng chọn một đáp án trước khi sang câu tiếp theo!", icon=":material/warning:")

            is_last = q_idx + 1 == total
            with st.container(key="btn_lg_next"):
                if st.button("Nộp bài & xem điểm" if is_last else "Câu tiếp", type="primary",
                             icon=":material/flag:" if is_last else ":material/arrow_forward:",
                             width="stretch", key="btn_next_q"):
                    if selected is None:
                        st.session_state.quiz_warning = True
                    else:
                        st.session_state.quiz_warning = False
                        st.session_state.quiz_answers[q_idx] = selected
                        if is_last:
                            st.session_state.quiz_finished = True
                        else:
                            st.session_state.quiz_index += 1
                    st.rerun()
    else:
        score_report = calculate_quiz_score(quizzes, st.session_state.quiz_answers)
        correct = score_report["correct"]
        wrong = score_report["wrong"]
        pct = score_report["pct"]
        study_set["last_score"] = score_report["last_score"]  # Lưu điểm gần nhất vào Thư viện
        ring = "var(--md-success)" if pct >= 80 else ("var(--md-amber)" if pct >= 50 else "var(--md-error)")
        title = "Xuất sắc! 🎉" if pct >= 80 else ("Khá tốt, cố thêm chút nữa!" if pct >= 50 else "Cần ôn thêm nhé!")
        render_html(f"""
        <div class="score-hero"><div class="score-ring" style="--p:{pct};--ring:{ring}">
        <div class="score-ring-inner"><b>{pct}%</b><small>Chính xác</small></div></div>
        <div><div class="score-title">{title}</div>
        <div class="score-sub">Kết quả đã được lưu vào Thư viện · Điểm gần nhất: <b>{correct}/{total}</b></div></div></div>
        """)

        c1, c2, c3 = st.columns(3)
        with c1, st.container(key="metric_indigo_quiz"):
            st.metric("Tổng điểm", f"{correct}/{total}")
        with c2, st.container(key="metric_success_quiz"):
            st.metric("Câu đúng", f"{correct}")
        with c3, st.container(key="metric_error_quiz"):
            st.metric("Câu sai", f"{wrong}")

        st.write("")
        render_section("fact_check", "Chi tiết", "Đáp án & giải thích", tone="success")
        for item in score_report["details"]:
            i = item["index"]
            user_ans = item["user_answer"]
            ok = item["is_correct"]
            with st.expander(f"Câu {i + 1}: {item['question']}", expanded=not ok,
                             icon=":material/check_circle:" if ok else ":material/cancel:"):
                render_html(f"""
                <div class="ans-row {'ans-ok' if ok else 'ans-bad'}">{icon('person')}
                <div><small>Lựa chọn của bạn · {'Đúng' if ok else 'Sai'}</small><div class="v">{esc(user_ans)}</div></div></div>
                <div class="ans-row ans-key">{icon('verified')}
                <div><small>Đáp án đúng</small><div class="v">{esc(item['correct_answer'])}</div></div></div>
                """)
                st.info(f"**Giải thích:** {item['explanation']}", icon=":material/lightbulb:")

        st.write("")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("Làm lại đề này", icon=":material/restart_alt:", width="stretch", key="quiz_retry"):
                start_quiz()
                st.rerun()
        with col_b:
            if st.button("Xem lại Kết quả", icon=":material/summarize:", width="stretch", key="quiz_to_res"):
                go_to("Tạo mới", 3)
        with col_c:
            if st.button("Về Thư viện", type="primary", icon=":material/local_library:", width="stretch", key="quiz_to_lib"):
                go_to("Thư viện")

    st.divider()
    if st.button("Quay lại Kết quả", type="tertiary", icon=":material/arrow_back:", key="quiz_back"):
        go_to("Tạo mới", 3)


# ----------------------------------------------------------
# 5.5 · MÀN 6 · THƯ VIỆN
# ----------------------------------------------------------
def render_library() -> None:
    library = st.session_state.library_db
    render_hero(
        "local_library", "Màn 6 · Thư viện",
        "Thư viện học liệu của bạn",
        "Tra cứu và mở lại ngay các bộ thẻ, câu hỏi trắc nghiệm đã lưu — không cần tải lên lại.",
        art_icon="collections_bookmark",
    )

    total_cards = sum(len(x["flashcards"]) for x in library)
    total_qs = sum(len(x["quizzes"]) for x in library)
    render_html(f"""
    <div class="md-stats-row">
      <div class="md-stat-tile"><div class="ic" style="background:var(--md-primary-tint);color:var(--md-primary)">{icon("folder_open")}</div>
      <div><b>{len(library)}</b><small>Bộ học liệu</small></div></div>
      <div class="md-stat-tile" style="animation-delay:60ms"><div class="ic" style="background:var(--md-indigo-tint);color:var(--md-indigo)">{icon("style")}</div>
      <div><b>{total_cards}</b><small>Flashcard</small></div></div>
      <div class="md-stat-tile" style="animation-delay:120ms"><div class="ic" style="background:var(--md-amber-tint);color:var(--md-amber-ink)">{icon("quiz")}</div>
      <div><b>{total_qs}</b><small>Câu hỏi trắc nghiệm</small></div></div>
    </div>
    """)

    with st.container(border=True, key="card_search"):
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            query = st.text_input("Tìm bộ thẻ", placeholder="Nhập tên bài, môn học hoặc tên file…",
                                  icon=":material/search:", key="lib_search")
        with col_filter:
            subject_filter = st.selectbox("Môn học", options=["Tất cả môn học"] + SUBJECT_LIST, key="lib_filter")

    q = query.strip().lower()
    results = [
        item for item in library
        if (subject_filter == "Tất cả môn học" or item["subject"] == subject_filter)
        and (not q or q in item["title"].lower() or q in item["file_name"].lower() or q in item["subject"].lower())
    ]

    render_html(f'<div class="md-results-label">Hiển thị {len(results)} / {len(library)} bộ học liệu</div>')

    if not results:
        with st.container(border=True, key="card_empty"):
            render_html(f"""
            <div class="md-empty">{icon("search_off")}<b>Không tìm thấy bộ thẻ phù hợp</b>
            Thử từ khoá khác hoặc chọn “Tất cả môn học”.</div>
            """)
        return

    for row_start in range(0, len(results), 2):
        cols = st.columns(2)
        for col, item in zip(cols, results[row_start:row_start + 2]):
            with col:
                with st.container(border=True, key=f"card_lib_{item['doc_id']}"):
                    kind = file_kind(item["file_name"])
                    src = "graphic_eq" if kind == "audio" else "image"
                    score = item.get("last_score", "Chưa làm")
                    level = score_level(score)
                    render_html(f"""
                    <div class="lib-top">{subject_chip(item["subject"])}
                    <span class="lib-src {kind}" title="{'Ghi âm' if kind == 'audio' else 'Ảnh'}">{icon(src)}</span></div>
                    <div class="lib-title">{esc(item["title"])}</div>
                    <div class="lib-file">{icon("attach_file")}{esc(item["file_name"])} · {icon("schedule")}{esc(item["created_at"])}</div>
                    <div class="lib-stats">
                      <div class="lib-stat"><b>{len(item["flashcards"])}</b><small>Thẻ</small></div>
                      <div class="lib-stat"><b>{len(item["quizzes"])}</b><small>Câu hỏi</small></div>
                      <div class="lib-stat {level}"><b>{esc(score.split(" ")[0] if level != "none" else "—")}</b><small>Điểm gần nhất</small></div>
                    </div>
                    """)
                    # Luồng FR10: Mở thẳng bộ thẻ → Màn 3, bỏ qua bước tải lên
                    if st.button("Mở", key=f"open_{item['doc_id']}", type="primary",
                                 icon=":material/open_in_new:", width="stretch"):
                        st.session_state.current_study_set = item
                        st.session_state.api_error_state = None
                        go_to("Tạo mới", 3)


# ==========================================================
# 6. ROUTER
# ==========================================================
if st.session_state.nav_menu == "Thư viện":
    render_library()
else:
    screen = st.session_state.current_screen
    if screen in (3, 4, 5) and st.session_state.current_study_set is None:
        st.session_state.current_screen = screen = 1
    if screen in (1, 2):
        render_create_upload_and_edit()
    elif screen == 3:
        render_results()
    elif screen == 4:
        render_flashcards()
    elif screen == 5:
        render_quiz()