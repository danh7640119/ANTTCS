import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH & BẢO MẬT ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    URL_SHEET = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("⚠️ LỖI CẤU HÌNH: Kiểm tra lại Streamlit Secrets!")
    st.stop()

LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thụy Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm", "Lê Thanh Tuyền"]

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# --- 2. CƠ CHẾ CACHE ĐỂ LOAD NHANH (10 giây làm mới) ---
@st.cache_data(ttl=10, show_spinner=False)
def load_gsheet_data(_conn, sheet_url, worksheet):
    return _conn.read(spreadsheet=sheet_url, worksheet=worksheet)

# CSS Giao diện
st.markdown("""
    <style>
    .dot-xuat-container { background-color: #FFF5F5; padding: 20px; border-radius: 10px; border: 2px dashed #FECACA; margin: 15px 0; }
    .morning-card { padding: 8px; border-radius: 5px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 5px; }
    .night-cax-card { padding: 8px; border-radius: 5px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 5px; }
    .night-ap-card { padding: 8px; border-radius: 5px; border-left: 5px solid #16A34A; background-color: #F0FDF4; margin-bottom: 5px; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .ap-tag { color: #64748B; font-size: 12px; font-style: italic; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Tải dữ liệu gốc
    raw_data = load_gsheet_data(conn, URL_SHEET, "luutru")
    df_raw = raw_data.iloc[2:].copy() # Bỏ 2 dòng đầu
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # Tải lịch sử phân công
    df_history = load_gsheet_data(conn, URL_SHEET, "NhiemVu")
    if df_history.empty:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # Sidebar điều khiển
    st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    # --- TÙY BIẾN CA GÁC (MỚI) ---
    st.sidebar.divider()
    st.sidebar.subheader("⏰ Tùy chỉnh ca gác")
    default_times = "07-10h, 10-13h, 13-15h, 15-17h, 17-20h, 20-23h, 23-01h, 01-03h, 03-05h, 05-07h"
    custom_times_str = st.sidebar.text_area("Danh sách giờ (cách nhau bằng dấu phẩy):", value=default_times)
    list_gio = [t.strip() for t in custom_times_str.split(",") if t.strip()]

    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT", "✅ ĐIỂM DANH"])

    # --- TAB 1: XEM NHIỆM VỤ (Tối ưu tốc độ) ---
    with tab_view:
        st.subheader(f"📌 LỊCH PHÂN CÔNG {selected_day} - TUẦN {selected_week}")
        tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            tasks['Ấp'] = tasks['HoTen'].map(dict_ap)
            c1, c2 = st.columns(2)
            with c1:
                st.info("🛡️ GÁC CỔNG")
                g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng']
                st.table(g_df[["Gio", "HoTen", "Ấp"]])
            with c2:
                st.warning("🚔 TUẦN TRA & ĐỘT XUẤT")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Ấp"]])
        else:
            st.info("Chưa có dữ liệu phân công chi tiết.")

    # --- TAB 2: PHÂN CÔNG (TÙY BIẾN LINH HOẠT) ---
    with tab_manage:
        if not is_admin:
            st.warning("Nhập mã để phân công.")
        else:
            current_saved = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
            day_summary = current_saved.groupby("HoTen")["Diem"].sum().reset_index() if not current_saved.empty else pd.DataFrame(columns=["HoTen", "Diem"])

            def get_pool(target_names, is_dx=False):
                names_nam = [n for n in target_names if n not in LIST_NU]
                df_p = pd.DataFrame({"HoTen": names_nam}).merge(day_summary, on="HoTen", how="left").fillna(0)
                def set_prio(name):
                    if name in night_cax_list: return 1
                    if name in night_ap_list: return 2
                    return 3
                df_p['Prio'] = df_p['HoTen'].apply(set_prio)
                df_p['StName'] = df_p['HoTen'].apply(lambda n: "Trực Xã" if n in night_cax_list else (f"Trực {dict_ap.get(n)}" if n in night_ap_list else "Trực Sáng"))
                # Sắp xếp theo yêu cầu của đồng chí
                if is_dx: df_p = df_p.sort_values(['Prio', 'Diem'], ascending=[True, True])
                else: df_p = df_p.sort_values(['Diem', 'Prio'], ascending=[True, True])
                df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({r['StName']}) - {int(r['Diem'])}đ", axis=1)
                return df_p

            pool_s = get_pool(morning_list)
            pool_d = get_pool(night_cax_list)
            pool_dx = get_pool(list(set(morning_list + night_cax_list + night_ap_list)), is_dx=True)

            st.subheader("🛡️ 1. GÁC CỔNG (Tự động theo danh sách giờ)")
            g_res = []
            cg1, cg2 = st.columns(2)
            for i, gio in enumerate(list_gio):
                # Tự động chọn pool: sáng cho các ca sớm, đêm cho các ca muộn (tạm chia đôi danh sách)
                p_df = pool_s if i < (len(list_gio)/2) else pool_d
                saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                idx = 0
                if not saved.empty and not p_df.empty:
                    m = p_df[p_df['HoTen'] == saved.iloc[0]['HoTen']]
                    if not m.empty: idx = p_df.index.get_loc(m.index[0])
                
                with (cg1 if i % 2 == 0 else cg2):
                    if not p_df.empty:
                        sel = st.selectbox(f"Ca {gio}", p_df["Display"], index=idx, key=f"gac_{gio}")
                        g_res.append({"HoTen": sel.split(" (")[0], "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": 1})

            st.subheader("🚔 2. TUẦN TRA")
            ct1, ct2 = st.columns(2)
            def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
            def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
            with ct1: tt1 = st.multiselect("Ca 1:", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in def_tt1])
            with ct2: tt2 = st.multiselect("Ca 2:", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in def_tt2])

            st.markdown('<div class="dot-xuat-container">', unsafe_allow_html=True)
            st.subheader("🆘 3. ĐỘT XUẤT")
            if 'n_dx' not in st.session_state: st.session_state.n_dx = 1
            if st.button("➕ Thêm việc"): st.session_state.n_dx += 1
            dx_res = []
            for i in range(st.session_state.n_dx):
                cx1, cx2, cx3 = st.columns([3, 5, 1])
                with cx1: t_n = st.text_input(f"Việc {i+1}", key=f"dxn_{i}")
                with cx2: t_m = st.multiselect(f"Quân {i+1}", pool_dx["Display"], key=f"dxm_{i}")
                with cx3: t_d = st.number_input(f"Đ", 1, 10, 1, key=f"dxd_{i}")
                if t_n and t_m:
                    for m in t_m: dx_res.append({"HoTen": m.split(" (")[0], "LoaiNhiemVu": f"ĐX: {t_n}", "Gio": "Đột xuất", "Diem": t_d})
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("💾 LƯU PHƯƠNG ÁN", use_container_width=True, type="primary"):
                final = g_res + [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1} for p in tt1] + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1} for p in tt2] + dx_res
                df_s = pd.DataFrame(final)
                df_s["Tuan"], df_s["Ngay"], df_s["NgayTao"] = selected_week, selected_day, datetime.now().strftime("%d/%m/%Y %H:%M")
                df_save = pd.concat([df_history[~((df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day))], df_s], ignore_index=True)
                conn.update(worksheet="NhiemVu", data=df_save)
                st.cache_data.clear() # Xóa cache để cập nhật dữ liệu mới
                st.success("Đã lưu!"); st.rerun()

    # --- TAB 3: ĐIỂM DANH ---
    with tab_attendance:
        if not is_admin: st.warning("Nhập mã.")
        else:
            active_names = sorted(list(set(morning_list + night_cax_list + night_ap_list)))
            with st.form("form_att"):
                v_list = []
                for n in active_names:
                    c1, c2, c3 = st.columns([3, 3, 4])
                    c1.write(f"**{n}**")
                    stt = c2.radio("TT", ["Có mặt", "Vắng"], key=f"at_{n}", horizontal=True, label_visibility="collapsed")
                    re = c3.text_input("Lý do", key=f"ar_{n}", label_visibility="collapsed")
                    if stt == "Vắng":
                        v_list.append({"Tuan": selected_week, "Ngay": selected_day, "HoTen": n, "TrangThai": "Vắng", "LyDo": re, "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M")})
                if st.form_submit_button("Lưu vắng"):
                    df_db = load_gsheet_data(conn, URL_SHEET, "DiemDanh")
                    conn.update(worksheet="DiemDanh", data=pd.concat([df_db, pd.DataFrame(v_list)], ignore_index=True))
                    st.cache_data.clear()
                    st.success("Xong!"); st.rerun()

    # --- TỔNG QUAN QUÂN SỐ ---
    st.markdown('<div class="section-header">👥 TỔNG QUAN QUÂN SỐ</div>', unsafe_allow_html=True)
    c_s, c_d, c_a = st.columns(3)
    with c_s:
        st.markdown("**☀️ SÁNG**")
        for n in morning_list: st.markdown(f'<div class="morning-card">{n} ({dict_ap.get(n)})</div>', unsafe_allow_html=True)
    with c_d:
        st.markdown("**🌙 XÃ**")
        for n in night_cax_list: st.markdown(f'<div class="night-cax-card">{n} ({dict_ap.get(n)})</div>', unsafe_allow_html=True)
    with c_a:
        st.markdown("**🏡 ẤP**")
        for n in night_ap_list: st.markdown(f'<div class="night-ap-card">{n} ({dict_ap.get(n)})</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
