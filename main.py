import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH ---
ADMIN_PASSWORD = "123" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện
st.markdown("""
    <style>
    .dot-xuat-container { background-color: #FFF5F5; padding: 20px; border-radius: 10px; border: 2px dashed #FECACA; margin: 15px 0; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .ap-tag { color: #64748B; font-size: 12px; font-style: italic; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # ĐỌC DỮ LIỆU
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
    st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    # Phân loại danh sách trực trong ngày
    morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG ĐỘT XUẤT & CHI TIẾT"])

    with tab_manage:
        if not is_admin:
            st.warning("Vui lòng nhập Mã điều hành.")
        else:
            current_saved = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
            summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])

            # --- LOGIC ƯU TIÊN ĐIỀU ĐỘNG ĐỘT XUẤT ---
            def get_prioritized_pool():
                # Lấy toàn bộ danh sách nam
                all_nam = [n for n in df_mem['HoTen'].unique() if n not in LIST_NU]
                df_p = pd.DataFrame({"HoTen": all_nam})
                df_p = df_p.merge(summary, on="HoTen", how="left").fillna(0)
                
                # Gán nhãn ưu tiên
                def check_status(name):
                    if name in night_cax_list: return (1, "Trực Xã")
                    if name in night_ap_list: return (2, f"Trực {dict_ap.get(name)}")
                    return (3, "Nghỉ/Hết ca")
                
                df_p['StatusInfo'] = df_p['HoTen'].apply(check_status)
                df_p['Priority'] = df_p['StatusInfo'].apply(lambda x: x[0])
                df_p['StatusName'] = df_p['StatusInfo'].apply(lambda x: x[1])
                
                # Sắp xếp: Ưu tiên (Xã -> Ấp -> Nghỉ) sau đó đến Điểm (Thấp -> Cao)
                df_p = df_p.sort_values(by=['Priority', 'Diem'], ascending=[True, True])
                
                df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({r['StatusName']}) - {int(r['Diem'])}đ", axis=1)
                return df_p

            pool_all = get_prioritized_pool()
            display_to_real = dict(zip(pool_all["Display"], pool_all["HoTen"]))

            # 1. PHẦN ĐỘT XUẤT (ĐƯA LÊN ĐẦU VÌ TÍNH CẤP THIẾT)
            st.markdown('<div class="dot-xuat-container">', unsafe_allow_html=True)
            st.subheader("🆘 ĐIỀU ĐỘNG ĐỘT XUẤT (Ưu tiên quân số tại Xã)")
            if 'num_dx_v16' not in st.session_state: st.session_state.num_dx_v16 = 1
            if st.button("➕ Thêm nhóm nhiệm vụ mới"): st.session_state.num_dx_v16 += 1
            
            saved_dx = current_saved[current_saved['LoaiNhiemVu'].str.contains("ĐX: ", na=False)]
            u_tasks = saved_dx['LoaiNhiemVu'].unique().tolist()
            dx_res = []
            
            for i in range(max(st.session_state.num_dx_v16, len(u_tasks))):
                st.write(f"**Nhiệm vụ {i+1}:**")
                c1, c2, c3 = st.columns([3, 5, 1])
                d_n = u_tasks[i].replace("ĐX: ", "") if i < len(u_tasks) else ""
                d_m = saved_dx[saved_dx['LoaiNhiemVu'] == u_tasks[i]]['HoTen'].tolist() if i < len(u_tasks) else []
                
                with c1: t_n = st.text_input(f"Tên việc {i+1}", value=d_n, key=f"dxn_{i}", placeholder="VD: Bắt trộm, Gây rối...")
                with c2: 
                    # Multiselect giờ đây sẽ hiện những người đang trực Xã ngay đầu danh sách
                    t_m = st.multiselect(f"Chọn Đ/C {i+1}", pool_all["Display"], 
                                         default=[f"{n} ({get_prioritized_pool().query('HoTen == @n')['StatusName'].iloc[0]}) - {int(summary[summary['HoTen']==n]['Diem'].sum())}đ" for n in d_m if n in pool_all["HoTen"].values], 
                                         key=f"dxm_{i}")
                with c3: t_d = st.number_input(f"Điểm", 1, 20, 3, key=f"dxd_{i}")
                
                if t_n and t_m:
                    for m_d in t_m: dx_res.append({"HoTen": display_to_real[m_d], "LoaiNhiemVu": f"ĐX: {t_n}", "Gio": "Đột xuất", "Diem": t_d})
            st.markdown('</div>', unsafe_allow_html=True)

            # 2. PHẦN CỐ ĐỊNH (Gác, Tuần tra - giữ logic cũ nhưng hiển thị rõ địa bàn)
            st.subheader("🛡️ CÁC CA TRỰC CỐ ĐỊNH TRONG NGÀY")
            # ... (Phần code Selectbox Gác cổng và Tuần tra tương tự bản trước) ...

            if st.button("💾 XÁC NHẬN LƯU PHƯƠNG ÁN", use_container_width=True, type="primary"):
                # Logic lưu vào Google Sheets
                pass

    # --- TAB XEM & DANH SÁCH TỔNG ---
    # ... (Giữ nguyên giao diện đẹp từ bản V15) ...

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
