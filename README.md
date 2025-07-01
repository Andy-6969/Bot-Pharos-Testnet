# Bot Pharos Testnet (Swap & Liquidity)

Bot ini dirancang untuk mengotomatiskan interaksi dengan ekosistem Pharos Testnet. Bot dapat melakukan tugas-tugas seperti Swap, menambah likuiditas (Add Liquidity), serta melakukan klaim harian untuk memaksimalkan partisipasi Anda di testnet. Dibuat dengan Python, bot ini mendukung banyak akun (multi-account) dan berjalan secara paralel (multi-thread) untuk efisiensi maksimal.

## ✨ Fitur Utama

- **✅ Multi-Akun**: Jalankan tugas untuk semua dompet yang Anda daftarkan di `privatekey.txt`.
- **🚀 Multi-Thread**: Proses beberapa akun secara bersamaan untuk menghemat waktu.
- **📊 Tampilan Info**: Menampilkan informasi penting untuk setiap akun:
    - Saldo Poin (PTS)
    - Status Check-in Harian
    - Status Klaim Faucet
- **🔁 Swap Otomatis**:
    - Melakukan swap PHRS ke token lain di **Zenith DEX**.
    - Melakukan swap PHRS ke USDT di **FaroSwap**.
- **💧 Penambahan Likuiditas**:
    - Secara otomatis membuat posisi likuiditas baru di **Zenith DEX** dengan pasangan PHRS dan token lainnya.
- **⚙️ Konfigurasi Mudah**: Atur semua parameter seperti jumlah swap, jeda waktu, dan fitur yang ingin diaktifkan langsung dari file `bot.py`.
- **🔄 Siklus Otomatis**: Setelah semua akun selesai diproses, bot akan menunggu selama 24 jam sebelum memulai siklus berikutnya secara otomatis.
