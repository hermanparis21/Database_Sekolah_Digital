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
    .stat-card { background: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KAMUS BAHASA ---
lang_dict = {
    "ID": {
        "slogan": "Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan",
        "login": "Masuk", "reg": "Registrasi Siswa Baru", "nama": "Nama Lengkap", "pass": "Password",
        "nis": "NIS (Min 4 digit)", "nik": "NIK (Min 4 digit)", "face_ref": "Ambil Foto Wajah Referensi (Wajib)",
        "absen_h": "📍 Presensi Wajah & GPS", "pilih_j": "Jenis Presensi", "face_now": "Verifikasi Wajah Sekarang",
        "tugas": "📚 Tugas Sekolah", "lapor": "📊 Laporan Presensi", "log_sys": "⚙️ Log System", "spp": "💰 Manajemen SPP", "out": "Keluar"
    },
    "EN": {
        "slogan": "Creating Pious, Achieving, and Environmentally Conscious Students",
        "login": "Login", "reg": "Student Registration", "nama": "Full Name", "pass": "Password",
        "nis": "Student ID (Min 4 digits)", "nik": "Teacher ID (Min 4 digits)", "face_ref": "Capture Reference Face",
        "absen_h": "📍 Attendance", "pilih_j": "Type", "face_now": "Verify Face Now",
        "tugas": "📚 Tasks", "lapor": "📊 Reports", "log_sys": "⚙️ Log System", "spp": "💰 Tuition Fee", "out": "Logout"
    }
}

# --- 4. DATA & LOGGING ---
if 'lang' not in st.session_state: st.session_state.lang = "ID"
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None

L = lang_dict[st.session_state.lang]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl="0s")

def add_log(user, activity, detail):
    try:
        df_log = load_data("log_system")
        new_entry = pd.DataFrame([{"waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"), "user": user, "aktivitas": activity, "keterangan": detail}])
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
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input(L['nama']).title()
            pw = st.text_input(L['pass'])
            id_val = st.text_input("NIS/NIK (Min 4 digit)")
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            st.info(L['face_ref'])
            f_ref = st.camera_input("Capture Face Reference")
            if st.form_submit_button(L['reg']):
                if not f_ref: st.error("Foto wajah wajib!"); return
                if (len(n) < 3) or (len(id_val) < 4): st.error("Input minimal karakter tidak terpenuhi!"); return
                df_u = load_data("users")
                new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_val}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True))
                add_log(n, "REGISTRASI", f"Role: {role}")
                st.success("Registrasi Berhasil!")

# --- 7. DASHBOARD ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}", L['spp']]
    if user['role'] in ["Guru", "Admin TU"]: menu_opt += [L['lapor'], L['log_sys']]
    choice = st.sidebar.radio("Menu", menu_opt)

    # --- HOME (RESUME DASHBOARD) ---
    if choice == "🏠 Home":
        st.subheader(f"Selamat Datang, {user['nama']}!")
        df_p = load_data("presensi")
        df_ts = load_data("tugas_selesai")
        today = datetime.now(jakarta_tz).strftime("%Y-%m-%d")

        if user['role'] in ["Guru", "Admin TU"]:
            st.markdown("### 📊 Ringkasan Harian")
            c1, c2, c3, c4 = st.columns(4)
            p_today = df_p[df_p['waktu'].str.contains(today, na=False)]
            
            with c1: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Masuk'])}</h3><p>Hadir</p></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Dhuha'])}</h3><p>Sholat Dhuha</p></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Dzuhur'])}</h3><p>Sholat Dzuhur</p></div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div class='stat-card'><h3>{len(df_ts[df_ts['waktu'].str.contains(today, na=False)])}</h3><p>Tugas Selesai</p></div>", unsafe_allow_html=True)
        
        elif user['role'] == "Siswa":
            st.info(f"Kelas Anda: {user['kelas']}")
            df_spp = load_data("spp")
            my_spp = df_spp[df_spp['nama'] == user['nama']]
            tunggakan = 1200000 - my_spp['jumlah'].sum() if not my_spp.empty else 1200000
            st.metric("Tunggakan SPP Anda", f"Rp {tunggakan:,.0f}")

    # --- PRESENSI (FIXED UNBOUND ERROR) ---
    elif choice == f"📍 {L['absen_h']}":
        st.subheader(L['absen_h'])
        loc = get_geolocation()
        if loc:
            u_loc = (loc['coords']['latitude'], loc['coords']['longitude'])
            dist = geodesic(u_loc, (-7.2164697698622335, 109.64013014754921)).meters
            if dist <= 100:
                m_absen = st.selectbox(L['pilih_j'], ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                img_now = st.camera_input(L['face_now'])
                if st.button("Submit") and img_now:
                    df_p = load_data("presensi") # MEMUAT DATA PRESENSI (FIXED)
                    new_p = pd.DataFrame([{"nama": user['nama'], "kelas": user.get('kelas', '-'), "waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"), "jenis": m_absen, "status": "VALID"}])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True))
                    add_log(user['nama'], "PRESENSI", m_absen)
                    st.success("Presensi Berhasil!")
            else: st.error(L['gps_fail'])

    # --- MANAJEMEN SPP ---
    elif choice == L['spp']:
        st.header(L['spp'])
        df_u = load_data("users")
        df_spp = load_data("spp")
        today_date = datetime.now(jakarta_tz).strftime("%Y-%m-%d")
        
        if user['role'] == "Admin TU":
            with st.expander("➕ Input Pembayaran Baru"):
                with st.form("spp_form"):
                    siswa_sel = st.selectbox("Pilih Siswa", df_u[df_u['role']=='Siswa']['nama'].tolist())
                    jml = st.number_input("Jumlah Bayar (Rp)", min_value=0)
                    if st.form_submit_button("Simpan Pembayaran"):
                        siswa_data = df_u[df_u['nama'] == siswa_sel].iloc[0]
                        new_pay = pd.DataFrame([{"nama": siswa_sel, "nis": siswa_data['id_unik'], "kelas": siswa_data['kelas'], "jumlah": jml, "tanggal": today_date}])
                        conn.update(worksheet="spp", data=pd.concat([df_spp, new_pay], ignore_index=True))
                        add_log(user['nama'], "BAYAR SPP", f"Siswa: {siswa_sel}")
                        st.success("Data Tersimpan!")
            
            st.subheader("📊 Rekap Tunggakan per Kelas")
            if not df_spp.empty:
                df_spp_rek = df_spp.groupby('kelas')['jumlah'].sum().reset_index()
                st.bar_chart(df_spp_rek.set_index('kelas'))
            else: st.info("Belum ada data pembayaran.")

        elif user['role'] == "Guru":
            st.write(f"Data SPP Kelas yang Diampu ({user['kelas']})")
            st.dataframe(df_spp[df_spp['kelas'] == user['kelas']], width='stretch')

        elif user['role'] == "Siswa":
            st.write("Riwayat Pembayaran Anda")
            st.dataframe(df_spp[df_spp['nama'] == user['nama']], width='stretch')

    # --- TUGAS ---
    elif choice == f"{L['tugas']}":
        st.header(L['tugas'])
        df_t = load_data("tugas"); df_done = load_data("tugas_selesai"); df_u = load_data("users")
        if user['role'] == "Guru":
            with st.expander("➕ Buat Tugas Baru"):
                with st.form("t_f"):
                    t_j = st.text_input("Judul"); t_d = st.text_area("Deskripsi"); t_k = st.multiselect("Kelas", list_kelas)
                    if st.form_submit_button("Kirim"):
                        new_t = pd.DataFrame([{"id": datetime.now(jakarta_tz).strftime("%H%M%S"), "guru": user['nama'], "judul": t_j, "deskripsi": t_d, "kelas": ",".join(t_k)}])
                        conn.update(worksheet="tugas", data=pd.concat([df_t, new_t], ignore_index=True))
                        st.rerun()
            for _, r in df_t.iterrows():
                target_kls = r['kelas'].split(',')
                total_s = len(df_u[(df_u['role'] == 'Siswa') & (df_u['kelas'].isin(target_kls))])
                sudah_s = len(df_done[df_done['id_tugas'].astype(str) == str(r['id'])])
                with st.expander(f"📊 {r['judul']} ({sudah_s}/{total_s})"):
                    st.progress((sudah_s/total_s) if total_s>0 else 0)
                    st.table(df_done[df_done['id_tugas'].astype(str) == str(r['id'])][['nama', 'kelas', 'waktu']])
        else:
            user_kls = str(user.get('kelas', ''))
            rel_t = df_t[df_t['kelas'].astype(str).str.contains(user_kls, na=False)]
            for _, r in rel_t.iterrows():
                is_comp = not df_done[(df_done['id_tugas'].astype(str) == str(r['id'])) & (df_done['nama'] == user['nama'])].empty
                st.markdown(f'<div class="task-card"><h4>{r["judul"]}</h4><p>{r["deskripsi"]}</p></div>', unsafe_allow_html=True)
                if not is_comp and st.button("Selesai", key=str(r['id'])):
                    new_d = pd.DataFrame([{"id_tugas": str(r['id']), "nama": user['nama'], "kelas": user['kelas'], "waktu": now_dt.strftime("%H:%M %d/%m")}])
                    conn.update(worksheet="tugas_selesai", data=pd.concat([df_done, new_d], ignore_index=True))
                    st.rerun()

    # --- LAPORAN & LOG ---
    elif choice == L['lapor']:
        st.header(L['lapor'])
        df_p = load_data("presensi")
        st.dataframe(df_p, width='stretch')

    elif choice == L['log_sys']:
        st.header(L['log_sys'])
        st.text_area("Logs", value=load_data("log_system").sort_values(by='waktu', ascending=False).to_string(index=False), height=400)

    if st.sidebar.button(L['out']):
        st.session_state.logged_in_user = None
        st.rerun()

if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
