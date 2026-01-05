import toml
import gspread
from google.oauth2.service_account import Credentials

# GANTI ID INI DENGAN ID SPREADSHEET ANDA
SPREADSHEET_ID = "1Pax10XvuHdo0Tu8dUk9d_7SYywqZYg9pgCthi5-qbTo"

def test_connection():
    print("--- MULAI DIAGNOSA ---")
    
    # 1. BACA FILE SECRETS
    try:
        secrets = toml.load(".streamlit/secrets.toml")
        creds_data = secrets["gcp_service_account"]
        email_robot = creds_data["client_email"]
        print(f"✅ File secrets.toml ditemukan.")
        print(f"🤖 KODE ANDA LOGIN SEBAGAI: \n   👉 {email_robot}")
        print("   (Pastikan email DI ATAS inilah yang dijadikan Editor di Google Sheet)")
    except Exception as e:
        print(f"❌ Gagal membaca secrets.toml: {e}")
        return

    # 2. COBA KONEK GOOGLE
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        client = gspread.authorize(creds)
        print("✅ Berhasil menghubungi Server Google.")
    except Exception as e:
        print(f"❌ Gagal otentikasi ke Google (Cek Private Key): {e}")
        return

    # 3. COBA BUKA SPREADSHEET
    try:
        sh = client.open_by_key(SPREADSHEET_ID)
        print(f"✅ BERHASIL! Menemukan Spreadsheet: '{sh.title}'")
        print("Masalah selesai. Silakan jalankan dashboard Anda lagi.")
    except Exception as e:
        print("\n❌ GAGAL MEMBUKA SPREADSHEET!")
        print(f"Pesan Error: {e}")
        print("\nSOLUSI:")
        print(f"1. Copy email ini: {email_robot}")
        print("2. Buka Google Sheet -> Klik tombol 'Share' (Bagikan).")
        print("3. Paste email tersebut dan jadikan 'Editor'.")
        print("4. Jika sudah ada, hapus dulu, lalu tambahkan ulang.")

if __name__ == "__main__":
    test_connection()