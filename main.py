import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH & BẢO MẬT ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
except Exception:
    st.error("⚠️ LỖI: Chưa cấu hình 'admin_password' trong Secrets!")
    st.stop()

GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}
LIST_GIO = list(GIO_ORDER.keys())

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu quân số gốc
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    df_raw.columns = ["Tuan", "Ap", "HoTen", "T2_N", "T2_D_CAX", "T2_D_Ap", "T3_N", "T3_D_CAX", "T3_D_Ap", "T4_N", "T4_D_CAX", "T4_D_Ap", "T5_N", "T5_D_CAX", "T5_D_Ap", "T6_N", "T6_D_CAX", "T6_D_Ap", "T7_N", "T7_D_CAX", "T7_D_Ap", "CN_N", "CN_D_CAX", "CN_D_Ap"]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # Sidebar
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Tuần trực:", [str(w) for w in df_mem['Tuan'].unique().tolist()[::-1]])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'].astype(str) == selected_week]
    
    # Danh sách quân số trực trong ngày
    m_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    all_today = list(set(m_list + n_cax_list + n_ap_list))

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG", "🔔 ĐIỂM DANH"])

    # --- TAB 1: XEM NHIỆM VỤ (CÔNG KHAI) ---
    with tab_view:
        try:
            df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
            tasks = df_history[(df_history['Tuan'].astype(str) == selected_week) & (df_history['Ngay'] == selected_day)]
            if not tasks.empty:
                st.subheader(f"📌 LỊCH TRỰC {selected_day} - TUẦN {selected_week}")
                c1, c2 = st.columns(2)
                with c1:
                    st.info("🛡️ GÁC CỔNG")
                    g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                    g_df['SortID'] = g_df['Gio'].map(GIO_ORDER)
                    st.table(g_df.sort_values('SortID')[["Gio", "HoTen"]])
                with c2:
                    st.warning("🚔 TUẦN TRA / ĐỘT XUẤT")
                    st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen"]])
            else:
                st.info("Chưa có lịch phân công chi tiết.")
        except: st.info("Chưa có dữ liệu nhiệm vụ.")

    # --- TAB 2: PHÂN CÔNG (BẢO MẬT - ĐÃ KHÔI PHỤC) ---
    with tab_manage:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập mã điều hành.")
        else:
            st.subheader(f"⚙️ THIẾT LẬP NHIỆM VỤ: {selected_day}")
            col1, col2 = st.columns(2)
            new_tasks = []
            
            with col1:
                st.write("**🛡️ PHÂN GÁC CỔNG**")
                for gio in LIST_GIO:
                    chosen = st.selectbox(f"Ca {gio}:", [""] + all_today, key=f"gac_{gio}")
                    if chosen: new_tasks.append({"Tuan": selected_week, "Ngay": selected_day, "HoTen": chosen, "LoaiNhiemVu": "Gác cổng", "Gio": gio})
            
            with col2:
                st.write("**🚔 TUẦN TRA / KHÁC**")
                tuan_tra = st.multiselect("Lực lượng tuần tra:", all_today)
                for p in tuan_tra: new_tasks.append({"Tuan": selected_week, "Ngay": selected_day, "HoTen": p, "LoaiNhiemVu": "Tuần tra", "Gio": "Cả ca"})
                
                dot_xuat = st.text_input("Nhiệm vụ đột xuất (nếu có):")
                dx_people = st.multiselect("Người thực hiện đột xuất:", all_today)
                for p in dx_people: new_tasks.append({"Tuan": selected_week, "Ngay": selected_day, "HoTen": p, "LoaiNhiemVu": dot_xuat if dot_xuat else "Đột xuất", "Gio": "Đột xuất"})

            if st.button("💾 LƯU PHÂN CÔNG", type="primary", use_container_width=True):
                if new_tasks:
                    df_new = pd.DataFrame(new_tasks)
                    df_new['NgayTao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    try:
                        df_old = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
                        df_old = df_old[~((df_old['Tuan'].astype(str) == selected_week) & (df_old['Ngay'] == selected_day))]
                        final_df = pd.concat([df_old, df_new], ignore_index=True)
                    except: final_df = df_new
                    conn.update(worksheet="NhiemVu", data=final_df)
                    st.success("Đã lưu lịch trực chi tiết!")
                    st.rerun()

    # --- TAB 3: ĐIỂM DANH (CHỈ LƯU NGƯỜI VẮNG - TRỰC QUAN) ---
    with tab_attendance:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập mã điều hành.")
        else:
            st.subheader(f"🔔 GHI NHẬN QUÂN SỐ VẮNG: {selected_day}")
            st.write("Chọn những đồng chí **VẮNG** mặt hôm nay:")
            
            # Chọn người vắng từ danh sách tổng hôm nay
            vắng_list = st.multiselect("Danh sách đồng chí vắng:", all_today)
            
            notes = {}
            if vắng_list:
                for p in vắng_list:
                    notes[p] = st.text_input(f"Lý do vắng của {p}:", key=f"note_{p}")
            
            if st.button("💾 XÁC NHẬN BÁO VẮNG", type="primary", use_container_width=True):
                data_vắng = []
                for p in vắng_list:
                    data_vắng.append({
                        "Tuan": selected_week,
                        "Ngay": selected_day,
                        "HoTen": p,
                        "TrangThai": "Vắng",
                        "Ghi chú": notes.get(p, ""),
                        "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                
                if data_vắng:
                    df_v_new = pd.DataFrame(data_vắng)
                    try:
                        df_v_old = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                        # Xóa báo vắng cũ của ngày này để cập nhật mới
                        df_v_old = df_v_old[~((df_v_old['Tuan'].astype(str) == selected_week) & (df_v_old['Ngay'] == selected_day))]
                        f_v_save = pd.concat([df_v_old, df_v_new], ignore_index=True)
                    except: f_v_save = df_v_new
                    conn.update(worksheet="DiemDanh", data=f_v_save)
                    st.success(f"Đã ghi nhận vắng {len(vắng_list)} đồng chí.")
                else:
                    st.info("Không có ai vắng mặt.")

            # THỐNG KÊ NHANH TRONG TUẦN
            st.markdown("---")
            st.write(f"**📊 TỔNG HỢP VẮNG TRONG TUẦN {selected_week}:**")
            try:
                df_tk = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                df_tk_week = df_tk[df_tk['Tuan'].astype(str) == selected_week]
                if not df_tk_week.empty:
                    st.dataframe(df_tk_week[["Ngay", "HoTen", "Ghi chú"]], hide_index=True, use_container_width=True)
                else: st.write("Tuần này đầy đủ quân số.")
            except: st.write("Chưa có dữ liệu vắng.")

except Exception as e:
    st.error(f"Lỗi: {e}")
