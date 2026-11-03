# Analisis Sentimen dan Topik Kekhawatiran AI

Aplikasi data mining untuk mengolah komentar publik tentang AI dari X, Reddit,
dan YouTube. Aplikasi web menggunakan Flask dengan halaman responsif, filter
interaktif, ringkasan visual, ekspor CSV, serta analisis teks langsung. Hasil
preprocessing disimpan sebagai CSV agar dapat dipakai ulang.

## Menjalankan di Windows

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python preprocess.py
python app.py
```

Buka `http://127.0.0.1:5000` di browser.

## Publikasi GitHub Pages

Workflow `.github/workflows/pages.yml` memproses data dan menerbitkan versi
statis website secara otomatis saat perubahan di-push ke branch `main` atau
`master`. Untuk mengaktifkannya di repository GitHub:

1. Buka **Settings → Pages**.
2. Pada **Build and deployment → Source**, pilih **GitHub Actions**.
3. Pastikan file workflow dan file CSV sumber sudah ikut di-push.
4. Buka tab **Actions**, tunggu workflow **Deploy GitHub Pages** selesai.
5. URL website akan tersedia di **Settings → Pages**. Untuk repository ini,
   alamatnya biasanya `https://akbarlingga.github.io/RuangAI/`.

GitHub Pages hanya melayani file statis. Workflow membangun halaman, CSS,
JavaScript, dan data JSON statis; filter dan analisis teks berjalan di browser
tanpa Flask. Untuk membangun versi statis secara lokal, jalankan
`python preprocess.py` lalu `python build_static.py`; hasilnya ada di `_site`.

## Proses data

`preprocess.py` membaca tiga sumber mentah yang tersedia di folder project:

- `x_ai_raw.csv`
- `reddit_ai_raw.csv`
- `komentar_youtube_relevan_dampak_ai_pada_masyarakat.csv`

Proses merapikan URL, mention, HTML entity, hashtag, markdown, emoji, dan spasi;
mengeluarkan teks kosong/placeholder, bot yang terdeteksi, promosi eksplisit,
serta ID ganda dalam sumber yang sama. Teks Inggris dan Indonesia dipertahankan.
File sumber asli tidak diubah. Output ada di
`data/processed/social_ai_processed.csv`, dengan teks mentah dan bersih, platform,
konteks sumber, tanggal, engagement, skor sentimen, label sentimen, dan topik.

Topik ditandai memakai kamus kata kunci yang transparan (pekerjaan, privasi,
deepfake/misinformasi, pendidikan, hak cipta/kreator, lingkungan/sumber daya,
risiko sosial/etika, serta manfaat/produktivitas). Satu komentar dapat memiliki
lebih dari satu topik.

## Batasan analisis

Label sentimen memakai leksikon bilingual dengan aturan negasi sederhana. Ini
bukan model sentimen yang dilatih atau divalidasi; slang, sarkasme, konteks,
campur bahasa, dan istilah yang tidak ada di kamus bisa salah diklasifikasikan.
Label topik juga berbasis kata kunci dan bukan hasil topic modeling statistik.
Sebelum digunakan sebagai hasil penelitian, tinjau sampel secara manual,
perbaiki kamus sesuai korpus, dan laporkan keterbatasan metode.
