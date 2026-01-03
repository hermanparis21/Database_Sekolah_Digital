import streamlit as st
import pandas as pd
from datetime import datetime
import datetime as dt
import pytz
import io
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# --- 1. KONFIGURASI ---
jakarta_tz = pytz.timezone('Asia/Jakarta')
SCHOOL_LOC = (-7.2164697698622335, 109.64013014754921)

st.set_page_config(page_title="SMA Muhammadiyah 4 Banjarnegara", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #059669; color: white; height: 3em; }
    .clock-text { text-align: center; font-weight: bold; font-size: 1.1em; color: #1e293b; background: #f1f5f9; padding: 10px; border-radius: 15px; border: 1px solid #cbd5e1; margin-bottom: 20px; }
    .header-text { text-align: center; color: #059669; margin-bottom: 0px; font-size: 2em; }
    .slogan { text-align: center; font-style: italic; color: #475569; margin-bottom: 10px; font-size: 1em; }
    .stat-card { background: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, ttl="0s"):
    return conn.read(worksheet=sheet_name, ttl=ttl)

def add_log(user, activity, detail):
    try:
        df_log = load_data("log_system")
        new_entry = pd.DataFrame([{"waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"), "user": user, "aktivitas": activity, "keterangan": detail}])
        conn.update(worksheet="log_system", data=pd.concat([df_log, new_entry], ignore_index=True))
    except: pass

def get_attendance_status(jenis, waktu_str):
    try:
        t = datetime.strptime(waktu_str, "%Y-%m-%d %H:%M:%S").time()
        if jenis == "Masuk": return "Valid" if dt.time(6,0) <= t <= dt.time(7,30) else "Terlambat"
        elif jenis == "Dhuha": return "Valid" if dt.time(7,15) <= t <= dt.time(8,0) else "Terlambat"
        elif jenis == "Dzuhur": return "Valid" if dt.time(11,30) <= t <= dt.time(13,0) else "Terlambat"
        elif jenis == "Pulang": return "Valid" if t >= dt.time(14,30) else "Pulang Cepat"
        return "Unknown"
    except: return "-"

# --- 3. STATE ---
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
L = {"slogan": "Mewujudkan Peserta Didik yang Bertaqwa, Berprestasi, dan Peduli Lingkungan", "login": "Masuk", "reg": "Registrasi Siswa Baru", "nama": "Nama Lengkap", "pass": "Password", "absen_h": "📍 Presensi Wajah & GPS", "pilih_j": "Jenis Presensi", "face_now": "Verifikasi Wajah Sekarang", "tugas": "📚 Tugas Sekolah", "lapor": "📊 Laporan Presensi", "log_sys": "⚙️ Log System", "spp": "💰 Manajemen SPP", "out": "Keluar"}
list_kelas = [f"{t}-{h}" for t in ["X", "XI", "XII"] for h in ["A", "B", "C", "D", "E", "F"]]

st.markdown(f"<h1 class='header-text'>🎓 SMA Muhammadiyah 4 Banjarnegara</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='slogan'>{L['slogan']}</p>", unsafe_allow_html=True)
now_dt = datetime.now(jakarta_tz)
st.markdown(f"<div class='clock-text'>🗓️ {now_dt.strftime('%A, %d %B %Y')} | ⏰ {now_dt.strftime('%H:%M:%S')} WIB</div>", unsafe_allow_html=True)

# --- 4. AUTH ---
def show_auth():
    tab1, tab2 = st.tabs([f"🔑 {L['login']}", f"📝 {L['reg']}"])
    with tab1:
        with st.form("l_form"):
            u = st.text_input(L['nama']).title(); p = st.text_input(L['pass'], type="password")
            if st.form_submit_button(L['login']):
                df_u = load_data("users")
                m = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p.strip())]
                if not m.empty:
                    st.session_state.logged_in_user = m.iloc[0].to_dict()
                    add_log(u, "LOGIN", "Berhasil"); st.rerun()
                else: st.error("Gagal!")
    with tab2:
        with st.form("r_form"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input(L['nama']).title(); pw = st.text_input(L['pass']); id_val = st.text_input("NIS/NIK")
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            f_ref = st.camera_input("Foto Referensi")
            if st.form_submit_button(L['reg']):
                if not f_ref or len(n) < 3: st.error("Data tidak lengkap!"); return
                df_u = load_data("users")
                new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_val, "foto_reg": f_ref.name}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True)); st.success("Registrasi Berhasil!")

# --- 5. DASHBOARD ---
def show_dashboard():
    user = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {user['nama']}")
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}", L['spp']]
    if user['role'] in ["Guru", "Admin TU"]: menu_opt += [L['lapor'], L['log_sys']]
    choice = st.sidebar.radio("Menu", menu_opt)

    if choice == "🏠 Home":
        st.subheader(f"Selamat Datang, {user['nama']}!")
        if user['role'] == "Siswa":
            st.info("Gunakan menu di samping untuk melakukan Presensi atau mengecek Tugas.")
        else:
            today = now_dt.strftime("%Y-%m-%d")
            df_p = load_data("presensi", ttl="5s")
            p_today = df_p[df_p['waktu'].str.contains(today, na=False)] if not df_p.empty else pd.DataFrame()
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Masuk']) if not p_today.empty else 0}</h3><p>Hadir Masuk</p></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Dhuha']) if not p_today.empty else 0}</h3><p>Dhuha</p></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='stat-card'><h3>{len(p_today[p_today['jenis']=='Dzuhur']) if not p_today.empty else 0}</h3><p>Dzuhur</p></div>", unsafe_allow_html=True)

    elif choice == f"📍 {L['absen_h']}":
        st.subheader(L['absen_h'])
        loc = get_geolocation()
        if loc:
            u_coords = (loc['coords']['latitude'], loc['coords']['longitude'])
            dist = geodesic(u_coords, SCHOOL_LOC).meters
            if dist <= 100:
                m_absen = st.selectbox(L['pilih_j'], ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                img_now = st.camera_input(L['face_now'])
                if st.button("Submit Presensi") and img_now:
                    df_p = load_data("presensi")
                    new_p = pd.DataFrame([{"nama": user['nama'], "kelas": user.get('kelas', '-'), "waktu": datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S"), "jenis": m_absen, "jarak": f"{int(dist)}m", "foto_absen": img_now.name}])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True))
                    st.success("Presensi Berhasil Disimpan!")
            else: st.error(f"Anda berada di luar radius sekolah ({int(dist)}m).")

    elif choice == f"{L['tugas']}":
        st.header(L['tugas'])
        df_t = load_data("tugas", ttl="5s"); df_done = load_data("tugas_selesai", ttl="5s")
        if user['role'] == "Guru":
            with st.form("t_f"):
                t_j = st.text_input("Judul Tugas"); t_d = st.text_area("Instruksi"); t_k = st.multiselect("Kelas", list_kelas)
                if st.form_submit_button("Sebarkan Tugas"):
                    df_tl = load_data("tugas")
                    new_t = pd.DataFrame([{"id": datetime.now(jakarta_tz).strftime("%H%M%S"), "guru": user['nama'], "judul": t_j, "deskripsi": t_d, "kelas": ",".join(t_k)}])
                    conn.update(worksheet="tugas", data=pd.concat([df_tl, new_t], ignore_index=True)); st.rerun()
            st.divider()
            if not df_done.empty:
                st.subheader("Opsi Ekspor Laporan Penyelesaian")
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_done.to_excel(wr, index=False)
                    st.download_button("📥 Ekspor Tugas (XLSX)", buf.getvalue(), "laporan_tugas.xlsx")
                with col_ex2:
                    st.download_button("📥 Ekspor Tugas (TXT)", df_done.to_string(index=False), "laporan_tugas.txt")
            st.divider()
            if not df_t.empty:
                for _, r in df_t.iterrows():
                    with st.expander(f"📋 {r['judul']} ({r['kelas']})"):
                        done_list = df_done[df_done['id_tugas'].astype(str) == str(r['id'])] if not df_done.empty else pd.DataFrame()
                        st.table(done_list[['nama', 'kelas', 'waktu']] if not done_list.empty else pd.DataFrame(columns=['Belum ada siswa']))
        else:
            uk = str(user.get('kelas',''))
            rel_t = df_t[df_t['kelas'].astype(str).str.contains(uk, na=False)] if not df_t.empty else pd.DataFrame()
            for _, r in rel_t.iterrows():
                is_c = not df_done[(df_done['id_tugas'].astype(str) == str(r['id'])) & (df_done['nama'] == user['nama'])].empty if not df_done.empty else False
                st.info(f"**{r['judul']}**: {r['deskripsi']}")
                if not is_c:
                    if st.button("Tandai Selesai", key=f"t_{r['id']}"):
                        df_dl = load_data("tugas_selesai")
                        new_d = pd.DataFrame([{"id_tugas": str(r['id']), "nama": user['nama'], "kelas": user['kelas'], "waktu": now_dt.strftime("%d/%m %H:%M")}])
                        conn.update(worksheet="tugas_selesai", data=pd.concat([df_dl, new_d], ignore_index=True)); st.rerun()
                else: st.success("Tugas ini sudah selesai.")

    elif choice == L['lapor']:
        st.header(L['lapor'])
        # --- PERBAIKAN: AUDIT GURU (KOMPARASI FOTO) ---
        tab_data, tab_audit = st.tabs(["📊 Data Presensi", "🔍 Audit Foto Siswa"])
        
        df_p = load_data("presensi", ttl="5s")
        df_u = load_data("users", ttl="5s")
        
        with tab_data:
            if not df_p.empty:
                df_p['Status Waktu'] = df_p.apply(lambda x: get_attendance_status(x['jenis'], x['waktu']), axis=1)
                st.dataframe(df_p.style.applymap(lambda v: 'color:red; font-weight:bold' if v in ['Terlambat','Pulang Cepat'] else '', subset=['Status Waktu']), width='stretch')
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_p.to_excel(wr, index=False)
                st.download_button("📥 Ekspor Laporan XLSX", buf.getvalue(), "presensi.xlsx")
                st.download_button("📥 Ekspor Laporan TXT", df_p.to_string(index=False), "presensi.txt")

        with tab_audit:
            st.subheader("Audit Kejujuran Wajah Siswa")
            if not df_p.empty:
                search_name = st.selectbox("Pilih Siswa untuk Audit", df_p['nama'].unique())
                user_reg_data = df_u[df_u['nama'] == search_name]
                user_abs_data = df_p[df_p['nama'] == search_name].tail(1) # Ambil absen terakhir
                
                if not user_reg_data.empty and not user_abs_data.empty:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.info("📸 Foto Registrasi (Referensi)")
                        st.write("File: " + str(user_reg_data.iloc[0].get('foto_reg', 'Tidak ada data')))
                        # Menampilkan placeholder jika URL foto tidak tersedia langsung di GS
                        st.warning("Gunakan Google Drive Link jika foto ingin ditampilkan visual di sini.")
                    with c2:
                        st.info("📍 Foto Saat Absen")
                        st.write("File: " + str(user_abs_data.iloc[0].get('foto_absen', 'Tidak ada data')))
                        st.write(f"Waktu: {user_abs_data.iloc[0]['waktu']}")
                else:
                    st.warning("Data foto tidak ditemukan.")

    elif choice == L['spp']:
        st.header(L['spp'])
        df_spp = load_data("spp", ttl="2s")
        if user['role'] == "Admin TU":
            with st.form("f_spp"):
                df_u = load_data("users")
                s_sel = st.selectbox("Pilih Siswa", df_u[df_u['role']=='Siswa']['nama'].tolist())
                ket = st.text_input("Keterangan")
                jml = st.number_input("Jumlah (Rp)", min_value=0)
                st_pay = st.selectbox("Status", ["Belum Lunas", "Lunas"])
                if st.form_submit_button("Simpan Data SPP"):
                    df_sl = load_data("spp")
                    new_p = pd.DataFrame([{"nama": s_sel, "keterangan": ket, "jumlah": jml, "status": st_pay, "tanggal": now_dt.strftime("%Y-%m-%d")}])
                    conn.update(worksheet="spp", data=pd.concat([df_sl, new_p], ignore_index=True)); st.success("Data Berhasil Diinput!")
            st.divider()
            st.dataframe(df_spp)
        else:
            st.subheader(f"Data Tagihan: {user['nama']}")
            my_spp = df_spp[df_spp['nama'] == user['nama']] if not df_spp.empty else pd.DataFrame()
            if not my_spp.empty: st.table(my_spp[['tanggal', 'keterangan', 'jumlah', 'status']])
            else: st.warning("Belum ada data tagihan resmi.")

    elif choice == L['log_sys']:
        st.header(L['log_sys'])
        st.dataframe(load_data("log_system").tail(100))

    if st.sidebar.button(L['out']): st.session_state.logged_in_user = None; st.rerun()

if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
