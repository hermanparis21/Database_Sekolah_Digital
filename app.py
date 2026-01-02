import streamlit as st
import pandas as pd
from datetime import datetime
import datetime as dt
import io
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Sekolah Digital", layout="wide", page_icon="🎓")

# --- 2. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl="0s")

# --- 3. FUNGSI AUTH ---
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

def show_auth():
    st.markdown("<h1 style='text-align: center; color: #059669;'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Database"):
        st.cache_data.clear()
        st.rerun()

    tab1, tab2 = st.tabs(["🔑 Masuk", "📝 Registrasi"])
    with tab1:
        with st.form("login"):
            u_nama = st.text_input("Nama Lengkap")
            u_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                df_u = load_data("users")
                match = df_u[(df_u['nama'].astype(str).str.strip() == u_nama.strip()) & (df_u['password'].astype(str) == u_pass)]
                if not match.empty:
                    st.session_state.logged_in_user = match.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Nama/Password Salah")

    with tab2:
        with st.form("reg"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n_nama = st.text_input("Nama Lengkap")
            n_pass = st.text_input("Password")
            n_nik = st.text_input("NIK (16 Digit)")
            n_kls = st.selectbox("Kelas", ["X-A", "X-B", "XI-A", "XI-B", "XII-A", "XII-B"]) if role == "Siswa" else "-"
            if st.form_submit_button("Daftar"):
                df_u = load_data("users")
                new_row = pd.DataFrame([{"nama": n_nama, "password": n_pass, "role": role, "kelas": n_kls, "nik": n_nik}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_row], ignore_index=True))
                st.cache_data.clear()
                st.success("Berhasil Daftar!")

# --- 4. DASHBOARD ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    choice = st.sidebar.radio("Navigasi", ["🏠 Beranda", "📍 Presensi", "📖 Lihat Nilai", "📝 Input Nilai", "📊 Laporan"])

    if choice == "📍 Presensi":
        st.header("📍 Presensi Mandiri (GPS & Selfie)")
        
        # Koordinat Sekolah
        sekolah_coords = (-7.2164697698622335, 109.64013014754921)
        
        st.write("Sedang mencari lokasi Anda...")
        loc = get_geolocation()
        
        if loc:
            user_coords = (loc['coords']['latitude'], loc['coords']['longitude'])
            jarak = geodesic(user_coords, sekolah_coords).meters
            
            # Tampilkan Map Kecil
            map_data = pd.DataFrame({'lat': [user_coords[0]], 'lon': [user_coords[1]]})
            st.map(map_data)

            if jarak > 100:
                st.error(f"❌ Jarak Anda {int(jarak)}m dari sekolah. Presensi hanya boleh dalam radius 100m.")
            else:
                st.success(f"✅ Lokasi Terverifikasi ({int(jarak)}m dari sekolah)")
                
                model = st.selectbox("Jenis Presensi", ["Masuk Sekolah", "Sholat Dhuha", "Sholat Dzuhur", "Pulang"])
                now = datetime.now().time()
                status, is_late = "Tepat Waktu", False

                # Logika Waktu
                if model == "Masuk Sekolah":
                    if not (dt.time(6,0) <= now <= dt.time(7,30)): status, is_late = "TERLAMBAT", True
                elif model == "Sholat Dhuha":
                    if not (dt.time(7,0) <= now <= dt.time(8,15)): status, is_late = "TELAT", True
                elif model == "Sholat Dzuhur":
                    if not (dt.time(11,30) <= now <= dt.time(13,0)): status, is_late = "TELAT", True
                elif model == "Pulang":
                    if now < dt.time(14,30):
                        st.warning("Belum jam pulang (14:30)"); return

                if is_late:
                    st.markdown(f"<h2 style='color:red;'><b>⚠️ {status}</b></h2>", unsafe_allow_html=True)
                
                # FITUR SELFIE
                st.info("Silakan selfie di depan gerbang atau masjid sekolah.")
                img = st.camera_input("Ambil Foto Selfie")
                
                if st.button("Kirim Presensi") and img:
                    df_p = load_data("presensi")
                    new_p = pd.DataFrame([{
                        "nama": user['nama'], 
                        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "jenis": model, 
                        "status": status, 
                        "jarak": f"{int(jarak)}m"
                    }])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True))
                    st.balloons()
                    st.success("Presensi Berhasil Disimpan!")
        else:
            st.warning("Mohon aktifkan GPS dan izinkan akses lokasi di browser Anda.")

    elif choice == "📝 Input Nilai" and user['role'] == "Guru":
        # (Kode input nilai Anda sebelumnya di sini...)
        st.write("Fitur Input Nilai")

    if st.sidebar.button("Keluar"):
        st.session_state.logged_in_user = None
        st.rerun()

# --- RUN ---
if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
