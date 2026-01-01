import streamlit as st
import pandas as pd
from datetime import datetime
import io
from streamlit_gsheets import GSheetsConnection

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Sekolah Digital", layout="wide", page_icon="🎓")

# --- 2. KONEKSI GOOGLE SHEETS ---
# Pastikan Anda sudah mengatur Secrets di Streamlit Cloud (st.secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    return conn.read(worksheet=sheet_name)

# --- 3. FUNGSI HELPER ---
def color_status(val):
    if val in ['Terlambat', 'Terlalu Awal']:
        return 'color: red; font-weight: bold'
    return 'color: green'

# --- 4. AUTH SESSION ---
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# --- 5. TAMPILAN LOGIN & REGISTRASI ---
def show_auth():
    st.markdown("<h1 style='text-align: center; color: #059669;'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
    
    # Tombol Refresh Data (Penting agar user baru terbaca)
    if st.button("🔄 Refresh Database"):
        st.cache_data.clear()
        st.rerun()

    tab1, tab2 = st.tabs(["🔑 Masuk", "📝 Registrasi"])
    
    with tab1:
        st.subheader("Login Pengguna")
        with st.form("login_form"):
            # Menggunakan text_input (manual), bukan selectbox
            u_nama_input = st.text_input("Nama Lengkap")
            u_pass_input = st.text_input("Password", type="password")
            
            submit_login = st.form_submit_button("Masuk")
            
            if submit_login:
                # Ambil data terbaru dari Google Sheets
                df_users = load_data("users")
                
                # Cek apakah nama dan password cocok
                # Menggunakan .strip() untuk menghindari spasi tak sengaja
                user_match = df_users[
                    (df_users['nama'].astype(str).str.strip() == u_nama_input.strip()) & 
                    (df_users['password'].astype(str) == u_pass_input)
                ]
                
                if not user_match.empty:
                    st.session_state.logged_in_user = user_match.iloc[0].to_dict()
                    st.success(f"Selamat datang, {u_nama_input}!")
                    st.rerun()
                else:
                    st.error("❌ Nama atau Password salah, atau user belum terdaftar.")

    with tab2:
        st.subheader("Pendaftaran User")
        # (Bagian form pendaftaran tetap sama seperti sebelumnya)
        with st.form("reg_form"):
            role = st.selectbox("Daftar Sebagai", ["Siswa", "Guru", "Admin TU"])
            new_nama = st.text_input("Nama Lengkap")
            new_pass = st.text_input("Buat Password", type="password")
            new_nik = st.text_input("NIK (16 Digit - Wajib Guru/Admin)")
            new_kelas = st.selectbox("Kelas", ["X-A", "X-B", "XI-A", "XI-B", "XII-A", "XII-B"]) if role == "Siswa" else "-"
            
            if st.form_submit_button("Daftar"):
                df_users = load_data("users") # Cek data lama dulu
                if role in ["Guru", "Admin TU"] and len(new_nik) != 16:
                    st.error("NIK harus 16 digit!")
                elif new_nama and new_pass:
                    new_data = pd.DataFrame([{"nama": new_nama, "password": new_pass, "role": role, "kelas": new_kelas, "nik": new_nik}])
                    updated_df = pd.concat([df_users, new_data], ignore_index=True)
                    conn.update(worksheet="users", data=updated_df)
                    st.cache_data.clear() # Hapus cache agar user baru langsung bisa login
                    st.success("✅ Registrasi Berhasil! Silakan klik tab 'Masuk'.")
                else:
                    st.error("Data tidak lengkap.")

# --- 6. DASHBOARD UTAMA ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    st.sidebar.write(f"Role: {user['role']}")
    
    menu = ["🏠 Beranda", "📍 Presensi"]
    if user['role'] == "Guru": menu.append("📝 Input Nilai")
    if user['role'] in ["Guru", "Admin TU"]: menu.append("📊 Laporan")
    if user['role'] == "Siswa": menu.append("📖 Lihat Nilai")
    
    choice = st.sidebar.radio("Menu Navigasi", menu)

    # --- FITUR INPUT NILAI (KHUSUS GURU) ---
    if choice == "📝 Input Nilai":
        st.header("📝 Form Input Nilai Siswa")
        df_siswa = load_data("users")
        df_siswa = df_siswa[df_siswa['role'] == 'Siswa']
        
        with st.form("nilai_form"):
            col1, col2 = st.columns(2)
            with col1:
                pilih_siswa = st.selectbox("Pilih Siswa", df_siswa['nama'].tolist())
                mapel = st.selectbox("Mata Pelajaran", ["Matematika", "B. Indonesia", "B. Inggris", "PAI", "Fisika", "Ekonomi"])
            with col2:
                jenis_ujian = st.selectbox("Jenis Nilai", ["Tugas", "UH", "UTS", "UAS"])
                skor = st.number_input("Input Nilai (0-100)", min_value=0, max_value=100)
            
            if st.form_submit_button("Simpan Nilai"):
                df_nilai = load_data("nilai")
                data_baru = pd.DataFrame([{
                    "nama_siswa": pilih_siswa,
                    "kelas": df_siswa[df_siswa['nama'] == pilih_siswa]['kelas'].values[0],
                    "mapel": mapel,
                    "jenis_ujian": jenis_ujian,
                    "nilai": skor,
                    "guru_penginput": user['nama']
                }])
                df_fix = pd.concat([df_nilai, data_baru], ignore_index=True)
                conn.update(worksheet="nilai", data=df_fix)
                st.success(f"Nilai {pilih_siswa} berhasil disimpan!")

    # --- FITUR LIHAT NILAI (KHUSUS SISWA) ---
    elif choice == "📖 Lihat Nilai":
        st.header("📖 Transkrip Nilai Anda")
        df_nilai = load_data("nilai")
        nilai_saya = df_nilai[df_nilai['nama_siswa'] == user['nama']]
        if nilai_saya.empty:
            st.info("Belum ada nilai yang diinput oleh Guru.")
        else:
            st.dataframe(nilai_saya, use_container_width=True)

    # --- FITUR LAPORAN (FILTER & EXPORT) ---
    elif choice == "📊 Laporan":
        st.header("📊 Laporan Keseluruhan")
        sub_menu = st.tabs(["Presensi", "Nilai"])
        
        with sub_menu[0]:
            df_p = load_data("presensi")
            if not df_p.empty:
                st.dataframe(df_p.style.applymap(color_status, subset=['status']), use_container_width=True)
                # Tombol Export Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_p.to_excel(writer, index=False)
                st.download_button("📥 Download Excel Presensi", data=buffer.getvalue(), file_name="presensi.xlsx")
        
        with sub_menu[1]:
            df_n = load_data("nilai")
            st.dataframe(df_n, use_container_width=True)

    # --- FITUR PRESENSI ---
    elif choice == "📍 Presensi":
        st.header("📍 Presensi Harian")
        if user['role'] == "Siswa":
            # (Logika presensi sama seperti sebelumnya, simpan ke conn.update)
            st.write("Fitur Presensi Siswa aktif...")
        else:
            st.write("Hanya Siswa yang dapat melakukan presensi.")

    if st.sidebar.button("🚪 Keluar"):
        st.session_state.logged_in_user = None
        st.rerun()

# --- RUN ---
if st.session_state.logged_in_user is None:
    show_auth()
else:
    show_dashboard()
