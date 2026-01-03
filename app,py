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
    st.markdown("<h1 style='text-align: center; color: #059669;'>SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #475569; font-size: 1.2em;'><i>'Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan'</i></p>", unsafe_allow_html=True)
    
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
                st.error("Login Gagal! Cek Nama dan Password.")
    with tab2:
        with st.form("r_f"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input("Nama Lengkap").title()
            pw = st.text_input("Password")
            id_v = st.text_input("NIS/NIK")
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            f_ref = st.camera_input("Foto Referensi Wajah")
            if st.form_submit_button("Daftar"):
                if n and pw and f_ref:
                    new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_v, "foto_reg": process_photo(f_ref)}])
                    if save_data("users", new_u): st.success("Registrasi Berhasil!")

# --- 5. DASHBOARD UTAMA ---
def show_dashboard():
    u = st.session_state.logged_in_user
    now = datetime.now(jakarta_tz)
    st.sidebar.markdown(f"### 👤 {u['nama']}")
    st.sidebar.info(f"{u['role']} | {u['kelas']}")
    
    menu = ["🏠 Home", "📍 Presensi Kehadiran", "📚 Tugas Sekolah", "💰 Status SPP"]
    if u['role'] in ["Guru", "Admin TU"]:
        menu += ["📢 Kirim Broadcast", "📊 Laporan & Audit"]
    
    choice = st.sidebar.radio("Navigasi", menu)

    # --- HOME ---
    if choice == "🏠 Home":
        st.subheader("Informasi Dashboard")
        
        # Jadwal Sholat (Statis/Manual Update)
        st.markdown(f"""<div style="background-color:#f0fdf4; padding:15px; border-radius:10px; border:1px solid #bbf7d0; margin-bottom:20px;">
            <h4 style="margin:0; color:#166534;">🕌 Jadwal Sholat Banjarnegara</h4>
            <p style="margin:5px 0 0 0;">Subuh: 04:15 | Dzuhur: 11:53 | Ashar: 15:19 | Maghrib: 18:08 | Isya: 19:23</p></div>""", unsafe_allow_html=True)

        if u['role'] == "Siswa":
            col_info, col_rekap = st.columns([2, 1])
            
            with col_info:
                st.markdown("##### 🔔 Notifikasi & Pengumuman")
                # 1. Notifikasi Audit Foto (Validasi/Peringatan)
                df_notif = load_data("audit_notif", ttl="2s")
                if not df_notif.empty:
                    my_n = df_notif[df_notif['nama'] == u['nama']].tail(3)
                    for _, n in my_n.iterrows():
                        is_warn = "⚠️" in n['pesan']
                        st.markdown(f"""<div style='background:{"#fee2e2" if is_warn else "#dcfce7"}; 
                                    border-left:5px solid {"#ef4444" if is_warn else "#22c55e"}; 
                                    padding:10px; border-radius:5px; margin-bottom:10px; color:black;'>{n['pesan']}</div>""", unsafe_allow_html=True)

                # 2. Broadcast Guru
                df_bc = load_data("broadcast", ttl="2s")
                if not df_bc.empty:
                    my_bc = df_bc[(df_bc['target'] == "Semua Kelas") | (df_bc['target'] == u['kelas'])].tail(3)
                    for _, b in my_bc.iterrows():
                        st.info(f"📢 **{b['judul']}**\n\n{b['pesan']}\n\n*Oleh: {b['pic']}*")
                
                if df_notif.empty and df_bc.empty:
                    st.write("Tidak ada pengumuman hari ini.")

            with col_rekap:
                st.markdown("##### 📊 Rekap Tugas")
                df_t = load_data("tugas")
                df_s = load_data("tugas_selesai")
                t_total = len(df_t[df_t['kelas'] == u['kelas']]) if not df_t.empty else 0
                t_done = len(df_s[df_s['nama'] == u['nama']]) if not df_s.empty else 0
                st.metric("📚 Belum Selesai", t_total - t_done)
                st.metric("✅ Sudah Selesai", t_done)

        else: # Guru/Admin Dashboard
            df_p = load_data("presensi", ttl="2s")
            df_ts = load_data("tugas_selesai")
            today = now.strftime("%Y-%m-%d")
            p_today = df_p[df_p['waktu'].str.contains(today)] if not df_p.empty else pd.DataFrame()
            
            st.markdown("#### Statistik Kehadiran & Tugas Hari Ini")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("🌅 Masuk", len(p_today[p_today['jenis'] == "Masuk"]))
            c2.metric("🕌 Dhuha", len(p_today[p_today['jenis'] == "Dhuha"]))
            c3.metric("☀️ Dzuhur", len(p_today[p_today['jenis'] == "Dzuhur"]))
            c4.metric("🏠 Pulang", len(p_today[p_today['jenis'] == "Pulang"]))
            c5.metric("📝 Tugas", len(df_ts[df_ts['waktu'].str.contains(today)]) if not df_ts.empty else 0)

    # --- PRESENSI ---
    elif choice == "📍 Presensi Kehadiran":
        st.subheader("Input Kehadiran")
        loc = get_geolocation()
        if loc:
            dist = geodesic(SCHOOL_LOC, (loc['coords']['latitude'], loc['coords']['longitude'])).meters
            st.write(f"Jarak: {dist:.2f}m")
            if dist <= 200:
                with st.form("abs"):
                    j = st.selectbox("Sesi", ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                    f = st.camera_input("Foto")
                    if st.form_submit_button("Kirim"):
                        status = "Hadir"
                        if j == "Masuk" and now.time() > dt.time(7,15): status = "Terlambat"
                        save_data("presensi", pd.DataFrame([{"nama": u['nama'], "kelas": u['kelas'], "jenis": j, "waktu": now.strftime("%Y-%m-%d %H:%M:%S"), "status": status, "foto_absen": process_photo(f)}]))
                        st.success("Presensi Berhasil!")
            else: st.error("Di luar jangkauan sekolah!")

    # --- TUGAS ---
    elif choice == "📚 Tugas Sekolah":
        df_t = load_data("tugas")
        df_s = load_data("tugas_selesai")
        if u['role'] == "Siswa":
            t1, t2 = st.tabs(["📝 Belum Selesai", "✅ Sudah Selesai"])
            with t1:
                my_t = df_t[df_t['kelas'] == u['kelas']] if not df_t.empty else pd.DataFrame()
                done_list = df_s[df_s['nama'] == u['nama']]['id_tugas'].tolist() if not df_s.empty else []
                for _, r in my_t.iterrows():
                    if r['judul_tugas'] not in done_list:
                        with st.expander(f"Tugas: {r['judul_tugas']}"):
                            st.write(r['deskripsi'])
                            if st.button(f"Selesaikan {r['judul_tugas']}"):
                                save_data("tugas_selesai", pd.DataFrame([{"nama": u['nama'], "kelas": u['kelas'], "id_tugas": r['judul_tugas'], "waktu": now.strftime("%Y-%m-%d %H:%M")}]))
                                st.rerun()
            with t2:
                st.table(df_s[df_s['nama'] == u['nama']])
        else:
            with st.form("t_f"):
                jt = st.text_input("Judul"); ds = st.text_area("Isi")
                ks = st.selectbox("Kelas", list_kelas); dl = st.date_input("Deadline")
                if st.form_submit_button("Posting"):
                    save_data("tugas", pd.DataFrame([{"judul_tugas": jt, "deskripsi": ds, "kelas": ks, "deadline": str(dl)}]))
            st.dataframe(df_s)

    # --- SPP ---
    elif choice == "💰 Status SPP":
        df_spp = load_data("spp", ttl="2s")
        if u['role'] == "Admin TU":
            st.subheader("Manajemen Pembayaran SPP")
            with st.form("spp_f"):
                sn = st.text_input("Nama Siswa (Sesuai Registrasi)")
                nom = st.number_input("Nominal", min_value=0)
                bln = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
                stts = st.selectbox("Status", ["Menunggak", "Lunas"])
                if st.form_submit_button("Simpan SPP"):
                    save_data("spp", pd.DataFrame([{"nama": sn, "nominal": nom, "bulan": bln, "status": stts, "tgl_update": now.strftime("%Y-%m-%d")}]))
            st.dataframe(df_spp)
        else:
            st.subheader("Riwayat SPP Anda")
            my_spp = df_spp[df_spp['nama'] == u['nama']] if not df_spp.empty else pd.DataFrame()
            tab_tung, tab_lun = st.tabs(["❌ Tunggakan", "✅ Lunas"])
            
            with tab_tung:
                # Perbaikan Minor: Filter hanya yang benar-benar 'Menunggak'
                tung = my_spp[my_spp['status'] == "Menunggak"]
                if not tung.empty: st.table(tung)
                else: st.success("Alhamdulillah, tidak ada tunggakan.")
            with tab_lun:
                lun = my_spp[my_spp['status'] == "Lunas"]
                if not lun.empty: st.table(lun)
                else: st.info("Belum ada riwayat pembayaran lunas.")

    # --- BROADCAST ---
    elif choice == "📢 Kirim Broadcast":
        st.subheader("Kirim Pengumuman")
        with st.form("bc_f"):
            jd = st.text_input("Judul"); msg = st.text_area("Isi Pesan")
            trg = st.selectbox("Target", ["Semua Kelas"] + list_kelas)
            pic = st.text_input("PIC", value=u['nama'])
            if st.form_submit_button("Sebarkan"):
                save_data("broadcast", pd.DataFrame([{"judul": jd, "pesan": msg, "target": trg, "pic": pic, "tgl": now.strftime("%Y-%m-%d")}]))
                st.success("Terkirim!")

    # --- LAPORAN & AUDIT ---
    elif choice == "📊 Laporan & Audit":
        df_p = load_data("presensi", ttl="2s")
        df_u = load_data("users")
        t1, t2 = st.tabs(["🔍 Verifikasi Wajah", "📄 Laporan Presensi"])
        
        with t1:
            if not df_p.empty:
                sel = st.selectbox("Pilih Siswa", df_p['nama'].unique())
                u_ref = df_u[df_u['nama'] == sel]; u_abs = df_p[df_p['nama'] == sel].tail(1)
                if not u_ref.empty and not u_abs.empty:
                    c1, c2 = st.columns(2)
                    c1.image(f"data:image/jpeg;base64,{u_ref.iloc[0]['foto_reg']}", caption="Foto Registrasi")
                    c2.image(f"data:image/jpeg;base64,{u_abs.iloc[0]['foto_absen']}", caption="Foto Terakhir")
                    if st.button("✅ Validkan"):
                        save_data("audit_notif", pd.DataFrame([{"nama": sel, "pesan": f"✅ Foto Absen {u_abs.iloc[0]['jenis']} Anda VALID."}]))
                        st.success("Terkirim ke siswa")
                    if st.button("⚠️ Kirim Peringatan"):
                        save_data("audit_notif", pd.DataFrame([{"nama": sel, "pesan": f"⚠️ Wajah Absen {u_abs.iloc[0]['jenis']} Tidak Sesuai Referensi!"}]))
                        st.warning("Peringatan terkirim")

        with t2:
            st.subheader("Filter Laporan")
            col_f1, col_f2 = st.columns(2)
            f_tgl = col_f1.date_input("Tanggal", value=now.date())
            f_kls = col_f2.selectbox("Kelas", ["Semua"] + list_kelas)
            df_filtered = df_p.copy()
            df_filtered['tgl_only'] = pd.to_datetime(df_filtered['waktu']).dt.date
            df_filtered = df_filtered[df_filtered['tgl_only'] == f_tgl]
            if f_kls != "Semua": df_filtered = df_filtered[df_filtered['kelas'] == f_kls]
            st.dataframe(df_filtered, use_container_width=True)
            st.download_button("📥 Export Excel", to_excel(df_filtered), "laporan_presensi.xlsx")

    if st.sidebar.button("🚪 Keluar"):
        st.session_state.logged_in_user = None
        st.rerun()

# --- RUN ---
if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
