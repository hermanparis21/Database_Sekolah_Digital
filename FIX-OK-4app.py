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
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

def save_data(sheet_name, data):
    try:
        existing_df = load_data(sheet_name)
        updated_df = pd.concat([existing_df, data], ignore_index=True)
        conn.update(worksheet=sheet_name, data=updated_df)
        return True
    except Exception as e:
        st.error(f"Gagal simpan ke {sheet_name}: {e}")
        return False

def process_photo(uploaded_file):
    img = Image.open(uploaded_file).convert("RGB")
    img.thumbnail((300, 300)) 
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=50)
    return base64.b64encode(buf.getvalue()).decode()

def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Laporan')
    writer.close()
    return output.getvalue()

# --- 3. SESSION STATE ---
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

# --- 4. TAMPILAN OTENTIKASI ---
def show_auth():
    st.markdown("<h2 style='text-align: center; color: #059669;'>SMA Muhammadiyah 4 Banjarnegara</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #475569;'><i>'Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan'</i></p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Masuk Sistem", "📝 Registrasi Anggota"])
    with tab1:
        with st.form("l_f"):
            u = st.text_input("Nama Lengkap").title()
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                df_u = load_data("users")
                if not df_u.empty:
                    m = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p.strip())]
                    if not m.empty:
                        st.session_state.logged_in_user = m.iloc[0].to_dict()
                        st.rerun()
                st.error("Login Gagal! Pastikan Nama dan Password Benar.")
    with tab2:
        with st.form("r_f"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input("Nama Lengkap").title()
            pw = st.text_input("Password")
            id_v = st.text_input("NIS/NIK")
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            f_ref = st.camera_input("Ambil Foto Referensi Wajah")
            if st.form_submit_button("Daftar Sekarang"):
                if n and pw and f_ref:
                    new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_v, "foto_reg": process_photo(f_ref)}])
                    if save_data("users", new_u): st.success("Registrasi Berhasil! Silakan Masuk.")

# --- 5. DASHBOARD UTAMA ---
def show_dashboard():
    u = st.session_state.logged_in_user
    now = datetime.now(jakarta_tz)
    st.sidebar.markdown(f"### 👤 {u['nama']}")
    st.sidebar.info(f"{u['role']} | {u['kelas']}")
    
    menu = ["🏠 Home", "📍 Presensi Kehadiran", "📚 Tugas Sekolah", "💰 Status SPP"]
    if u['role'] in ["Guru", "Admin TU"]:
        menu += ["📢 Kirim Broadcast", "📊 Laporan & Audit"]
    
    choice = st.sidebar.radio("Navigasi Utama", menu)

    # --- MENU: HOME ---
    if choice == "🏠 Home":
        st.subheader(f"Dashboard {u['role']}")
        st.markdown(f"""<div style="background-color:#f0fdf4; padding:15px; border-radius:10px; border:1px solid #bbf7d0;">
            <h4 style="margin:0; color:#166534;">🕌 Jadwal Sholat Banjarnegara Hari Ini</h4>
            <p style="margin:5px 0 0 0;">Subuh: 04:15 | Dzuhur: 11:53 | Ashar: 15:19 | Maghrib: 18:08 | Isya: 19:23</p></div>""", unsafe_allow_html=True)

        if u['role'] == "Siswa":
            # REKAP TUGAS SISWA
            df_t = load_data("tugas")
            df_s = load_data("tugas_selesai")
            t_total = len(df_t[df_t['kelas'] == u['kelas']]) if not df_t.empty else 0
            t_done = len(df_s[df_s['nama'] == u['nama']]) if not df_s.empty else 0
            
            c1, c2 = st.columns(2)
            c1.metric("📚 Tugas Belum Selesai", t_total - t_done)
            c2.metric("✅ Tugas Sudah Selesai", t_done)

            # Audit Notif
            df_notif = load_data("audit_notif", ttl="2s")
            if not df_notif.empty:
                my_n = df_notif[df_notif['nama'] == u['nama']].tail(2)
                for _, n in my_n.iterrows():
                    st.toast(n['pesan'])

        else: # REKAP GURU & ADMIN
            df_p = load_data("presensi", ttl="2s")
            df_ts = load_data("tugas_selesai", ttl="2s")
            today = now.strftime("%Y-%m-%d")
            p_today = df_p[df_p['waktu'].str.contains(today)] if not df_p.empty else pd.DataFrame()
            
            st.markdown("#### Statistik Sekolah Hari Ini")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("🌅 Masuk", len(p_today[p_today['jenis'] == "Masuk"]))
            c2.metric("🕌 Dhuha", len(p_today[p_today['jenis'] == "Dhuha"]))
            c3.metric("☀️ Dzuhur", len(p_today[p_today['jenis'] == "Dzuhur"]))
            c4.metric("🏠 Pulang", len(p_today[p_today['jenis'] == "Pulang"]))
            c5.metric("📝 Tugas Selesai", len(df_ts[df_ts['waktu'].str.contains(today)]) if not df_ts.empty else 0)

    # --- MENU: PRESENSI ---
    elif choice == "📍 Presensi Kehadiran":
        st.subheader("Presensi Lokasi & Wajah")
        loc = get_geolocation()
        if loc:
            dist = geodesic(SCHOOL_LOC, (loc['coords']['latitude'], loc['coords']['longitude'])).meters
            st.write(f"📍 Jarak Anda: {dist:.2f}m dari Sekolah")
            if dist <= 200:
                with st.form("abs"):
                    j = st.selectbox("Pilih Sesi", ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                    f = st.camera_input("Foto Presensi")
                    if st.form_submit_button("Kirim Absensi") and f:
                        status = "Hadir"
                        if j == "Masuk" and now.time() > dt.time(7,15): status = "Terlambat"
                        save_data("presensi", pd.DataFrame([{"nama": u['nama'], "kelas": u['kelas'], "jenis": j, "waktu": now.strftime("%Y-%m-%d %H:%M:%S"), "status": status, "foto_absen": process_photo(f)}]))
                        st.success("Presensi Berhasil Dikirim!")
            else: st.error("Anda berada di luar radius sekolah!")

    # --- MENU: TUGAS ---
    elif choice == "📚 Tugas Sekolah":
        df_t = load_data("tugas")
        df_s = load_data("tugas_selesai")
        
        if u['role'] == "Siswa":
            t_tab1, t_tab2 = st.tabs(["📝 Belum Selesai", "✅ Sudah Selesai"])
            with t_tab1:
                my_t = df_t[df_t['kelas'] == u['kelas']] if not df_t.empty else pd.DataFrame()
                done_ids = df_s[df_s['nama'] == u['nama']]['id_tugas'].tolist() if not df_s.empty else []
                
                for _, r in my_t.iterrows():
                    if r['judul_tugas'] not in done_ids:
                        with st.expander(f"Tugas: {r['judul_tugas']}"):
                            st.write(r['deskripsi'])
                            st.caption(f"Deadline: {r.get('deadline','-')}")
                            if st.button(f"Tandai Selesai: {r['judul_tugas']}"):
                                save_data("tugas_selesai", pd.DataFrame([{"nama": u['nama'], "kelas": u['kelas'], "id_tugas": r['judul_tugas'], "waktu": now.strftime("%Y-%m-%d %H:%M")}]))
                                st.rerun()
            with t_tab2:
                my_done = df_s[df_s['nama'] == u['nama']] if not df_s.empty else pd.DataFrame()
                st.table(my_done)

        else: # Guru
            st.subheader("Input Tugas Baru")
            with st.form("t_t"):
                jt = st.text_input("Judul"); ds = st.text_area("Deskripsi")
                ks = st.selectbox("Kelas", list_kelas); dl = st.date_input("Deadline")
                if st.form_submit_button("Posting Tugas"):
                    save_data("tugas", pd.DataFrame([{"judul_tugas": jt, "deskripsi": ds, "kelas": ks, "deadline": str(dl)}]))
            
            st.subheader("Daftar Siswa Selesai Tugas")
            st.dataframe(df_s, use_container_width=True)

    # --- MENU: SPP ---
    elif choice == "💰 Status SPP":
        df_spp = load_data("spp", ttl="2s")
        if u['role'] == "Admin TU":
            st.subheader("Kelola Tagihan SPP")
            with st.form("spp_f"):
                sn = st.text_input("Nama/NIS Siswa")
                nom = st.number_input("Nominal Tagihan", min_value=0)
                bln = st.selectbox("Untuk Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
                ket = st.selectbox("Status", ["Menunggak", "Lunas"])
                if st.form_submit_button("Update Data SPP"):
                    save_data("spp", pd.DataFrame([{"nama": sn, "nominal": nom, "bulan": bln, "status": ket, "update_pada": now.strftime("%Y-%m-%d")}]))
            st.dataframe(df_spp)
        else:
            st.subheader("Informasi Tunggakan SPP")
            my_spp = df_spp[df_spp['nama'].str.contains(u['nama'], case=False)] if not df_spp.empty else pd.DataFrame()
            if not my_spp.empty:
                # Logika: Jika status terakhir Lunas, maka tunggakan 0
                latest = my_spp.tail(1).iloc[0]
                if latest['status'] == "Lunas":
                    st.success(f"Tagihan Bulan {latest['bulan']}: LUNAS (Rp 0)")
                else:
                    st.error(f"Tunggakan Bulan {latest['bulan']}: Rp {latest['nominal']:,}")
            else:
                st.info("Belum ada data tagihan SPP dari Admin TU.")

    # --- LAPORAN & EXPORT ---
    elif choice == "📊 Laporan & Audit":
        df_p = load_data("presensi", ttl="2s")
        if not df_p.empty:
            def highlight_terlambat(row):
                return ['background-color: #fee2e2; color: #b91c1c; font-weight: bold' if row.status == 'Terlambat' else '' for _ in row]
            st.dataframe(df_p.style.apply(highlight_terlambat, axis=1), use_container_width=True)
            st.download_button("📥 Export Presensi (Excel)", to_excel(df_p), "laporan_presensi.xlsx")

    if st.sidebar.button("🚪 Keluar"):
        st.session_state.logged_in_user = None
        st.rerun()

# --- HEADER SEKOLAH ---
st.markdown("<h1 style='text-align: center; color: #059669;'>SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #475569; font-size: 1.1em;'><i>Visi: Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan</i></p>", unsafe_allow_html=True)

if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
