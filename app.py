import streamlit as st
import pandas as pd
from datetime import datetime
import datetime as dt
import pytz
import io
import base64
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
from PIL import Image

# --- 1. KONFIGURASI & STYLE ---
jakarta_tz = pytz.timezone('Asia/Jakarta')
SCHOOL_LOC = (-7.2164697698622335, 109.64013014754921)

st.set_page_config(page_title="SMA Muhammadiyah 4 Banjarnegara", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #059669; color: white; height: 3em; }
    .clock-text { text-align: center; font-weight: bold; font-size: 1.1em; color: #1e293b; background: #f1f5f9; padding: 10px; border-radius: 15px; border: 1px solid #cbd5e1; margin-bottom: 20px; }
    .header-text { text-align: center; color: #059669; margin-bottom: 0px; font-size: 2em; }
    .slogan { text-align: center; font-style: italic; color: #475569; margin-bottom: 10px; font-size: 1em; }
    .highlight-sholat { background: #fef9c3; border: 2px solid #facc15; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 15px; }
    .terlambat-text { color: #dc2626; font-weight: bold; }
    .stat-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KONEKSI & HELPER ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, ttl="0s"):
    try: return conn.read(worksheet=sheet_name, ttl=ttl)
    except: return pd.DataFrame()

def process_photo(uploaded_file):
    img = Image.open(uploaded_file).convert("RGB")
    img.thumbnail((300, 300)) 
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=50)
    return base64.b64encode(buf.getvalue()).decode()

def get_attendance_status(jenis, waktu_str):
    try:
        t = datetime.strptime(waktu_str, "%Y-%m-%d %H:%M:%S").time()
        if jenis == "Masuk": return "Valid" if dt.time(6,0) <= t <= dt.time(7,30) else "Terlambat"
        elif jenis == "Dhuha": return "Valid" if dt.time(7,15) <= t <= dt.time(8,0) else "Terlambat"
        elif jenis == "Dzuhur": return "Valid" if dt.time(11,30) <= t <= dt.time(13,0) else "Terlambat"
        elif jenis == "Pulang": return "Valid" if t >= dt.time(14,30) else "Pulang Cepat"
        return "Unknown"
    except: return "-"

# --- 3. LOGIKA AUTH ---
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
L = {"login": "Masuk", "reg": "Registrasi", "nama": "Nama Lengkap", "pass": "Password", "absen_h": "Presensi", "tugas": "Tugas", "lapor": "Laporan", "spp": "SPP", "out": "Keluar", "broadcast": "Broadcast"}
list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

def show_auth():
    t1, t2 = st.tabs([f"🔑 {L['login']}", f"📝 {L['reg']}"])
    with t1:
        with st.form("login_form"):
            u = st.text_input(L['nama']).title(); p = st.text_input(L['pass'], type="password")
            if st.form_submit_button(L['login']):
                df_u = load_data("users")
                m = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p.strip())]
                if not m.empty: st.session_state.logged_in_user = m.iloc[0].to_dict(); st.rerun()
                else: st.error("Nama atau Password salah")
    with t2:
        with st.form("reg_form"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input(L['nama']).title(); pw = st.text_input(L['pass']); id_v = st.text_input("NIS/NIK")
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            f_ref = st.camera_input("Foto Wajah (Registrasi)")
            if st.form_submit_button(L['reg']) and f_ref:
                df_u = load_data("users")
                new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_v, "foto_reg": process_photo(f_ref)}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True)); st.success("Registrasi Berhasil! Silakan Login.")

# --- 4. DASHBOARD UTAMA ---
def show_dashboard():
    u = st.session_state.logged_in_user
    now_dt = datetime.now(jakarta_tz)
    st.sidebar.title(f"👤 {u['nama']}")
    st.sidebar.write(f"Role: {u['role']} | {u['kelas']}")
    
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"📚 {L['tugas']}", f"💰 {L['spp']}"]
    if u['role'] in ["Guru", "Admin TU"]: menu_opt += [f"📢 {L['broadcast']}", f"📊 {L['lapor']}"]
    choice = st.sidebar.radio("Menu Navigasi", menu_opt)

    # --- HOME ---
    if "Home" in choice:
        st.subheader(f"Selamat Datang, {u['nama']}")
        
        # JADWAL SHOLAT HARI INI
        st.markdown(f"""<div class='highlight-sholat'><b>🕌 Jadwal Sholat Hari Ini (Banjarnegara)</b><br>
            Subuh: 04:15 | Dzuhur: 11:52 | Ashar: 15:18 | Maghrib: 18:07 | Isya: 19:22</div>""", unsafe_allow_html=True)
        
        with st.expander("📅 Jadwal Sholat 1 Bulan"):
            ds = {"Tanggal": [f"{i} Jan" for i in range(1, 32)], "Subuh": ["04:15"]*31, "Dzuhur": ["11:52"]*31, "Ashar": ["15:18"]*31, "Maghrib": ["18:07"]*31, "Isya": ["19:22"]*31}
            st.dataframe(pd.DataFrame(ds), hide_index=True)

        if u['role'] == "Siswa":
            col1, col2 = st.columns(2)
            df_t = load_data("tugas"); df_s = load_data("tugas_selesai")
            t_total = len(df_t[df_t['kelas'] == u['kelas']])
            t_done = len(df_s[(df_s['nama'] == u['nama'])])
            col1.metric("📚 Tugas Tersedia", t_total)
            col2.metric("✅ Tugas Selesai", t_done)
        
        else: # Role Guru/Admin
            df_p = load_data("presensi", ttl="2s")
            df_ts = load_data("tugas_selesai", ttl="2s")
            today_str = now_dt.strftime("%Y-%m-%d")
            p_today = df_p[df_p['waktu'].str.contains(today_str)] if not df_p.empty else pd.DataFrame()
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.markdown(f"<div class='stat-card'>🌅 Masuk<br><b>{len(p_today[p_today['jenis']=='Masuk'])}</b></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='stat-card'>🕌 Dhuha<br><b>{len(p_today[p_today['jenis']=='Dhuha'])}</b></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='stat-card'>☀️ Dzuhur<br><b>{len(p_today[p_today['jenis']=='Dzuhur'])}</b></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='stat-card'>🏠 Pulang<br><b>{len(p_today[p_today['jenis']=='Pulang'])}</b></div>", unsafe_allow_html=True)
            c5.markdown(f"<div class='stat-card'>📝 Tugas<br><b>{len(df_ts[df_ts['waktu'].str.contains(today_str)]) if not df_ts.empty else 0}</b></div>", unsafe_allow_html=True)

    # --- PRESENSI ---
    elif L['absen_h'] in choice:
        st.subheader("📍 Presensi Digital")
        loc = get_geolocation()
        if loc:
            dist = geodesic(SCHOOL_LOC, (loc['coords']['latitude'], loc['coords']['longitude'])).meters
            st.write(f"Jarak ke Sekolah: {dist:.2f} meter")
            if dist <= 200:
                with st.form("absen_form"):
                    j = st.selectbox("Jenis Presensi", ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                    f = st.camera_input("Ambil Foto")
                    if st.form_submit_button("Kirim Presensi") and f:
                        df_p = load_data("presensi")
                        new_p = pd.DataFrame([{"nama": u['nama'], "kelas": u['kelas'], "jenis": j, "waktu": now_dt.strftime("%Y-%m-%d %H:%M:%S"), "foto_absen": process_photo(f)}])
                        conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True))
                        st.success("Presensi Berhasil!")
            else: st.error("Anda berada di luar jangkauan radius sekolah!")

    # --- TUGAS ---
    elif L['tugas'] in choice:
        st.subheader("📚 Manajemen Tugas")
        if u['role'] == "Siswa":
            df_t = load_data("tugas", ttl="5s")
            df_s = load_data("tugas_selesai", ttl="5s")
            my_t = df_t[df_t['kelas'] == u['kelas']]
            for _, r in my_t.iterrows():
                with st.expander(f"📖 {r['judul_tugas']}"):
                    st.write(r['deskripsi'])
                    if st.button(f"Selesaikan: {r['judul_tugas']}", key=r['judul_tugas']):
                        new_s = pd.DataFrame([{"nama": u['nama'], "id_tugas": r['judul_tugas'], "waktu": now_dt.strftime("%Y-%m-%d %H:%M")}])
                        conn.update(worksheet="tugas_selesai", data=pd.concat([df_s, new_s], ignore_index=True))
                        st.success("Tugas ditandai selesai!")
        else: # Guru
            with st.form("tambah_tugas"):
                jt = st.text_input("Judul Tugas"); dtg = st.text_area("Deskripsi"); kt = st.selectbox("Untuk Kelas", list_kelas)
                if st.form_submit_button("Posting Tugas"):
                    df_t = load_data("tugas")
                    new_t = pd.DataFrame([{"judul_tugas": jt, "deskripsi": dtg, "kelas": kt}])
                    conn.update(worksheet="tugas", data=pd.concat([df_t, new_t], ignore_index=True))
            
            st.write("---")
            df_done = load_data("tugas_selesai", ttl="5s")
            st.write("Siswa Selesai Tugas:")
            st.dataframe(df_done, use_container_width=True)
            st.download_button("📥 Export Excel (Tugas)", df_done.to_csv(index=False).encode('utf-8'), "rekap_tugas.csv", "text/csv")

    # --- SPP ---
    elif L['spp'] in choice:
        st.subheader("💰 Informasi SPP")
        st.info(f"👤 **Nama Siswa:** {u['nama']}")
        st.success("✅ Belum ada tagihan atau tunggakan SPP.")

    # --- LAPORAN (GURU/TU) ---
    elif L['lapor'] in choice:
        st.subheader("📊 Laporan Presensi")
        df_p = load_data("presensi", ttl="5s")
        if not df_p.empty:
            df_p['Status'] = df_p.apply(lambda x: get_attendance_status(x['jenis'], x['waktu']), axis=1)
            def color_st(v): return 'color: red; font-weight: bold' if v == 'Terlambat' else ''
            st.dataframe(df_p.style.applymap(color_st, subset=['Status']), use_container_width=True)

    if st.sidebar.button(L['out']): st.session_state.logged_in_user = None; st.rerun()

# --- RUN APP ---
st.markdown(f"<h1 class='header-text'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='slogan'>Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan</p>", unsafe_allow_html=True)
st.markdown(f"<div class='clock-text'>🗓️ {datetime.now(jakarta_tz).strftime('%A, %d %B %Y | %H:%M:%S')} WIB</div>", unsafe_allow_html=True)

if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
