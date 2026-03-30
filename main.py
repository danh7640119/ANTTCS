import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Chỉ huy ANTT", layout="wide", page_icon="👮")

st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 15px; border-radius: 12px; border-left: 8px solid #1E3A8A; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .double-duty { background-color: #FFFBEB; border-left: 8px solid #F59E0B; border: 2px solid #FDE68A; }
    .name-text { color: #1E3A8A; font-size: 16px; font-weight: bold; }
    .location-tag { margin-top: 5px; font-weight: bold; color: #059669; background-color: #ECFDF5; padding: 2px 8px; border-radius: 4px; display: inline-block; font-size: 12px; }
    .group-header { background-color: #1E3A8A; color: white; padding: 10px; border-radius: 5px; margin: 15px 0; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- DANH SÁCH CÁC ĐỒNG CHÍ NỮ (Bạn hãy điền tên chính xác vào đây) ---
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"] 

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu
    df_raw = conn.read(spreadsheet=url, ttl=0, worksheet="1727254590", skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    for col in df.columns[3:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # Đọc lịch sử nhiệm vụ
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 2. XỬ LÝ THỜI GIAN ---
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    now = datetime.now()
    today_str = now.strftime("%d/%m")
    default_week_idx = next((i for i, w in enumerate(list_weeks) if today_str in str(w)), 0)

    st.title("📋 QUẢN LÝ QUÂN SỐ & PHÂN CÔNG")

    # --- 3. BỘ LỌC SIDEBAR ---
    st.sidebar.header("📅 THỜI GIAN")
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks, index=default_week_idx)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn ngày:", days_vn, index=now.weekday())
    selected_shift = st.sidebar.radio("Xem danh sách trực:", ["Sáng", "Đêm"], horizontal=True)

    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    # --- 4. HIỂN THỊ DANH SÁCH QUÂN SỐ (NHƯ BAN ĐẦU) ---
    st.markdown(f'<div class="time-box">📅 {selected_week} | {selected_day} | Ca {selected_shift}</div>', unsafe_allow_html=True)
    
    night_list_cax = df_week[df_week[f"{d_code}_D_CAX"] == 'x']['HoTen'].tolist()
    night_list_ap = df_week[df_week[f"{d_code}_D_Ap"] == 'x']['HoTen'].tolist()
    morning_list = df_week[df_week[f"{d_code}_N"] == 'x']['HoTen'].tolist()

    if selected_shift == "Sáng":
        on_duty = df_week[df_week[f"{d_code}_N"] == 'x']
        st.markdown(f'<div class="group-header">DANH SÁCH TRỰC BAN NGÀY ({len(on_duty)} đ/c)</div>', unsafe_allow_html=True)
        cols_grid = st.columns(3)
        for i, (_, row) in enumerate(on_duty.iterrows()):
            is_double = "double-duty" if (row['HoTen'] in night_list_cax or row['HoTen'] in night_list_ap) else ""
            with cols_grid[i % 3]:
                st.markdown(f'<div class="duty-card {is_double}"><div class="name-text">{row["HoTen"]}</div><div class="location-tag">📍 Tại Xã</div></div>', unsafe_allow_html=True)
    else:
        cax_duty = df_week[df_week[f"{d_code}_D_CAX"] == 'x']
        ap_duty = df_week[df_week[f"{d_code}_D_Ap"] == 'x']
        st.markdown(f'<div class="group-header">DANH SÁCH TRỰC ĐÊM ({len(cax_duty)+len(ap_duty)} đ/c)</div>', unsafe_allow_html=True)
        st.subheader("🏢 Tại Công an xã")
        c1 = st.columns(3)
        for i, (_, r) in enumerate(cax_duty.iterrows()):
            is_db = "double-duty" if r['HoTen'] in morning_list else ""
            with c1[i % 3]: st.markdown(f'<div class="duty-card {is_db}"><div class="name-text">{r["HoTen"]}</div></div>', unsafe_allow_html=True)
        st.subheader("🏘️ Tại các Ấp")
        c2 = st.columns(3)
        for i, (_, r) in enumerate(ap_duty.iterrows()):
            is_db = "double-duty" if r['HoTen'] in morning_list else ""
            with c2[i % 3]: st.markdown(f'<div class="duty-card {is_db}"><div class="name-text">{r["HoTen"]}</div></div>', unsafe_allow_html=True)

    # --- 5. LOGIC LỌC ĐỐI TƯỢNG PHÂN CÔNG ---
    # Người tại xã (Sáng + Đêm Xã) - Loại trừ Nữ
    nguoi_tai_xa = df_week[(df_week[f"{d_code}_N"] == 'x') | (df_week[f"{d_code}_D_CAX"] == 'x')]
    list_nam_xa = [n for n in nguoi_tai_xa['HoTen'].tolist() if n not in LIST_NU]
    
    # Toàn bộ quân số (bao gồm cả Ấp) cho nhiệm vụ phát sinh
    list_tat_ca = df_week['HoTen'].tolist()

    # Tính điểm cuốn chiếu
    if not df_history.empty:
        summary = df_history.groupby("HoTen")["Diem"].sum().reset_index()
        df_prio = pd.DataFrame({"HoTen": list_nam_xa}).merge(summary, on="HoTen", how="left").fillna(0)
        list_goi_y = df_prio.sort_values(by="Diem", ascending=True)["HoTen"].tolist()
    else:
        list_goi_y = list_nam_xa

    # --- 6. PHẦN GỢI Ý & PHÂN CÔNG (Ở DƯỚI CÙNG) ---
    st.markdown("---")
    st.header("⚡ PHÂN CÔNG NHIỆM VỤ CỤ THỂ")
    
    col_g, col_t = st.columns(2)
    
    with col_g:
        st.subheader("🛡️ Gác cổng (Chỉ ca ngày tới 17h)")
        CA_GAC_NGAY = [("07:00-10:00",1), ("10:00-13:00",1), ("13:00-15:00",1), ("15:00-17:00",1)]
        final_gac = []
        for i, (g, d) in enumerate(CA_GAC_NGAY):
            sel = st.selectbox(f"Ca {g}", list_goi_y, index=i%len(list_goi_y) if list_goi_y else 0, key=f"g_{i}")
            final_gac.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": g, "Diem": d})

    with col_t:
        st.subheader("🚔 Tuần tra đêm (Chỉ đ/c tại Xã)")
        tt1 = st.multiselect("Ca 1 (18h-22h):", list_goi_y)
        tt2 = st.multiselect("Ca 2 (22h-02h):", list_goi_y)

    st.subheader("🆘 Nhiệm vụ phát sinh (Giữ đối tượng...)")
    st.caption("Lưu ý: Có thể chọn cả các đồng chí trực tại Ấp")
    col_ps1, col_ps2, col_ps3 = st.columns([2,1,1])
    with col_ps1: ps_name = st.text_input("Tên việc phát sinh:")
    with col_ps2: ps_mem = st.multiselect("Đồng chí thực hiện:", list_tat_ca)
    with col_ps3: ps_d = st.number_input("Điểm thưởng:", 1, 5, 3)

    if st.button("💾 XÁC NHẬN VÀ LƯU TOÀN BỘ", use_container_width=True, type="primary"):
        data_save = []
        data_save.extend(final_gac)
        for p in tt1: data_save.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
        for p in tt2: data_save.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
        if ps_name and ps_mem:
            for p in ps_mem: data_save.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_d})
        
        df_final = pd.DataFrame(data_save)
        df_final["Tuan"] = selected_week
        df_final["Ngay"] = selected_day
        df_final["NgayTao"] = datetime.now().strftime("%d/%m/%Y")
        
        try:
            updated_df = pd.concat([df_history, df_final], ignore_index=True)
            conn.update(worksheet="NhiemVu", data=updated_df)
            st.success("🎉 Đã lưu thành công và cập nhật điểm tích lũy!")
        except:
            st.error("Lỗi: Không thể ghi dữ liệu. Kiểm tra Sheet 'NhiemVu'.")

except Exception as e:
    st.error(f"Lỗi: {e}")
