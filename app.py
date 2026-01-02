import streamlit as st
import pandas as pd
from datetime import datetime
import datetime as dt
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SMA Muhammadiyah 4 Banjarnegara", layout="wide", page_icon="🎓")

# CSS untuk desain modern & mobile-friendly
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #059669; color: white; height: 3em; }
    .clock-text { text-align: center; font-weight: bold; font-size: 1.1em; color: #1e293b; background: #f1f5f9; padding: 10px; border-radius: 15px; border: 1px solid #cbd5e1; margin-bottom: 20px; }
    .header-text { text-align: center; color: #059669; margin-bottom: 0px; font-size: 2em; }
    .slogan { text-align: center; font-style: italic; color: #475569; margin-bottom: 10px; font-size: 1em; }
    .task-card { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #059669; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KAMUS BAHASA (ID/EN) ---
lang_dict = {
    "ID": {
        "slogan": "Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan",
        "login": "Masuk", "reg": "Registrasi", "nama": "Nama Lengkap", "pass": "Password",
        "nis": "NIS (Siswa)", "nik": "NIK (Guru)", "face_ref": "Ambil Foto Wajah Referensi",
        "absen_h": "📍 Presensi (GPS & Wajah)", "pilih_j": "Jenis Presensi",
        "m_sek": "Masuk Sekolah", "m_dhu": "Sholat Dhuha", "m_dzu": "Sholat Dzuhur", "m_pul": "Pulang",
        "gps_ok": "Lokasi Terverifikasi", "gps_fail": "Di luar jangkauan!", "face_now": "Foto Wajah Sekarang",
        "tugas": "📚 Tugas Sekolah", "input_t": "Buat Tugas Baru", "dead": "Tenggat", "done": "Selesai",
        "success": "Berhasil Disimpan!", "out": "Keluar"
    },
    "EN": {
        "slogan": "Creating Pious, Achieving, and Environmentally Conscious Students",
        "login": "Login", "reg": "Registration", "nama": "Full Name", "pass": "Password",
        "nis": "Student ID (NIS)", "nik": "Teacher ID (NIK)", "face_ref": "Capture Reference Face",
        "absen_h": "📍 Attendance (GPS & Face)", "pilih_j": "Attendance Type",
        "m_sek": "School Entry", "m_dhu": "Dhuha Prayer", "m_dzu": "Dhuhur Prayer", "m_pul": "Go Home",
        "gps_ok": "Location Verified", "gps_fail": "Out of range!", "face_now": "Capture Face Now",
        "tugas": "📚 School Tasks", "input_t": "Create New Task", "dead": "Deadline", "done": "Done",
        "success": "Saved Successfully!", "out": "Logout"
    }
}

# --- 3. SESSION & DATA ---
if 'lang' not in st.session_state: st.session_state.lang = "ID"
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None

L = lang_dict[st.session_state.lang]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl="0s")

list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

# --- 4. HEADER ---
st.markdown(f"<h1 class='header-text'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='slogan'>{L['slogan']}</p>", unsafe_allow_html=True)

now_dt = datetime.now()
st.markdown(f"<div class='clock-text'>🗓️ {now_dt.strftime('%A, %d %B %Y')} | ⏰ {now_dt.strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

if st.button("🌐 Switch Language (ID/EN)"):
    st.session_state.lang = "EN" if st.session_state.lang == "ID" else "ID"
    st.rerun()

# --- 5. AUTH (LOGIN & REGISTRASI DENGAN FOTO MASTER) ---
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
            st.info(L['face_ref'])
            foto_master = st.camera_input("Foto Master")
            if st.form_submit_button(L['reg']):
                df_u = load_data("users")
                if id_val in df_u.iloc[:, 4].astype(str).tolist(): # Cek ID unik
                    st.error("ID/NIS sudah terdaftar!")
                elif not foto_master:
                    st.error("Foto Wajah Referensi Wajib!")
                else:
                    new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_val}])
                    conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True))
                    st.success("Registrasi Berhasil!")

# --- 6. DASHBOARD UTAMA ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    
    menu = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}"]
    if user['role'] in ["Guru", "Admin TU"]: menu.append("📊 Laporan")
    choice = st.sidebar.radio("Menu", menu)

    # --- MENU PRESENSI (GPS + WAJAH) ---
    if choice == f"📍 {L['absen_h']}":
        st.subheader(L['absen_h'])
        school_loc = (-7.2164697698622335, 109.64013014754921)
        loc = get_geolocation()
        
        if loc:
            u_loc = (loc['coords']['latitude'], loc['coords']['longitude'])
            dist = geodesic(u_loc, school_loc).meters
            
            if dist > 100:
                st.error(f"❌ {L['gps_fail']} (Jarak: {int(dist)}m)")
            else:
                st.success(f"✅ {L['gps_ok']} ({int(dist)}m)")
                m_absen = st.selectbox(L['pilih_j'], [L['m_sek'], L['m_dhu'], L['m_dzu'], L['m_pul']])
                
                # Capture wajah saat presensi
                st.info(L['face_now'])
                img_now = st.camera_input("Verify Face")
                
                if st.button("Submit Attendance") and img_now:
                    df_p = load_data("presensi")
                    new_p = pd.DataFrame([{
                        "nama": user['nama'], "kelas": user['kelas'], 
                        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "jenis": m_absen, "jarak": f"{int(dist)}m"
                    }])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True))
                    st.balloons(); st.success(L['success'])
        else: st.warning("Sedang mencari GPS...")

    # --- MENU TUGAS ---
    elif choice == f"{L['tugas']}":
        st.header(L['tugas'])
        if user['role'] == "Guru":
            with st.expander(f"➕ {L['input_t']}"):
                with st.form("task_f"):
                    t_j = st.text_input("Judul Tugas")
                    t_d = st.text_area("Deskripsi")
                    t_dl = st.date_input(L['dead'])
                    t_k = st.multiselect("Pilih Kelas", list_kelas)
                    if st.form_submit_button("Kirim Tugas"):
                        df_t = load_data("tugas")
                        new_t = pd.DataFrame([{"id": datetime.now().strftime("%Y%m%d%H%M"), "guru": user['nama'], "judul": t_j, "deskripsi": t_j, "deadline": str(t_dl), "kelas": ",".join(t_k)}])
                        conn.update(worksheet="tugas", data=pd.concat([df_t, new_t], ignore_index=True))
                        st.success("Tugas Disebarkan!")

        # List Tugas untuk Siswa
        df_tugas = load_data("tugas")
        df_done = load_data("tugas_selesai")
        
        relevant_tasks = df_tugas[df_tugas['kelas'].str.contains(user['kelas'])] if user['role'] == "Siswa" else df_tugas
        
        for _, row in relevant_tasks.iterrows():
            is_done = not df_done[(df_done['id_tugas'] == row['id']) & (df_done['nama'] == user['nama'])].empty
            st.markdown(f"""<div class="task-card"><h4>{row['judul']}</h4><p>{row['deskripsi']}</p>
                        <small>📅 Deadline: {row['deadline']} | 👨‍🏫 {row['guru']}</small></div>""", unsafe_allow_html=True)
            if user['role'] == "Siswa" and not is_done:
                if st.button(f"Mark as {L['done']}", key=row['id']):
                    new_done = pd.DataFrame([{"id_tugas": row['id'], "nama": user['nama'], "waktu": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                    conn.update(worksheet="tugas_selesai", data=pd.concat([df_done, new_done], ignore_index=True))
                    st.rerun()
            elif is_done: st.success("✅ " + L['done'])

    if st.sidebar.button(L['out']):
        st.session_state.logged_in_user = None
        st.rerun()

# --- 7. RUN ---
if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
