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
    .metric-box { background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KAMUS BAHASA ---
lang_dict = {
    "ID": {
        "slogan": "Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan",
        "login": "Masuk", "reg": "Registrasi", "nama": "Nama Lengkap", "pass": "Password",
        "nis": "NIS (Min 4 digit)", "nik": "NIK (Min 4 digit)", "absen_h": "📍 Presensi Wajah & GPS",
        "tugas": "📚 Tugas Sekolah", "lapor": "📊 Laporan", "log_sys": "⚙️ Log System", "out": "Keluar"
    },
    "EN": {
        "slogan": "Creating Pious, Achieving, and Environmentally Conscious Students",
        "login": "Login", "reg": "Registration", "nama": "Full Name", "pass": "Password",
        "nis": "NIS (Min 4 digits)", "nik": "NIK (Min 4 digits)", "absen_h": "📍 Attendance",
        "tugas": "📚 Tasks", "lapor": "📊 Reports", "log_sys": "⚙️ Log System", "out": "Logout"
    }
}

# --- 4. DATA & LOGGING FUNCTION ---
if 'lang' not in st.session_state: st.session_state.lang = "ID"
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None

L = lang_dict[st.session_state.lang]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl="0s")

def add_log(user, activity, detail):
    try:
        df_log = load_data("log_system")
        new_entry = pd.DataFrame([{
            "waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"),
            "user": user, "aktivitas": activity, "keterangan": detail
        }])
        conn.update(worksheet="log_system", data=pd.concat([df_log, new_entry], ignore_index=True))
    except: pass

list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

# --- 5. HEADER & JAM ---
st.markdown(f"<h1 class='header-text'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='slogan'>{L['slogan']}</p>", unsafe_allow_html=True)

now_dt = datetime.now(jakarta_tz)
st.markdown(f"<div class='clock-text'>🗓️ {now_dt.strftime('%A, %d %B %Y')} | ⏰ {now_dt.strftime('%H:%M:%S')} WIB</div>", unsafe_allow_html=True)

# --- 6. AUTHENTICATION ---
def show_auth():
    tab1, tab2 = st.tabs([f"🔑 {L['login']}", f"📝 {L['reg']}"])
    with tab1:
        with st.form("l_form"):
            u = st.text_input(L['nama']).title()
            p = st.text_input(L['pass'], type="password")
            if st.form_submit_button(L['login']):
                df_u = load_data("users")
                m = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p)]
                if not m.empty:
                    st.session_state.logged_in_user = m.iloc[0].to_dict()
                    add_log(u, "LOGIN", "Login berhasil")
                    st.rerun()
                else: st.error("Login Gagal!")
    with tab2:
        with st.form("r_form"):
            role = st.selectbox("Role", ["Siswa", "Guru"])
            n = st.text_input(L['nama']).title()
            pw = st.text_input(L['pass'])
            id_val = st.text_input(L['nis'] if role == "Siswa" else L['nik'])
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            if st.form_submit_button(L['reg']):
                if (role == "Siswa" and (len(n) < 3 or len(id_val) < 4)) or (role == "Guru" and len(n) < 4):
                    st.error("Input tidak memenuhi syarat karakter minimum!")
                else:
                    df_u = load_data("users")
                    new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_val}])
                    conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True))
                    add_log(n, "REGISTRASI", f"Daftar sebagai {role}")
                    st.success("Registrasi Berhasil!")

# --- 7. DASHBOARD ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}"]
    if user['role'] in ["Guru", "Admin TU"]: 
        menu_opt += [L['lapor'], L['log_sys']]
    choice = st.sidebar.radio("Menu", menu_opt)

    # --- PRESENSI ---
    if choice == f"📍 {L['absen_h']}":
        st.subheader(L['absen_h'])
        loc = get_geolocation()
        if loc:
            u_loc = (loc['coords']['latitude'], loc['coords']['longitude'])
            dist = geodesic(u_loc, (-7.2164697698622335, 109.64013014754921)).meters
            if dist <= 100:
                img = st.camera_input("Verify Face")
                if st.button("Kirim Presensi") and img:
                    df_p = load_data("presensi")
                    new_p = pd.DataFrame([{"nama": user['nama'], "kelas": user.get('kelas', '-'), "waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"), "status": "VALID"}])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True))
                    add_log(user['nama'], "PRESENSI", "Berhasil presensi")
                    st.success("Berhasil!")
            else: st.error(L['gps_fail'])

    # --- TUGAS (DENGAN GRAFIK PERSENTASE) ---
    elif choice == f"{L['tugas']}":
        st.header(L['tugas'])
        df_t = load_data("tugas")
        df_done = load_data("tugas_selesai")
        df_u = load_data("users")

        if user['role'] == "Guru":
            with st.expander("➕ Buat Tugas Baru"):
                with st.form("t_f"):
                    t_j = st.text_input("Judul"); t_d = st.text_area("Deskripsi"); t_k = st.multiselect("Kelas", list_kelas)
                    if st.form_submit_button("Sebarkan"):
                        new_t = pd.DataFrame([{"id": datetime.now(jakarta_tz).strftime("%H%M%S"), "guru": user['nama'], "judul": t_j, "deskripsi": t_d, "kelas": ",".join(t_k)}])
                        conn.update(worksheet="tugas", data=pd.concat([df_t, new_t], ignore_index=True))
                        add_log(user['nama'], "BUAT TUGAS", t_j); st.rerun()

            st.subheader("📈 Statistik Pengumpulan")
            for _, r in df_t.iterrows():
                # Hitung Persentase
                target_kls_list = r['kelas'].split(',')
                total_siswa = len(df_u[(df_u['role'] == 'Siswa') & (df_u['kelas'].isin(target_kls_list))])
                sudah_selesai = len(df_done[df_done['id_tugas'].astype(str) == str(r['id'])])
                persen = (sudah_selesai / total_siswa * 100) if total_siswa > 0 else 0
                
                with st.expander(f"📊 {r['judul']} - {sudah_selesai}/{total_siswa} Siswa"):
                    st.progress(persen / 100)
                    st.write(f"Persentase Penyelesaian: **{int(persen)}%**")
                    st.table(df_done[df_done['id_tugas'].astype(str) == str(r['id'])][['nama', 'kelas', 'waktu']])

        else: # SISWA
            user_kls = str(user.get('kelas', ''))
            df_t['kelas'] = df_t['kelas'].astype(str)
            rel_t = df_t[df_t['kelas'].str.contains(user_kls, na=False)]
            for _, r in rel_t.iterrows():
                is_comp = not df_done[(df_done['id_tugas'].astype(str) == str(r['id'])) & (df_done['nama'] == user['nama'])].empty
                st.markdown(f'<div class="task-card"><h4>{r["judul"]}</h4><p>{r["deskripsi"]}</p></div>', unsafe_allow_html=True)
                if not is_comp:
                    if st.button("Selesai / Done", key=str(r['id'])):
                        new_d = pd.DataFrame([{"id_tugas": str(r['id']), "nama": user['nama'], "kelas": user['kelas'], "waktu": datetime.now(jakarta_tz).strftime("%H:%M %d/%m")}])
                        conn.update(worksheet="tugas_selesai", data=pd.concat([df_done, new_d], ignore_index=True))
                        add_log(user['nama'], "TUGAS SELESAI", r['judul']); st.rerun()
                else: st.success("✅ Selesai")

    # --- LOG SYSTEM ---
    elif choice == L['log_sys']:
        st.header(L['log_sys'])
        df_logs = load_data("log_system")
        st.text_area("System Logs", value=df_logs.sort_values(by='waktu', ascending=False).to_string(index=False), height=400)
        st.download_button("📥 Download Log", df_logs.to_csv(index=False), "logs.txt")

    if st.sidebar.button(L['out']):
        add_log(user['nama'], "LOGOUT", "Logout dari sistem")
        st.session_state.logged_in_user = None
        st.rerun()

# --- 8. RUN APP ---
if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
