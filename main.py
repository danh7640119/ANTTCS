import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Lịch trực ANTTCS", layout="wide", page_icon="📋")

# --- CSS TÙY CHỈNH (Khớp giao diện bạn đang dùng) ---
st.markdown("""
    <style>
    .time-box { 
        background-color: #F3F4F6; padding: 12px; border-radius: 8px; 
        border-left: 6px solid #1E3A8A; margin-bottom: 20px; 
        font-weight: bold; color: #1E3A8A; font-size: 18px;
    }
    .duty-card { 
        padding: 20px; border-radius: 12px; border-left: 8px solid #1E3A8A; 
        background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        margin-bottom: 15px; min-height: 160px;
    }
    .name-text { color: #1E3A8A; font-size: 20px; font-weight: bold; }
    .info-text { color: #4B5563; font-size: 14px; margin-top: 6px; }
    .location-tag { 
        margin-top: 15px; font-weight: bold; color: #059669; 
        background-color: #ECFDF5; padding: 6px 12px; border-radius: 6px; 
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 TRA CỨU LỊCH TRỰC TRỰC TUYẾN")

try:
    # --- KẾT NỐI ---
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. LẤY THỜI GIAN TUẦN (Ô G1)
    header_df = conn.read(spreadsheet=url, ttl=0, worksheet="1567366671", nrows=1, header=None)
    thoi_gian_tuan = header_df.iloc[0, 6] if not header_df.empty else "Dữ liệu lịch trực"
    st.markdown(f'<div class="time-box">📅 Đang xem: {thoi_gian_tuan}</div>', unsafe_allow_html=True)

    # 2. ĐỌC DỮ LIỆU BẢNG (Dùng skiprows=4 để khớp dòng 5 làm tiêu đề)
    # Dòng 5 chứa các tiêu đề: STT, Ấp, Họ tên, Chức vụ...
    raw_df = conn.read(spreadsheet=url, ttl=0, worksheet="1567366671", skiprows=3)

    # 3. ĐỊNH NGHĨA CỘT (Khớp 100% ảnh: 3 cột mỗi ngày)
    columns = ["STT", "Ap", "HoTen", "ChucVu"]
    days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    
    for code in day_codes:
        columns.append(f"{code}_N")      # Cột Ngày
        columns.append(f"{code}_D_CAX")  # Cột Đêm - CAX
        columns.append(f"{code}_D_Ap")   # Cột Đêm - Ấp
    
    # Gán tên cột và làm sạch dữ liệu
    raw_df.columns = columns[:len(raw_df.columns)]
    df = raw_df.dropna(subset=['HoTen']).copy()
    
    # Làm sạch dấu 'x' (chuyển về chữ thường, xóa khoảng trắng)
    for col in df.columns[4:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # 4. BỘ LỌC SIDEBAR
    st.sidebar.header("🔍 TÙY CHỌN TRA CỨU")
    selected_day = st.sidebar.selectbox("📅 Chọn ngày:", days)
    selected_shift = st.sidebar.radio("⏰ Chọn ca trực:", ["Sáng", "Đêm"])

    # Map tên ngày sang mã cột
    d_map = dict(zip(days, day_codes))
    d = d_map[selected_day]

    # 5. LOGIC LỌC NGƯỜI TRỰC
    if selected_shift == "Sáng":
        # Ca sáng chỉ lọc ở cột Ngày
        on_duty = df[df[f"{d}_N"] == 'x']
    else:
        # Ca đêm lọc ở cả cột Đêm-CAX và Đêm-Ấp
        on_duty = df[(df[f"{d}_D_CAX"] == 'x') | (df[f"{d}_D_Ap"] == 'x')]

    # 6. HIỂN THỊ KẾT QUẢ
    st.subheader(f"🚩 Danh sách trực: {selected_day} - Ca {selected_shift}")
    
    if not on_duty.empty:
        cols = st.columns(3)
        for idx, (_, row) in enumerate(on_duty.iterrows()):
            with cols[idx % 3]:
                # Xác định vị trí trực
                if selected_shift == "Sáng":
                    vi_tri = "Tại Công an xã"
                else:
                    if row[f"{d}_D_CAX"] == 'x':
                        vi_tri = "Tại Công an xã"
                    else:
                        vi_tri = f"Tại Ấp ({row['Ap']})"
                
                # Hiển thị thẻ nhân sự
                st.markdown(f"""
                    <div class="duty-card">
                        <div class="name-text">{row['HoTen']}</div>
                        <div class="info-text">🎖️ <b>Chức vụ:</b> {row['ChucVu']}</div>
                        <div class="info-text">🏠 <b>Đơn vị:</b> {row['Ap']}</div>
                        <div class="location-tag">📍 {vi_tri}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(f"Không có dữ liệu trực cho {selected_day} - Ca {selected_shift}. Vui lòng kiểm tra dấu 'x' trong file Google Sheets.")

    # Tùy chọn xem bảng gốc để đối soát
    with st.expander("📊 Xem bảng dữ liệu gốc tuần này"):
        st.dataframe(raw_df)

except Exception as e:
    st.error(f"Lỗi kết nối dữ liệu: {e}")
    st.info("Kiểm tra lại GID của Sheet và quyền chia sẻ của link Google Sheets.")
