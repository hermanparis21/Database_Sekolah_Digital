import streamlit as st
import pandas as pd
from datetime import datetime
import datetime as dt
import pytz
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# --- 1. KONFIGURASI ZONA WAKTU ---
jakarta_tz = pytz.timezone('Asia/Jakarta')

# --- 2. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SMA Muhammadiyah 4 Banjarnegara", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #059669; color: white; height: 3em; }
    .clock-text { text-align: center; font-weight: bold; font-size: 1.1em; color: #1e293b; background: #f1f5f9; padding: 10px; border-radius: 15px; border: 1px solid #cbd5e1; margin-bottom: 20px; }
    .header-text { text-align: center; color: #059669; margin-bottom: 0px; font-size: 2em; }
    .slogan { text-align: center; font-style: italic; color: #475569; margin-bottom: 10px; font-size: 1em; }
    .task-card { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #059669; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KAMUS BAHASA ---
lang_dict = {
    "ID": {
        "slogan": "Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan",
        "login": "Masuk", "reg": "Registrasi", "nama": "Nama Lengkap", "pass": "Password",
        "nis": "NIS (Siswa)", "nik": "NIK (Guru)", "face_ref": "Ambil Foto Wajah Referensi",
        "absen_h": "📍 Presensi (GPS & Wajah)", "pilih_j": "Jenis Presensi",
        "m_sek": "Masuk Sekolah", "m_dhu": "Sholat Dhuha", "m_dzu": "Sholat Dzuhur", "m_pul": "Pulang",
        "gps_ok": "Lokasi Terverifikasi", "gps_fail": "Di luar jangkauan!", "face_now": "Foto Wajah Sekarang",
        "tugas": "📚 Tugas Sekolah", "input_t": "Buat Tugas Baru", "dead": "Tenggat", "done": "Selesai",
        "lapor": "📊 Laporan & Log Guru", "success": "Berhasil Disimpan!", "out": "Keluar"
    },
    "EN": {
        "slogan": "Creating Pious, Achieving, and Environmentally Conscious Students",
        "login": "Login", "reg": "Registration", "nama": "Full Name", "pass": "Password",
        "nis": "Student ID (NIS)", "nik": "Teacher ID (NIK)", "face_ref": "Capture Reference Face",
        "absen_h": "📍 Attendance (GPS & Face)", "pilih_j": "Attendance Type",
        "m_sek": "School Entry", "m_dhu": "Dhuha Prayer", "m_dzu": "Dhuhur Prayer", "m_pul": "Go Home",
        "gps_ok": "Location Verified", "gps_fail": "Out of range!", "face_now": "Capture Face Now",
        "tugas": "📚 School Tasks", "input_t": "Create New Task", "dead": "Deadline", "done": "Done",
        "lapor": "📊 Teacher Log & Reports", "success": "Saved Successfully!", "out": "Logout"
    }
}

# --- 4. DATA & SESSION ---
if 'lang' not in st.session_state: st.session_state.lang = "ID"
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None

L = lang_dict[st.session_state.lang]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl="0s")

list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

# --- 5. HEADER ---
st.markdown(f"<h1 class='header-text'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='slogan'>{L['slogan']}</p>", unsafe_allow_html=True)

now_dt = datetime.now(jakarta_tz)
st.markdown(f"<div class='clock-text'>🗓️ {now_dt.strftime('%A, %d %B %Y')} | ⏰ {now_dt.strftime('%H:%M:%S')} WIB</div>", unsafe_allow_html=True)

if st.button("🌐 Switch Language (ID/EN)"):
    st.session_state.lang = "EN" if st.session_state.lang == "ID" else "ID"
    st.rerun()

# --- 6. AUTH ---
def show_auth():
    tab1, tab2 = st.tabs([f"🔑 {L['login']}", f"📝 {L['reg']}"])
    with tab1:
        with st.form("login_form"):
            u = st.text_input(L['nama'])
            p = st.text_input(L['pass'], type="password")
            if st.form_submit_button(L['login']):
                df_u = load_data("users")
                m = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p)]
                if not m.empty:
                    st.session_state.logged_in_user = m.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Login Gagal")
    with tab2:
        with st.form("reg_form"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input(L['nama'])
            pw = st.text_input(L['pass'])
            id_val = st.text_input(L['nis'] if role == "Siswa" else L['nik'])
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            foto_master = st.camera_input("Foto Master (Reference)")
            if st.form_submit_button(L['reg']):
                df_u = load_data("users")
                new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_val}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True))
                st.success("Registrasi Berhasil!")

# --- 7. DASHBOARD ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}"]
    if user['role'] in ["Guru", "Admin TU"]: menu_opt.append(L['lapor'])
    choice = st.sidebar.radio("Menu", menu_opt)

    # --- PRESENSI ---
    if choice == f"📍 {L['absen_h']}":
        st.subheader(L['absen_h'])
        loc = get_geolocation()
        if loc:
            u_loc = (loc['coords']['latitude'], loc['coords']['longitude'])
            dist = geodesic(u_loc, (-7.2164697698622335, 109.64013014754921)).meters
            if dist <= 100:
                m_absen = st.selectbox(L['pilih_j'], [L['m_sek'], L['m_dhu'], L['m_dzu'], L['m_pul']])
                img_now = st.camera_input("Verify Face")
                if st.button("Submit") and img_now:
                    df_p = load_data("presensi")
                    new_p = pd.DataFrame([{"nama": user['nama'], "kelas": user.get('kelas', '-'), "waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"), "jenis": m_absen, "status": "VALID"}])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True))
                    st.success(L['success'])
            else: st.error(L['gps_fail'])

    # --- TUGAS ---
    elif choice == f"{L['tugas']}":
        st.header(L['tugas'])
        if user['role'] == "Guru":
            with st.expander(f"➕ {L['input_t']}"):
                with st.form("task_f"):
                    t_j = st.text_input("Judul Tugas"); t_d = st.text_area("Deskripsi")
                    t_dl = st.date_input(L['dead']); t_k = st.multiselect("Pilih Kelas", list_kelas)
                    if st.form_submit_button("Kirim"):
                        df_t = load_data("tugas")
                        new_t = pd.DataFrame([{"id": datetime.now(jakarta_tz).strftime("%Y%m%d%H%M"), "guru": user['nama'], "judul": t_j, "deskripsi": t_d, "deadline": str(t_dl), "kelas": ",".join(t_k)}])
                        conn.update(worksheet="tugas", data=pd.concat([df_t, new_t], ignore_index=True))
                        st.success("Tugas Dikirim!")
        
        df_tugas = load_data("tugas")
        df_done = load_data("tugas_selesai")
        df_tugas['kelas'] = df_tugas['kelas'].astype(str).replace('nan', '')
        u_kls = str(user.get('kelas', ''))
        rel_tasks = df_tugas[df_tugas['kelas'].str.contains(u_kls, na=False)] if user['role'] == "Siswa" else df_tugas
        
        for _, row in rel_tasks.iterrows():
            is_done = not df_done[(df_done['id_tugas'].astype(str) == str(row['id'])) & (df_done['nama'] == user['nama'])].empty
            st.markdown(f'<div class="task-card"><h4>{row["judul"]}</h4><p>{row["deskripsi"]}</p></div>', unsafe_allow_html=True)
            if user['role'] == "Siswa" and not is_done:
                if st.button(f"Mark as {L['done']}", key=str(row['id'])):
                    conn.update(worksheet="tugas_selesai", data=pd.concat([df_done, pd.DataFrame([{"id_tugas": str(row['id']), "nama": user['nama'], "waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M")}])], ignore_index=True))
                    st.rerun()
            elif is_done: st.success("✅ " + L['done'])

    # --- LAPORAN & LOG (FITUR BARU UNTUK GURU) ---
    elif choice == L['lapor']:
        st.header(L['lapor'])
        df_p = load_data("presensi")
        
        tab1, tab2 = st.tabs(["📋 Log Presensi", "📅 Filter Tanggal"])
        
        with tab1:
            f_kls = st.multiselect("Filter Kelas Siswa", list_kelas)
            if f_kls:
                df_show = df_p[df_p['kelas'].isin(f_kls)]
            else:
                df_show = df_p
            st.dataframe(df_show, use_container_width=True)
            st.download_button("📥 Download Log CSV", df_show.to_csv(index=False), "log_absensi.csv")
            
        with tab2:
            f_date = st.date_input("Pilih Tanggal")
            df_date = df_p[df_p['waktu'].astype(str).str.contains(str(f_date))]
            st.write(f"Data Presensi Tanggal: {f_date}")
            st.table(df_date)

    if st.sidebar.button(L['out']):
        st.session_state.logged_in_user = None
        st.rerun()

# --- 8. RUN ---
if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
