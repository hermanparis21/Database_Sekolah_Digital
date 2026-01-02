import streamlit as st
import pandas as pd
from datetime import datetime
import datetime as dt
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import time

# --- 1. KONFIGURASI HALAMAN & CSS ---
st.set_page_config(page_title="SMA Muhammadiyah 4 Banjarnegara", layout="wide", page_icon="🎓")

# CSS Modern untuk tampilan yang lebih intuitif (Mobile Friendly)
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #059669; color: white; border: none; }
    .stTextInput>div>div>input, .stSelectbox>div>div>select { border-radius: 10px; }
    .header-text { text-align: center; color: #059669; margin-bottom: 0px; }
    .slogan { text-align: center; font-style: italic; color: #475569; font-size: 0.9em; margin-bottom: 10px; }
    .clock-text { text-align: center; font-weight: bold; font-size: 1.1em; color: #1e293b; background: #e2e8f0; padding: 10px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MULTI-LANGUAGE DICTIONARY ---
lang_dict = {
    "ID": {
        "slogan": "Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan",
        "login": "Masuk", "reg": "Registrasi", "nama": "Nama Lengkap", "pass": "Kata Sandi",
        "role": "Peran", "kelas_wali": "Wali Kelas untuk Kelas:", "absen": "Presensi", 
        "nilai": "Lihat Nilai", "input_n": "Input Nilai", "lapor": "Laporan Log", "out": "Keluar"
    },
    "EN": {
        "slogan": "Creating Pious, Achieving, and Environmentally Conscious Students",
        "login": "Login", "reg": "Registration", "nama": "Full Name", "pass": "Password",
        "role": "Role", "kelas_wali": "Homeroom Teacher for Class:", "absen": "Attendance", 
        "nilai": "View Grades", "input_n": "Input Grades", "lapor": "Log Reports", "out": "Logout"
    }
}

# --- 3. SESSION STATE ---
if 'lang' not in st.session_state: st.session_state.lang = "ID"
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None

L = lang_dict[st.session_state.lang]

# --- 4. DATA & KONEKSI ---
conn = st.connection("gsheets", type=GSheetsConnection)
def load_data(sheet_name): return conn.read(worksheet=sheet_name, ttl="0s")

list_kelas = [f"{tingkat}-{huruf}" for tingkat in ["X", "XI", "XII"] for huruf in ["A", "B", "C", "D", "E", "F"]]

# --- 5. HEADER (SLOGAN & CLOCK) ---
st.markdown(f"<h1 class='header-text'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='slogan'>{L['slogan']}</p>", unsafe_allow_html=True)

# Jam Real-time Sederhana
t = datetime.now()
st.markdown(f"<div class='clock-text'>🗓️ {t.strftime('%A, %d %B %Y')} | ⏰ {t.strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# Switch Bahasa
col_l1, col_l2 = st.columns([8, 2])
with col_l2:
    if st.button("🇮🇩 ID / 🇬🇧 EN"):
        st.session_state.lang = "EN" if st.session_state.lang == "ID" else "ID"
        st.rerun()

# --- 6. AUTHENTICATION ---
def show_auth():
    tab1, tab2 = st.tabs([f"🔑 {L['login']}", f"📝 {L['reg']}"])
    
    with tab1:
        with st.form("login_form"):
            u_nama = st.text_input(L['nama'])
            u_pass = st.text_input(L['pass'], type="password")
            if st.form_submit_button(L['login']):
                df_u = load_data("users")
                match = df_u[(df_u['nama'].astype(str).str.strip() == u_nama.strip()) & (df_u['password'].astype(str) == u_pass)]
                if not match.empty:
                    st.session_state.logged_in_user = match.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Invalid credentials")

    with tab2:
        with st.form("reg_form"):
            role = st.selectbox(L['role'], ["Siswa", "Guru", "Admin TU"])
            n_nama = st.text_input(L['nama'])
            n_pass = st.text_input(L['pass'])
            n_nik = st.text_input("NIK (16 Digits)")
            
            # Perbaikan Registrasi Guru (Multi-select Kelas Wali)
            n_wali = st.multiselect(L['kelas_wali'], list_kelas) if role == "Guru" else []
            n_kls = st.selectbox("Kelas (Siswa)", list_kelas) if role == "Siswa" else "-"
            
            if st.form_submit_button(L['reg']):
                df_u = load_data("users")
                new_row = pd.DataFrame([{"nama": n_nama, "password": n_pass, "role": role, "kelas": n_kls, "nik": n_nik, "wali_kelas": ",".join(n_wali)}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_row], ignore_index=True))
                st.success("Registration Success!")

# --- 7. DASHBOARD UTAMA ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.markdown(f"### 👤 {user['nama']}")
    st.sidebar.write(f"Role: {user['role']}")
    
    menu_options = ["🏠 Home", f"📍 {L['absen']}", f"📖 {L['nilai']}"]
    if user['role'] in ["Guru", "Admin TU"]: menu_options.append(f"📊 {L['lapor']}")
    
    choice = st.sidebar.radio("Menu", menu_options)

    # --- FITUR LAPORAN (UNTUK GURU & ADMIN) ---
    if choice == f"📊 {L['lapor']}":
        st.header(f"📊 {L['lapor']}")
        df_p = load_data("presensi")
        
        # Filter Mobile Friendly
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_kelas = st.multiselect("Filter Kelas", list_kelas)
        with col_f2:
            f_date = st.date_input("Filter Tanggal", [])

        # Logika Filter (Sederhana)
        if f_kelas:
            # Catatan: Pastikan kolom 'kelas' ada di tab presensi
            df_p = df_p[df_p['kelas'].isin(f_kelas)]
        
        st.dataframe(df_p, use_container_width=True)
        
        # Download Button
        csv = df_p.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Log (CSV)", csv, "log_absen.csv", "text/csv")

    # (Fitur Presensi & Input Nilai tetap menggunakan logika sebelumnya namun dengan L['label'])
    
    if st.sidebar.button(L['out']):
        st.session_state.logged_in_user = None
        st.rerun()

# --- RUN ---
if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
