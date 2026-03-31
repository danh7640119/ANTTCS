import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT & TRANG ---
# Bạn có thể đổi mật khẩu tại đây
ADMIN_PASSWORD = "13579" 

st.set_page_config(page_title="Hệ thống Điều hành ANTT", layout="wide", page_icon="👮")

# CSS giữ nguyên như cũ
st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 12px; border-radius: 10px; border-left: 6px solid #1E3A8A; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .double-duty { background-color: #FFFBEB; border-left: 6px solid #F59E0B; border: 2px solid #FDE68A; }
    .name-text { color: #1E3A8A; font-size: 16px; font-weight: bold; }
    .group-header { background-color: #1E3A8A; color: white; padding: 10px; border-radius: 5px; margin: 15px 0; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KẾT NỐI DỮ LIỆU ---
try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc Sheet trực gốc (Dùng GID hoặc Tên Sheet đều được)
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    # ... (Phần xử lý columns giữ nguyên như các bản trước) ...
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    # Đọc lịch sử nhiệm vụ (Sheet NhiemVu)
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 3. GIAO DIỆN SIDEBAR & BẢO MẬT ---
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Nhập mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)

    st.sidebar.divider()
    st.sidebar.header("📅 CHỌN THỜI GIAN")
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    selected_week = st.sidebar.selectbox("Tuần:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày:", days_vn, index=datetime.now().weekday())

    # --- 4. CHIA TAB ---
    tab_view, tab_manage = st.tabs(["📋 XEM LỊCH TRỰC", "⚙️ PHÂN LỊCH CHI TIẾT"])

    with tab_view:
        st.title("👮 DANH SÁCH TRỰC TRONG NGÀY")
        st.markdown(f'<div class="time-box">📅 {selected_week} | {selected_day}</div>', unsafe_allow_html=True)
        # Hiển thị danh sách Card Trắng/Vàng như cũ tại đây
        # (Bạn copy đoạn code hiển thị card cũ bỏ vào đây)
        st.info("💡 Chế độ xem công khai. Để phân công nhiệm vụ, vui lòng nhập mã điều hành ở Sidebar.")

        # HIỂN THỊ LỊCH GÁC ĐÃ LƯU (Nếu có)
        if not df_history.empty:
            today_tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
            if not today_tasks.empty:
                st.subheader("📌 Lịch gác & Nhiệm vụ đã phân công:")
                st.table(today_tasks[["Gio", "HoTen", "LoaiNhiemVu"]])

    with tab_manage:
        if is_admin:
            st.title("⚡ TRẠM ĐIỀU HÀNH TÁC CHIẾN")
            
            # --- PHẦN PHÂN LỊCH CHI TIẾT (Chỉ hiện khi nhập đúng Pass) ---
            # 1. Lấy danh sách quân số để phân công (Logic như bản trước)
            # 2. Hiển thị Selectbox để chọn người gác/tuần tra
            # 3. Nút bấm "LƯU TOÀN BỘ"
            
            st.warning("Bạn đang ở chế độ Điều hành. Mọi thay đổi sẽ được ghi vào hệ thống.")
            
            # (Copy toàn bộ phần Code Phân ca gác, Tuần tra và Nhiệm vụ phát sinh bỏ vào đây)
            # Ví dụ:
            if st.button("💾 XÁC NHẬN LƯU DỮ LIỆU"):
                # Code lưu dữ liệu lên Google Sheets
                st.success("Đã ghi nhận dữ liệu thành công!")
        else:
            st.error("🚫 Truy cập bị từ chối! Vui lòng nhập đúng mã điều hành ở bên trái để sử dụng chức năng này.")
            st.image("https://cdn-icons-png.flaticon.com/512/3064/3064155.png", width=100)

except Exception as e:
    st.error(f"Lỗi: {e}")
