# Giga OSINT

Toolkit OSINT berbasis terminal dengan menu bertingkat, ratusan fitur, dan tampilan futuristik.
Berjalan di **Termux (Android)**, **Ubuntu/Linux**, macOS, dan Windows.

> **Only Education.** Gunakan hanya untuk belajar, penelitian, dan target milik sendiri atau yang sudah berizin tertulis. Jangan disalah gunakan!

---

## Persyaratan

| Kebutuhan | Keterangan |
|-----------|------------|
| Python    | Versi 3.8 atau lebih baru (disarankan versi terbaru) |
| Git       | Untuk mengunduh dan memperbarui tools |
| Internet  | Dibutuhkan saat memasang tools tambahan dan menjalankan fitur online |

Python 3 sudah cukup untuk menjalankan menu utama. Paket tambahan (misalnya `phonenumbers`, `Pillow`) dan tools pihak ketiga akan dipasang otomatis oleh Giga OSINT **setelah menanyakan y/n** kepada kamu.

---

## Instalasi di Termux (Android)

> Pakai Termux dari **F-Droid** atau GitHub Releases. Versi Play Store sudah lama tidak diperbarui dan sering error.

**Langkah 1 - Perbarui Termux**

```bash
pkg update && pkg upgrade -y
```

Jika muncul pertanyaan `Y/n` atau pilihan konfigurasi, tekan **Enter** untuk memilih bawaan.

**Langkah 2 - Pasang Python dan Git**

```bash
pkg install python git -y
```

**Langkah 3 - Unduh Giga OSINT**

```bash
git clone https://github.com/XyasZor/gs.git
```

**Langkah 4 - Masuk ke folder tools**

```bash
cd gs
```

**Langkah 5 - Jalankan**

```bash
python main.py
```

**Langkah 6 (opsional) - Izinkan akses galeri dan file**

Dibutuhkan jika ada fitur yang membaca foto atau file dari penyimpanan HP.

```bash
termux-setup-storage
```

Tekan **Izinkan** pada jendela yang muncul. Setelah itu file HP bisa diakses lewat `/sdcard/...`.

**Langkah 7 (opsional) - Buat perintah singkat `giga`**

```bash
echo "alias gs='python ~/gs/main.py'" >> ~/.bashrc
source ~/.bashrc
```

Selanjutnya cukup ketik `gs` dari folder mana pun.

> Termux tidak memakai `sudo`. Untuk memasang paket gunakan `pkg install nama_paket`.

---

## Instalasi di Ubuntu / Debian / Kali

**Langkah 1 - Perbarui sistem**

```bash
sudo apt update && sudo apt upgrade -y
```

**Langkah 2 - Pasang Python, pip, venv, dan Git**

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

**Langkah 3 - Unduh Giga OSINT**

```bash
git clone https://github.com/XyasZor/gs.git
```

**Langkah 4 - Masuk ke folder tools**

```bash
cd gs
```

**Langkah 5 - Buat lingkungan virtual (disarankan)**

Ubuntu 23.04 ke atas membatasi `pip` di Python sistem. Dengan venv, paket tambahan terpasang rapi tanpa error.

```bash
python3 -m venv ~/.venv
source ~/.venv/bin/activate
```

Tanda berhasil: di awal baris terminal muncul `(.venv)`.

**Langkah 6 - Jalankan**

```bash
python3 main.py
```

**Langkah 7 (opsional) - Buat perintah singkat `gs`**

```bash
echo "alias gs='~/.venv/bin/python3 ~/gs/main.py'" >> ~/.bashrc
source ~/.bashrc
```

Selanjutnya cukup ketik `gs` dari folder mana pun, tanpa perlu mengaktifkan venv lagi.

> Jangan menjalankan Giga OSINT sebagai root kecuali terpaksa. Jika perintah pemasangan tool meminta hak admin, tambahkan `sudo` di depan perintah yang ditampilkan.

---

## Cara Memakai

Setelah dijalankan, ikuti arahan di layar:

| Input | Fungsi |
|-------|--------|
| Angka, lalu **Enter** | Membuka kategori atau fitur sesuai nomor |
| `0` | Kembali ke menu sebelumnya, atau keluar dari tools di menu utama |
| `/kata` | Mencari fitur, contoh `/nmap` |
| `h` | Menampilkan panduan |

Opsi saat menjalankan:

| Opsi | Fungsi |
|------|--------|
| `--cepat` | Tanpa animasi (cocok untuk SSH atau koneksi lambat) |
| `--ascii` | Simbol ASCII saja (untuk terminal lama) |
| `--polos` | Tanpa warna |
| `--bantuan` | Menampilkan bantuan singkat |

Contoh: `python3 giga_osint.py --cepat`

Jika sebuah fitur butuh tools tambahan, Giga OSINT akan bertanya **y/n** terlebih dahulu sebelum memasangnya. Data, tools, dan hasil pemindaian disimpan di folder `~/.giga_osint`.

---

## Memperbarui

```bash
cd gs
git pull
```

Ubuntu yang memakai venv: jalankan `source ~/.venv/bin/activate` dulu sebelum menjalankan tools.

---

## Masalah Umum

| Masalah | Solusi |
|---------|--------|
| `command not found: python` di Termux | Jalankan `pkg install python -y` |
| `python: command not found` di Ubuntu | Pakai `python3`, bukan `python` |
| `externally-managed-environment` | Pakai venv (Langkah 5 Ubuntu) |
| Pemasangan paket Python gagal di Termux | Jalankan `pkg install build-essential -y`, lalu ulangi |
| Tampilan berantakan atau simbol aneh | Jalankan dengan `--ascii`, atau perbesar jendela terminal |
| Tool berbasis Go gagal dipasang | Ubuntu: `sudo apt install golang` / Termux: `pkg install golang` |
| Sertifikat SSL error | Periksa tanggal dan jam perangkat, lalu `sudo apt install ca-certificates` di Ubuntu |

---

## Disclaimer

Project ini dibuat **Only Education.** Penulis tidak bertanggung jawab atas penyalahgunaan. Pastikan setiap pemindaian hanya dilakukan pada target milik sendiri atau yang sudah memberi izin tertulis, serta patuhi hukum yang berlaku di negaramu.
