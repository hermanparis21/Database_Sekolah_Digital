import streamlit as st
import pandas as pd
from datetime import datetime
import datetime as dt
import pytz
import io
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# --- 1. KONFIGURASI ZONA WAKTU ---
jakarta_tz = pytz.timezone('Asia/Jakarta')
SCHOOL_LOC = (-7.2164697698622335, 109.64013014754921)

# --- 2. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SMA Muhammadiyah 4 Banjarnegara", layout="wide", page_icon="🎓")

# CSS Tetap Sama
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

# --- 3. DATA & LOGGING (HEAVILY OPTIMIZED) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Fungsi muat data dengan proteksi kuota lebih ketat
@st.cache_data(ttl=10) # Data disimpan di memori selama 10 detik untuk semua user
def fetch_sheet(sheet_name):
    return conn.read(worksheet=sheet_name)

def load_data(sheet_name):
    return fetch_sheet(sheet_name)

def add_log(user, activity, detail):
    try:
        df_log = conn.read(worksheet="log_system", ttl="0s")
        new_entry = pd.DataFrame([{"waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"), "user": user, "aktivitas": activity, "keterangan": detail}])
        conn.update(worksheet="log_system", data=pd.concat([df_log, new_entry], ignore_index=True))
    except: pass

# --- 4. LOGIKA STATUS ---
def get_attendance_status(jenis, waktu_str):
    try:
        t = datetime.strptime(waktu_str, "%Y-%m-%d %H:%M:%S").time()
        if jenis == "Masuk": return "Valid" if dt.time(6,0) <= t <= dt.time(7,30) else "Terlambat"
        elif jenis == "Dhuha": return "Valid" if dt.time(7,15) <= t <= dt.time(8,0) else "Terlambat"
        elif jenis == "Dzuhur": return "Valid" if dt.time(11,30) <= t <= dt.time(13,0) else "Terlambat"
        elif jenis == "Pulang": return "Valid" if t >= dt.time(14,30) else "Pulang Cepat"
        return "Unknown"
    except: return "Format Error"

# --- 5. INITIAL STATE ---
if 'lang' not in st.session_state: st.session_state.lang = "ID"
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
lang_dict = {"ID": {"slogan": "Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan", "login": "Masuk", "reg": "Registrasi Siswa Baru", "nama": "Nama Lengkap", "pass": "Password", "nis": "NIS (Min 4 digit)", "nik": "NIK (Min 4 digit)", "face_ref": "Ambil Foto Wajah Referensi (Wajib)", "absen_h": "📍 Presensi Wajah & GPS", "pilih_j": "Jenis Presensi", "face_now": "Verifikasi Wajah Sekarang", "tugas": "📚 Tugas Sekolah", "lapor": "📊 Laporan Presensi", "log_sys": "⚙️ Log System", "spp": "💰 Manajemen SPP", "out": "Keluar"}}
L = lang_dict[st.session_state.lang]
list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

# Header
st.markdown(f"<h1 class='header-text'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='slogan'>{L['slogan']}</p>", unsafe_allow_html=True)
now_dt = datetime.now(jakarta_tz)
st.markdown(f"<div class='clock-text'>🗓️ {now_dt.strftime('%A, %d %B %Y')} | ⏰ {now_dt.strftime('%H:%M:%S')} WIB</div>", unsafe_allow_html=True)

# --- 6. AUTHENTICATION ---
def show_auth():
    tab1, tab2 = st.tabs([f"🔑 {L['login']}", f"📝 {L['reg']}"])
    with tab1:
        with st.form("l_form"):
            u = st.text_input(L['nama']).title(); p = st.text_input(L['pass'], type="password")
            if st.form_submit_button(L['login']):
                df_u = load_data("users")
                m = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p)]
                if not m.empty:
                    st.session_state.logged_in_user = m.iloc[0].to_dict()
                    add_log(u, "LOGIN", "Login berhasil"); st.rerun()
                else: st.error("Login Gagal!")
    with tab2:
        with st.form("r_form"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input(L['nama']).title(); pw = st.text_input(L['pass']); id_val = st.text_input("NIS/NIK (Min 4 digit)")
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            st.info(L['face_ref']); f_ref = st.camera_input("Capture")
            if st.form_submit_button(L['reg']):
                if not f_ref: st.error("Foto wajib!"); return
                df_u = load_data("users")
                new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_val}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True)); st.success("Berhasil!")

# --- 7. DASHBOARD ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}", L['spp']]
    if user['role'] in ["Guru", "Admin TU"]: menu_opt += [L['lapor'], L['log_sys']]
    choice = st.sidebar.radio("Menu", menu_opt)

    # --- HOME ---
    if choice == "🏠 Home":
        st.subheader(f"Selamat Datang, {user['nama']}!")
        today = datetime.now(jakarta_tz).strftime("%Y-%m-%d")
        if user['role'] in ["Guru", "Admin TU"]:
            df_p = load_data("presensi"); df_ts = load_data("tugas_selesai")
            p_today = df_p[df_p['waktu'].str.contains(today, na=False)]
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Masuk'])}</h3><p>Hadir</p></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Dhuha'])}</h3><p>Dhuha</p></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Dzuhur'])}</h3><p>Dzuhur</p></div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div class='stat-card'><h3>{len(df_ts[df_ts['waktu'].str.contains(today, na=False)])}</h3><p>Tugas</p></div>", unsafe_allow_html=True)
        else:
            df_spp = load_data("spp")
            tunggakan = 1200000 - df_spp[df_spp['nama'] == user['nama']]['jumlah'].sum()
            st.metric("Tunggakan SPP", f"Rp {tunggakan:,.0f}")

    # --- PRESENSI ---
    elif choice == f"📍 {L['absen_h']}":
        st.subheader(L['absen_h'])
        loc = get_geolocation()
        if loc:
            u_coords = (loc['coords']['latitude'], loc['coords']['longitude'])
            dist = geodesic(u_coords, SCHOOL_LOC).meters
            if dist <= 100:
                m_absen = st.selectbox(L['pilih_j'], ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                img_now = st.camera_input(L['face_now'])
                if st.button("Submit") and img_now:
                    df_p = conn.read(worksheet="presensi", ttl="0s") # Pakai Live Data khusus Write
                    new_p = pd.DataFrame([{"nama": user['nama'], "kelas": user.get('kelas', '-'), "waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"), "jenis": m_absen, "jarak": f"{int(dist)}m", "coords": f"{u_coords}"}])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True))
                    st.success("Presensi Berhasil!")
            else: st.error(f"Jarak Anda: {int(dist)}m (Radius 100m)")

    # --- TUGAS (FIXED QUOTA) ---
    elif choice == f"{L['tugas']}":
        st.header(L['tugas'])
        df_t = load_data("tugas")
        df_done = load_data("tugas_selesai")
        
        if user['role'] == "Guru":
            with st.expander("➕ Buat Tugas Baru"):
                with st.form("t_f"):
                    t_j = st.text_input("Judul"); t_d = st.text_area("Deskripsi"); t_k = st.multiselect("Kelas", list_kelas)
                    if st.form_submit_button("Kirim"):
                        df_t_live = conn.read(worksheet="tugas", ttl="0s")
                        new_t = pd.DataFrame([{"id": datetime.now(jakarta_tz).strftime("%H%M%S"), "guru": user['nama'], "judul": t_j, "deskripsi": t_d, "kelas": ",".join(t_k)}])
                        conn.update(worksheet="tugas", data=pd.concat([df_t_live, new_t], ignore_index=True)); st.rerun()
            for _, r in df_t.iterrows():
                with st.expander(f"📊 {r['judul']}"):
                    st.table(df_done[df_done['id_tugas'].astype(str) == str(r['id'])])
            st.divider()
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df_done.to_excel(writer, index=False)
            st.download_button("📥 Ekspor Tugas (XLSX)", output.getvalue(), "laporan_tugas.xlsx")

        else: # SISWA
            user_kls = str(user.get('kelas',''))
            rel_t = df_t[df_t['kelas'].astype(str).str.contains(user_kls, na=False)]
            for _, r in rel_t.iterrows():
                is_comp = not df_done[(df_done['id_tugas'].astype(str) == str(r['id'])) & (df_done['nama'] == user['nama'])].empty
                st.markdown(f'<div class="task-card"><h4>{r["judul"]}</h4><p>{r["deskripsi"]}</p></div>', unsafe_allow_html=True)
                if not is_comp:
                    if st.button(f"Klik Selesai: {r['judul']}", key=f"btn_{r['id']}"):
                        df_live = conn.read(worksheet="tugas_selesai", ttl="0s")
                        new_d = pd.DataFrame([{"id_tugas": str(r['id']), "nama": user['nama'], "kelas": user['kelas'], "waktu": now_dt.strftime("%d/%m %H:%M")}])
                        conn.update(worksheet="tugas_selesai", data=pd.concat([df_live, new_d], ignore_index=True)); st.rerun()
                else: st.success("✅ Tugas Selesai")

    # --- LAPORAN ---
    elif choice == L['lapor']:
        st.header(L['lapor'])
        df_p = load_data("presensi")
        df_p['Status Waktu'] = df_p.apply(lambda x: get_attendance_status(x['jenis'], x['waktu']), axis=1)
        st.dataframe(df_p.style.applymap(lambda v: 'color:red; font-weight:bold' if v in ['Terlambat','Pulang Cepat'] else '', subset=['Status Waktu']), width='stretch')
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer: df_p.to_excel(writer, index=False)
        st.download_button("📥 Ekspor XLSX", buffer.getvalue(), "laporan.xlsx")

    # --- SPP ---
    elif choice == L['spp']:
        df_spp = load_data("spp")
        if user['role'] == "Admin TU":
            with st.form("spp"):
                df_u = load_data("users")
                s_sel = st.selectbox("Siswa", df_u[df_u['role']=='Siswa']['nama'].tolist())
                jml = st.number_input("Jumlah", min_value=0)
                if st.form_submit_button("Bayar"):
                    df_spp_live = conn.read(worksheet="spp", ttl="0s")
                    s_data = df_u[df_u['nama'] == s_sel].iloc[0]
                    new_p = pd.DataFrame([{"nama": s_sel, "nis": s_data['id_unik'], "kelas": s_data['kelas'], "jumlah": jml, "tanggal": now_dt.strftime("%Y-%m-%d")}])
                    conn.update(worksheet="spp", data=pd.concat([df_spp_live, new_p], ignore_index=True)); st.success("Bayar Berhasil!")
        st.dataframe(df_spp[df_spp['nama'] == user['nama']] if user['role'] == "Siswa" else df_spp)

    elif choice == L['log_sys']:
        st.table(load_data("log_system").tail(20))

    if st.sidebar.button(L['out']): st.session_state.logged_in_user = None; st.rerun()

if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
