import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import google.generativeai as genai
import json
import re

# --- 1. CẤU HÌNH TRANG & BẢO MẬT ---
st.set_page_config(
    page_title="Điều Hành Trực ANTTCS Bắc Tân Uyên",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS giao diện hiện đại, tối ưu mobile & thẻ nhiệm vụ
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background: #ffffff; padding: 12px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .card-task {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
        border-left: 5px solid #2563eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-sang { background-color: #fef3c7; color: #b45309; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; }
    .badge-dem { background-color: #ede9fe; color: #6d28d9; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; }
    .badge-ap { background-color: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    URL_SHEET = st.secrets["connections"]["gsheets"]["spreadsheet"]
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    st.error("⚠️ LỖI CẤU HÌNH: Vui lòng kiểm tra lại cấu hình trong st.secrets!")
    st.stop()

# Danh sách nữ đồng chí miễn gác đêm / tuần tra
LIST_NU = [
    "Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương",
    "Huỳnh Thụy Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm", "Lê Thanh Tuyền"
]

# --- 2. HÀM XỬ LÝ DỮ LIỆU & CACHE ---
@st.cache_data(ttl=10, show_spinner=False)
def load_data(_conn, sheet_url, worksheet):
    return _conn.read(spreadsheet=sheet_url, worksheet=worksheet)

conn = st.connection("gsheets", type=GSheetsConnection)

# Đọc sheet quân số 'luutru'
df_raw = load_data(conn, URL_SHEET, "luutru")
df_raw = df_raw.iloc[2:].copy()
cols = ["Tuan", "Ap", "HoTen"]
day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
for code in day_codes:
    cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
df_raw.columns = cols[:len(df_raw.columns)]
df_mem = df_raw.dropna(subset=['HoTen']).copy()
dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

# Đọc lịch sử 'NhiemVu'
df_history = load_data(conn, URL_SHEET, "NhiemVu")
if df_history.empty:
    df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao", "NgayThucTe"])
elif "NgayThucTe" not in df_history.columns:
    df_history["NgayThucTe"] = ""

# --- 3. TÍNH TOÁN NGÀY THỰC TẾ DỄ NHẬN BIẾT ---
def parse_week_start(week_str):
    """Trích xuất ngày Thứ 2 của tuần từ tiêu đề tuần, ví dụ: 'Tuần 03 (17/08 - 23/08)'"""
    today = date.today()
    match = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", str(week_str))
    if match:
        d1, m1 = int(match.group(1)), int(match.group(2))
        return date(today.year, m1, d1)
    return None

list_tuan = df_mem['Tuan'].dropna().unique().tolist()[::-1]

# Tự động chọn tuần hiện tại
default_tuan_idx = 0
today = date.today()
for i, w in enumerate(list_tuan):
    st_date = parse_week_start(w)
    if st_date and (st_date <= today <= st_date + timedelta(days=6)):
        default_tuan_idx = i
        break

# --- 4. SIDEBAR ĐIỀU HÀNH ---
st.sidebar.markdown("### 🔐 HỆ THỐNG ĐIỀU HÀNH")
access_key = st.sidebar.text_input("Mã điều hành:", type="password")
is_admin = (access_key == ADMIN_PASSWORD)

selected_week = st.sidebar.selectbox("Tuần trực:", list_tuan, index=default_tuan_idx)
week_start_date = parse_week_start(selected_week)

# Tạo danh sách ngày kèm ngày/tháng thực tế
day_options = []
day_to_actual_date = {}
for i, d_name in enumerate(days_vn):
    if week_start_date:
        act_d = week_start_date + timedelta(days=i)
        label = f"{d_name} ({act_d.strftime('%d/%m/%Y')})"
        day_to_actual_date[label] = act_d.strftime('%Y-%m-%d')
    else:
        label = d_name
        day_to_actual_date[label] = today.strftime('%Y-%m-%d')
    day_options.append(label)

cur_weekday = datetime.now().weekday()
selected_day_label = st.sidebar.selectbox("Ngày trực:", day_options, index=cur_weekday)
selected_day = selected_day_label.split(" (")[0] # Trả về lại "Thứ 2", "Thứ 3",...
actual_date_str = day_to_actual_date[selected_day_label]

st.sidebar.divider()
st.sidebar.markdown("### ⏰ Tùy chỉnh ca gác")
default_times = "07-10h, 10-13h, 13-15h, 15-17h, 17-20h, 20-23h, 23-01h, 01-03h, 03-05h, 05-07h"
custom_times_str = st.sidebar.text_area("Danh sách giờ:", value=default_times)
list_gio = [t.strip() for t in custom_times_str.split(",") if t.strip()]

# Lọc quân số theo ngày
d_code = dict(zip(days_vn, day_codes))[selected_day]
df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

# --- 5. GIAO DIỆN TABS ---
tab_view, tab_manage, tab_ai, tab_att = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT", "🤖 TRỢ LÝ AI", "✅ ĐIỂM DANH"])

# ==========================================
# TAB 1: XEM NHIỆM VỤ
# ==========================================
with tab_view:
    st.subheader(f"📌 LỊCH PHÂN CÔNG: {selected_day_label}")
    tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
    
    if not tasks.empty:
        tasks = tasks.copy()
        tasks['Ấp'] = tasks['HoTen'].map(dict_ap)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🛡️ Ca Gác Cổng")
            g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng']
            st.dataframe(g_df[["Gio", "HoTen", "Ấp"]], use_container_width=True, hide_index=True)
            
        with c2:
            st.markdown("#### 🚔 Tuần Tra & Đột Xuất")
            o_df = tasks[tasks['LoaiNhiemVu'] != 'Gác cổng']
            st.dataframe(o_df[["LoaiNhiemVu", "Gio", "HoTen", "Ấp"]], use_container_width=True, hide_index=True)
            
        # Nút sao chép văn bản thông báo gửi nhóm
        st.divider()
        report_text = f"🛡️ LỊCH TRỰC ANTTCS {selected_day_label.upper()}\n"
        report_text += "---------------------------------\n"
        report_text += "☀️ GÁC CỔNG:\n"
        for _, r in g_df.iterrows():
            report_text += f"- {r['Gio']}: {r['HoTen']} (Ấp {r['Ấp']})\n"
        report_text += "\n🚔 TUẦN TRA & ĐỘT XUẤT:\n"
        for _, r in o_df.iterrows():
            report_text += f"- {r['LoaiNhiemVu']} ({r['Gio']}): {r['HoTen']} (Ấp {r['Ấp']})\n"
        report_text += "---------------------------------\n⚠️ Đề nghị các đ/c nhận ca đúng giờ!"
        
        st.text_area("📋 Đoạn văn bản gửi thông báo Zalo/Nhóm nội bộ:", value=report_text, height=140)
    else:
        st.info("Chưa có dữ liệu phân công cho ngày này.")

# ==========================================
# TAB 2: PHÂN CÔNG CHI TIẾT (TÍCH HỢP GEMINI GỢI Ý)
# ==========================================
with tab_manage:
    if not is_admin:
        st.warning("🔒 Vui lòng nhập Mã điều hành tại thanh bên trái để phân công.")
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
            if is_dx:
                df_p = df_p.sort_values(['Prio', 'Diem'], ascending=[True, True])
            else:
                df_p = df_p.sort_values(['Diem', 'Prio'], ascending=[True, True])
            df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({r['StName']}) - Đã phân: {int(r['Diem'])}đ", axis=1)
            return df_p

        pool_s = get_pool(morning_list)
        pool_d = get_pool(night_cax_list)
        pool_dx = get_pool(list(set(morning_list + night_cax_list + night_ap_list)), is_dx=True)

        # KHU VỰC GỢI Ý NHANH VỚI GEMINI
        with st.expander("✨ Bấm để AI tự động sắp xếp nhanh", expanded=False):
            ai_c1, ai_c2 = st.columns([4, 1])
            with ai_c1:
                ai_req = st.text_input("Ghi chú đặc biệt cho AI (nếu có):", placeholder="VD: Tùng gác ca 1, tối tuần tra C1 gồm có Nam và Hiển...")
            with ai_c2:
                st.write("")
                st.write("")
                btn_gen = st.button("🚀 Xếp Lịch", use_container_width=True)

            if btn_gen:
                if not GEMINI_API_KEY:
                    st.error("Chưa cài GEMINI_API_KEY trong secrets!")
                else:
                    with st.spinner("AI đang tính toán phân bổ công bằng..."):
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        prompt_gen = f"""
                        Bạn là trợ lý điều hành lịch trực ANTTCS. Hãy phân công ca cho: {selected_day_label}.
                        QUÂN SỐ:
                        - Sáng: {morning_list}
                        - Đêm Công an xã: {night_cax_list}
                        - Đêm Ấp: {night_ap_list}
                        - Danh sách giờ: {list_gio}
                        - Miễn trực: {LIST_NU}
                        - Ghi chú chỉ huy: {ai_req}
                        
                        YÊU CẦU:
                        - 4 ca đầu lấy người trực Sáng. Các ca sau lấy người trực Đêm Xã.
                        - Tuần tra C1 (18-22h): 3-4 người trực Đêm Xã.
                        - Tuần tra C2 (22-02h): 3-4 người trực Đêm Xã.
                        
                        BẮT BUỘC TRẢ VỀ DẠNG JSON:
                        {{
                          "gac_cong": {{"ca_gio": "Họ và tên"}},
                          "tuan_tra_c1": ["Họ tên 1", "Họ tên 2"],
                          "tuan_tra_c2": ["Họ tên 3", "Họ tên 4"]
                        }}
                        """
                        try:
                            res = model.generate_content(prompt_gen, generation_config={"response_mime_type": "application/json"})
                            st.session_state["ai_plan"] = json.loads(res.text)
                            st.success("✅ Đã tạo phương án! Dữ liệu đã tự động điền vào các ô phía dưới.")
                        except Exception as e:
                            st.error(f"Lỗi AI: {e}")

        ai_plan = st.session_state.get("ai_plan", {})

        # 1. GÁC CỔNG
        st.markdown("#### 🛡️ 1. Gác Cổng")
        g_res = []
        cg1, cg2 = st.columns(2)
        for i, gio in enumerate(list_gio):
            p_df = pool_s if i < 4 else pool_d
            saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
            
            target_name = None
            if not saved.empty:
                target_name = saved.iloc[0]['HoTen']
            elif ai_plan and "gac_cong" in ai_plan and gio in ai_plan["gac_cong"]:
                target_name = ai_plan["gac_cong"][gio]

            idx = 0
            if target_name and not p_df.empty:
                m = p_df[p_df['HoTen'] == target_name]
                if not m.empty:
                    idx = p_df.index.get_loc(m.index[0])

            with (cg1 if i % 2 == 0 else cg2):
                if not p_df.empty:
                    sel = st.selectbox(f"Ca {gio}", p_df["Display"], index=idx, key=f"gac_{gio}_{selected_day}")
                    g_res.append({"HoTen": sel.split(" (")[0], "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": 1})

        # 2. TUẦN TRA
        st.markdown("#### 🚔 2. Tuần Tra Đêm")
        def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
        def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
        if not def_tt1 and "tuan_tra_c1" in ai_plan: def_tt1 = ai_plan["tuan_tra_c1"]
        if not def_tt2 and "tuan_tra_c2" in ai_plan: def_tt2 = ai_plan["tuan_tra_c2"]

        ct1, ct2 = st.columns(2)
        with ct1:
            tt1 = st.multiselect("Ca 1 (18-22h):", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in def_tt1])
        with ct2:
            tt2 = st.multiselect("Ca 2 (22-02h):", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in def_tt2])

        # 3. ĐỘT XUẤT
        st.markdown("#### 🆘 3. Đột Xuất (Hiện trường / Hỗ trợ)")
        saved_dx = current_saved[current_saved['LoaiNhiemVu'].str.startswith('ĐX: ', na=False)]
        if not saved_dx.empty:
            unique_tasks = saved_dx.groupby('LoaiNhiemVu').agg({'Diem': 'first'}).reset_index()
            unique_tasks['TenViec'] = unique_tasks['LoaiNhiemVu'].str.replace('ĐX: ', '', regex=False)
            default_n_dx = len(unique_tasks)
        else:
            unique_tasks = pd.DataFrame(columns=['LoaiNhiemVu', 'Diem', 'TenViec'])
            default_n_dx = 1

        if 'n_dx' not in st.session_state:
            st.session_state.n_dx = default_n_dx

        c_btn1, c_btn2, _ = st.columns([2, 2, 8])
        with c_btn1:
            if st.button("➕ Thêm việc", use_container_width=True):
                st.session_state.n_dx += 1
        with c_btn2:
            if st.button("➖ Bớt việc", use_container_width=True) and st.session_state.n_dx > 1:
                st.session_state.n_dx -= 1

        dx_res = []
        for i in range(st.session_state.n_dx):
            val_name, val_points, val_selected_mem = "", 1, []
            if i < len(unique_tasks):
                row_task = unique_tasks.iloc[i]
                val_name = row_task['TenViec']
                val_points = int(row_task['Diem'])
                saved_members = saved_dx[saved_dx['LoaiNhiemVu'] == row_task['LoaiNhiemVu']]['HoTen'].tolist()
                val_selected_mem = [d for d in pool_dx["Display"] if d.split(" (")[0] in saved_members]

            cx1, cx2, cx3 = st.columns([3, 5, 1])
            with cx1:
                t_n = st.text_input(f"Tên việc {i+1}", value=val_name, key=f"dxn_{i}_{selected_day}", placeholder="VD: TNGT Ngã ba...")
            with cx2:
                t_m = st.multiselect(f"Quân số {i+1}", pool_dx["Display"], default=val_selected_mem, key=f"dxm_{i}_{selected_day}")
            with cx3:
                t_d = st.number_input(f"Điểm", 1, 10, value=val_points, key=f"dxd_{i}_{selected_day}")

            if t_n and t_m:
                for m in t_m:
                    dx_res.append({"HoTen": m.split(" (")[0], "LoaiNhiemVu": f"ĐX: {t_n}", "Gio": "Đột xuất", "Diem": t_d})

        st.write("")
        if st.button("💾 LƯU PHƯƠNG ÁN TRỰC", use_container_width=True, type="primary"):
            final = g_res + \
                    [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1} for p in tt1] + \
                    [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1} for p in tt2] + \
                    dx_res
            df_s = pd.DataFrame(final)
            df_s["Tuan"] = selected_week
            df_s["Ngay"] = selected_day
            df_s["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            df_s["NgayThucTe"] = actual_date_str

            df_save = pd.concat([df_history[~((df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day))], df_s], ignore_index=True)
            conn.update(worksheet="NhiemVu", data=df_save)
            st.cache_data.clear()
            if "ai_plan" in st.session_state:
                del st.session_state["ai_plan"]
            st.success("✅ Đã lưu phương án thành công vào bảng Nhiệm Vụ!")
            st.rerun()

# ==========================================
# TAB 3: TRỢ LÝ CHATBOT AI
# ==========================================
with tab_ai:
    st.markdown("### 💬 Trợ Lý Hỏi Đáp Lịch Trực")
    st.caption("AI tra cứu trực tiếp từ bảng Nhiệm Vụ vừa lưu.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("VD: Hôm nay có những ai gác cổng? Tối nay ai tuần tra?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        context_data = df_history[["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "NgayThucTe"]].to_string(index=False)
        full_p = f"""
        Bạn là Trợ lý Điều hành ANTTCS Bắc Tân Uyên.
        Hôm nay trên thực tế là: {selected_day_label}, mã ngày: {actual_date_str}.
        
        DỮ LIỆU ĐÃ LƯU TRONG HỆ THỐNG:
        {context_data}
        
        Câu hỏi của cán bộ: "{prompt}"
        
        Yêu cầu:
        - Trả lời rõ ràng, chính xác từng ca trực, nhóm theo Gác cổng, Tuần tra hoặc Đột xuất.
        - Trả lời bằng tiếng Việt lịch sự, nghiêm túc.
        """
        with st.chat_message("assistant"):
            with st.spinner("Đang kiểm tra dữ liệu trực..."):
                try:
                    c_model = genai.GenerativeModel("gemini-1.5-flash")
                    res = c_model.generate_content(full_p)
                    ans = res.text
                except Exception as e:
                    ans = f"Lỗi AI: {e}"
                st.markdown(ans)
        st.session_state.chat_history.append({"role": "assistant", "content": ans})

# ==========================================
# TAB 4: ĐIỂM DANH
# ==========================================
with tab_att:
    if not is_admin:
        st.warning("🔒 Vui lòng nhập Mã điều hành để điểm danh.")
    else:
        st.markdown(f"#### ✅ Điểm Danh Quân Số Ngày: {selected_day_label}")
        active_names = sorted(list(set(morning_list + night_cax_list + night_ap_list)))
        with st.form("form_att"):
            v_list = []
            for n in active_names:
                c1, c2, c3 = st.columns([3, 3, 4])
                c1.write(f"**{n}** (Ấp {dict_ap.get(n)})")
                stt = c2.radio("TT", ["Có mặt", "Vắng"], key=f"at_{n}", horizontal=True, label_visibility="collapsed")
                re_txt = c3.text_input("Lý do vắng", key=f"ar_{n}", label_visibility="collapsed")
                if stt == "Vắng":
                    lt = [l for l, lst in [("Sáng", morning_list), ("Đêm Xã", night_cax_list), ("Đêm Ấp", night_ap_list)] if n in lst]
                    v_list.append({
                        "Tuan": selected_week,
                        "Ngay": selected_day,
                        "HoTen": n,
                        "TrangThai": "Vắng",
                        "LyDo": re_txt,
                        "LoaiTruc": ", ".join(lt),
                        "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "NgayThucTe": actual_date_str
                    })
            if st.form_submit_button("💾 LƯU DANH SÁCH VẮNG", use_container_width=True):
                if v_list:
                    df_db = load_data(conn, URL_SHEET, "DiemDanh")
                    conn.update(worksheet="DiemDanh", data=pd.concat([df_db, pd.DataFrame(v_list)], ignore_index=True))
                    st.cache_data.clear()
                    st.success("✅ Đã lưu danh sách vắng!")
                    st.rerun()
                else:
                    st.success("✅ Quân số đầy đủ, không có đồng chí nào vắng!")

# --- 6. KHỐI TỔNG QUAN QUÂN SỐ Ở DƯỚI CÙNG ---
st.divider()
st.markdown(f"### 👥 TỔNG HỢP QUÂN SỐ THEO LỊCH ĐĂNG KÝ ({selected_day_label})")
c_s, c_d, c_a = st.columns(3)
with c_s:
    st.markdown('<span class="badge-sang">☀️ TRỰC SÁNG</span>', unsafe_allow_html=True)
    for n in morning_list:
        st.write(f"- **{n}** (Ấp {dict_ap.get(n)})")
with c_d:
    st.markdown('<span class="badge-dem">🌙 TRỰC ĐÊM CÔNG AN XÃ</span>', unsafe_allow_html=True)
    for n in night_cax_list:
        st.write(f"- **{n}** (Ấp {dict_ap.get(n)})")
with c_a:
    st.markdown('<span class="badge-ap">🏡 TRỰC ĐÊM ẤP</span>', unsafe_allow_html=True)
    for n in night_ap_list:
        st.write(f"- **{n}** (Ấp {dict_ap.get(n)})")
