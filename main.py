import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT (CHỈ TỪ SECRETS) ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
except Exception:
    st.error("⚠️ LỖI: Chưa cấu hình 'admin_password' trong Secrets!")
    st.stop()

LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện
st.markdown("""
    <style>
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    .thong-ke-box { background-color: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; }
    .vắng-status { color: #E11D48; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu quân số gốc
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # Sidebar
    st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    # Lấy danh sách trực trong ngày
    m_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG", "🔔 ĐIỂM DANH"])

    # --- TAB ĐIỂM DANH (Đã bảo mật & Thêm thống kê) ---
    with tab_attendance:
        if not is_admin:
            st.warning("⚠️ Vui lòng nhập Mã điều hành để truy cập dữ liệu Điểm danh.")
        else:
            st.subheader(f"📊 ĐIỂM DANH: {selected_day} - TUẦN {selected_week}")
            
            # 1. Phần thực hiện điểm danh
            all_today = []
            for n in m_list: all_today.append({"HoTen": n, "LoaiTruc": "Trực Sáng"})
            for n in n_cax_list: all_today.append({"HoTen": n, "LoaiTruc": "Trực Đêm Xã"})
            for n in n_ap_list: all_today.append({"HoTen": n, "LoaiTruc": "Trực Ấp"})
            
            df_att_input = pd.DataFrame(all_today).drop_duplicates(subset=['HoTen'])
            
            if not df_att_input.empty:
                df_att_input['Vắng'] = False
                df_att_input['Lý do vắng'] = ""
                
                edited_df = st.data_editor(
                    df_att_input,
                    column_config={
                        "HoTen": "Họ và Tên",
                        "LoaiTruc": "Ca trực",
                        "Vắng": st.column_config.CheckboxColumn("Vắng?", default=False),
                        "Lý do vắng": st.column_config.TextColumn("Ghi chú")
                    },
                    disabled=["HoTen", "LoaiTruc"],
                    hide_index=True,
                    key="editor_v23"
                )
                
                if st.button("💾 LƯU ĐIỂM DANH NGÀY", type="primary"):
                    save_data = edited_df.copy()
                    save_data['TrangThai'] = save_data['Vắng'].apply(lambda x: "Vắng" if x else "Có mặt")
                    save_data['Tuan'] = selected_week
                    save_data['Ngay'] = selected_day
                    save_data['NgayTao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    try:
                        old_df = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                        old_df = old_df[~((old_df['Tuan'].astype(str) == str(selected_week)) & (old_df['Ngay'] == selected_day))]
                        final_save = pd.concat([old_df, save_data[["Tuan", "Ngay", "HoTen", "TrangThai", "Lý do vắng", "LoaiTruc", "NgayTao"]]], ignore_index=True)
                    except:
                        final_save = save_data
                    
                    conn.update(worksheet="DiemDanh", data=final_save)
                    st.success("Đã lưu dữ liệu điểm danh!")
                    st.rerun()

            # 2. PHẦN THỐNG KÊ VẮNG TRONG TUẦN (Yêu cầu của bạn)
            st.markdown('<div class="section-header">📉 THỐNG KÊ QUÂN SỐ VẮNG (TUẦN ' + str(selected_week) + ')</div>', unsafe_allow_html=True)
            try:
                df_all_att = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                # Lọc quân số vắng của tuần đang chọn
                df_vắng_tuan = df_all_att[(df_all_att['Tuan'].astype(str) == str(selected_week)) & 
                                          (df_all_att['TrangThai'] == "Vắng")]
                
                if not df_vắng_tuan.empty:
                    # Đếm số buổi vắng của từng người
                    summary_vắng = df_vắng_tuan.groupby('HoTen').size().reset_index(name='Số buổi vắng')
                    
                    col_tk1, col_tk2 = st.columns([1, 2])
                    with col_tk1:
                        st.write("**Tổng hợp số buổi vắng:**")
                        st.dataframe(summary_vắng, hide_index=True)
                    with col_tk2:
                        st.write("**Chi tiết các ngày vắng:**")
                        st.dataframe(df_vắng_tuan[["Ngay", "HoTen", "Lý do vắng"]], hide_index=True)
                else:
                    st.write("✅ Tuần này quân số trực đầy đủ, không có ai vắng.")
            except:
                st.info("Chưa có dữ liệu thống kê cho tuần này.")

    # --- CÁC TAB KHÁC GIỮ NGUYÊN (V21/V22) ---
    with tab_manage:
        if is_admin: st.write("--- Cấu hình nhiệm vụ ---")
    with tab_view:
        st.write("--- Xem nhiệm vụ ---")

except Exception as e:
    st.error(f"Lỗi: {e}")
