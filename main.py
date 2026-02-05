import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Lịch trực ANTTCS", layout="wide", page_icon="📋")

# CSS để làm thẻ nhân sự đẹp hơn
st.markdown("""
    <style>
    .duty-card {
        padding: 20px;
        border-radius: 10px;
        border-left: 8px solid #1E3A8A;
        background-color: white;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        min-height: 150px;
    }
    .name-text { color: #1E3A8A; font-size: 20px; font-weight: bold; }
    .info-text { color: #4B5563; font-size: 14px; margin-top: 5px; }
    .location-tag { 
        margin-top: 15px; 
        font-weight: bold; 
        color: #059669; 
        background-color: #ECFDF5; 
        padding: 5px 10px; 
        border-radius: 5px;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 HỆ THỐNG TRA CỨU LỊCH TRỰC")

# --- KẾT NỐI DỮ LIỆU ---
try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lưu ý: Tôi giữ nguyên skiprows=3 theo code bạn đang chạy ổn định
    raw_df = conn.read(spreadsheet=url, ttl=0, worksheet="1567366671", skiprows=3)

    # --- XỬ LÝ CỘT ---
    columns = ["STT", "Ap", "HoTen", "ChucVu"]
    days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for day in days:
        columns.extend([f"{day}_N_CAX", f"{day}_N_Ap", f"{day}_D_CAX", f"{day}_D_Ap"])
    
    raw_df.columns = columns[:len(raw_df.columns)]
    
    df = raw_df.dropna(subset=['HoTen']).copy()
    for col in df.columns[4:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # --- BỘ LỌC SIDEBAR ---
    st.sidebar.header("🔍 TÙY CHỌN TRA CỨU")
    
    selected_day_name = st.sidebar.selectbox("📅 Chọn ngày trong tuần:", 
        ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"])
    
    selected_shift = st.sidebar.radio("⏰ Chọn ca trực:", ["Sáng", "Đêm"])

    # Chuyển đổi lựa chọn sang mã cột
    day_map = {"Thứ 2":"T2", "Thứ 3":"T3", "Thứ 4":"T4", "Thứ 5":"T5", "Thứ 6":"T6", "Thứ 7":"T7", "Chủ nhật":"CN"}
    d_code = day_map[selected_day_name]
    s_code = "N" if selected_shift == "Sáng" else "D"
    
    col_cax = f"{d_code}_{s_code}_CAX"
    col_ap = f"{d_code}_{s_code}_Ap"

    # --- LỌC NGƯỜI TRỰC ---
    # Kiểm tra cả 2 cột CAX và Ấp để không sót người
    on_duty = df[(df[col_cax] == 'x') | (df[col_ap] == 'x')]

    # --- HIỂN THỊ ---
    st.subheader(f"🚩 Danh sách trực: {selected_day_name} - Ca {selected_shift}")
    
    if not on_duty.empty:
        cols = st.columns(3)
        for idx, (_, row) in enumerate(on_duty.iterrows()):
            with cols[idx % 3]:
                # --- LOGIC MỚI CHO VỊ TRÍ TRỰC ---
                if selected_shift == "Sáng":
                    # Ban ngày mặc định tất cả tại CAX
                    vi_tri = "Tại Công an xã"
                else:
                    # Ban đêm mới kiểm tra cụ thể
                    if row[col_cax] == 'x':
                        vi_tri = "Tại Công an xã"
                    else:
                        vi_tri = f"Tại Ấp ({row['Ap']})"
                
                st.markdown(f"""
                    <div class="duty-card">
                        <div class="name-text">{row['HoTen']}</div>
                        <div class="info-text">🎖️ <b>Chức vụ:</b> {row['ChucVu']}</div>
                        <div class="info-text">🏠 <b>Đơn vị:</b> {row['Ap']}</div>
                        <div class="location-tag">📍 {vi_tri}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(f"Hiện chưa có dữ liệu phân công trực cho {selected_day_name} ca {selected_shift}.")

    # Bảng đối soát
    with st.expander("📊 Xem bảng dữ liệu gốc tuần này"):
        st.dataframe(raw_df)

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
