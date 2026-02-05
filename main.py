import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Lịch trực ANTT", layout="wide", page_icon="📋")

# --- CSS TÙY CHỈNH NÂNG CAO ---
st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 15px; border-radius: 12px; border-left: 8px solid #1E3A8A; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; }
    /* Màu đặc biệt cho người trực cả ngày lẫn đêm */
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
    
    # Đọc dữ liệu từ Sheet Lưu Trữ
    df_raw = conn.read(spreadsheet=url, ttl=0, worksheet="LuuTru", skiprows=0)

    # Định nghĩa cột
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    # Làm sạch dữ liệu 'x'
    for col in df.columns[3:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # --- BỘ LỌC SIDEBAR ---
    st.sidebar.header("📅 THỜI GIAN TRỰC")
    list_weeks = df['Tuan'].unique().tolist()
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks)
    
    list_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn ngày:", list_days)
    selected_shift = st.sidebar.radio("Chọn ca trực:", ["Sáng", "Đêm"], horizontal=True)

    # Xử lý logic mã ngày
    day_map = dict(zip(list_days, day_codes))
    d = day_map[selected_day]
    
    # Lọc dữ liệu theo tuần và ngày đã chọn
    df_week = df[df['Tuan'] == selected_week]

    # --- HIỂN THỊ ---
    st.title("📋 TRA CỨU QUÂN SỐ TRỰC")
    st.markdown(f'<div class="time-box">📅 {selected_week} | {selected_day} | Ca {selected_shift}</div>', unsafe_allow_html=True)

    if selected_shift == "Sáng":
        on_duty = df_week[df_week[f"{d}_N"] == 'x']
        st.markdown(f'<div class="group-header">DANH SÁCH TRỰC BAN NGÀY <span class="count-badge">Tổng: {len(on_duty)} đ/c</span></div>', unsafe_allow_html=True)
        
        if not on_duty.empty:
            grid = st.columns(3)
            for idx, (_, row) in enumerate(on_duty.iterrows()):
                with grid[idx % 3]:
                    st.markdown(f"""
                        <div class="duty-card">
                            <div class="name-text">{row['HoTen']}</div>
                            <div class="info-text">🏠 Đơn vị: {row['Ap']}</div>
                            <div class="location-tag">📍 Tại Công an xã</div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Không có dữ liệu trực sáng.")

    else:
        # CA ĐÊM: PHÂN NHÓM
        cax_duty = df_week[df_week[f"{d}_D_CAX"] == 'x']
        ap_duty = df_week[df_week[f"{d}_D_Ap"] == 'x']
        
        # Lấy danh sách những người trực sáng để so sánh (tô màu)
        morning_duty_list = df_week[df_week[f"{d}_N"] == 'x']['HoTen'].tolist()

        st.markdown(f'<div class="group-header">TỔNG QUÂN SỐ TRỰC ĐÊM <span class="count-badge">Tổng: {len(cax_duty) + len(ap_duty)} đ/c</span></div>', unsafe_allow_html=True)

        # 1. Nhóm Công an xã
        st.markdown("#### 🏢 Nhóm trực tại Công an xã")
        if not cax_duty.empty:
            grid_cax = st.columns(3)
            for idx, (_, row) in enumerate(cax_duty.iterrows()):
                is_double = "double-duty" if row['HoTen'] in morning_duty_list else ""
                note = "<br><small>⚠️ <i>Có trực ca sáng</i></small>" if is_double else ""
                with grid_cax[idx % 3]:
                    st.markdown(f"""
                        <div class="duty-card {is_double}">
                            <div class="name-text">{row['HoTen']}</div>
                            <div class="info-text">🏠 Đơn vị: {row['Ap']}</div>
                            <div class="location-tag">📍 Tại Công an xã</div>{note}
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Không có người trực tại CAX.")

        # 2. Nhóm Ấp
        st.markdown("#### 🏘️ Nhóm trực tại các Ấp")
        if not ap_duty.empty:
            grid_ap = st.columns(3)
            for idx, (_, row) in enumerate(ap_duty.iterrows()):
                is_double = "double-duty" if row['HoTen'] in morning_duty_list else ""
                note = "<br><small>⚠️ <i>Có trực ca sáng</i></small>" if is_double else ""
                with grid_ap[idx % 3]:
                    st.markdown(f"""
                        <div class="duty-card {is_double}">
                            <div class="name-text">{row['HoTen']}</div>
                            <div class="info-text">🏠 Đơn vị: {row['Ap']}</div>
                            <div class="location-tag">📍 Tại Ấp {row['Ap']}</div>{note}
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Không có người trực tại Ấp.")

except Exception as e:
    st.error(f"Lỗi: {e}")
