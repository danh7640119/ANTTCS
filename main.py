import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Lịch trực ANTTCS", layout="wide")

# CSS (Giữ nguyên để hiển thị Card đẹp như hình bạn chụp)
st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 10px; border-radius: 5px; border-left: 5px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 20px; border-radius: 10px; border-left: 8px solid #1E3A8A; background-color: white; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 15px; }
    .name-text { color: #1E3A8A; font-size: 20px; font-weight: bold; }
    .location-tag { margin-top: 15px; font-weight: bold; color: #059669; background-color: #ECFDF5; padding: 5px 10px; border-radius: 5px; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. LẤY THỜI GIAN TUẦN (Ô G1)
    header_df = conn.read(spreadsheet=url, ttl=0, worksheet="1567366671", nrows=1, header=None)
    thoi_gian_tuan = header_df.iloc[0, 6] if not header_df.empty else "Dữ liệu lịch trực"
    
    st.title("📋 HỆ THỐNG TRA CỨU LỊCH TRỰC")
    st.markdown(f'<div class="time-box">📅 Đang xem: {thoi_gian_tuan}</div>', unsafe_allow_html=True)

    # 2. ĐỌC DỮ LIỆU BẢNG (Dùng skiprows=4 để lấy dòng 5 làm tiêu đề)
    # Theo ảnh: Dòng 5 chứa "1", "Tân Lợi", "Hồ Thế Lập"...
    raw_df = conn.read(spreadsheet=url, ttl=0, worksheet="1567366671", skiprows=5)

    # 3. ĐỊNH NGHĨA CỘT (Khớp 100% với ảnh: Ngày | Đêm-CAX | Đêm-Ấp)
    # Tổng cộng mỗi ngày có 3 cột dữ liệu trực
    columns = ["STT", "Ap", "HoTen", "ChucVu"]
    days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for day in days:
        columns.append(f"{day}_N")      # Cột Ngày
        columns.append(f"{day}_D_CAX")  # Cột Đêm - CAX
        columns.append(f"{day}_D_Ap")   # Cột Đêm - Ấp
    
    # Gán tên cột (Cắt bớt nếu file không đủ cột hoặc lấy đủ nếu file thừa)
    raw_df.columns = columns[:len(raw_df.columns)]
    
    # Làm sạch: Loại bỏ dòng phụ và khoảng trắng
    df = raw_df.dropna(subset=['HoTen']).copy()
    for col in df.columns[4:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # 4. BỘ LỌC SIDEBAR
    selected_day = st.sidebar.selectbox("📅 Chọn ngày:", ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"])
    selected_shift = st.sidebar.radio("⏰ Chọn ca trực:", ["Sáng", "Đêm"])

    day_map = {"Thứ 2":"T2", "Thứ 3":"T3", "Thứ 4":"T4", "Thứ 5":"T5", "Thứ 6":"T6", "Thứ 7":"T7", "Chủ nhật":"CN"}
    d = day_map[selected_day]

    # 5. LOGIC LỌC NGƯỜI TRỰC
    if selected_shift == "Sáng":
        # Ca sáng lọc theo cột Ngày (_N)
        on_duty = df[df[f"{d}_N"] == 'x']
    else:
        # Ca đêm lọc theo 2 cột Đêm (_D_CAX và _D_Ap)
        on_duty = df[(df[f"{d}_D_CAX"] == 'x') | (df[f"{d}_D_Ap"] == 'x')]

    st.subheader(f"🚩 Danh sách trực: {selected_day} - Ca {selected_shift}")

    if not on_duty.empty:
        cols = st.columns(3)
        for idx, (_, row) in enumerate(on_duty.iterrows()):
            with cols[idx % 3]:
                # Xác định vị trí
                if selected_shift == "Sáng":
                    vi_tri = "Tại Công an xã"
                else:
                    vi_tri = "Tại Công an xã" if row[f"{d}_D_CAX"] == 'x' else f"Tại Ấp ({row['Ap']})"
                
                st.markdown(f"""
                    <div class="duty-card">
                        <div class="name-text">{row['HoTen']}</div>
                        <div class="info-text">🎖️ <b>Chức vụ:</b> {row['ChucVu']}</div>
                        <div class="info-text">🏠 <b>Đơn vị:</b> {row['Ap']}</div>
                        <div class="location-tag">📍 {vi_tri}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("Không có dữ liệu trực. Hãy kiểm tra dấu 'x' trong file.")

except Exception as e:
    st.error(f"Lỗi: {e}")

