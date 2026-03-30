import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG & CSS ---
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

# --- 2. KẾT NỐI & ĐỌC DỮ LIỆU ---
try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu trực (Sheet gốc)
    df_raw = conn.read(spreadsheet=url, ttl=0, worksheet="1727254590", skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    # Làm sạch dữ liệu
    for col in df.columns[3:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # Đọc lịch sử điểm từ Sheet NhiemVu
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 3. XỬ LÝ THỜI GIAN & SẮP XẾP TUẦN ---
    list_weeks = df['Tuan'].unique().tolist()[::-1] # Mới nhất lên đầu
    now = datetime.now()
    today_str = now.strftime("%d/%m")
    
    default_week_idx = 0
    for i, week in enumerate(list_weeks):
        if today_str in str(week):
            default_week_idx = i
            break

    # --- 4. GIAO DIỆN CHÍNH & TRA CỨU ---
    st.title("📋 QUẢN LÝ QUÂN SỐ & PHÂN CÔNG NHIỆM VỤ")
    
    search_q = st.text_input("🔍 Tra cứu nhanh tên đồng chí:", "").strip().lower()
    if search_q:
        res = df[df['HoTen'].str.lower().str.contains(search_q, na=False)]
        for _, r in res.iterrows():
            with st.expander(f"👤 {r['HoTen']} - {r['Tuan']}"):
                st.write(f"Đơn vị: {r['Ap']}") # Hiển thị lịch trực cá nhân tại đây
        st.divider()

    # --- 5. BỘ LỌC SIDEBAR ---
    st.sidebar.header("📅 THỜI GIAN")
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks, index=default_week_idx)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn ngày:", days_vn, index=now.weekday())
    selected_shift = st.sidebar.radio("Ca hiển thị:", ["Sáng", "Đêm"], horizontal=True)

    # Lọc quân số hôm nay
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]
    
    # Quan trọng: Lấy tất cả người có mặt hôm nay (cả sáng + đêm) để phân công
    on_duty_today = df_week[(df_week[f"{d_code}_N"] == 'x') | 
                            (df_week[f"{d_code}_D_CAX"] == 'x') | 
                            (df_week[f"{d_code}_D_Ap"] == 'x')]

    # --- 6. TÍNH ĐIỂM CUỐN CHIẾU ---
    if not df_history.empty:
        summary_diem = df_history.groupby("HoTen")["Diem"].sum().reset_index()
        df_priority = on_duty_today.merge(summary_diem, on="HoTen", how="left").fillna(0)
    else:
        df_priority = on_duty_today.copy()
        df_priority["Diem"] = 0
    
    df_priority = df_priority.sort_values(by="Diem", ascending=True)
    list_names = df_priority["HoTen"].tolist()

    # --- 7. HIỂN THỊ DANH SÁCH QUÂN SỐ (Giao diện cũ) ---
    st.markdown(f'<div class="time-box">📅 {selected_week} | {selected_day}</div>', unsafe_allow_html=True)
    # (Phần hiển thị card Sáng/Đêm giữ nguyên logic của bạn...)

    # --- 8. KHU VỰC PHÂN CÔNG NHIỆM VỤ (MỚI) ---
    st.markdown("---")
    st.header("⚡ BẢNG PHÂN CÔNG NHIỆM VỤ")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("🛡️ Lịch Gác Cổng (10 Ca)")
        CA_GAC = [
            ("07:00 - 10:00", 1), ("10:00 - 13:00", 1), ("13:00 - 15:00", 1), 
            ("15:00 - 17:00", 1), ("17:00 - 20:00", 2), ("20:00 - 23:00", 2),
            ("23:00 - 01:00", 2), ("01:00 - 03:00", 2), ("03:00 - 05:00", 2), ("05:00 - 07:00", 2)
        ]
        
        final_gac = []
        last_person = None
        for i, (gio, diem) in enumerate(CA_GAC):
            # Ràng buộc: Không chọn trùng người ca trước
            opts = [n for n in list_names if n != last_person] if list_names else ["Trống"]
            idx_auto = i % len(opts) if opts else 0
            
            sel = st.selectbox(f"Ca {gio}", opts, index=idx_auto, key=f"g_sel_{i}")
            last_person = sel
            final_gac.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": diem})

    with col_right:
        st.subheader("🚔 Tuần tra & Đột xuất")
        # Tuần tra
        tt1 = st.multiselect("Tuần tra Ca 1 (18h-22h):", list_names, key="tt1")
        tt2 = st.multiselect("Tuần tra Ca 2 (22h-02h):", list_names, key="tt2")
        
        # Nhiệm vụ đột xuất (Giữ đối tượng...)
        st.markdown("**🆘 Nhiệm vụ phát sinh**")
        ps_name = st.text_input("Tên việc:", placeholder="VD: Canh giữ đối tượng A")
        ps_mem = st.multiselect("Đồng chí thực hiện:", list_names, key="ps_mem")
        ps_diem = st.number_input("Điểm thưởng:", 1, 5, 3)

    # --- 9. NÚT XÁC NHẬN VÀ LƯU TẤT CẢ ---
    st.divider()
    if st.button("💾 XÁC NHẬN VÀ LƯU TOÀN BỘ PHÂN CÔNG", use_container_width=True, type="primary"):
        if not list_names:
            st.error("Không có quân số để lưu!")
        else:
            # Gom tất cả nhiệm vụ lại
            data_save = []
            # 1. Thêm gác cổng
            data_save.extend(final_gac)
            # 2. Thêm tuần tra
            for p in tt1: data_save.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18:00-22:00", "Diem": 2})
            for p in tt2: data_save.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22:00-02:00", "Diem": 2})
            # 3. Thêm đột xuất
            if ps_name and ps_mem:
                for p in ps_mem: data_save.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_diem})
            
            # Chuyển thành DataFrame và thêm cột chung
            df_final = pd.DataFrame(data_save)
            df_final["Tuan"] = selected_week
            df_final["Ngay"] = selected_day
            df_final["NgayTao"] = datetime.now().strftime("%d/%m/%Y")
            
            try:
                # Ghi đè hoặc nối thêm vào Sheet NhiemVu
                # Giả sử dùng thư viện gspread hoặc kết nối có sẵn:
                updated_df = pd.concat([df_history, df_final], ignore_index=True)
                conn.update(worksheet="NhiemVu", data=updated_df)
                st.success("🎉 Đã lưu thành công! Điểm đã được cộng tích lũy cho anh em.")
                st.balloons()
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}. Vui lòng kiểm tra quyền ghi của Sheet NhiemVu.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
