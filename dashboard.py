import streamlit as st
import pandas as pd
import gspread
from gspread.utils import rowcol_to_a1
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
from PIL import Image
import base64
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Dashboard Mesin Las",
    page_icon="🛠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNGSI UNTUK BACKGROUND GAMBAR ---
def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception as e:
        return None

# Tentukan path gambar background di sini
# Ganti path ini sesuai lokasi gambar di laptop Anda
bg_image_path = "pal-main.png" 
img_base64 = get_img_as_base64(bg_image_path)

# Logic CSS Background
if img_base64:
    # Angka 0.9 pada rgba menunjukkan tingkat ketebalan warna penutup (90% tertutup, 10% gambar)
    # Ubah 0.9 menjadi 0.7 jika ingin gambar lebih jelas, atau 0.95 jika ingin lebih tipis
    page_bg_img = f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(244, 246, 249, 0.8), rgba(244, 246, 249, 0.8)), 
                          url("data:image/png;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """
else:
    # Fallback jika gambar tidak ditemukan
    page_bg_img = """
    <style>
    .stApp {
        background-color: #F4F6F9;
    }
    </style>
    """

# --- INJECT CSS UTAMA ---
st.markdown(page_bg_img, unsafe_allow_html=True)

st.markdown("""
    <style>
    /* 1. Background Sidebar */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.95); /* Putih sedikit transparan */
        box-shadow: 2px 0 5px rgba(0,0,0,0.05);
    }

    /* 2. Styling Header Utama */
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 5px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 25px;
    }

    /* 3. Card KPI Style */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.9); /* Sedikit transparan agar menyatu */
        border-radius: 12px;
        padding: 15px;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
    }

    div[data-testid="stMetricLabel"] {
        color: #64748B;
        font-size: 0.9rem;
    }

    div[data-testid="stMetricValue"] {
        color: #1E293B;
        font-weight: bold;
    }

    /* 4. Tombol Submit & Primary */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* 5. Mempercantik Tabel & Chart (Container Putih) */
    div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"], 
    [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(255, 255, 255, 0.95); /* Putih solid/semi-transparan */
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: none !important;
    }

    /* Dark mode adjustment */
    @media (prefers-color-scheme: dark) {
        .stApp { background-color: #0E1117; background-image: none; }
        div[data-testid="stMetric"], div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"] {
            background-color: #262730;
            border: 1px solid #464b5c;
            box-shadow: none;
        }
        .main-header { color: #4A90E2; }
    }
    </style>
    
""", unsafe_allow_html=True)

# --- KONEKSI KE GOOGLE SHEETS ---
@st.cache_resource
def get_gsheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    return client

# Perintah Delete Data
def delete_data_from_sheet(ws, row_index):
    try:
        ws.delete_rows(row_index)
        return True
    except Exception as e:
        st.error(f"Gagal menghapus data: {e}")
        return False

# --- FUNGSI PARSING TANGGAL PINTAR ---
def parse_flexible_date(date_val):
    if not date_val:
        return datetime.today().date()
        
    date_str = str(date_val).strip()
    if date_str == "":
        return datetime.today().date()

    try:
        return pd.to_datetime(date_str, dayfirst=True, errors='coerce').date()
    except:
        pass

    month_map = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'mei': '05',
        'jun': '06', 'jul': '07', 'aug': '08', 'agu': '08', 'sep': '09', 'oct': '10', 'okt': '10',
        'nov': '11', 'dec': '12', 'des': '12'
    }
    
    try:
        clean_str = date_str.replace('-', ' ').replace('/', ' ')
        parts = clean_str.split()
        
        if len(parts) == 3:
            day, mon, year = parts
            mon_lower = mon.lower()
            
            if mon_lower in month_map:
                mon_num = month_map[mon_lower]
                if len(year) == 2: year = '20' + year
                iso_date = f"{year}-{mon_num}-{day.zfill(2)}"
                return datetime.strptime(iso_date, "%Y-%m-%d").date()
    except:
        pass
        
    return datetime.today().date()

def load_data():
    client = get_gsheet_client()
    sh = client.open("ALAT UKUR_Merged") 
    worksheet = sh.worksheet("Merge")
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        df.columns = df.columns.str.strip()
        
    return df, worksheet

# --- FUNGSI CEK STATUS OTOMATIS ---
def run_auto_status_check(df, worksheet):
    if 'Status' in df.columns and 'Kalibrasi berikutnya' in df.columns:
        today = datetime.today().date()
        updates_to_push = []
        
        try:
            headers = worksheet.row_values(1) 
            status_col_idx = headers.index('Status') + 1
            status_col_letter = rowcol_to_a1(1, status_col_idx)[:-1]
        except:
            status_col_letter = 'I'

        count_updated = 0
        for index, row in df.iterrows():
            try:
                status_now = str(row.get('Status', '')).strip().upper()
                tgl_next_raw = row.get('Kalibrasi berikutnya', '')
                
                if status_now == 'DONE':
                    tgl_next = parse_flexible_date(tgl_next_raw)
                    if str(tgl_next_raw).strip() != "" and tgl_next <= today:
                        sheet_row = index + 2
                        updates_to_push.append({
                            'range': f"{status_col_letter}{sheet_row}",
                            'values': [['RE CAL']]
                        })
                        count_updated += 1
            except Exception:
                pass
        
        if updates_to_push:
            try:
                worksheet.batch_update(updates_to_push)
                st.toast(f"✅ Berhasil mengubah status {count_updated} alat menjadi 'RE CAL'", icon='🤖')
                return True
            except Exception as e:
                st.error(f"Gagal update otomatis: {e}")
                return False
        else:
            st.toast("Semua status sudah sesuai, tidak ada update.", icon='👍')
            return False

# --- FUNGSI UPDATE & TAMBAH DATA ---
def add_data_to_sheet(worksheet, data_row):
    worksheet.append_row(data_row)
    st.toast('Data berhasil ditambahkan!', icon='✅')

def update_data_in_sheet(worksheet, row_number, data_row):
    worksheet.update(range_name=f"A{row_number}:M{row_number}", values=[data_row])
    st.toast('Data berhasil diperbarui!', icon='🔄')

# --- LOGIKA UTAMA ---
try:
    df, worksheet = load_data()
    
    if 'Status' in df.columns:
        df['Status'] = df['Status'].astype(str).str.upper().str.strip()

    # --- SIDEBAR NAVIGASI ---
    with st.sidebar:
        # Menampilkan gambar di sidebar juga (opsional)
        try:
            st.image('Logo PT PAL.jpg', use_container_width=True)
        except:
            st.write("Logo PT PAL")
            
        st.title("🗂 Navigasi")
        pilihan_halaman = st.radio(
            "Pilih Menu:", 
            ["📊 Dashboard Utama", "📝 Input & Edit Data", "⏰ Reminder Kalibrasi", "📂 Database Lengkap"],
            index=0
        )
        
        st.markdown("---")
        st.caption("🚀 Dashboard Version 2.9 (Asset Monitoring)")

    # =========================================================================
    # HALAMAN 1: DASHBOARD UTAMA
    # =========================================================================
    if pilihan_halaman == "📊 Dashboard Utama":
        with st.container(border=True):
            st.markdown('<div class="main-header">Dashboard Monitoring Aset</div>', unsafe_allow_html=True)
            st.markdown('<div class="sub-header">Overview status kalibrasi dan kondisi mesin secara real-time</div>', unsafe_allow_html=True)
        
        total_asset = len(df)
        total_rusak = len(df[df['Status'] == 'RUSAK'])
        total_done = len(df[df['Status'] == 'DONE'])
        total_recal = len(df[df['Status'] == 'RE CAL'])
        OOT = len(df[df['Status'] == 'OOT'])

        kp1, kp2, kp3, kp4, kp5 = st.columns(5)
        kp1.metric("📦 Total Aset", f"{total_asset}", "Unit Terdaftar")
        kp2.metric("✅ Siap Pakai", f"{total_done}", f"{round(total_done/total_asset*100,1) if total_asset > 0 else 0}%")
        kp3.metric("⚠ Perlu Kalibrasi", f"{total_recal}", "Segera Tindak Lanjuti", delta_color="inverse")
        kp4.metric("❌ Rusak", f"{total_rusak}", "Butuh Perbaikan", delta_color="inverse")
        kp5.metric("⏳ OOT", f"{OOT}", "OOT", delta_color="inverse")
        st.markdown("---")

        col_chart_1, col_chart_2 = st.columns([1.5, 1])

        with col_chart_1:
            st.subheader("📊 Distribusi Aset per Divisi")
            if 'DIVISI' in df.columns and 'Status' in df.columns:
                chart_data = df.groupby(['DIVISI', 'Status']).size().reset_index(name='Jumlah')
                fig_bar = px.bar(
                    chart_data, 
                    x="DIVISI", y="Jumlah", color="Status", 
                    barmode="group",
                    color_discrete_map={"DONE": "#00C853", "RUSAK": "#FF3D00", "RE CAL": "#FFD600", "OOT": "#888888"},
                    template="plotly_white"
                )
                fig_bar.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        with col_chart_2:
            st.subheader("🍩 Persentase Kondisi")
            status_counts = df['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Jumlah']
            fig_pie = px.pie(
                status_counts, values='Jumlah', names='Status', 
                color='Status',
                hole=0.6,
                color_discrete_map={"DONE": "#00C853", "RUSAK": "#FF3D00", "RE CAL": "#746C40", "OOT": "#888888"}
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=False
            )
            fig_pie.update_traces(textinfo='percent+label', textposition='inside')
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown("---")
        
        # --- BAGIAN BARU: CHART MONITORING BULANAN ---
        st.subheader("📅 Monitoring Expired Bulanan")
        st.caption("Lihat jumlah alat yang akan habis masa kalibrasinya pada bulan tertentu berdasarkan Divisi.")

        with st.container(border=True):
            # UBAH LAYOUT: Jadi 2 Kolom (Kiri: Filter & Info, Kanan: Chart)
            c_kiri, c_kanan = st.columns([1, 2.5])
            
            # --- KOLOM KIRI: KONTROL & RINGKASAN ---
            with c_kiri:
                st.markdown("##### 🎛️ Filter Periode")
                
                # 1. Filter (Disusun vertikal agar mengisi ruang)
                nama_bulan_indo = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
                bulan_sekarang_idx = datetime.now().month - 1
                tahun_sekarang = datetime.now().year

                dash_bulan_str = st.selectbox("Pilih Bulan", nama_bulan_indo, index=bulan_sekarang_idx, key="dash_month_select")
                dash_tahun_val = st.number_input("Pilih Tahun", min_value=2020, value=tahun_sekarang, key="dash_year_select")
                
                st.divider() # Garis pemisah visual

                # Proses Filter Data
                dash_bulan_num = nama_bulan_indo.index(dash_bulan_str) + 1
                
                df_monitor = df.copy()
                df_monitor['parsed_date'] = pd.to_datetime(
                    df_monitor['Kalibrasi berikutnya'].apply(parse_flexible_date), 
                    errors='coerce' 
                )
                df_monitor = df_monitor.dropna(subset=['parsed_date'])

                df_filtered_dash = df_monitor[
                    (df_monitor['parsed_date'].dt.month == dash_bulan_num) & 
                    (df_monitor['parsed_date'].dt.year == dash_tahun_val)
                ]

                # 2. Menampilkan KPI / Ringkasan Statistik
                if not df_filtered_dash.empty:
                    total_items = len(df_filtered_dash)
                    
                    # Mencari Divisi dengan jumlah terbanyak
                    chart_div_data = df_filtered_dash.groupby('DIVISI').size().reset_index(name='Jumlah')
                    top_div = chart_div_data.loc[chart_div_data['Jumlah'].idxmax()]
                    
                    # Tampilkan Metric
                    st.metric(
                        label="🚨 Total Aset Expired",
                        value=f"{total_items} Unit",
                        delta="Segera Kalibrasi",
                        delta_color="inverse"
                    )
                    
                    st.metric(
                        label="🏗️ Terbanyak di Divisi",
                        value=top_div['DIVISI'],
                        help=f"Sebanyak {top_div['Jumlah']} unit"
                    )
                    
                    st.write("") # Spasi
                else:
                    st.success("Tidak ada data expired.")

            # --- KOLOM KANAN: CHART ---
            with c_kanan:
                if not df_filtered_dash.empty:
                    # Buat Bar Chart
                    fig_monthly_div = px.bar(
                        chart_div_data, 
                        x="DIVISI", 
                        y="Jumlah",
                        color="DIVISI", 
                        text="Jumlah",
                        title=f"Grafik Sebaran Aset Expired: {dash_bulan_str} {dash_tahun_val}",
                        template="plotly_white",
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    
                    fig_monthly_div.update_traces(textposition='outside')
                    fig_monthly_div.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        height=400, # Tinggi chart agar pas
                        margin=dict(t=40, b=0, l=0, r=0)
                    )
                    
                    st.plotly_chart(fig_monthly_div, use_container_width=True)
                else:
                    st.image("https://cdn-icons-png.flaticon.com/512/4076/4076478.png", width=150)
                    st.subheader(f"Aman! Bulan {dash_bulan_str} {dash_tahun_val} Kosong.")
                    st.caption("Tidak ada alat yang perlu dikalibrasi pada periode ini.")
    # =========================================================================
    # HALAMAN 2: INPUT, UPDATE & DELETE DATA
    # =========================================================================
    elif pilihan_halaman == "📝 Input & Edit Data":
        with st.container(border=True):
            st.markdown('<div class="main-header">Manajemen Data</div>', unsafe_allow_html=True)
            st.markdown('<div class="sub-header">Kelola data aset: Tambah, Update, atau Hapus.</div>', unsafe_allow_html=True)
        
        with st.container(border=True):
            col_mode_1, col_mode_2 = st.columns([1, 3])
            with col_mode_1:
                st.markdown("### 🛠 Pilih Aksi")
            with col_mode_2:
                mode = st.radio("", ["Tambah Data Baru", "Update Data Lama", "Hapus Data"], horizontal=True, label_visibility="collapsed")

        default_val = {
            "kode": "", "nama": "", "merk": "", "no_seri": "", "range": "",
            "tgl_kal": datetime.today().date(), "tgl_next": datetime.today().date(),
            "divisi": "KANIA", "status": "DONE", "kategori": "ALAT UKUR", "ket": ""
        }
        selected_row_index = None
        current_no = len(df) + 1

        if mode != "Tambah Data Baru": 
            if df.empty:
                st.warning("Data kosong, tidak bisa melakukan aksi ini.")
                st.stop()
            
            st.write(" ")
            col_search_1, col_search_2 = st.columns([3, 1])
            with col_search_1:
                df['label'] = df['Kodefikasi'].astype(str) + " - " + df['Nama Alat'].astype(str)
                pilihan_aset = st.selectbox("🔍 Cari Aset (Ketik Kode atau Nama):", df['label'].tolist())
            
            selected_data = df[df['label'] == pilihan_aset].iloc[0]
            
            try:
                if 'No.' in selected_data:
                    current_no = int(selected_data['No.'])
                elif 'No' in selected_data:
                    current_no = int(selected_data['No'])
                else:
                    current_no = 0
            except:
                current_no = 0
            
            default_val["kode"] = selected_data.get('Kodefikasi', '')
            default_val["nama"] = selected_data.get('Nama Alat', '')
            default_val["merk"] = str(selected_data.get('Merk / Type', ''))
            default_val["no_seri"] = str(selected_data.get('No. Seri', ''))
            default_val["range"] = str(selected_data.get('Range', ''))
            default_val["divisi"] = selected_data.get('DIVISI', 'KANIA')
            default_val["status"] = selected_data.get('Status', 'DONE')
            default_val["kategori"] = selected_data.get('KATEGORI', 'ALAT UKUR')
            default_val["ket"] = str(selected_data.get('KETERANGAN', ''))
            default_val["tgl_kal"] = parse_flexible_date(selected_data.get('Tgl Kalibrasi'))
            default_val["tgl_next"] = parse_flexible_date(selected_data.get('Kalibrasi berikutnya')) 

            row_idx_pandas = df[df['label'] == pilihan_aset].index[0]
            selected_row_index = int(row_idx_pandas + 2)

        st.markdown("---")

        with st.form("data_form", clear_on_submit=(mode == "Tambah Data Baru")):
            is_disabled = (mode == "Hapus Data")
            
            if mode == "Hapus Data":
                st.warning("⚠️ **PERHATIAN: ANDA DALAM MODE HAPUS DATA**")
                st.info("Silakan cek data di bawah ini. Jika tombol 'Hapus' ditekan, data akan hilang permanen.")

            st.markdown("#### 1️⃣ Identitas Alat")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.text_input("No. Urut", value=current_no, disabled=True)
                kode = st.text_input("Kodefikasi", value=default_val["kode"], placeholder="Contoh: MS-LAS-01", disabled=is_disabled)
            with c2:
                nama = st.text_input("Nama Alat", value=default_val["nama"], placeholder="Contoh: Mesin Las Trafo", disabled=is_disabled)
                merk = st.text_input("Merk / Type", value=default_val["merk"], disabled=is_disabled)
            with c3:
                no_seri = st.text_input("No. Seri", value=default_val["no_seri"], disabled=is_disabled)
                Range = st.text_input("Range", value=default_val["range"], disabled=is_disabled)

            st.write("")
            st.markdown("#### 2️⃣ Jadwal Kalibrasi & Status")
            with st.container(border=True):
                col_dates_1, col_dates_2 = st.columns(2)
                with col_dates_1:
                    tgl_kal = st.date_input("📅 Tgl Kalibrasi Terakhir", value=default_val["tgl_kal"], disabled=is_disabled)
                    list_divisi = ["KANIA", "KAPSEL", "KAPRANG", "REKUM", "HCM", "HARKAN"]
                    idx_div = list_divisi.index(default_val["divisi"]) if default_val["divisi"] in list_divisi else 0
                    divisi = st.selectbox("🏢 Divisi Pemilik", list_divisi, index=idx_div, disabled=is_disabled)

                with col_dates_2:
                    tgl_next = st.date_input("📅 Jadwal Kalibrasi Berikutnya", value=default_val["tgl_next"], disabled=is_disabled)
                    list_status = ["DONE", "RUSAK", "OOT", "RE CAL"]
                    idx_stat = list_status.index(default_val["status"]) if default_val["status"] in list_status else 0
                    status = st.selectbox("🚦 Status Kondisi", list_status, index=idx_stat, disabled=is_disabled)
                    if default_val["status"] == "RE CAL" and mode == "Update Data Lama":
                        st.caption("ℹ Status otomatis menjadi 'RE CAL' karena jadwal kalibrasi sudah lewat.")

            st.write("")
            st.markdown("#### 3️⃣ Detail Tambahan")
            list_kat = ["ALAT UKUR", "DATA MESIN LAS"]
            idx_kat = list_kat.index(default_val["kategori"]) if default_val["kategori"] in list_kat else 0
            kategori = st.radio("Kategori Aset", list_kat, index=idx_kat, horizontal=True, disabled=is_disabled)
            Keterangan = st.text_area("Catatan / Keterangan", value=default_val["ket"], placeholder="Tambahkan catatan...", disabled=is_disabled)

            st.write(" ")
            
            if mode == "Hapus Data":
                confirm_delete = st.checkbox("✅ Saya yakin ingin menghapus data ini secara permanen")
                submitted = st.form_submit_button("🗑️ Hapus Data Sekarang", type="primary")
            else:
                submitted = st.form_submit_button(f"💾 Simpan Data ({mode})", type="primary")

            if submitted:
                if mode == "Hapus Data":
                    if confirm_delete:
                        try:
                            delete_data_from_sheet(worksheet, selected_row_index)
                            st.success(f"Data {kode} berhasil dihapus!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menghapus: {e}")
                    else:
                        st.error("Mohon centang konfirmasi untuk menghapus.")
                
                else: 
                    is_valid = True
                    clean_kode = str(kode).strip()
                    existing_codes = df['Kodefikasi'].astype(str).str.strip().tolist()

                    if not clean_kode:
                        st.error("⛔ Kodefikasi tidak boleh kosong!")
                        is_valid = False
                    elif mode == "Tambah Data Baru":
                        if clean_kode in existing_codes:
                            st.error(f"⛔ Error: Kodefikasi '{clean_kode}' sudah ada di database.")
                            is_valid = False
                    elif mode == "Update Data Lama":
                        original_code = str(default_val["kode"]).strip()
                        if clean_kode != original_code and clean_kode in existing_codes:
                            st.error(f"⛔ Error: Kodefikasi '{clean_kode}' sudah digunakan oleh alat lain.")
                            is_valid = False

                    if is_valid:
                        row_data = [
                            int(current_no), kode, nama, merk, no_seri, Range,
                            str(tgl_kal), str(tgl_next), status, "DONE",
                            divisi, kategori, Keterangan
                        ]
                        try:
                            if mode == "Tambah Data Baru":
                                add_data_to_sheet(worksheet, row_data)
                            else:
                                update_data_in_sheet(worksheet, selected_row_index, row_data)
                            
                            st.success("Data berhasil disimpan ke server!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan: {e}")

    # =========================================================================
    # HALAMAN 3: REMINDER KALIBRASI 
    # =========================================================================
    elif pilihan_halaman == "⏰ Reminder Kalibrasi":
        with st.container(border=True):
            st.markdown('<div class="main-header">Reminder Kalibrasi</div>', unsafe_allow_html=True)
            st.info("💡 Tekan tombol di bawah untuk memeriksa dan memperbarui status alat yang kedaluwarsa secara otomatis.")
        
        if st.button("🔄 Cek & Update Status Kedaluwarsa", type="primary"):
            with st.spinner("Sedang memeriksa data..."):
                updated = run_auto_status_check(df, worksheet)
                if updated:
                    st.rerun()

        st.divider()

        nama_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        sekarang = datetime.now()
        
        col_filter1, col_filter2 = st.columns([2, 1])
        with col_filter1:
            pilih_bulan_str = st.selectbox("📅 Pilih Bulan:", nama_bulan, index=sekarang.month - 1)
        with col_filter2:
            pilih_tahun = st.number_input("📅 Pilih Tahun:", min_value=2020, value=sekarang.year)

        bulan_pilihan_angka = nama_bulan.index(pilih_bulan_str) + 1

        with st.container(border=True):
            st.markdown(f'<div class="sub-header">Daftar alat yang jadwal kalibrasinya jatuh pada bulan <b>{pilih_bulan_str} {pilih_tahun}</b>.</div>', unsafe_allow_html=True)
        
        # --- PROSES FILTER DATA ---
        df_reminder = df.copy()
        # Parsing tanggal
        df_reminder['parsed_date'] = pd.to_datetime(
            df_reminder['Kalibrasi berikutnya'].apply(parse_flexible_date), 
            errors='coerce' 
        )
        df_reminder = df_reminder.dropna(subset=['parsed_date'])
        
        if not df_reminder.empty:
            # 1. Filter Awal Berdasarkan Bulan & Tahun
            df_final = df_reminder[
                (df_reminder['parsed_date'].dt.month == bulan_pilihan_angka) & 
                (df_reminder['parsed_date'].dt.year == pilih_tahun)
            ].copy()

            # 2. Filter Divisi
            list_divisi_opsi = ["Tampilkan Semua"] + sorted(df['DIVISI'].astype(str).unique().tolist())
            filter_divisi = st.selectbox("📂 Filter Berdasarkan Divisi:", list_divisi_opsi)
            
            if filter_divisi != "Tampilkan Semua":
                df_final = df_final[df_final['DIVISI'] == filter_divisi]
            
            # 3. Filter Pencarian (Search Box) - REVISI DISINI
            # Menggunakan text_input agar saat mengetik, tabel langsung terfilter
            keyword_pencarian = st.text_input("🔍 Filter Berdasarkan Alat (Ketik Kode atau Nama):", placeholder="Contoh: Las, MS-001...")
    
            if keyword_pencarian:
                # Filter jika Kodefikasi ATAU Nama Alat mengandung kata kunci (case insensitive)
                mask = (df_final['Kodefikasi'].astype(str).str.contains(keyword_pencarian, case=False)) | \
                       (df_final['Nama Alat'].astype(str).str.contains(keyword_pencarian, case=False))
                df_final = df_final[mask]

            # --- MENAMPILKAN DATA ---
            count_due = len(df_final)
            
            if count_due > 0:
                st.warning(f"⚠ Ditemukan *{count_due}* alat yang perlu dikalibrasi pada {pilih_bulan_str} {pilih_tahun}!")
                df_final = df_final.sort_values(by='parsed_date', ascending=True)

                cols_to_show = ["Kodefikasi", "Nama Alat", "Merk / Type", "Kalibrasi berikutnya", "DIVISI", "Status"]
                cols_final = [c for c in cols_to_show if c in df_final.columns]
                cols_for_display = cols_final + ['parsed_date']

                def highlight_urgency(row):
                    try:
                        target_date = row['parsed_date'].date()
                        today = datetime.now().date()
                        diff = (target_date - today).days
                        if diff <= 7:
                            return ['background-color: #ffb3b3; color: black'] * len(row) # Merah muda (H-7)
                        elif diff <= 14:
                            return ['background-color: #ffdfba; color: black'] * len(row) # Oranye muda (H-14)
                        else:
                            return [''] * len(row)
                    except:
                        return [''] * len(row)

                styled_df = df_final[cols_for_display].style.apply(highlight_urgency, axis=1)

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    column_config={
                        "Kalibrasi berikutnya": st.column_config.DateColumn("Jatuh Tempo", format="DD/MM/YYYY"),
                        "Status": st.column_config.TextColumn("Status", width="small"),
                        "parsed_date": None
                    },
                    hide_index=True
                )
            else:
                # Pesan jika data tidak ditemukan setelah filter
                if filter_divisi == "Tampilkan Semua" and not keyword_pencarian:
                    st.success(f"✅ Tidak ada jadwal kalibrasi untuk bulan {pilih_bulan_str} {pilih_tahun}. Aman!")
                else:
                    st.info(f"ℹ️ Data tidak ditemukan dengan kriteria filter saat ini.")

        else:
            st.info("Tidak ditemukan data tanggal kalibrasi yang valid untuk diproses.")
    # =========================================================================
    # HALAMAN 4: DATABASE LENGKAP
    # =========================================================================
    elif pilihan_halaman == "📂 Database Lengkap":
        st.markdown('<div class="main-header">Database Aset</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Tampilan tabel lengkap seluruh data aset.</div>', unsafe_allow_html=True)
        
        with st.container(border=True):
            col_filt_1, col_filt_2 = st.columns([1, 4])
            with col_filt_1:
                st.markdown("##### 🌪 Filter Data")
            with col_filt_2:
                filter_status = st.multiselect("Pilih Status:", df['Status'].unique(), placeholder="Tampilkan semua...")
        
        if filter_status:
            df_display = df[df['Status'].isin(filter_status)]
        else:
            df_display = df
            
        st.dataframe(
            df_display, 
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn("Status Kondisi", width="medium"),
                "Tgl Kalibrasi": st.column_config.DateColumn("Tgl Kalibrasi", format="DD/MM/YYYY"),
                "Kalibrasi berikutnya": st.column_config.DateColumn("Next Kalibrasi", format="DD/MM/YYYY"),
            },
            hide_index=True
        )

except Exception as e:
    st.error(f"Terjadi kesalahan sistem: {e}")
    with st.expander("Lihat Detail Error"):
        st.write(e)
    st.info("Tips: Pastikan koneksi internet stabil dan file secrets.toml sudah dikonfigurasi dengan benar.")