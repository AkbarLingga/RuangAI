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
