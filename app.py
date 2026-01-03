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

# --- 1. KONFIGURASI ---
jakarta_tz = pytz.timezone('Asia/Jakarta')
SCHOOL_LOC = (-7.2164697698622335, 109.64013014754921)

st.set_page_config(page_title="SMA Muhammadiyah 4 Banjarnegara", layout="wide", page_icon="🎓")

# CSS Styling (Status Terlambat dibuat BOLD & MERAH kembali)
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #059669; color: white; height: 3em; }
    .clock-text { text-align: center; font-weight: bold; font-size: 1.1em; color: #1e293b; background: #f1f5f9; padding: 10px; border-radius: 15px; border: 1px solid #cbd5e1; margin-bottom: 20px; }
    .header-text { text-align: center; color: #059669; margin-bottom: 0px; font-size: 2em; }
    .slogan { text-align: center; font-style: italic; color: #475569; margin-bottom: 10px; font-size: 1em; }
    .notif-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #059669; background: #f0fdf4; }
    .terlambat-text { color: #dc2626; font-weight: bold; }
    .highlight-sholat { background: #fef9c3; border: 2px solid #facc15; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KONEKSI DATA ---
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

# --- 3. STATE & UI ---
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
L = {"slogan": "Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan", "login": "Masuk", "reg": "Registrasi", "nama": "Nama Lengkap", "pass": "Password", "absen_h": "📍 Presensi", "tugas": "📚 Tugas", "lapor": "📊 Laporan", "spp": "💰 SPP", "out": "Keluar", "broadcast": "📢 Broadcast"}
list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

st.markdown(f"<h1 class='header-text'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='slogan'>{L['slogan']}</p>", unsafe_allow_html=True)
now_dt = datetime.now(jakarta_tz)
st.markdown(f"<div class='clock-text'>🗓️ {now_dt.strftime('%A, %d %B %Y')} | ⏰ {now_dt.strftime('%H:%M:%S')} WIB</div>", unsafe_allow_html=True)

# --- 4. DASHBOARD ---
def show_dashboard():
    u = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {u['nama']}")
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}", L['spp']]
    if u['role'] in ["Guru", "Admin TU"]: menu_opt += [L['broadcast'], L['lapor']]
    choice = st.sidebar.radio("Menu", menu_opt)

    if choice == "🏠 Home":
        st.subheader(f"Dashboard {u['role']}")
        
        # JADWAL SHOLAT HIGHLIGHT HARI INI
        st.markdown(f"""<div class='highlight-sholat'>
            <b>🕌 Jadwal Sholat Hari Ini - Banjarnegara</b><br>
            <span style='font-size:1.2em;'>Subuh: 04:15 | Dzuhur: 11:52 | Ashar: 15:18 | Maghrib: 18:07 | Isya: 19:22</span>
        </div>""", unsafe_allow_html=True)

        with st.expander("📅 Jadwal Sholat Bulan Ini"):
            # Simulasi Jadwal Satu Bulan
            data_sholat = {"Tanggal": [f"{i} Jan" for i in range(1, 32)], "Subuh": ["04:15"]*31, "Dzuhur": ["11:52"]*31, "Ashar": ["15:18"]*31, "Maghrib": ["18:07"]*31, "Isya": ["19:22"]*31}
            st.dataframe(pd.DataFrame(data_sholat), hide_index=True)

        # NOTIFIKASI / BROADCAST (Siswa)
        if u['role'] == "Siswa":
            df_bc = load_data("broadcast", ttl="5s")
            if not df_bc.empty:
                rel_bc = df_bc[(df_bc['target'] == "Semua Kelas") | (df_bc['target'] == u['kelas'])]
                for _, b in rel_bc.iterrows():
                    st.markdown(f"<div class='notif-box'><b>{b['judul']}</b><br>{b['isi']}<br><small>📅 {b['tanggal']} | 📍 {b['tempat']}</small></div>", unsafe_allow_html=True)

    elif choice == L['spp']:
        st.subheader(L['spp'])
        st.info(f"👤 **Nama Siswa:** {u['nama']}")
        st.success("✅ Saat ini belum ada tagihan atau tunggakan SPP untuk akun Anda.")

    elif choice == f"{L['tugas']}":
        st.subheader(L['tugas'])
        df_t = load_data("tugas", ttl="5s"); df_done = load_data("tugas_selesai", ttl="5s")
        
        if u['role'] == "Guru":
            st.subheader("Daftar Siswa Selesai")
            if not df_done.empty: 
                st.dataframe(df_done[['nama', 'kelas', 'waktu']])
                # MENU EXPORT EXCEL
                csv = df_done.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export ke CSV/Excel", data=csv, file_name="tugas_selesai.csv", mime="text/csv")
        else:
            # Role Siswa: Munculkan riwayat tugas selesai
            st.subheader("✅ Riwayat Tugas Selesai Anda")
            if not df_done.empty:
                my_done = df_done[df_done['nama'] == u['nama']]
                st.table(my_done[['id_tugas', 'waktu']])

    elif choice == L['lapor']:
        st.header(L['lapor'])
        df_p = load_data("presensi", ttl="5s")
        if not df_p.empty:
            df_p['Status'] = df_p.apply(lambda x: get_attendance_status(x['jenis'], x['waktu']), axis=1)
            
            # Formating: Terlambat Bold Merah
            def color_status(val):
                color = 'red; font-weight: bold' if val == 'Terlambat' else 'black'
                return f'color: {color}'
            
            st.dataframe(df_p.style.applymap(color_status, subset=['Status']), width='stretch')

    elif choice == L['broadcast']:
        st.subheader("Kirim Pesan Broadcast")
        # Pastikan Sheet "broadcast" ada di GSheets Anda untuk menghindari error WorksheetNotFound
        with st.form("bc_form"):
            t_j = st.text_input("Judul"); t_i = st.text_area("Isi")
            t_target = st.selectbox("Target", ["Semua Kelas"] + list_kelas)
            if st.form_submit_button("📢 Kirim"):
                df_b = load_data("broadcast")
                new_b = pd.DataFrame([{"judul": t_j, "isi": t_i, "target": t_target, "tanggal": now_dt.strftime("%Y-%m-%d")}])
                try:
                    conn.update(worksheet="broadcast", data=pd.concat([df_b, new_b], ignore_index=True))
                    st.success("Terkirim!")
                except Exception as e:
                    st.error(f"Gagal! Pastikan tab 'broadcast' ada di Google Sheets. Error: {e}")

    if st.sidebar.button(L['out']): st.session_state.logged_in_user = None; st.rerun()

# --- 5. AUTH (Fungsi Minimalis) ---
def show_auth():
    with st.form("l_f"):
        u = st.text_input(L['nama']).title(); p = st.text_input(L['pass'], type="password")
        if st.form_submit_button(L['login']):
            df_u = load_data("users")
            m = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p.strip())]
            if not m.empty: st.session_state.logged_in_user = m.iloc[0].to_dict(); st.rerun()
            else: st.error("Login Gagal")

if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
