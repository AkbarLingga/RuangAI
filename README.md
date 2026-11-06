# Analisis Sentimen dan Topik Kekhawatiran AI

Aplikasi data mining untuk mengolah komentar publik tentang AI dari X, Reddit,
dan YouTube. Aplikasi web menggunakan Flask dengan halaman responsif, filter
interaktif, ringkasan visual, ekspor CSV, serta analisis teks langsung. Hasil
preprocessing disimpan sebagai CSV agar dapat dipakai ulang.

## Struktur folder

```text
analysis/        Kode pengolahan: cleaning, sentimen, topik, model, evaluasi
scraping/        Kode pengambilan data dari X dan Reddit
web/             Semua file penyokong website
  app.py           Server Flask
  build_static.py  Pembuat versi GitHub Pages
  templates/       Halaman HTML
  static/          CSS dan JavaScript
data/
  raw/           BELUM dibersihkan, dipisah per platform (x, reddit, youtube)
    archive/     Data YouTube mentah versi lama
  interim/       Gabungan data mentah, BELUM dibersihkan
  cleaned/       SUDAH dibersihkan, versi lama per platform (belum diseimbangkan)
  processed/     SUDAH dibersihkan, diseimbangkan, dan diberi label; dipakai web
    archive/     Hasil analisis versi lama
reports/         Laporan komposisi data
docs/            Proposal
tests/           Tes otomatis
```

## Menjalankan di Windows

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python web/app.py
```

Buka `http://127.0.0.1:5000` di browser.

## Memperbarui data X dan Reddit

Untuk mengambil sampel ulang dari arsip publik X dan Reddit, jalankan:

```powershell
python scraping/refresh_social_sources.py
python analysis/preprocess.py
```

File `data/raw/x/x_ai_refreshed_raw.csv` dan
`data/raw/reddit/reddit_ai_refreshed_raw.csv` memakai kolom
yang sama dengan CSV YouTube. Proses refresh mengambil 1.624 posting X dari
arsip publik yang tersedia (541–542 per bulan, Desember 2022–Februari 2023)
dan 1.632 komentar Reddit, tersebar 48 komentar per bulan dari Januari
2024–Oktober 2026. Data X berasal dari arsip riset, bukan pencarian
langsung/live di X; berkas arsip Parquet 80 MB memerlukan PyArrow, yang
dipasang bersama requirements. Setelah preprocessing, grafik tren menampilkan
bulan yang memiliki data; periode arsip X memang berbeda dari periode Reddit
dan YouTube.

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
`python analysis/preprocess.py` lalu `python web/build_static.py`; hasilnya ada di `_site`.

## Proses data

`analysis/preprocess.py` membaca tiga sumber mentah berikut:

- `data/raw/x/x_ai_refreshed_raw.csv`
- `data/raw/reddit/reddit_ai_refreshed_raw.csv`
- `data/raw/archive/komentar_youtube_relevan_dampak_ai_pada_masyarakat.csv`

Proses merapikan URL, mention, HTML entity, hashtag, markdown, emoji, dan spasi;
mengeluarkan teks kosong/placeholder, bot yang terdeteksi, promosi eksplisit,
serta ID ganda dalam sumber yang sama. Teks Inggris dan Indonesia dipertahankan.
File sumber asli tidak diubah. Output ada di
`data/processed/social_ai_processed.csv`, dengan teks mentah dan bersih, platform,
konteks sumber, tanggal, engagement, skor sentimen, polaritas ternormalisasi,
label sentimen, dan topik.

Dashboard memvisualisasikan distribusi sentimen, perbandingan platform, topik,
tren persentase sentimen per bulan yang dipisah menurut platform, serta distribusi
polaritas seluruh data bersih. Setiap grafik tren menghitung persentase dalam
platform masing-masing, mengikuti filter aktif, dan tooltip titik menunjukkan
jumlah komentar untuk membaca persentase sesuai ukuran sampelnya. Bulan tanpa
data tidak dihubungkan oleh garis; platform dengan data di satu bulan menampilkan
pesan bahwa datanya belum cukup untuk menunjukkan tren. Tren menggambarkan
dataset dan tidak dapat langsung dianggap sebagai perubahan opini populasi.
Polaritas per komentar dihitung
dari skor leksikon dibagi jumlah kata sentimen, lalu dibatasi pada rentang -1
sampai +1; ringkasan polaritas tidak mengikuti filter dashboard.

Analyzer juga menampilkan probabilitas Logistic Regression TF-IDF. Model saat
ini dilatih dari label leksikon pada dataset bersih, sehingga probabilitasnya
belum dikalibrasi atau tervalidasi terhadap anotasi manusia dan bukan ukuran
akurasi. Gunakan alur anotasi dan evaluasi di bagian berikut sebelum
menafsirkan hasil sebagai performa model untuk penelitian.

## Validasi dan perbandingan model sentimen

Label kamus di dashboard berfungsi sebagai baseline, bukan label kebenaran.
Untuk mengukur kinerja secara lebih bertanggung jawab, buat sampel anotasi
berstrata menurut platform dan label baseline:

```powershell
python analysis/evaluate_sentiment.py sample --size 300 --seed 42
```

Beri label secara manual pada kolom `human_sentiment` di
`data/annotations/sentiment_annotations.csv` dengan nilai `Positif`, `Netral`,
atau `Negatif`. Gunakan panduan anotasi yang konsisten. Bila ada dua anotator,
mereka dapat memberi label pada salinan sampel yang terpisah lalu menyepakati
label akhir di kolom tersebut. File yang sudah ada tidak ditimpa.

Setelah ketiga kelas memiliki cukup anotasi, jalankan:

```powershell
python analysis/evaluate_sentiment.py evaluate --test-size 0.2 --seed 42
```

Perintah ini membandingkan baseline kamus dengan pipeline TF-IDF dan Logistic
Regression pada pembagian train/test berstrata yang sama. Vectorizer hanya
dilatih pada data train untuk menghindari kebocoran data. Accuracy, macro-F1,
confusion matrix, precision, recall, dan F1 per kelas disimpan ke
`data/evaluation/sentiment_evaluation.json`. Sampel 300 komentar adalah titik
awal untuk evaluasi kelas; hasilnya tidak otomatis menjadi label dashboard dan
belum tentu mewakili populasi. Tinjau kecukupan sampel, konsistensi anotator,
dan bias platform sebelum menarik kesimpulan.

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
