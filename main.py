import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Lịch trực ANTT", layout="wide", page_icon="📋")

# --- CSS TÙY CHỈNH ---
st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 15px; border-radius: 12px; border-left: 8px solid #1E3A8A; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; }
    .double-duty { background-color: #FFFBEB; border-left: 8px solid #F59E0B; border: 1px solid #FDE68A; }
    .name-text { color: #1E3A8A; font-size: 18px; font-weight: bold; }
    .location-tag { margin-top: 10px; font-weight: bold; color: #059669; background-color: #ECFDF5; padding: 4px 10px; border-radius: 6px; display: inline-block; font-size: 13px; }
    .group-header { background-color: #1E3A8A; color: white; padding: 8px 15px; border-radius: 5px; margin-top: 20px; margin-bottom: 15px; font-weight: bold; }
    .count-badge { background-color: #E5E7EB; color: #1F2937; padding: 2px 8px; border-radius: 10px; font-size: 14px; margin-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. ĐỌC DỮ LIỆU
    df_raw = conn.read(spreadsheet=url, ttl=0, worksheet="1727254590", skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    for col in df.columns[3:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # --- TỰ ĐỘNG XÁC ĐỊNH TUẦN HIỆN TẠI ---
    list_weeks = df['Tuan'].unique().tolist()
    today_str = datetime.now().strftime("%d/%m") # Lấy định dạng ngày/tháng (VD: 09/02)
    
    # Tìm tuần nào chứa ngày hôm nay trong chuỗi văn bản (VD: "Tuần 02 (09/02 - 15/02)")
    default_index = 0
    for i, week_name in enumerate(list_weeks):
        if today_str in str(week_name):
            default_index = i
            break

    st.title("📋 TRA CỨU QUÂN SỐ TRỰC")

    # --- Ô TÌM KIẾM ---
    search_query = st.text_input("🔍 Nhập tên để tra cứu lịch cá nhân:", "").strip().lower()
    # ... (giữ nguyên logic search cũ của bạn) ...

    # --- BỘ LỌC SIDEBAR ---
    st.sidebar.header("📅 THỜI GIAN TRỰC")
    
    # Sử dụng index đã tính toán để mặc định chọn tuần đúng
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks, index=default_index)
    
    # Tự động chọn Thứ dựa trên ngày hiện tại
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    today_weekday = datetime.now().weekday() # Thứ 2 là 0, CN là 6
    selected_day = st.sidebar.selectbox("Chọn ngày:", days_vn, index=today_weekday)
    
    selected_shift = st.sidebar.radio("Chọn ca trực:", ["Sáng", "Đêm"], horizontal=True)

    # --- HIỂN THỊ DANH SÁCH (giữ nguyên logic cũ) ---
    day_map = dict(zip(days_vn, day_codes))
    d = day_map[selected_day]
    df_week = df[df['Tuan'] == selected_week]
    
    # ... (phần hiển thị Card và đếm quân số giữ nguyên như cũ) ...

except Exception as e:
    st.error(f"Lỗi: {e}")
