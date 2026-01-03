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
    .notif-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #059669; background: #f0fdf4; }
    .terlambat-text { color: #dc2626; font-weight: bold; }
    .highlight-sholat { background: #fef9c3; border: 2px solid #facc15; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 15px; }
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
                conn.update(worksheet="users", data=pd.concat([df_u, new_u], ignore_index=True)); st.success("Registrasi Berhasil!")

# --- 5. DASHBOARD ---
def show_dashboard():
    u = st.session_state.logged_in_user
    st.sidebar.title(f"👤 {u['nama']}")
    menu_opt = ["🏠 Home", f"📍 {L['absen_h']}", f"{L['tugas']}", L['spp']]
    if u['role'] in ["Guru", "Admin TU"]: menu_opt += [L['broadcast'], L['lapor']]
    choice = st.sidebar.radio("Menu", menu_opt)

    if choice == "🏠 Home":
        st.subheader(f"Dashboard {u['role']}")
        st.markdown(f"""<div class='highlight-sholat'><b>🕌 Jadwal Sholat Hari Ini - Banjarnegara</b><br>
            Subuh: 04:15 | Dzuhur: 11:52 | Ashar: 15:18 | Maghrib: 18:07 | Isya: 19:22</div>""", unsafe_allow_html=True)
        with st.expander("📅 Jadwal Sholat 1 Bulan (Banjarnegara)"):
            ds = {"Tanggal": [f"{i} Jan" for i in range(1, 32)], "Subuh": ["04:15"]*31, "Dzuhur": ["11:52"]*31, "Maghrib": ["18:07"]*31}
            st.dataframe(pd.DataFrame(ds), hide_index=True)

        if u['role'] == "Siswa":
            # Peringatan Kejujuran dari Admin/Guru
            df_wn = load_data("audit_notif", ttl="5s")
            if not df_wn.empty:
                my_w = df_wn[df_wn['nama'] == u['nama']].tail(3)
                for _, w in my_w.iterrows():
                    st.warning(f"{w['pesan']} ({w['waktu']})")

    elif choice == L['spp']:
        st.subheader(L['spp'])
        st.info(f"👤 **Nama Siswa:** {u['nama']}")
        st.success("✅ Tidak ada tunggakan SPP.")

    elif choice == f"{L['tugas']}":
        df_done = load_data("tugas_selesai", ttl="5s")
        if u['role'] == "Guru":
            st.subheader("Daftar Siswa Selesai Tugas")
            st.dataframe(df_done, use_container_width=True)
            st.download_button("📥 Export Excel", df_done.to_csv().encode('utf-8'), "tugas.csv", "text/csv")
        else:
            st.subheader("Tugas Selesai")
            st.table(df_done[df_done['nama'] == u['nama']])

    elif choice == L['lapor']:
        tab1, tab2 = st.tabs(["📊 Data Presensi", "🔍 Audit Wajah"])
        df_p = load_data("presensi", ttl="5s")
        
        with tab1:
            c1, c2 = st.columns(2)
            f_t = c1.date_input("Filter Tanggal", value=None)
            f_k = c2.selectbox("Filter Kelas", ["Semua"] + list_kelas)
            if not df_p.empty:
                df_p['Status'] = df_p.apply(lambda x: get_attendance_status(x['jenis'], x['waktu']), axis=1)
                dff = df_p.copy()
                if f_t: dff = dff[dff['waktu'].str.contains(str(f_t))]
                if f_k != "Semua": dff = dff[dff['kelas'] == f_k]
                
                def style_tr(v):
                    return 'color: red; font-weight: bold' if v == 'Terlambat' else ''
                st.dataframe(dff.style.applymap(style_tr, subset=['Status']), use_container_width=True)

        with tab2:
            df_u = load_data("users", ttl="5s")
            s_n = st.selectbox("Pilih Siswa", df_p['nama'].unique()) if not df_p.empty else None
            if s_n:
                ur = df_u[df_u['nama'] == s_n]; ua = df_p[df_p['nama'] == s_n].tail(1)
                if not ur.empty and not ua.empty:
                    c1, c2 = st.columns(2)
                    c1.image(f"data:image/jpeg;base64,{ur.iloc[0]['foto_reg']}", caption="Reg")
                    c2.image(f"data:image/jpeg;base64,{ua.iloc[0]['foto_absen']}", caption="Absen")
                    if st.button("⚠️ Kirim Peringatan"):
                        df_w = load_data("audit_notif")
                        nw = pd.DataFrame([{"nama": s_n, "pesan": "⚠️ Foto absen tidak sesuai!", "waktu": now_dt.strftime("%H:%M")}])
                        conn.update(worksheet="audit_notif", data=pd.concat([df_w, nw]))
                        st.warning("Terkirim!")

    elif choice == L['broadcast']:
        with st.form("bc"):
            tj = st.text_input("Judul"); ti = st.text_area("Isi")
            if st.form_submit_button("📢 Broadcast"):
                df_b = load_data("broadcast")
                nb = pd.DataFrame([{"judul": tj, "isi": ti, "target": "Semua Kelas", "tanggal": str(now_dt.date())}])
                conn.update(worksheet="broadcast", data=pd.concat([df_b, nb]))
                st.success("Berhasil!")

    if st.sidebar.button(L['out']): st.session_state.logged_in_user = None; st.rerun()

if st.session_state.logged_in_user is None: show_auth()
else: show_dashboard()
