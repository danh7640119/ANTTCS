import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH ---
ADMIN_PASSWORD = "123" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện
st.markdown("""
    <style>
    .dot-xuat-container { background-color: #FFF5F5; padding: 20px; border-radius: 10px; border: 2px dashed #FECACA; margin: 15px 0; }
    .morning-card { padding: 8px; border-radius: 5px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 5px; }
    .night-cax-card { padding: 8px; border-radius: 5px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 5px; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .ap-tag { color: #64748B; font-size: 12px; font-style: italic; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # ĐỌC DỮ LIỆU GỐC
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
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT"])

    with tab_view:
        st.subheader(f"📌 LỊCH TRỰC CHI TIẾT {selected_day}")
        tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            c_v1, c_v2 = st.columns(2)
            with c_v1:
                st.info("🛡️ Gác Cổng")
                g_v = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                g_v['SortID'] = g_v['Gio'].map(GIO_ORDER)
                st.table(g_v.sort_values('SortID')[["Gio", "HoTen"]])
            with c_v2:
                st.warning("🚔 Tuần Tra & Đột Xuất")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Gio"]])
        else: st.info("Chưa có dữ liệu.")

    with tab_manage:
        if not is_admin:
            st.warning("Vui lòng nhập mật mã điều hành.")
        else:
            current_saved = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
            summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])

            # --- HÀM TẠO DANH SÁCH CHỌN LỌC ---
            def get_prioritized_pool(target_names):
                # Chỉ lấy những người có trong danh sách truyền vào (target_names)
                names_nam = [n for n in target_names if n not in LIST_NU]
                df_p = pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0)
                
                def get_status(name):
                    if name in night_cax_list: return (1, "Trực Xã")
                    if name in night_ap_list: return (2, f"Trực {dict_ap.get(name, 'Ấp')}")
                    return (3, "Trực Sáng")
                
                df_p['Status'] = df_p['HoTen'].apply(get_status)
                df_p['Prio'] = df_p['Status'].apply(lambda x: x[0])
                df_p['StName'] = df_p['Status'].apply(lambda x: x[1])
                # Sắp xếp: Ưu tiên Xã -> Ấp -> Sáng, sau đó đến Điểm thấp nhất
                df_p = df_p.sort_values(['Prio', 'Diem'], ascending=[True, True])
                df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({r['StName']}) - {int(r['Diem'])}đ", axis=1)
                return df_p

            # Danh sách chỉ gồm những người ĐANG TRỰC NGÀY ĐÓ (Xã + Ấp + Sáng)
            active_today = list(set(morning_list + night_cax_list + night_ap_list))
            pool_dx = get_prioritized_pool(active_today)
            pool_gac_s = get_prioritized_pool(morning_list)
            pool_gac_d = get_prioritized_pool(night_cax_list)
            
            # 1. GÁC CỔNG
            st.subheader("🛡️ 1. PHÂN CA GÁC CỔNG")
            gac_results = []
            cg1, cg2 = st.columns(2)
            for i, gio in enumerate(list(GIO_ORDER.keys())):
                p_df = pool_gac_s if i < 4 else pool_gac_d
                saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                idx = 0
                if not saved.empty and not p_df.empty:
                    m = p_df[p_df['HoTen'] == saved.iloc[0]['HoTen']]
                    if not m.empty: idx = p_df.index.get_loc(m.index[0])
                with (cg1 if i < 5 else cg2):
                    if not p_df.empty:
                        sel = st.selectbox(f"Ca {gio}", p_df["Display"], index=idx, key=f"gac_{i}")
                        gac_results.append({"HoTen": sel.split(" (")[0], "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": (1 if i < 4 else 2)})

            # 2. TUẦN TRA
            st.divider()
            st.subheader("🚔 2. TUẦN TRA ĐÊM")
            def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist() or pool_gac_d["HoTen"].head(4).tolist()
            def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist() or pool_gac_d["HoTen"].iloc[4:8].tolist()
            ct1, ct2 = st.columns(2)
            with ct1: tt1 = st.multiselect("Ca 1 (18-22h):", pool_gac_d["Display"], default=[d for d in pool_gac_d["Display"] if d.split(" (")[0] in def_tt1], key="tt1")
            with ct2: tt2 = st.multiselect("Ca 2 (22-02h):", pool_gac_d["Display"], default=[d for d in pool_gac_d["Display"] if d.split(" (")[0] in def_tt2], key="tt2")

            # 3. ĐỘT XUẤT (CHỈ LẤY NGƯỜI TRỰC)
            st.markdown('<div class="dot-xuat-container">', unsafe_allow_html=True)
            st.subheader("🆘 3. ĐIỀU ĐỘNG ĐỘT XUẤT")
            st.caption("Lưu ý: Danh sách chỉ hiển thị những đồng chí có lịch trực trong ngày.")
            if 'n_dx' not in st.session_state: st.session_state.n_dx = 1
            if st.button("➕ Thêm việc đột xuất"): st.session_state.n_dx += 1
            
            s_dx = current_saved[current_saved['LoaiNhiemVu'].str.contains("ĐX: ", na=False)]
            u_t = s_dx['LoaiNhiemVu'].unique().tolist()
            dx_final = []
            for i in range(max(st.session_state.n_dx, len(u_t))):
                st.write(f"--- Việc {i+1} ---")
                cx1, cx2, cx3 = st.columns([3, 5, 1])
                d_name = u_t[i].replace("ĐX: ", "") if i < len(u_t) else ""
                d_m_real = s_dx[s_dx['LoaiNhiemVu'] == u_t[i]]['HoTen'].tolist() if i < len(u_t) else []
                with cx1: t_n = st.text_input(f"Nhiệm vụ {i+1}", value=d_name, key=f"dn_{i}")
                with cx2: t_m = st.multiselect(f"Đ/C thực hiện {i+1}", pool_dx["Display"], default=[d for d in pool_dx["Display"] if d.split(" (")[0] in d_m_real], key=f"dm_{i}")
                with cx3: t_d = st.number_input(f"Điểm", 1, 15, 3, key=f"dd_{i}")
                if t_n and t_m:
                    for m in t_m: dx_final.append({"HoTen": m.split(" (")[0], "LoaiNhiemVu": f"ĐX: {t_n}", "Gio": "Đột xuất", "Diem": t_d})
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("💾 LƯU TOÀN BỘ PHƯƠNG ÁN", use_container_width=True, type="primary"):
                final = gac_results + [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2} for p in tt1] + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2} for p in tt2] + dx_final
                df_s = pd.DataFrame(final)
                df_s["Tuan"], df_s["Ngay"], df_s["NgayTao"] = selected_week, selected_day, datetime.now().strftime("%d/%m/%Y %H:%M")
                if not df_history.empty:
                    df_history = df_history[~((df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day))]
                    f_save = pd.concat([df_history, df_s], ignore_index=True)
                else: f_save = df_s
                conn.update(worksheet="NhiemVu", data=f_save)
                st.success("Đã lưu lịch trực thành công!")
                st.rerun()

    # --- DANH SÁCH TỔNG ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN</div>', unsafe_allow_html=True)
    c_s, c_d, c_a = st.columns(3)
    with c_s:
        st.markdown("<p style='color:#2563EB; font-weight:bold;'>☀️ TRỰC SÁNG</p>", unsafe_allow_html=True)
        for n in morning_list: st.markdown(f'<div class="morning-card {"double-duty-warning" if n in night_cax_list else ""}"><div class="name-tag">{n}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)
    with c_d:
        st.markdown("<p style='color:#EA580C; font-weight:bold;'>🌙 TRỰC ĐÊM XÃ</p>", unsafe_allow_html=True)
        for n in night_cax_list: st.markdown(f'<div class="night-cax-card {"double-duty-warning" if n in morning_list else ""}"><div class="name-tag">{n}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)
    with c_a:
        st.markdown("<p style='color:#16A34A; font-weight:bold;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in night_ap_list: st.markdown(f'<div class="night-ap-card"><div class="name-tag">{n}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
