import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
except Exception:
    st.error("⚠️ LỖI: Chưa cấu hình 'admin_password' trong Secrets!")
    st.stop()

LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện
st.markdown("""
    <style>
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    .morning-card { padding: 8px; border-radius: 5px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 5px; }
    .morning-night-card { padding: 8px; border-radius: 5px; border-left: 5px solid #F59E0B; background-color: #FEF3C7; margin-bottom: 5px; }
    .name-tag { font-weight: bold; color: #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu quân số
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # Sidebar điều hướng
    st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    # Phân loại danh sách trực thực tế
    m_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG", "🔔 ĐIỂM DANH"])

    # --- TAB ĐIỂM DANH (MỚI) ---
    with tab_attendance:
        if not is_admin:
            st.warning("Vui lòng nhập Mã điều hành để thực hiện điểm danh quân số.")
        else:
            st.subheader(f"📊 ĐIỂM DANH QUÂN SỐ TRỰC {selected_day}")
            
            # Tạo DataFrame danh sách những người phải trực hôm nay
            all_today = []
            for n in m_list: all_today.append({"HoTen": n, "LoaiTruc": "Trực Sáng"})
            for n in n_cax_list: all_today.append({"HoTen": n, "LoaiTruc": "Trực Đêm Xã"})
            for n in n_ap_list: all_today.append({"HoTen": n, "LoaiTruc": "Trực Ấp"})
            
            df_att = pd.DataFrame(all_today).drop_duplicates(subset=['HoTen'], keep='first')
            
            if not df_att.empty:
                st.write("Tích chọn những đồng chí **VẮNG MẶT**:")
                
                # Sử dụng data_editor để điểm danh nhanh
                df_att['Vắng'] = False
                df_att['Lý do vắng'] = ""
                
                edited_df = st.data_editor(
                    df_att,
                    column_config={
                        "HoTen": "Họ và Tên",
                        "LoaiTruc": "Ca trực chính",
                        "Vắng": st.column_config.CheckboxColumn("Vắng?", default=False),
                        "Lý do vắng": st.column_config.TextColumn("Ghi chú lý do", placeholder="VD: Nghỉ phép, ốm...")
                    },
                    disabled=["HoTen", "LoaiTruc"],
                    hide_index=True,
                    use_container_width=True
                )
                
                if st.button("💾 XÁC NHẬN ĐIỂM DANH", type="primary", use_container_width=True):
                    # Lọc ra những người vắng để lưu, hoặc lưu tất cả kèm trạng thái
                    final_att = edited_df.copy()
                    final_att['TrangThai'] = final_att['Vắng'].apply(lambda x: "Vắng" if x else "Có mặt")
                    final_att['Tuan'] = selected_week
                    final_att['Ngay'] = selected_day
                    final_att['NgayTao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    # Lưu vào sheet DiemDanh
                    try:
                        # Đọc dữ liệu cũ để tránh trùng lặp cùng 1 ngày
                        old_att = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                        old_att = old_att[~((old_att['Tuan'].astype(str) == str(selected_week)) & (old_att['Ngay'] == selected_day))]
                        save_att = pd.concat([old_att, final_att[["Tuan", "Ngay", "HoTen", "TrangThai", "Lý do vắng", "LoaiTruc", "NgayTao"]]], ignore_index=True)
                    except:
                        save_att = final_att[["Tuan", "Ngay", "HoTen", "TrangThai", "Lý do vắng", "LoaiTruc", "NgayTao"]]
                    
                    conn.update(worksheet="DiemDanh", data=save_att)
                    st.success(f"✅ Đã cập nhật điểm danh ngày {selected_day} thành công!")
            else:
                st.info("Không có quân số trực được phân công cho ngày này.")

    # --- TAB PHÂN CÔNG & XEM (Giữ nguyên logic bảo mật V21) ---
    with tab_manage:
        if is_admin:
            st.write("--- Thực hiện phân công nhiệm vụ chi tiết ---")
            # [Dán logic phân công từ V21 vào đây]
    
    with tab_view:
        st.write(f"--- Lịch công tác ngày {selected_day} ---")
        # [Dán logic hiển thị từ V21 vào đây]

except Exception as e:
    st.error(f"Lỗi: {e}")
