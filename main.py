import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
ADMIN_PASSWORD = "13579" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện (Giữ phong cách chuyên nghiệp)
st.markdown("""
    <style>
    .dot-xuat-container { background-color: #FFF5F5; padding: 20px; border-radius: 10px; border: 2px dashed #FECACA; margin: 15px 0; }
    .morning-card { padding: 10px; border-radius: 8px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 8px; }
    .night-cax-card { padding: 10px; border-radius: 8px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 8px; }
    .double-duty-warning { background-color: #FEE2E2 !important; border: 2px solid #EF4444 !important; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .ap-tag { color: #64748B; font-size: 12px; font-style: italic; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
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

    # Sidebar điều hướng
    st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    list_weeks = df_mem['Tuan'].unique().tolist()[::-1]
    selected_week = st.sidebar.selectbox("Tuần trực:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT"])

    with tab_view:
        st.subheader(f"📌 LỊCH CÔNG TÁC {selected_day}")
        tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.info("🛡️ Gác Cổng (Theo ID ca)")
                gac_v = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                gac_v['SortID'] = gac_v['Gio'].map(GIO_ORDER)
                st.table(gac_v.sort_values('SortID')[["Gio", "HoTen"]])
            with c2:
                st.warning("🚔 Tuần Tra & Đột Xuất")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Gio"]])
        else: st.info("Chưa có lịch phân công cho ngày này.")

    with tab_manage:
        if not is_admin:
            st.warning("Vui lòng nhập đúng Mã điều hành để thực hiện phân công.")
        else:
            current_saved = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
            summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
            
            def get_selection_pool(names):
                names_nam = [n for n in names if n not in LIST_NU]
                df_p = pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0)
                df_p = df_p.sort_values("Diem", ascending=True)
                df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({dict_ap.get(r['HoTen'], 'N/A')}) - {int(r['Diem'])}đ", axis=1)
                return df_p

            pool_s_df = get_selection_pool(morning_list)
            pool_d_df = get_selection_pool(night_cax_list)
            all_mem_df = get_selection_pool(df_mem['HoTen'].unique().tolist())
            display_to_real = dict(zip(all_mem_df["Display"], all_mem_df["HoTen"]))

            # 1. PHẦN GÁC CỔNG
            st.subheader("🛡️ 1. PHÂN CA GÁC CỔNG")
            gac_results = []
            cg1, cg2 = st.columns(2)
            for i, gio in enumerate(list(GIO_ORDER.keys())):
                p_df = pool_s_df if i < 4 else pool_d_df
                saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                
                default_idx = 0
                if not saved.empty and not p_df.empty:
                    match = p_df[p_df['HoTen'] == saved.iloc[0]['HoTen']]
                    if not match.empty: default_idx = p_df.index.get_loc(match.index[0])
                
                with (cg1 if i < 5 else cg2):
                    if not p_df.empty:
                        sel = st.selectbox(f"Ca {gio}", p_df["Display"], index=default_idx, key=f"gac_v15_{i}")
                        gac_results.append({"HoTen": display_to_real[sel], "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": (1 if i < 4 else 2)})

            # 2. PHẦN TUẦN TRA
            st.divider()
            st.subheader("🚔 2. TUẦN TRA ĐÊM")
            def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist() or pool_d_df["HoTen"].head(4).tolist()
            def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist() or pool_d_df["HoTen"].iloc[4:8].tolist()
            
            ct1, ct2 = st.columns(2)
            with ct1: 
                tt1_sel = st.multiselect("Ca 1 (18-22h):", pool_d_df["Display"], 
                                         default=[f"{n} ({dict_ap.get(n)}) - {int(summary[summary['HoTen']==n]['Diem'].sum())}đ" for n in def_tt1 if n in pool_d_df["HoTen"].values])
            with ct2: 
                tt2_sel = st.multiselect("Ca 2 (22-02h):", pool_d_df["Display"], 
                                         default=[f"{n} ({dict_ap.get(n)}) - {int(summary[summary['HoTen']==n]['Diem'].sum())}đ" for n in def_tt2 if n in pool_d_df["HoTen"].values])

            # 3. PHẦN ĐỘT XUẤT (DIV RIÊNG)
            st.markdown('<div class="dot-xuat-container">', unsafe_allow_html=True)
            st.subheader("🆘 3. ĐIỀU ĐỘNG ĐỘT XUẤT")
            if 'num_tasks_v15' not in st.session_state: st.session_state.num_tasks_v15 = 1
            if st.button("➕ Thêm đầu việc đột xuất"): st.session_state.num_tasks_v15 += 1
            
            saved_dx = current_saved[current_saved['LoaiNhiemVu'].str.contains("ĐX: ", na=False)]
            unique_tasks = saved_dx['LoaiNhiemVu'].unique().tolist()
            dx_results = []
            
            loop_cnt = max(st.session_state.num_tasks_v15, len(unique_tasks))
            for i in range(loop_cnt):
                st.write(f"**Nhóm việc {i+1}:**")
                c_dx1, c_dx2, c_dx3 = st.columns([3, 5, 1])
                d_name = unique_tasks[i].replace("ĐX: ", "") if i < len(unique_tasks) else ""
                d_m_real = saved_dx[saved_dx['LoaiNhiemVu'] == unique_tasks[i]]['HoTen'].tolist() if i < len(unique_tasks) else []
                
                with c_dx1: t_name = st.text_input(f"Tên nhiệm vụ {i+1}", value=d_name, key=f"dx_n15_{i}", placeholder="VD: Truy bắt...")
                with c_dx2: t_m_sel = st.multiselect(f"Phân quân số {i+1}", all_mem_df["Display
