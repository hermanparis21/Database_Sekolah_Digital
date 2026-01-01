import streamlit as st
import pandas as pd
from datetime import datetime
import io
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Sekolah Digital", layout="wide", page_icon="🎓")

# --- 2. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    # Membersihkan cache agar data selalu terbaru
    return conn.read(worksheet=sheet_name, ttl="0s")

# --- 3. FUNGSI HELPER ---
def color_status(val):
    if val in ['TERLAMBAT', 'TELAT', 'Terlalu Awal']:
        return 'color: red; font-weight: bold'
    return 'color: green'

# --- 4. AUTH SESSION ---
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# --- 5. TAMPILAN LOGIN & REGISTRASI ---
def show_auth():
    st.markdown("<h1 style='text-align: center; color: #059669;'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
    
    if st.button("🔄 Refresh Database"):
        st.cache_data.clear()
        st.rerun()

    tab1, tab2 = st.tabs(["🔑 Masuk", "📝 Registrasi"])
    
    with tab1:
        with st.form("login_form"):
            u_nama_input = st.text_input("Nama Lengkap")
            u_pass_input = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                df_users = load_data("users")
                user_match = df_users[(df_users['nama'].astype(str).str.strip() == u_nama_input.strip()) & 
                                      (df_users['password'].astype(str) == u_pass_input)]
                if not user_match.empty:
                    st.session_state.logged_in_user = user_match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Nama atau Password salah!")

    with tab2:
        with st.form("reg_form"):
            role = st.selectbox("Daftar Sebagai", ["Siswa", "Guru", "Admin TU"])
            new_nama = st.text_input("Nama Lengkap")
            new_pass = st.text_input("Buat Password", type="password")
            new_nik = st.text_input("NIK (16 Digit - Wajib Guru/Admin)")
            new_kelas = st.selectbox("Kelas", ["X-A", "X-B", "XI-A", "XI-B", "XII-A", "XII-B"]) if role == "Siswa" else "-"
            
            if st.form_submit_button("Daftar"):
                if role in ["Guru", "Admin TU"] and len(new_nik) != 16:
                    st.error("NIK harus 16 digit!")
                elif new_nama and new_pass:
                    df_users = load_data("users")
                    new_data = pd.DataFrame([{"nama": new_nama, "password": new_pass, "role": role, "kelas": new_kelas, "nik": new_nik}])
                    updated_df = pd.concat([df_users, new_data], ignore_index=True)
                    conn.update(worksheet="users", data=updated_df)
                    st.cache_data.clear()
                    st.success("Registrasi Berhasil!")

# --- 6. DASHBOARD UTAMA ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    st.sidebar.info(f"Role: {user['role']}")
    
    menu = ["🏠 Beranda", "📍 Presensi", "📖 Lihat Nilai"]
    if user['role'] == "Guru": menu.append("📝 Input Nilai")
    if user['role'] in ["Guru", "Admin TU"]: menu.append("📊 Laporan")
    
    choice = st.sidebar.radio("Menu Navigasi", menu)

    # --- FITUR PRESENSI (UPDATE TERBARU) ---
    if choice == "📍 Presensi":
        st.header("📍 Presensi Mandiri Siswa")
        
        # Lokasi Sekolah
        target_loc = (-7.2164697698622335, 109.64013014754921)
        loc = get_geolocation()
        
        if loc:
            user_loc = (loc['coords']['latitude'], loc['coords']['longitude'])
            jarak = geodesic(user_loc, target_loc).meters
            
            if jarak > 100:
                st.error(f"❌ Jarak Anda {int(jarak)}m. Anda harus berada radius 100m dari sekolah!")
            else:
                st.success("✅ Lokasi Terverifikasi (Di Area Sekolah)")
                
                model_absen = st.selectbox("Pilih Jenis Presensi", ["Masuk Sekolah", "Sholat Dhuha", "Sholat Dzuhur", "Pulang"])
                now = datetime.now().time()
                status = "Tepat Waktu"
                is_late = False

                # Logika Waktu
                if model_absen == "Masuk Sekolah":
                    if not (datetime.time(6,0) <= now <= datetime.time(7,30)):
                        status, is_late = "TERLAMBAT", True
                elif model_absen == "Sholat Dhuha":
                    if not (datetime.time(7,0) <= now <= datetime.time(8,15)):
                        status, is_late = "TELAT", True
                elif model_absen == "Sholat Dzuhur":
                    if not (datetime.time(11,30) <= now <= datetime.time(13,0)):
                        status, is_late = "TELAT", True
                elif model_absen == "Pulang":
                    if now < datetime.time(14,30):
                        st.warning("Belum jam pulang!")
                        return

                if is_late:
                    st.markdown(f"<h2 style='color:red;'><b>⚠️ {status}</b></h2>", unsafe_allow_html=True)
                
                img_file = st.camera_input("Ambil Foto Selfie")
                
                if st.button("Kirim Presensi") and img_file:
                    df_p = load_data("presensi")
                    data_baru = pd.DataFrame([{
                        "nama": user['nama'], "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "jenis": model_absen, "status": status, "jarak": f"{int(jarak)}m"
                    }])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, data_baru], ignore_index=True))
                    st.balloons()
                    st.success("Presensi Berhasil Disimpan!")
        else:
            st.warning("Menunggu izin GPS browser...")

    # --- FITUR INPUT NILAI (GURU) ---
    elif choice == "📝 Input Nilai":
        st.header("📝 Input Nilai")
        df_siswa = load_data("users")
        df_siswa = df_siswa[df_siswa['role'] == 'Siswa']
        with st.form("n_form"):
            s_nama = st.selectbox("Siswa", df_siswa['nama'].tolist())
            mapel = st.selectbox("Mapel", ["Matematika", "PAI", "B. Indonesia"])
            skor = st.number_input("Nilai", 0, 100)
            if st.form_submit_button("Simpan"):
                df_n = load_data("nilai")
                new_n = pd.DataFrame([{"nama_siswa": s_nama, "mapel": mapel, "nilai": skor}])
                conn.update(worksheet="nilai", data=pd.concat([df_n, new_n], ignore_index=True))
                st.success("Nilai tersimpan!")

    elif st.sidebar.button("🚪 Keluar"):
        st.session_state.logged_in_user = None
        st.rerun()

# --- RUN ---
if st.session_state.logged_in_user is None:
    show_auth()
else:
    show_dashboard()
