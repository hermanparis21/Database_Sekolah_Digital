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

# --- 1. KONFIGURASI DASAR ---
jakarta_tz = pytz.timezone('Asia/Jakarta')
SCHOOL_LOC = (-7.2164697698622335, 109.64013014754921)

st.set_page_config(page_title="SMA Muhammadiyah 4 Banjarnegara", layout="wide", page_icon="🎓")

# --- 2. KONEKSI DATA & FUNGSI HELPER ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, ttl="0s"):
    try:
        df = conn.read(worksheet=sheet_name, ttl=ttl)
        df.columns = df.columns.str.strip() # Pembersihan nama kolom
        return df
    except Exception as e:
        return pd.DataFrame()

def save_data(sheet_name, data):
    try:
        existing_df = load_data(sheet_name)
        updated_df = pd.concat([existing_df, data], ignore_index=True)
        conn.update(worksheet=sheet_name, data=updated_df)
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke {sheet_name}: {e}")
        return False

def process_photo(uploaded_file):
    img = Image.open(uploaded_file).convert("RGB")
    img.thumbnail((300, 300)) 
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=50)
    return base64.b64encode(buf.getvalue()).decode()

def get_status_absen(jenis, waktu_str):
    try:
        waktu_obj = datetime.strptime(waktu_str, "%Y-%m-%d %H:%M:%S").time()
        if jenis == "Masuk":
            return "Tepat Waktu" if waktu_obj <= dt.time(7, 15) else "Terlambat"
        elif jenis == "Dhuha":
            return "Tepat Waktu" if waktu_obj <= dt.time(8, 0) else "Terlambat"
        return "Hadir"
    except:
        return "-"

# --- 3. SESSION STATE ---
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

# --- 4. TAMPILAN OTENTIKASI ---
def show_auth():
    st.markdown("### 🔑 Akses Sistem")
    tab1, tab2 = st.tabs(["Masuk", "Registrasi Siswa/Guru"])
    
    with tab1:
        with st.form("form_login"):
            u = st.text_input("Nama Lengkap (Sesuai Registrasi)").title()
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                df_u = load_data("users")
                if not df_u.empty:
                    match = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p.strip())]
                    if not match.empty:
                        st.session_state.logged_in_user = match.iloc[0].to_dict()
                        st.rerun()
                st.error("Nama atau Password salah!")

    with tab2:
        with st.form("form_reg"):
            role = st.selectbox("Daftar Sebagai", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input("Nama Lengkap").title()
            pw = st.text_input("Buat Password")
            id_val = st.text_input("NIS (untuk Siswa) / NIK (untuk Guru)")
            kls = st.selectbox("Pilih Kelas", list_kelas) if role == "Siswa" else "-"
            f_ref = st.camera_input("Ambil Foto Wajah untuk Referensi")
            
            if st.form_submit_button("Daftar Sekarang"):
                if n and pw and f_ref:
                    new_u = pd.DataFrame([{
                        "nama": n, "password": pw, "role": role, 
                        "kelas": kls, "id_unik": id_val, 
                        "foto_reg": process_photo(f_ref)
                    }])
                    if save_data("users", new_u):
                        st.success("Registrasi Berhasil! Silakan klik tab 'Masuk'.")
                else:
                    st.warning("Mohon lengkapi data dan ambil foto!")

# --- 5. DASHBOARD UTAMA ---
def show_dashboard():
    u = st.session_state.logged_in_user
    now = datetime.now(jakarta_tz)
    
    # Sidebar
    st.sidebar.markdown(f"### 👤 {u['nama']}")
    st.sidebar.info(f"Role: {u['role']} | {u['kelas']}")
    
    menu = ["🏠 Home", "📍 Presensi Kehadiran", "📚 Tugas Sekolah", "💰 Status SPP"]
    if u['role'] in ["Guru", "Admin TU"]:
        menu += ["📢 Kirim Broadcast", "📊 Laporan & Audit Wajah"]
    
    choice = st.sidebar.radio("Navigasi Menu", menu)

    # --- MENU: HOME ---
    if choice == "🏠 Home":
        st.subheader("Informasi Sekolah")
        
        # Jadwal Sholat (Data Banjarnegara)
        st.markdown(f"""
        <div style="background-color:#f0fdf4; padding:15px; border-radius:10px; border:1px solid #bbf7d0;">
            <h4 style="margin:0; color:#166534;">🕌 Jadwal Sholat Banjarnegara Hari Ini</h4>
            <p style="margin:5px 0 0 0;">Subuh: 04:15 | Dzuhur: 11:53 | Ashar: 15:19 | Maghrib: 18:08 | Isya: 19:23</p>
        </div>
        """, unsafe_allow_html=True)

        if u['role'] == "Siswa":
            # Cek Notifikasi dari Guru
            df_notif = load_data("audit_notif", ttl="2s")
            if not df_notif.empty:
                my_n = df_notif[df_notif['nama'] == u['nama']].tail(1)
                if not my_n.empty:
                    color = "#ef4444" if "⚠️" in my_n.iloc[0]['pesan'] else "#059669"
                    st.markdown(f"<div style='border-left:5px solid {color}; padding:10px; background:#fff1f2;'>{my_n.iloc[0]['pesan']}</div>", unsafe_allow_html=True)

            # Rekap Tugas
            df_t = load_data("tugas"); df_s = load_data("tugas_selesai")
            col1, col2 = st.columns(2)
            col1.metric("📚 Tugas Tersedia", len(df_t[df_t['kelas'] == u['kelas']]) if not df_t.empty else 0)
            col2.metric("✅ Selesai Dikerjakan", len(df_s[df_s['nama'] == u['nama']]) if not df_s.empty else 0)

        else: # Home Guru/Admin
            df_p = load_data("presensi", ttl="2s")
            df_ts = load_data("tugas_selesai")
            today = now.strftime("%Y-%m-%d")
            p_today = df_p[df_p['waktu'].str.contains(today)] if not df_p.empty else pd.DataFrame()
            
            st.markdown("#### Statistik Kehadiran Hari Ini")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("🌅 Masuk", len(p_today[p_today['jenis'] == "Masuk"]))
            c2.metric("🕌 Dhuha", len(p_today[p_today['jenis'] == "Dhuha"]))
            c3.metric("☀️ Dzuhur", len(p_today[p_today['jenis'] == "Dzuhur"]))
            c4.metric("🏠 Pulang", len(p_today[p_today['jenis'] == "Pulang"]))
            c5.metric("📝 Tugas", len(df_ts[df_ts['waktu'].str.contains(today)]) if not df_ts.empty else 0)

    # --- MENU: PRESENSI ---
    elif choice == "📍 Presensi Kehadiran":
        st.subheader("Input Kehadiran")
        loc = get_geolocation()
        if loc:
            lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
            dist = geodesic(SCHOOL_LOC, (lat, lon)).meters
            st.write(f"📍 Jarak Anda ke Sekolah: {dist:.2f} meter")
            
            if dist <= 200:
                with st.form("form_absen"):
                    j = st.selectbox("Pilih Sesi Absen", ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                    f = st.camera_input("Ambil Foto Wajah")
                    if st.form_submit_button("Kirim Absensi") and f:
                        new_abs = pd.DataFrame([{
                            "nama": u['nama'], "kelas": u['kelas'], 
                            "jenis": j, "waktu": now.strftime("%Y-%m-%d %H:%M:%S"),
                            "foto_absen": process_photo(f)
                        }])
                        if save_data("presensi", new_abs):
                            st.success("Absen Berhasil Disimpan!")
            else:
                st.error("Maaf, Anda harus berada di radius 200m dari sekolah untuk absen.")

    # --- MENU: TUGAS ---
    elif choice == "📚 Tugas Sekolah":
        if u['role'] == "Siswa":
            st.subheader("Daftar Tugas Anda")
            df_t = load_data("tugas")
            if not df_t.empty:
                my_t = df_t[df_t['kelas'] == u['kelas']]
                for _, r in my_t.iterrows():
                    with st.expander(f"📝 {r['judul_tugas']}"):
                        st.write(r['deskripsi'])
                        if st.button(f"Selesai Mengerjakan: {r['judul_tugas']}"):
                            save_data("tugas_selesai", pd.DataFrame([{
                                "nama": u['nama'], "id_tugas": r['judul_tugas'], 
                                "waktu": now.strftime("%Y-%m-%d %H:%M")
                            }]))
                            st.success("Tugas Berhasil Dicatat!")
        else:
            st.subheader("Manajemen Tugas Guru")
            with st.form("tambah_tugas"):
                jt = st.text_input("Judul Tugas")
                ds = st.text_area("Deskripsi/Instruksi")
                ks = st.selectbox("Ditujukan untuk Kelas", list_kelas)
                if st.form_submit_button("Posting Tugas"):
                    save_data("tugas", pd.DataFrame([{"judul_tugas": jt, "deskripsi": ds, "kelas": ks}]))
                    st.success("Tugas berhasil diposting!")

    # --- MENU: BROADCAST ---
    elif choice == "📢 Kirim Broadcast":
        st.subheader("Kirim Pesan ke Dashboard Siswa")
        with st.form("f_bc"):
            msg = st.text_area("Tulis Pengumuman...")
            if st.form_submit_button("Kirim Sekarang"):
                save_data("broadcast", pd.DataFrame([{
                    "pengirim": u['nama'], "pesan": msg, "waktu": now.strftime("%Y-%m-%d %H:%M")
                }]))
                st.success("Broadcast berhasil dikirim!")

    # --- MENU: LAPORAN & AUDIT ---
    elif choice == "📊 Laporan & Audit Wajah":
        st.subheader("Audit Kejujuran Presensi")
        df_p = load_data("presensi", ttl="2s")
        df_u = load_data("users")
        
        if not df_p.empty:
            sel_nama = st.selectbox("Pilih Siswa untuk Audit", df_p['nama'].unique())
            u_ref = df_u[df_u['nama'] == sel_nama]
            u_abs = df_p[df_p['nama'] == sel_nama].tail(1)
            
            if not u_ref.empty and not u_abs.empty:
                c1, c2 = st.columns(2)
                c1.image(f"data:image/jpeg;base64,{u_ref.iloc[0]['foto_reg']}", caption="Foto Referensi (Registrasi)")
                c2.image(f"data:image/jpeg;base64,{u_abs.iloc[0]['foto_absen']}", caption="Foto Saat Absen Terakhir")
                
                ca1, ca2 = st.columns(2)
                if ca1.button("✅ Validasi (Foto Sama)"):
                    save_data("audit_notif", pd.DataFrame([{"nama": sel_nama, "pesan": "✅ Absensi Anda dinyatakan VALID.", "status": "Valid"}]))
                    st.success("Siswa telah divalidasi.")
                if ca2.button("⚠️ Kirim Peringatan (Foto Beda)"):
                    save_data("audit_notif", pd.DataFrame([{"nama": sel_nama, "pesan": "⚠️ Peringatan: Wajah absen tidak sesuai referensi!", "status": "Peringatan"}]))
                    st.error("Peringatan dikirim ke siswa.")
            
            st.divider()
            st.write("Daftar Riwayat Presensi:")
            st.dataframe(df_p)

    # Tombol Keluar
    if st.sidebar.button("🚪 Keluar"):
        st.session_state.logged_in_user = None
        st.rerun()

# --- HEADER APLIKASI ---
st.markdown("<h1 style='text-align: center; color: #059669;'>🎓 MUHAMKA DIGITAL SCHOOL</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-style: italic;'>SMA Muhammadiyah 4 Banjarnegara</p>", unsafe_allow_html=True)

if st.session_state.logged_in_user is None:
    show_auth()
else:
    show_dashboard()
