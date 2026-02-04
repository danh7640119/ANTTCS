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
    }
    .name-text { color: #1E3A8A; font-size: 20px; font-weight: bold; }
    .info-text { color: #4B5563; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 HỆ THỐNG TRA CỨU LỊCH TRỰC")

# --- KẾT NỐI DỮ LIỆU ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Đọc dữ liệu từ dòng 5 (skiprows=3)
    raw_df = conn.read(worksheet="nhaplieu", skiprows=3)
    
    # --- XỬ LÝ CỘT (Để tránh lỗi lấy tên nhưng không có dữ liệu) ---
    # File của bạn có: STT(0), Ấp(1), Họ tên(2), Chức vụ(3) và 28 cột trực (7 ngày x 4 ca)
    columns = ["STT", "Ap", "HoTen", "ChucVu"]
    days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for day in days:
        columns.extend([f"{day}_N_CAX", f"{day}_N_Ap", f"{day}_D_CAX", f"{day}_D_Ap"])
    
    # Gán lại tên cột chuẩn cho DataFrame
    raw_df.columns = columns[:len(raw_df.columns)]
    
    # Làm sạch dữ liệu: Xóa dòng trống và khoảng trắng trong dấu 'x'
    df = raw_df.dropna(subset=['HoTen']).copy()
    for col in df.columns[4:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # --- BỘ LỌC SIDEBAR ---
    st.sidebar.header("🔍 TÙY CHỌN TRA CỨU")
    
    # Nếu bạn có sheet LƯU TRỮ nhiều tuần, có thể thêm lọc Tuần ở đây
    selected_day_name = st.sidebar.selectbox("📅 Chọn ngày trong tuần:", 
        ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"])
    
    selected_shift = st.sidebar.radio("⏰ Chọn ca trực:", ["Sáng", "Đêm"])

    # Chuyển đổi lựa chọn sang mã cột
    day_map = {"Thứ 2":"T2", "Thứ 3":"T3", "Thứ 4":"T4", "Thứ 5":"T5", "Thứ 6":"T6", "Thứ 7":"T7", "Chủ nhật":"CN"}
    d_code = day_map[selected_day_name]
    s_code = "N" if selected_shift == "Sáng" else "D"
    
    # Xác định 2 cột cần kiểm tra (CAX và Ấp)
    col_cax = f"{d_code}_{s_code}_CAX"
    col_ap = f"{d_code}_{s_code}_Ap"

    # --- LỌC NGƯỜI TRỰC ---
    on_duty = df[(df[col_cax] == 'x') | (df[col_ap] == 'x')]

    # --- HIỂN THỊ ---
    st.subheader(f"🚩 Danh sách trực: {selected_day_name} - Ca {selected_shift}")
    
    if not on_duty.empty:
        # Chia cột để hiển thị dạng lưới (3 cột)
        cols = st.columns(3)
        for idx, (_, row) in enumerate(on_duty.iterrows()):
            with cols[idx % 3]:
                # Xác định vị trí trực cụ thể để hiện icon
                vi_tri = "Tại CAX" if row[col_cax] == 'x' else "Tại Ấp"
                
                st.markdown(f"""
                    <div class="duty-card">
                        <div class="name-text">{row['HoTen']}</div>
                        <div class="info-text">🎖️ Chức vụ: {row['ChucVu']}</div>
                        <div class="info-text">📍 Đơn vị: {row['Ap']}</div>
                        <div style="margin-top:10px; font-weight:bold; color:#059669;">🚩 Trực: {vi_tri}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(f"Hiện chưa có dữ liệu phân công trực cho {selected_day_name} ca {selected_shift}.")

    # Thêm bảng tổng hợp để đối soát
    with st.expander("📊 Xem bảng dữ liệu gốc tuần này"):
        st.dataframe(raw_df)

except Exception as e:
    st.error(f"Lỗi kết nối dữ liệu: {e}")
    st.info("Mẹo: Hãy kiểm tra xem bạn đã chia sẻ Google Sheets ở chế độ 'Anyone with the link can view' chưa.")



