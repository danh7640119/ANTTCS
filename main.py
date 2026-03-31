import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
except:
    st.error("⚠️ LỖI: Chưa cấu hình 'admin_password' trong Secrets!")
    st.stop()

# Cấu hình ca gác cổng
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}
LIST_GIO = list(GIO_ORDER.keys())

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. ĐỌC DỮ LIỆU NHÂN SỰ (luutru)
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen", "T2_N", "T2_D_CAX", "T2_D_Ap", "T3_N", "T3_D_CAX", "T3_D_Ap", "T4_N", "T4_D_CAX", "T4_D_Ap", "T5_N", "T5_D_CAX", "T5_D_Ap", "T6_N", "T6_D_CAX", "T6_D_Ap", "T7_N", "T7_D_CAX", "T7_D_Ap", "CN_N", "CN_D_CAX", "CN_D_Ap"]
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # 3. ĐỌC LỊCH SỬ NHIỆM VỤ (NhiemVu)
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "NgayTao"])

    # --- SIDEBAR ---
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    all_weeks = [str(w) for w in df_mem['Tuan'].unique().tolist() if pd.notna(w)][::-1]
    sel_week = st.sidebar.selectbox("Tuần trực:", all_weeks)
    
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    sel_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    # Lọc quân số trong ngày
    d_code = dict(zip(days_vn, day_codes))[sel_day]
    df_curr = df_mem[df_mem['Tuan'].astype(str) == sel_week]
    
    m_list = df_curr[df_curr[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    d_list = df_curr[df_curr[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    a_list = df_curr[df_curr[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    all_today = sorted(list(set(m_list + d_list + a_list)))

    # --- CHIA TAB (Đã sửa tên biến đồng nhất) ---
    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG NV", "🔔 BÁO VẮNG"])

    # TAB 1: XEM (CÔNG KHAI)
    with tab_view:
        st.subheader(f"📌 LỊCH TRỰC {sel_day} - TUẦN {sel_week}")
        tasks = df_history[(df_history['Tuan'].astype(str) == sel_week) & (df_history['Ngay'] == sel_day)]
        if not tasks.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.info("🛡️ GÁC CỔNG")
                g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                g_df['Sort'] = g_df['Gio'].map(GIO_ORDER)
                st.table(g_df.sort_values('Sort')[["Gio", "HoTen"]])
            with c2:
                st.warning("🚔 TUẦN TRA / ĐỘT XUẤT")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen"]])
        else:
            st.info("Chưa có lịch phân công chi tiết cho ngày này.")

    # TAB 2: PHÂN CÔNG (BẢO MẬT)
    with tab_manage:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập mã điều hành để phân công nhiệm vụ.")
        else:
            st.subheader("⚙️ THIẾT LẬP NHIỆM VỤ CHI TIẾT")
            if not all_today:
                st.error("Không tìm thấy quân số trực trong bảng 'luutru'!")
            else:
                new_tasks = []
                cg, ck = st.columns(2)
                with cg:
                    st.write("**🛡️ PHÂN GÁC CỔNG**")
                    for g in LIST_GIO:
                        p_sel = st.selectbox(f"Ca {g}:", [""] + all_today, key=f"g_{g}")
                        if p_sel: new_tasks.append({"Tuan": sel_week, "Ngay": sel_day, "HoTen": p_sel, "LoaiNhiemVu": "Gác cổng", "Gio": g})
                with ck:
                    st.write("**🚔 TUẦN TRA & ĐỘT XUẤT**")
                    tt = st.multiselect("Tuần tra đêm:", d_list)
                    for p in tt: new_tasks.append({"Tuan": sel_week, "Ngay": sel_day, "HoTen": p, "LoaiNhiemVu": "Tuần tra", "Gio": "Đêm"})
                    dx_n = st.text_input("Tên việc đột xuất:")
                    dx_p = st.multiselect("Người thực hiện:", all_today)
                    for p in dx_p: new_tasks.append({"Tuan": sel_week, "Ngay": sel_day, "HoTen": p, "LoaiNhiemVu": dx_n if dx_n else "Đột xuất", "Gio": "Đột xuất"})

                if st.button("💾 LƯU PHÂN CÔNG", type="primary", use_container_width=True):
                    df_new = pd.DataFrame(new_tasks)
                    df_new['NgayTao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    old_df = df_history[~((df_history['Tuan'].astype(str) == sel_week) & (df_history['Ngay'] == sel_day))]
                    final_df = pd.concat([old_df, df_new], ignore_index=True)
                    conn.update(worksheet="NhiemVu", data=final_df)
                    st.success("Đã lưu lịch trực!")
                    st.rerun()

    # TAB 3: BÁO VẮNG (BẢO MẬT - CHỈ HIỆN Ô CHỌN NGƯỜI VẮNG)
    with tab_attendance:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập mã điều hành để báo vắng.")
        else:
            st.subheader("🔔 GHI NHẬN QUÂN SỐ VẮNG")
            v_list = st.multiselect("Chọn những đồng chí vắng mặt hôm nay:", all_today)
            v_notes = {}
            for v in v_list:
                v_notes[v] = st.text_input(f"Lý do vắng của {v}:", key=f"note_{v}")
            
            if st.button("💾 XÁC NHẬN BÁO VẮNG", type="primary"):
                if v_list:
                    v_data = [{"Tuan": sel_week, "Ngay": sel_day, "HoTen": v, "TrangThai": "Vắng", "LyDo": v_notes[v], "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M")} for v in v_list]
                    df_v_new = pd.DataFrame(v_data)
                    try:
                        df_v_old = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                        df_v_old = df_v_old[~((df_v_old['Tuan'].astype(str) == sel_week) & (df_v_old['Ngay'] == sel_day))]
                        f_v_save = pd.concat([df_v_old, df_v_new], ignore_index=True)
                    except: f_v_save = df_v_new
                    conn.update(worksheet="DiemDanh", data=f_v_save)
                    st.success(f"Đã ghi nhận vắng {len(v_list)} đồng chí.")
                else:
                    st.info("Không có ai vắng mặt.")

except Exception as e:
    st.error(f"Hệ thống gặp lỗi: {e}")
