import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import google.generativeai as genai
import json
import re

# --- 1. CẤU HÌNH TRANG & BẢO MẬT ---
st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide", page_icon="🛡️")

# --- HÀM TÌM KEY THÔNG MINH TRONG SECRETS (TRÁNH MỌI LỖI ĐỊNH DẠNG) ---
def get_gemini_key():
    if "GEMINI_API_KEY" in st.secrets:
        return str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
    for sec_name in st.secrets:
        sec = st.secrets[sec_name]
        if isinstance(sec, dict) and "GEMINI_API_KEY" in sec:
            return str(sec["GEMINI_API_KEY"]).strip().strip('"').strip("'")
    for k, v in st.secrets.items():
        if isinstance(v, str) and v.strip().startswith("AIza"):
            return v.strip().strip('"').strip("'")
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, str) and sub_v.strip().startswith("AIza"):
                    return sub_v.strip().strip('"').strip("'")
    return ""

try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    URL_SHEET = st.secrets["connections"]["gsheets"]["spreadsheet"]
    GEMINI_API_KEY = get_gemini_key()
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    st.error("⚠️ LỖI CẤU HÌNH: Kiểm tra lại Streamlit Secrets!")
    st.stop()

# Danh sách nữ đồng chí đã yêu cầu
LIST_NU = [
    "Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương",
    "Huỳnh Thụy Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm", "Lê Thanh Tuyền"
]

# --- PHỤC HỒI CSS GIAO DIỆN NGUYÊN BẢN (CARD MÀU VÀ KHỐI TRỢ LÝ) ---
st.markdown("""
<style>
    .card-sang {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border: 1px solid #fde68a;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .card-dem-cax {
        background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
        border: 1px solid #ddd6fe;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .card-dem-ap {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .mem-item {
        background: #ffffff;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 6px;
        border: 1px solid rgba(0,0,0,0.06);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 500;
    }
    .mem-ap-tag {
        font-size: 12px;
        color: #4b5563;
        background: #f3f4f6;
        padding: 2px 8px;
        border-radius: 10px;
    }
    .ai-box {
        background: #f0fdf4;
        border: 1.5px solid #86efac;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. HÀM DÒ TÌM MODEL GEMINI CHÍNH XÁC (TRÁNH LỖI 404) ---
def get_working_gemini_model():
    try:
        supported = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for candidate in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
            for m_name in supported:
                if candidate in m_name:
                    return genai.GenerativeModel(m_name)
        if supported:
            return genai.GenerativeModel(supported[0])
    except Exception:
        pass
    return genai.GenerativeModel("gemini-1.5-flash-latest")

# --- 3. LOAD VÀ CACHE DỮ LIỆU (TỐI ƯU TRÁNH RATE-LIMIT GOOGLE) ---
@st.cache_data(ttl=60, show_spinner=False)
def load_data(_conn, sheet_url, worksheet):
    return _conn.read(spreadsheet=sheet_url, worksheet=worksheet)

conn = st.connection("gsheets", type=GSheetsConnection)

# Đọc quân số từ sheet 'luutru'
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

# Quản lý df_history trong session_state để lưu là hiện ngay
if "df_history" not in st.session_state:
    df_h = load_data(conn, URL_SHEET, "NhiemVu")
    if df_h.empty:
        df_h = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao", "NgayThucTe"])
    elif "NgayThucTe" not in df_h.columns:
        df_h["NgayThucTe"] = ""
    st.session_state["df_history"] = df_h

df_history = st.session_state["df_history"]

# --- 4. TÍNH TOÁN NGÀY THỰC TẾ DỄ NHẬN BIẾT ---
def parse_week_start(week_str):
    today = date.today()
    match = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", str(week_str))
    if match:
        d1, m1 = int(match.group(1)), int(match.group(2))
        return date(today.year, m1, d1)
    return None

list_tuan = df_mem['Tuan'].dropna().unique().tolist()[::-1]
default_tuan_idx = 0
today = date.today()
for i, w in enumerate(list_tuan):
    st_date = parse_week_start(w)
    if st_date and (st_date <= today <= st_date + timedelta(days=6)):
        default_tuan_idx = i
        break

# --- 5. SIDEBAR ---
st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
access_key = st.sidebar.text_input("Mã điều hành:", type="password")
is_admin = (access_key == ADMIN_PASSWORD)

selected_week = st.sidebar.selectbox("Tuần trực:", list_tuan, index=default_tuan_idx)
week_start_date = parse_week_start(selected_week)

# Tạo danh sách ngày trực rõ ràng ngày/tháng
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
selected_day = selected_day_label.split(" (")[0]
actual_date_str = day_to_actual_date[selected_day_label]

st.sidebar.divider()
st.sidebar.subheader("⏰ Tùy chỉnh ca gác")
default_times = "07-10h, 10-13h, 13-15h, 15-17h, 17-20h, 20-23h, 23-01h, 01-03h, 03-05h, 05-07h"
custom_times_str = st.sidebar.text_area("Danh sách giờ (cách nhau dấu phẩy):", value=default_times)
list_gio = [t.strip() for t in custom_times_str.split(",") if t.strip()]

# Lọc quân số theo ngày
d_code = dict(zip(days_vn, day_codes))[selected_day]
df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

# --- 6. GIAO DIỆN TABS ---
tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG & TRỢ LÝ AI", "✅ ĐIỂM DANH"])

# ==========================================
# TAB 1: XEM NHIỆM VỤ
# ==========================================
with tab_view:
    st.subheader(f"📌 LỊCH PHÂN CÔNG: {selected_day_label} - {selected_week}")
    tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
    if not tasks.empty:
        tasks = tasks.copy()
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
        st.info("Chưa có dữ liệu phân công cho ngày này.")

# ==========================================
# TAB 2: PHÂN CÔNG CHI TIẾT & CHATBOT DUYỆT TỰ ĐỘNG
# ==========================================
with tab_manage:
    if not is_admin:
        st.warning("🔒 Vui lòng nhập Mã điều hành tại thanh bên trái để sử dụng phân công.")
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

        # ----------------------------------------------------
        # KHU VỰC TRỢ LÝ AI CHATBOX & PHÊ DUYỆT TRỰC TIẾP
        # ----------------------------------------------------
        st.markdown("### 🤖 TRỢ LÝ ĐIỀU HÀNH & XẾP LỊCH TỰ ĐỘNG (GEMINI)")
        
        # Nút yêu cầu nhanh có sẵn trên đầu
        btn_quick_auto = st.button("⚡ Yêu cầu AI tự sắp lịch hôm nay", help="Bấm để AI tự tính toán chia đều quân số vào các ca")

        # Lưu trữ lịch sử trao đổi với Trợ lý AI
        if "manage_chat" not in st.session_state:
            st.session_state.manage_chat = []

        # Hiển thị các tin nhắn trao đổi
        for msg in st.session_state.manage_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Ô nhập câu hỏi / yêu cầu của người dùng
        user_query = st.chat_input("Hỏi lịch hoặc ra lệnh cho AI (VD: Xếp lại ca gác cho Tùng gác đầu, thêm 1 ca bảo vệ hiện trường...)")
        
        # Xử lý khi bấm nút nhanh hoặc gõ chat
        active_prompt = None
        if btn_quick_auto:
            active_prompt = "Hãy tự động sắp xếp toàn bộ lịch trực hôm nay công bằng và tối ưu nhất."
        elif user_query:
            active_prompt = user_query

        if active_prompt:
            st.session_state.manage_chat.append({"role": "user", "content": active_prompt})
            with st.chat_message("user"):
                st.markdown(active_prompt)

            if not GEMINI_API_KEY:
                st.error("Chưa cấu hình GEMINI_API_KEY trong Secrets!")
            else:
                with st.chat_message("assistant"):
                    with st.spinner("AI đang phân tích yêu cầu và tính toán phân bổ..."):
                        try:
                            model = get_working_gemini_model()
                            
                            prompt_system = f"""
                            Bạn là Trợ lý Điều hành ANTTCS Bắc Tân Uyên.
                            Ngày đang chọn: {selected_day_label} ({actual_date_str}).
                            QUÂN SỐ TRỰC HÔM NAY:
                            - Sáng: {morning_list}
                            - Đêm Công an Xã: {night_cax_list}
                            - Đêm Ấp: {night_ap_list}
                            - Ca gác: {list_gio}
                            - Miễn trực (Nữ): {LIST_NU}

                            DỮ LIỆU ĐÃ PHÂN CÔNG HIỆN TẠI (NẾU CÓ):
                            {current_saved.to_string(index=False)}

                            YÊU CẦU TỪ NGƯỜI DÙNG: "{active_prompt}"

                            Nhiệm vụ của bạn:
                            1. Trả lời tóm tắt phương án bằng văn bản dễ hiểu.
                            2. NẾU người dùng yêu cầu xếp lịch / điều chỉnh ca / chia quân số, HÃY TRẢ VỀ THÊM KHỐI JSON nằm trong thẻ ```json ... ``` theo cấu trúc:
                            {{
                               "gac_cong": {{"ca_gio": "Họ và tên"}},
                               "tuan_tra_c1": ["Họ tên 1", "Họ tên 2"],
                               "tuan_tra_c2": ["Họ tên 3", "Họ tên 4"],
                               "dot_xuat": [{{"ten_viec": "Tên việc", "quan_so": ["Họ tên"], "diem": 1}}]
                            }}
                            (Lưu ý: 4 ca gác đầu ưu tiên lấy từ Sáng; các ca sau lấy từ Đêm Xã. Tuần tra C1 và C2 lấy từ Đêm Xã).
                            """
                            response = model.generate_content(prompt_system)
                            reply_text = response.text
                            
                            # Tìm xem có JSON đề xuất không
                            json_match = re.search(r"```json\s*(\{.*?\})\s*```", reply_text, re.DOTALL)
                            if not json_match:
                                json_match = re.search(r"(\{[\s\S]*\"gac_cong\"[\s\S]*\})", reply_text)

                            if json_match:
                                try:
                                    parsed_data = json.loads(json_match.group(1))
                                    st.session_state["pending_ai_proposal"] = parsed_data
                                    # Cắt bỏ phần JSON thô khỏi tin nhắn hiển thị cho đẹp
                                    display_text = reply_text.replace(json_match.group(0), "").strip()
                                    if not display_text:
                                        display_text = "Tôi đã lập xong phương án phân công tối ưu cho ngày hôm nay."
                                    st.markdown(display_text)
                                    st.session_state.manage_chat.append({"role": "assistant", "content": display_text})
                                except Exception:
                                    st.markdown(reply_text)
                                    st.session_state.manage_chat.append({"role": "assistant", "content": reply_text})
                            else:
                                st.markdown(reply_text)
                                st.session_state.manage_chat.append({"role": "assistant", "content": reply_text})
                                
                        except Exception as err:
                            st.error(f"Lỗi AI: {err}")

        # KHỐI PHÊ DUYỆT (Giống Google Sheets AI)
        if "pending_ai_proposal" in st.session_state and st.session_state["pending_ai_proposal"]:
            proposal = st.session_state["pending_ai_proposal"]
            st.markdown("""
            <div class="ai-box">
                <h4 style="margin:0; color:#15803d;">📋 ĐỀ XUẤT PHÂN CÔNG TỪ AI ĐANG CHỜ PHÊ DUYỆT</h4>
                <p style="margin:5px 0 10px 0; font-size:14px; color:#166534;">
                    AI đã tính toán xong danh sách gác và tuần tra. Hãy bấm nút <b>Phê Duyệt</b> bên dưới để tự động điền vào các ô chọn.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            app_col1, app_col2 = st.columns([2, 5])
            with app_col1:
                if st.button("✅ PHÊ DUYỆT & ĐIỀN VÀO FORM", type="primary", use_container_width=True):
                    st.session_state["applied_ai_plan"] = proposal
                    del st.session_state["pending_ai_proposal"]
                    st.success("✅ Đã phê duyệt! Toàn bộ ca đã được điền vào form bên dưới.")
                    st.rerun()
            with app_col2:
                if st.button("❌ Bỏ qua đề xuất này", use_container_width=True):
                    del st.session_state["pending_ai_proposal"]
                    st.rerun()

        st.divider()

        # ----------------------------------------------------
        # FORM PHÂN CÔNG CHI TIẾT (ĐÃ KẾT NỐI VỚI KẾT QUẢ PHÊ DUYỆT)
        # ----------------------------------------------------
        applied_plan = st.session_state.get("applied_ai_plan", {})

        # 1. GÁC CỔNG
        st.subheader("🛡️ 1. GÁC CỔNG")
        g_res = []
        cg1, cg2 = st.columns(2)
        for i, gio in enumerate(list_gio):
            p_df = pool_s if i < 4 else pool_d
            saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]

            target_name = None
            if not saved.empty:
                target_name = saved.iloc[0]['HoTen']
            elif applied_plan and "gac_cong" in applied_plan and gio in applied_plan["gac_cong"]:
                target_name = applied_plan["gac_cong"][gio]

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
        st.subheader("🚔 2. TUẦN TRA")
        def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
        def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
        if not def_tt1 and "tuan_tra_c1" in applied_plan: 
            def_tt1 = applied_plan["tuan_tra_c1"]
        if not def_tt2 and "tuan_tra_c2" in applied_plan: 
            def_tt2 = applied_plan["tuan_tra_c2"]

        ct1, ct2 = st.columns(2)
        with ct1:
            tt1 = st.multiselect("Ca 1:", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in def_tt1])
        with ct2:
            tt2 = st.multiselect("Ca 2:", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in def_tt2])

        # 3. ĐỘT XUẤT
        st.subheader("🆘 3. ĐỘT XUẤT (Ưu tiên Xã > Ấp)")
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
                t_n = st.text_input(f"Việc {i+1}", value=val_name, key=f"dxn_{i}_{selected_day}")
            with cx2:
                t_m = st.multiselect(f"Quân {i+1}", pool_dx["Display"], default=val_selected_mem, key=f"dxm_{i}_{selected_day}")
            with cx3:
                t_d = st.number_input(f"Đ", 1, 10, value=val_points, key=f"dxd_{i}_{selected_day}")

            if t_n and t_m:
                for m in t_m:
                    dx_res.append({"HoTen": m.split(" (")[0], "LoaiNhiemVu": f"ĐX: {t_n}", "Gio": "Đột xuất", "Diem": t_d})

        st.write("")
        # NÚT LƯU PHƯƠNG ÁN (LƯU VÀ CẬP NHẬT TỨC THÌ)
        if st.button("💾 LƯU PHƯƠNG ÁN", use_container_width=True, type="primary"):
            with st.spinner("Đang lưu dữ liệu vào Google Sheets..."):
                final = g_res + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1} for p in tt1] + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1} for p in tt2] + \
                        dx_res
                df_s = pd.DataFrame(final)
                df_s["Tuan"] = selected_week
                df_s["Ngay"] = selected_day
                df_s["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                df_s["NgayThucTe"] = actual_date_str

                df_save = pd.concat([
                    df_history[~((df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day))],
                    df_s
                ], ignore_index=True)

                conn.update(worksheet="NhiemVu", data=df_save)
                
                # Cập nhật bộ nhớ đệm session_state trực tiếp, không xóa toàn bộ cache
                st.session_state["df_history"] = df_save
                if "applied_ai_plan" in st.session_state:
                    del st.session_state["applied_ai_plan"]
                
                st.success("✅ Đã lưu phương án thành công!")
                st.rerun()

# ==========================================
# TAB 3: ĐIỂM DANH
# ==========================================
with tab_attendance:
    if not is_admin:
        st.warning("Vui lòng nhập Mã điều hành để điểm danh.")
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
                    lt = [l for l, lst in [("Sáng", morning_list), ("Đêm Xã", night_cax_list), ("Đêm Ấp", night_ap_list)] if n in lst]
                    v_list.append({
                        "Tuan": selected_week,
                        "Ngay": selected_day,
                        "HoTen": n,
                        "TrangThai": "Vắng",
                        "LyDo": re,
                        "LoaiTruc": ", ".join(lt),
                        "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "NgayThucTe": actual_date_str
                    })
            if st.form_submit_button("💾 LƯU VẮNG", use_container_width=True):
                if v_list:
                    df_db = load_data(conn, URL_SHEET, "DiemDanh")
                    conn.update(worksheet="DiemDanh", data=pd.concat([df_db, pd.DataFrame(v_list)], ignore_index=True))
                    st.cache_data.clear()
                    st.success("Đã lưu điểm danh vắng!")
                    st.rerun()
                else:
                    st.success("Đầy đủ quân số!")

# ==========================================
# PHẦN CUỐI: TỔNG QUAN QUÂN SỐ NGUYÊN BẢN (KHỐI THẺ MÀU ĐẶC TRƯNG)
# ==========================================
st.divider()
st.markdown(f"### 👥 TỔNG HỢP QUÂN SỐ THEO LỊCH ĐĂNG KÝ ({selected_day_label})")
c_s, c_d, c_a = st.columns(3)

with c_s:
    st.markdown('<div class="card-sang"><h4>☀️ TRỰC SÁNG</h4>', unsafe_allow_html=True)
    for n in morning_list:
        is_night = (n in night_cax_list)
        night_icon = " 🌙" if is_night else ""
        st.markdown(f'''
        <div class="mem-item">
            <span>{n}{night_icon}</span>
            <span class="mem-ap-tag">Ấp: {dict_ap.get(n, "—")}</span>
        </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c_d:
    st.markdown('<div class="card-dem-cax"><h4>🌙 TRỰC ĐÊM XÃ</h4>', unsafe_allow_html=True)
    for n in night_cax_list:
        st.markdown(f'''
        <div class="mem-item">
            <span>{n}</span>
            <span class="mem-ap-tag">Ấp: {dict_ap.get(n, "—")}</span>
        </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c_a:
    st.markdown('<div class="card-dem-ap"><h4>🏡 TRỰC ĐÊM ẤP</h4>', unsafe_allow_html=True)
    for n in night_ap_list:
        st.markdown(f'''
        <div class="mem-item">
            <span>{n}</span>
            <span class="mem-ap-tag">Ấp: {dict_ap.get(n, "—")}</span>
        </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
