import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Lịch trực ANTTCS", layout="wide", page_icon="📋")

# --- CSS TÙY CHỈNH ---
st.markdown("""
    <style>
    .time-box {
        background-color: #F3F4F6;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #1E3A8A;
        margin-bottom: 20px;
        font-weight: bold;
        color: #1E3A8A;
    }
    .duty-card {
        padding: 20px; border-radius: 10px; border-left: 8px solid #1E3A8A;
        background-color: white; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px; min-height: 140px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 HỆ THỐNG TRA CỨU LỊCH TRỰC")

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. LẤY THÔNG TIN TUẦN TỪ Ô G1
    header_df = conn.read(spreadsheet=url, ttl=0, worksheet="1567366671", nrows=1, header=None)
    thoi_gian_tuan = header_df.iloc[0, 6] if not header_df.empty else "Không rõ thời gian"
    
    # Hiển thị thông tin tuần ra màn hình
    st.markdown(f'<div class="time-box">📅 Đang xem: {thoi_gian_tuan}</div>', unsafe_allow_html=True)

    # 2. ĐỌC DỮ LIỆU BẢNG TRỰC
    raw_df = conn.read(spreadsheet=url, ttl=0, worksheet="1567366671", skiprows=3)

    # 3. ĐẶT TÊN CỘT (Cấu trúc 3 cột/ngày như đã sửa)
    columns = ["STT", "Ap", "HoTen", "ChucVu"]
    days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for day in days:
        columns.extend([f"{day}_N", f"{day}_D_CAX", f"{day}_D_Ap"])
    
    raw_df.columns = columns[:len(raw_df.columns)]
    df = raw_df.dropna(subset=['HoTen']).copy()
    for col in df.columns[4:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # 4. BỘ LỌC VÀ LOGIC HIỂN THỊ (Giữ nguyên phần logic ban ngày/ban đêm của bạn)
    # ... [Phần code lọc và hiển thị Card giống như bài trước] ...
    
    # (Ví dụ nhanh phần lọc)
    selected_day_name = st.sidebar.selectbox("📅 Chọn ngày:", ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"])
    selected_shift = st.sidebar.radio("⏰ Chọn ca:", ["Sáng", "Đêm"])
    day_map = {"Thứ 2":"T2", "Thứ 3":"T3", "Thứ 4":"T4", "Thứ 5":"T5", "Thứ 6":"T6", "Thứ 7":"T7", "Chủ nhật":"CN"}
    d_code = day_map[selected_day_name]

    if selected_shift == "Sáng":
        on_duty = df[df[f"{d_code}_N"] == 'x']
    else:
        on_duty = df[(df[f"{d_code}_D_CAX"] == 'x') | (df[f"{d_code}_D_Ap"] == 'x')]

    st.subheader(f"🚩 Danh sách trực: {selected_day_name} - Ca {selected_shift}")
    # ... [Hiển thị card] ...

except Exception as e:
    st.error(f"Lỗi: {e}")
