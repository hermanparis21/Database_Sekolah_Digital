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

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; background-color: #059669; color: white; height: 3em; }
    .clock-text { text-align: center; font-weight: bold; font-size: 1.1em; color: #1e293b; background: #f1f5f9; padding: 10px; border-radius: 15px; border: 1px solid #cbd5e1; margin-bottom: 20px; }
    .header-text { text-align: center; color: #059669; margin-bottom: 0px; font-size: 2em; }
    .slogan { text-align: center; font-style: italic; color: #475569; margin-bottom: 10px; font-size: 1em; }
    .stat-card { background: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; border: 1px solid #e2e8f0; margin-bottom:10px; }
    .notif-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #059669; background: #f0fdf4; }
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

# --- 4. AUTH ---
def show_auth():
    t1, t2 = st.tabs([f"🔑 {L['login']}", f"📝 {L['reg']}"])
    with t1:
        with st.form("l_f"):
            u = st.text_input(L['nama']).title(); p = st.text_input(L['pass'], type="password")
            if st.form_submit_button(L['login']):
                df_u = load_data("users")
                m = df_u[(df_u['nama'].astype(str).str.strip() == u.strip()) & (df_u['password'].astype(str) == p.strip())]
                if not m.empty: st.session_state.logged_in_user = m.iloc[0].to_dict(); st.rerun()
                else: st.error("Login Gagal")
    with t2:
        with st.form("r_f"):
            role = st.selectbox("Role", ["Siswa", "Guru", "Admin TU"])
            n = st.text_input(L['nama']).title(); pw = st.text_input(L['pass']); id_v = st.text_input("NIS/NIK")
            kls = st.selectbox("Kelas", list_kelas) if role == "Siswa" else "-"
            f_ref = st.camera_input("Foto Registrasi")
            if st.form_submit_button(L['reg']) and f_ref:
                df_u = load_data("users")
                new_u = pd.DataFrame([{"nama": n, "password": pw, "role": role, "kelas": kls, "id_unik": id_v, "foto_reg": process_photo(f_ref)}])
                conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True)); st.success("Berhasil!")

# --- 5. DASHBOARD ---
def show_dashboard():
    u = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {u['nama']}")
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}", L['spp']]
    if u['role'] in ["Guru", "Admin TU"]: menu_opt += [L['broadcast'], L['lapor']]
    choice = st.sidebar.radio("Menu", menu_opt)

    if choice == "🏠 Home":
        st.subheader(f"Dashboard {u['role']}")
        
        # JADWAL SHOLAT BANJARNEGARA (Parameter Instruksi)
        st.markdown("""<div style='background:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:20px;'>
            <b>🕌 Waktu Sholat Wilayah Banjarnegara</b> (7°24' LS, 109°42' BB)<br>
            <small>Arah Kiblat: 294.78° | Jarak ke Mekah: 8264.2 km</small>
            <div style='display:flex; justify-content:space-between; margin-top:10px;'>
                <span>Subuh: 04:15</span><span>Dzuhur: 11:52</span><span>Ashar: 15:18</span><span>Maghrib: 18:07</span><span>Isya: 19:22</span>
            </div></div>""", unsafe_allow_html=True)

        # NOTIFIKASI / BROADCAST (Untuk Siswa)
        df_bc = load_data("broadcast", ttl="5s")
        if u['role'] == "Siswa":
            st.subheader("📢 Pengumuman Sekolah")
            if not df_bc.empty:
                rel_bc = df_bc[(df_bc['target'] == "Semua Kelas") | (df_bc['target'] == u['kelas'])]
                for _, b in rel_bc.iterrows():
                    with st.container():
                        st.markdown(f"""<div class='notif-box'>
                            <b>{b['judul']}</b><br>{b['isi']}<br>
                            <small>📅 {b['tanggal']} | 📍 {b['tempat']} | 👤 PIC: {b['pic']}</small>
                            </div>""", unsafe_allow_html=True)
            
            # Peringatan Kejujuran
            df_warn = load_data("audit_notif", ttl="5s")
            if not df_warn.empty:
                my_warn = df_warn[df_warn['nama'] == u['nama']].tail(3)
                for _, w in my_warn.iterrows():
                    color = "blue" if w['status'] == "Valid" else "red"
                    st.toast(f"Pesan Kedisiplinan: {w['pesan']}", icon="⚠️" if color=="red" else "✅")
                    st.markdown(f"<div style='color:{color}; border:1px solid {color}; padding:10px; border-radius:5px; margin-bottom:5px;'>{w['pesan']} ({w['waktu']})</div>", unsafe_allow_html=True)

    elif choice == L['broadcast']:
        st.subheader("Kirim Pesan Broadcast")
        with st.form("bc_form"):
            t_j = st.text_input("Judul Pengumuman"); t_i = st.text_area("Isi Pengumuman")
            t_t = st.date_input("Tanggal Pelaksanaan"); t_p = st.text_input("Tempat")
            t_pic = st.text_input("Panitia/PIC"); t_target = st.selectbox("Target", ["Semua Kelas"] + list_kelas)
            if st.form_submit_button("📢 Sebar Pengumuman"):
                df_b = load_data("broadcast")
                new_b = pd.DataFrame([{"judul": t_j, "isi": t_i, "tanggal": str(t_t), "tempat": t_p, "pic": t_pic, "target": t_target}])
                conn.update(worksheet="broadcast", data=pd.concat([df_b, new_b], ignore_index=True)); st.success("Terkirim!")

    elif choice == f"📍 {L['absen_h']}":
        st.subheader(L['absen_h'])
        loc = get_geolocation()
        if loc:
            dist = geodesic((loc['coords']['latitude'], loc['coords']['longitude']), SCHOOL_LOC).meters
            if dist <= 100:
                m_absen = st.selectbox("Jenis", ["Masuk", "Dhuha", "Dzuhur", "Pulang"])
                img_now = st.camera_input("Verifikasi Wajah")
                if st.button("Submit Presensi") and img_now:
                    df_p = load_data("presensi")
                    new_p = pd.DataFrame([{"nama": u['nama'], "kelas": u.get('kelas', '-'), "waktu": now_dt.strftime("%Y-%m-%d %H:%M:%S"), "jenis": m_absen, "jarak": f"{int(dist)}m", "foto_absen": process_photo(img_now)}])
                    conn.update(worksheet="presensi", data=pd.concat([df_p, new_p], ignore_index=True)); st.success("Presensi Berhasil!")
            else: st.error(f"Di luar radius ({int(dist)}m)")

    elif choice == f"{L['tugas']}":
        st.subheader(L['tugas'])
        df_t = load_data("tugas", ttl="5s"); df_done = load_data("tugas_selesai", ttl="5s")
        if u['role'] == "Guru":
            with st.form("t_f"):
                t_j = st.text_input("Judul Tugas"); t_d = st.text_area("Instruksi"); t_k = st.multiselect("Kelas", list_kelas)
                if st.form_submit_button("Sebarkan"):
                    new_t = pd.DataFrame([{"id": now_dt.strftime("%H%M%S"), "guru": u['nama'], "judul": t_j, "deskripsi": t_d, "kelas": ",".join(t_k)}])
                    conn.update(worksheet="tugas", data=pd.concat([df_t, new_t], ignore_index=True)); st.rerun()
            st.divider()
            st.subheader("Daftar Siswa Selesai")
            if not df_done.empty: st.table(df_done[['nama', 'kelas', 'waktu']])
        else:
            rel_t = df_t[df_t['kelas'].str.contains(u['kelas'], na=False)] if not df_t.empty else pd.DataFrame()
            for _, r in rel_t.iterrows():
                is_c = not df_done[(df_done['id_tugas'].astype(str) == str(r['id'])) & (df_done['nama'] == u['nama'])].empty if not df_done.empty else False
                st.info(f"**{r['judul']}**: {r['deskripsi']}")
                if not is_c and st.button("Tandai Selesai", key=f"t_{r['id']}"):
                    new_d = pd.DataFrame([{"id_tugas": str(r['id']), "nama": u['nama'], "kelas": u['kelas'], "waktu": now_dt.strftime("%Y-%m-%d %H:%M:%S")}])
                    conn.update(worksheet="tugas_selesai", data=pd.concat([df_done, new_d], ignore_index=True)); st.rerun()
            st.subheader("✅ Tugas Selesai Anda")
            if not df_done.empty: st.table(df_done[df_done['nama'] == u['nama']][['id_tugas', 'waktu']])

    elif choice == L['lapor']:
        st.header(L['lapor'])
        tab1, tab2 = st.tabs(["📊 Data", "🔍 Audit Wajah"])
        df_p = load_data("presensi", ttl="5s")
        
        with tab1:
            c1, c2, c3 = st.columns(3)
            f_tgl = c1.date_input("Filter Tanggal", value=None)
            f_kls = c2.selectbox("Filter Kelas", ["Semua"] + list_kelas)
            f_sts = c3.selectbox("Filter Jenis", ["Semua", "Masuk", "Dhuha", "Dzuhur", "Pulang"])
            
            if not df_p.empty:
                df_p['Status Waktu'] = df_p.apply(lambda x: get_attendance_status(x['jenis'], x['waktu']), axis=1)
                dff = df_p.copy()
                if f_tgl: dff = dff[dff['waktu'].str.contains(str(f_tgl))]
                if f_kls != "Semua": dff = dff[dff['kelas'] == f_kls]
                if f_sts != "Semua": dff = dff[dff['jenis'] == f_sts]
                st.dataframe(dff.drop(columns=['foto_absen'], errors='ignore'), use_container_width=True)

        with tab2:
            df_u = load_data("users", ttl="5s")
            if not df_p.empty:
                s_n = st.selectbox("Pilih Siswa Audit", df_p['nama'].unique())
                ur = df_u[df_u['nama'] == s_n]; ua = df_p[df_p['nama'] == s_n].tail(1)
                if not ur.empty and not ua.empty:
                    c1, c2 = st.columns(2)
                    c1.image(f"data:image/jpeg;base64,{ur.iloc[0]['foto_reg']}", caption="Registrasi")
                    c2.image(f"data:image/jpeg;base64,{ua.iloc[0]['foto_absen']}", caption="Presensi")
                    
                    ca, cb = st.columns(2)
                    if ca.button("⚠️ Kirim Peringatan (Beda)"):
                        df_w = load_data("audit_notif")
                        new_w = pd.DataFrame([{"nama": s_n, "pesan": "⚠️ Peringatan Kedisiplinan: Foto absen tidak sesuai dengan data registrasi. Mohon jujur dalam presensi!", "status": "Peringatan", "waktu": now_dt.strftime("%H:%M")}])
                        conn.update(worksheet="audit_notif", data=pd.concat([df_w, new_w], ignore_index=True)); st.warning("Peringatan dikirim!")
                    if cb.button("✅ Validasi (Sesuai)"):
                        df_w = load_data("audit_notif")
                        new_w = pd.DataFrame([{"nama": s_n, "pesan": "✅ Terima kasih telah melakukan presensi dengan jujur.", "status": "Valid", "waktu": now_dt.strftime("%H:%M")}])
                        conn.update(worksheet="audit_notif", data=pd.concat([df_w, new_w], ignore_index=True)); st.success("Validasi dikirim!")

    if st.sidebar.button(L['out']): st.session_state.logged_in_user = None; st.rerun()

if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
