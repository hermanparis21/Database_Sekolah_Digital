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
    st.markdown("<p style='text-align: center; color: #475569;'><i>'Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan'</i></p>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔑 Masuk", "📝 Registrasi"])
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
                st.error("Login Gagal!")
    with tab2:
        with st.form("r_f"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input("Nama Lengkap").title()
            pw = st.text_input("Password")
            id_v = st.text_input("NIS/NIK")
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            f_ref = st.camera_input("Foto Referensi")
            if st.form_submit_button("Daftar"):
                if n and pw and f_ref:
                    new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_v, "foto_reg": process_photo(f_ref)}])
                    if save_data("users", new_u): st.success("Berhasil!")

# --- 5. DASHBOARD UTAMA ---
def show_dashboard():
    u = st.session_state.logged_in_user
    now = datetime.now(jakarta_tz)
    st.sidebar.markdown(f"### 👤 {u['nama']}")
    st.sidebar.info(f"{u['role']} | {u['kelas']}")
    
    menu = ["🏠 Home", "📍 Presensi Kehadiran", "📚 Tugas Sekolah", "💰 Status SPP"]
    if u['role'] in ["Guru", "Admin TU"]:
        menu += ["📢 Kirim Broadcast", "📊 Laporan & Audit"]
    
    choice = st.sidebar.radio("Menu", menu)

    # --- HOME ---
    if choice == "🏠 Home":
        st.subheader("Dashboard")
        st.markdown(f"""<div style="background-color:#f0fdf4; padding:15px; border-radius:10px; border:1px solid #bbf7d0;">
            <h4 style="margin:0;">🕌 Jadwal Sholat Banjarnegara</h4>
            <p>Subuh: 04:15 | Dzuhur: 11:53 | Ashar: 15:19 | Maghrib: 18:08 | Isya: 19:23</p></div>""", unsafe_allow_html=True)

        if u['role'] == "Siswa":
            # Cek Notifikasi Audit (Muncul di Home Siswa)
            df_notif = load_data("audit_notif", ttl="2s")
            if not df_notif.empty:
                my_n = df_notif[df_notif['nama'] == u['nama']].tail(3)
                for _, n in my_n.iterrows():
                    color = "#dc2626" if "⚠️" in n['pesan'] else "#16a34a"
                    st.markdown(f"<div style='border-left:5px solid {color}; padding:10px; background:#f8fafc; margin-bottom:5px;'>{n['pesan']}</div>", unsafe_allow_html=True)

            # Broadcast Terbaru
            df_bc = load_data("broadcast", ttl="5s")
            if not df_bc.empty:
                with st.expander("📢 Pengumuman Terbaru"):
                    st.table(df_bc.tail(5))

    # --- PRESENSI ---
    elif choice == "📍 Presensi Kehadiran":
        st.subheader("Presensi GPS")
        loc = get_geolocation()
        if loc:
            dist = geodesic(SCHOOL_LOC, (loc['coords']['latitude'], loc['coords']['longitude'])).meters
            st.write(f"Jarak: {dist:.2f}m")
            if dist <= 200:
                with st.form("abs"):
                    j = st.selectbox("Sesi", ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                    f = st.camera_input("Foto")
                    if st.form_submit_button("Kirim"):
                        t_absen = now.time()
                        status = "Hadir"
                        if j == "Masuk" and t_absen > dt.time(7,15): status = "Terlambat"
                        elif j == "Dhuha" and t_absen > dt.time(8,0): status = "Terlambat"
                        
                        save_data("presensi", pd.DataFrame([{"nama": u['nama'], "kelas": u['kelas'], "jenis": j, "waktu": now.strftime("%Y-%m-%d %H:%M:%S"), "status": status, "foto_absen": process_photo(f)}]))
                        st.success("Absen Tersimpan!")
            else: st.error("Di luar jangkauan!")

    # --- TUGAS ---
    elif choice == "📚 Tugas Sekolah":
        df_t = load_data("tugas")
        df_s = load_data("tugas_selesai")
        if u['role'] == "Siswa":
            st.subheader("Tugas Saya")
            if not df_t.empty:
                my_t = df_t[df_t['kelas'] == u['kelas']]
                for _, r in my_t.iterrows():
                    with st.expander(f"📝 {r['judul_tugas']} (Deadline: {r.get('deadline','-')})"):
                        st.write(r['deskripsi'])
                        if st.button(f"Selesai: {r['judul_tugas']}"):
                            save_data("tugas_selesai", pd.DataFrame([{"nama": u['nama'], "kelas": u['kelas'], "id_tugas": r['judul_tugas'], "waktu": now.strftime("%Y-%m-%d %H:%M")}]))
                            st.rerun()
        else:
            st.subheader("Input Tugas")
            with st.form("t_t"):
                jt = st.text_input("Judul"); ds = st.text_area("Deskripsi")
                ks = st.selectbox("Kelas", list_kelas); dl = st.date_input("Deadline")
                if st.form_submit_button("Posting"):
                    save_data("tugas", pd.DataFrame([{"judul_tugas": jt, "deskripsi": ds, "kelas": ks, "deadline": str(dl)}]))
            
            st.subheader("Rekap Penyelesaian Tugas")
            st.dataframe(df_s, use_container_width=True)
            if not df_s.empty: st.download_button("📥 Export Excel", to_excel(df_s), "rekap_tugas.xlsx")

    # --- SPP ---
    elif choice == "💰 Status SPP":
        df_spp = load_data("spp", ttl="2s")
        if u['role'] == "Admin TU":
            st.subheader("Input Pembayaran SPP")
            with st.form("spp_f"):
                sn = st.text_input("Nama Siswa"); ni = st.text_input("NIS")
                nom = st.number_input("Nominal", min_value=0)
                bln = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
                ket = st.selectbox("Keterangan", ["Lunas", "Menunggak"])
                ddl = st.date_input("Batas Bayar")
                if st.form_submit_button("Simpan Data"):
                    save_data("spp", pd.DataFrame([{"nama": sn, "nis": ni, "nominal": nom, "bulan": bln, "keterangan": ket, "deadline": str(ddl)}]))
            
            st.subheader("Data SPP")
            st.dataframe(df_spp)
            if not df_spp.empty: st.download_button("📥 Export SPP", to_excel(df_spp), "data_spp.xlsx")
        else:
            st.subheader("Status SPP Saya")
            my_spp = df_spp[df_spp['nama'] == u['nama']] if not df_spp.empty else pd.DataFrame()
            if not my_spp.empty:
                st.table(my_spp)
            else:
                st.info("Belum ada tunggakan atau tagihan SPP.")

    # --- BROADCAST ---
    elif choice == "📢 Kirim Broadcast":
        st.subheader("Broadcast Pro")
        with st.form("bc"):
            jd = st.text_input("Judul Broadcast"); isi = st.text_area("Isi Pesan")
            trg = st.selectbox("Target", ["Semua Kelas"] + list_kelas)
            pic = st.text_input("PIC / Pengirim", value=u['nama'])
            if st.form_submit_button("Kirim"):
                save_data("broadcast", pd.DataFrame([{"judul": jd, "pesan": isi, "target": trg, "pic": pic, "tanggal": now.strftime("%Y-%m-%d")}]))
                st.success("Terkirim!")

    # --- LAPORAN ---
    elif choice == "📊 Laporan & Audit":
        df_p = load_data("presensi", ttl="2s")
        df_u = load_data("users")
        tab_a, tab_l = st.tabs(["🔍 Audit Wajah", "📄 Rekap Laporan"])
        
        with tab_a:
            if not df_p.empty:
                sel = st.selectbox("Siswa", df_p['nama'].unique())
                u_r = df_u[df_u['nama'] == sel]; u_a = df_p[df_p['nama'] == sel].tail(1)
                if not u_r.empty and not u_a.empty:
                    c1, c2 = st.columns(2)
                    c1.image(f"data:image/jpeg;base64,{u_r.iloc[0]['foto_reg']}", caption="Registrasi")
                    c2.image(f"data:image/jpeg;base64,{u_a.iloc[0]['foto_absen']}", caption="Absen")
                    if st.button("✅ Valid"):
                        save_data("audit_notif", pd.DataFrame([{"nama": sel, "pesan": f"✅ Absensi {u_a.iloc[0]['jenis']} Valid."}]))
                    if st.button("⚠️ Peringatan"):
                        save_data("audit_notif", pd.DataFrame([{"nama": sel, "pesan": f"⚠️ Wajah {u_a.iloc[0]['jenis']} Tidak Sesuai!"}]))
        
        with tab_l:
            if not df_p.empty:
                def style_row(row):
                    return ['color: red; font-weight: bold' if row.status == 'Terlambat' else '' for _ in row]
                st.dataframe(df_p.style.apply(style_row, axis=1), use_container_width=True)
                st.download_button("📥 Export Presensi", to_excel(df_p), "presensi.xlsx")

    if st.sidebar.button("🚪 Keluar"):
        st.session_state.logged_in_user = None
        st.rerun()

# --- RUN ---
st.markdown("<h1 style='text-align: center; color: #059669;'>🎓 MUHAMKA DIGITAL SCHOOL</h1>", unsafe_allow_html=True)
if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
