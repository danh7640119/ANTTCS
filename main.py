import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
except Exception:
    st.error("⚠️ LỖI: Chưa cấu hình 'admin_password' trong Streamlit Secrets!")
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
    .night-cax-card { padding: 8px; border-radius: 5px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 5px; }
    .name-tag { font-weight: bold; color: #1E3A8A; }
    .ap-tag { color: #64748B; font-size: 12px; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. ĐỌC DỮ LIỆU
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # Sidebar
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'].astype(str) == str(selected_week)]
    
    m_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG", "🔔 ĐIỂM DANH"])

    # --- TAB 1: XEM NHIỆM VỤ (CÔNG KHAI) ---
    with tab_view:
        st.subheader(f"📌 LỊCH CÔNG TÁC {selected_day} - TUẦN {selected_week}")
        tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            tasks['Ấp'] = tasks['HoTen'].map(dict_ap)
            c1, c2 = st.columns(2)
            with c1:
                st.info("🛡️ GÁC CỔNG")
                g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                g_df['SortID'] = g_df['Gio'].map(GIO_ORDER)
                st.table(g_df.sort_values('SortID')[["Gio", "HoTen", "Ấp"]])
            with c2:
                st.warning("🚔 TUẦN TRA & ĐỘT XUẤT")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Ấp"]])
        else:
            st.info("Chưa có dữ liệu nhiệm vụ chi tiết.")

    # --- TAB 2: PHÂN CÔNG (BẢO MẬT) ---
    with tab_manage:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập mã điều hành để phân công.")
        else:
            # Logic phân công gác cổng, tuần tra... (như các bản trước)
            st.subheader("⚙️ THIẾT LẬP NHIỆM VỤ")
            current_saved = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
            # (Phần này bạn giữ nguyên logic selectbox và nút Lưu từ bản V21 nhé)
            st.write("Thực hiện chọn quân số và bấm Lưu tại đây.")

    # --- TAB 3: ĐIỂM DANH (BẢO MẬT) ---
    with tab_attendance:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập mã điều hành để thực hiện điểm danh.")
        else:
            st.subheader(f"🔔 ĐIỂM DANH QUÂN SỐ {selected_day}")
            
            # Gom danh sách trực hôm nay
            all_today = []
            for n in m_list: all_today.append({"HoTen": n, "LoaiTruc": "Sáng"})
            for n in n_cax_list: all_today.append({"HoTen": n, "LoaiTruc": "Đêm Xã"})
            for n in n_ap_list: all_today.append({"HoTen": n, "LoaiTruc": "Trực Ấp"})
            df_att_input = pd.DataFrame(all_today).drop_duplicates(subset=['HoTen'])

            if not df_att_input.empty:
                # Chức năng điểm danh chính
                df_att_input['Vắng'] = False
                df_att_input['Ghi chú'] = ""
                
                # BẢNG ĐIỂM DANH CÓ THỂ CHỈNH SỬA
                edited_att = st.data_editor(
                    df_att_input,
                    column_config={
                        "HoTen": "Họ và Tên",
                        "LoaiTruc": "Ca trực",
                        "Vắng": st.column_config.CheckboxColumn("Vắng?", default=False),
                        "Ghi chú": st.column_config.TextColumn("Lý do vắng")
                    },
                    disabled=["HoTen", "LoaiTruc"],
                    hide_index=True,
                    key="att_editor_v25"
                )
                
                if st.button("💾 XÁC NHẬN LƯU ĐIỂM DANH", type="primary", use_container_width=True):
                    save_att = edited_att.copy()
                    save_att['TrangThai'] = save_att['Vắng'].apply(lambda x: "Vắng" if x else "Có mặt")
                    save_att['Tuan'] = str(selected_week)
                    save_att['Ngay'] = selected_day
                    save_att['NgayTao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    try:
                        all_att = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                        # Xóa dữ liệu cũ của ngày này để ghi đè
                        all_att = all_att[~((all_att['Tuan'].astype(str) == str(selected_week)) & (all_att['Ngay'] == selected_day))]
                        f_save = pd.concat([all_att, save_att[["Tuan", "Ngay", "HoTen", "TrangThai", "Ghi chú", "LoaiTruc", "NgayTao"]]], ignore_index=True)
                    except:
                        f_save = save_data
                    
                    conn.update(worksheet="DiemDanh", data=f_save)
                    st.success("✅ Đã lưu danh sách điểm danh vào hệ thống!")
                    st.rerun()

            # PHẦN THỐNG KÊ (HIỆN DƯỚI NÚT LƯU)
            st.markdown('<div class="section-header">📉 DANH SÁCH VẮNG TRONG TUẦN</div>', unsafe_allow_html=True)
            try:
                df_check = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                vắng_tuan = df_check[(df_check['Tuan'].astype(str) == str(selected_week)) & (df_check['TrangThai'] == "Vắng")]
                if not vắng_tuan.empty:
                    st.dataframe(vắng_tuan[["Ngay", "HoTen", "Ghi chú"]], hide_index=True, use_container_width=True)
                else:
                    st.write("Tuần này chưa ghi nhận quân số vắng.")
            except:
                st.write("Chưa có dữ liệu thống kê.")

    # --- QUÂN SỐ TỔNG QUAN (LUÔN HIỆN Ở DƯỚI CÙNG) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN</div>', unsafe_allow_html=True)
    # (Phần card màu Xanh/Vàng/Cam hiển thị quân số Sáng-Đêm-Ấp giữ nguyên)

except Exception as e:
    st.error(f"Lỗi: {e}")
