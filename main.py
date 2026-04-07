import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    URL_SHEET = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("⚠️ LỖI CẤU HÌNH: Chưa tìm thấy Secrets!")
    st.stop()

LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thụy Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm", "Lê Thanh Tuyền"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện (GIỮ NGUYÊN GỐC)
st.markdown("""
    <style>
    .dot-xuat-container { background-color: #FFF5F5; padding: 20px; border-radius: 10px; border: 2px dashed #FECACA; margin: 15px 0; }
    .morning-card { padding: 8px; border-radius: 5px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 5px; }
    .morning-night-card { padding: 8px; border-radius: 5px; border-left: 5px solid #F59E0B; background-color: #FEF3C7; margin-bottom: 5px; }
    .night-cax-card { padding: 8px; border-radius: 5px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 5px; }
    .night-ap-card { padding: 8px; border-radius: 5px; border-left: 5px solid #16A34A; background-color: #F0FDF4; margin-bottom: 5px; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .ap-tag { color: #64748B; font-size: 12px; font-style: italic; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu trực tiếp (Đã bỏ ttl)
    df_raw = conn.read(spreadsheet=URL_SHEET, worksheet="luutru", skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    try:
        df_history = conn.read(spreadsheet=URL_SHEET, worksheet="NhiemVu")
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # Sidebar
    st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
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

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT", "✅ ĐIỂM DANH"])

    # --- TAB 1: XEM NHIỆM VỤ ---
    with tab_view:
        st.subheader(f"📌 LỊCH PHÂN CÔNG {selected_day} - TUẦN {selected_week}")
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
            st.info("Chưa có dữ liệu phân công chi tiết.")

    # --- TAB 2: PHÂN CÔNG CHI TIẾT (GIỮ NGUYÊN GỐC) ---
    with tab_manage:
        if not is_admin:
            st.warning("Vui lòng nhập Mã điều hành để thực hiện phân công.")
        else:
            current_saved = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
            summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])

            def get_pool(target_names):
                names_nam = [n for n in target_names if n not in LIST_NU]
                df_p = pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0)
                df_p['StName'] = df_p['HoTen'].apply(lambda n: "Trực Xã" if n in night_cax_list else (f"Trực {dict_ap.get(n)}" if n in night_ap_list else "Trực Sáng"))
                df_p['Prio'] = df_p['HoTen'].apply(lambda n: 1 if n in night_cax_list else (2 if n in night_ap_list else 3))
                df_p = df_p.sort_values(['Prio', 'Diem'], ascending=[True, True])
                df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({r['StName']}) - {int(r['Diem'])}đ", axis=1)
                return df_p

            active_today = list(set(morning_list + night_cax_list + night_ap_list))
            pool_dx = get_pool(active_today); pool_s = get_pool(morning_list); pool_d = get_pool(night_cax_list)

            st.subheader("🛡️ 1. PHÂN CA GÁC CỔNG")
            g_res = []
            cg1, cg2 = st.columns(2)
            for i, gio in enumerate(list(GIO_ORDER.keys())):
                p_df = pool_s if i < 4 else pool_d
                saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                idx = 0
                if not saved.empty and not p_df.empty:
                    m = p_df[p_df['HoTen'] == saved.iloc[0]['HoTen']]
                    if not m.empty: idx = p_df.index.get_loc(m.index[0])
                with (cg1 if i < 5 else cg2):
                    if not p_df.empty:
                        sel = st.selectbox(f"Ca {gio}", p_df["Display"], index=idx, key=f"gac_{i}")
                        g_res.append({"HoTen": sel.split(" (")[0], "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": (1 if i < 4 else 2)})

            st.divider()
            st.subheader("🚔 2. TUẦN TRA ĐÊM")
            def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist() or pool_d["HoTen"].head(4).tolist()
            def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist() or pool_d["HoTen"].iloc[4:8].tolist()
            ct1, ct2 = st.columns(2)
            with ct1: tt1 = st.multiselect("Ca 1 (18-22h):", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in def_tt1], key="tt1")
            with ct2: tt2 = st.multiselect("Ca 2 (22-02h):", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in def_tt2], key="tt2")

            st.markdown('<div class="dot-xuat-container">', unsafe_allow_html=True)
            st.subheader("🆘 3. ĐỘT XUẤT")
            if 'n_dx' not in st.session_state: st.session_state.n_dx = 1
            if st.button("➕ Thêm việc"): st.session_state.n_dx += 1
            s_dx = current_saved[current_saved['LoaiNhiemVu'].str.contains("ĐX: ", na=False)]
            u_t = s_dx['LoaiNhiemVu'].unique().tolist()
            dx_res = []
            for i in range(max(st.session_state.n_dx, len(u_t))):
                cx1, cx2, cx3 = st.columns([3, 5, 1])
                d_n = u_t[i].replace("ĐX: ", "") if i < len(u_t) else ""
                d_m = s_dx[s_dx['LoaiNhiemVu'] == u_t[i]]['HoTen'].tolist() if i < len(u_t) else []
                with cx1: t_n = st.text_input(f"Việc {i+1}", value=d_n, key=f"dxn_{i}")
                with cx2: t_m = st.multiselect(f"Quân {i+1}", pool_dx["Display"], default=[d for d in pool_dx["Display"] if d.split(" (")[0] in d_m], key=f"dxm_{i}")
                with cx3: t_d = st.number_input(f"Đ", 1, 15, 3, key=f"dxd_{i}", label_visibility="collapsed")
                if t_n and t_m:
                    for m in t_m: dx_res.append({"HoTen": m.split(" (")[0], "LoaiNhiemVu": f"ĐX: {t_n}", "Gio": "Đột xuất", "Diem": t_d})
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("💾 LƯU PHƯƠNG ÁN ĐIỀU ĐỘNG", use_container_width=True, type="primary"):
                final = g_res + [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2} for p in tt1] + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2} for p in tt2] + dx_res
                df_s = pd.DataFrame(final)
                df_s["Tuan"], df_s["Ngay"], df_s["NgayTao"] = selected_week, selected_day, datetime.now().strftime("%d/%m/%Y %H:%M")
                df_save = pd.concat([df_history[~((df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day))], df_s], ignore_index=True)
                conn.update(worksheet="NhiemVu", data=df_save)
                st.success("Đã lưu thành công!"); st.rerun()

    # --- TAB 3: ĐIỂM DANH (CHỈ HIỆN Đ/C TRỰC - CHỈ LƯU VẮNG) ---
    with tab_attendance:
        if not is_admin:
            st.warning("Vui lòng nhập Mã điều hành để điểm danh.")
        else:
            st.subheader(f"✅ ĐIỂM DANH QUÂN SỐ TRỰC {selected_day}")
            current_active_names = sorted(list(set(morning_list + night_cax_list + night_ap_list)))
            
            if not current_active_names:
                st.info("Ngày này không có đồng chí nào trực.")
            else:
                with st.form("form_att_v2"):
                    vắng_data = []
                    for name in current_active_names:
                        c1, c2, c3 = st.columns([3, 3, 4])
                        c1.write(f"**{name}**")
                        stt = c2.radio("Trạng thái", ["Có mặt", "Vắng"], key=f"at_{name}", horizontal=True, label_visibility="collapsed")
                        re = c3.text_input("Lý do", key=f"ar_{name}", placeholder="Lý do vắng...", label_visibility="collapsed")
                        
                        if stt == "Vắng":
                            lt = []
                            if name in morning_list: lt.append("Sáng")
                            if name in night_cax_list: lt.append("Đêm Xã")
                            if name in night_ap_list: lt.append("Đêm Ấp")
                            vắng_data.append({
                                "Tuan": selected_week, "Ngay": selected_day, "HoTen": name, 
                                "TrangThai": "Vắng", "LyDo": re, "LoaiTruc": ", ".join(lt), 
                                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M")
                            })
                    
                    if st.form_submit_button("💾 XÁC NHẬN & LƯU VẮNG"):
                        if vắng_data:
                            try:
                                df_db = conn.read(spreadsheet=URL_SHEET, worksheet="DiemDanh")
                                df_f = pd.concat([df_db, pd.DataFrame(vắng_data)], ignore_index=True)
                                conn.update(worksheet="DiemDanh", data=df_f)
                                st.success(f"Đã lưu {len(vắng_data)} đ/c vắng mặt vào Google Sheet.")
                            except Exception as e: st.error(f"Lỗi bảng DiemDanh: {e}")
                        else: st.success("Tất cả có mặt đủ!")

    # --- QUÂN SỐ TỔNG QUAN (CÔNG KHAI) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN</div>', unsafe_allow_html=True)
    c_s, c_d, c_a = st.columns(3)
    with c_s:
        st.markdown("<p style='color:#2563EB; font-weight:bold; text-align:center;'>☀️ TRỰC SÁNG</p>", unsafe_allow_html=True)
        for n in morning_list:
            is_night_cax = n in night_cax_list
            card_class = "morning-night-card" if is_night_cax else "morning-card"
            st.markdown(f'<div class="{card_class}"><div class="name-tag">{n} {"🌙" if is_night_cax else ""}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)
    with c_d:
        st.markdown("<p style='color:#EA580C; font-weight:bold; text-align:center;'>🌙 TRỰC ĐÊM XÃ</p>", unsafe_allow_html=True)
        for n in night_cax_list: st.markdown(f'<div class="night-cax-card"><div class="name-tag">{n}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)
    with c_a:
        st.markdown("<p style='color:#16A34A; font-weight:bold; text-align:center;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in night_ap_list: st.markdown(f'<div class="night-ap-card"><div class="name-tag">{n}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
