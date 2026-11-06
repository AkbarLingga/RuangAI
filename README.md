# Analisis Sentimen dan Topik Kekhawatiran AI

Aplikasi data mining untuk mengolah komentar publik tentang AI dari X, Reddit,
dan YouTube. Sentimen dan sarkasme diklasifikasikan oleh model Transformer
(RoBERTa, turunan BERT), tanpa kamus kata positif dan negatif. Hasilnya
ditampilkan di dashboard Flask dengan filter, grafik, ekspor CSV, serta analisis
teks langsung.

## Struktur folder

```text
analysis/        Kode pengolahan: cleaning, topik, model Transformer, evaluasi
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
pip install -r requirements-ml.txt
python web/app.py
```

Buka `http://127.0.0.1:5000` di browser. Dashboard hanya butuh
`requirements.txt`. Paket di `requirements-ml.txt` diperlukan untuk fitur analisis
teks langsung dan untuk memproses ulang data. Saat pertama dipakai, model diunduh
dari Hugging Face.

## Proses data

Dataset dibuat oleh satu perintah:

```powershell
python analysis/merge_social_data.py
```

Urutannya:

1. Membaca data mentah di `data/raw/x`, `data/raw/reddit`, dan `data/raw/youtube`.
2. Membersihkan URL, mention, HTML entity, hashtag, markdown, dan emoji.
3. Membuang noise, ID ganda, teks ganda, dan teks bukan bahasa Inggris.
4. Mengambil 2.000 komentar per platform dengan batas dominasi per sumber.
5. Mengklasifikasikan sentimen dan sarkasme dengan model Transformer.
6. Menandai topik memakai kata kunci.
7. Menyimpan `data/processed/social_ai_processed.csv` dan laporan di `reports/`.

Proses ini memakan waktu sekitar 20 menit di CPU.

## Model

| Tugas | Model |
| --- | --- |
| Sentimen | `cardiffnlp/twitter-roberta-base-sentiment-latest` |
| Sarkasme | `cardiffnlp/twitter-roberta-base-irony` dan `jkhan447/sarcasm-detection-RoBerta-base-CR` |

**Sentimen.** Label adalah kelas dengan probabilitas tertinggi. Polaritas adalah
probabilitas positif dikurangi probabilitas negatif, dengan rentang -1 sampai +1.

**Sarkasme.** Skor sarkasme adalah skor terendah dari kedua model, dan komentar
ditandai kalau skornya minimal 0,8. Dua model dipakai karena satu model saja
terlalu sering menandai komentar tulus. Tanda sarkasme tidak mengubah label
sentimen.

Aturan ini diuji pada dua data berlabel yang seimbang, masing-masing 400 teks:

| Data uji | Presisi | Recall |
| --- | ---: | ---: |
| Komentar Reddit (`marcbishara/sarcasm-on-reddit`) | 0,85 | 0,19 |
| iSarcasm (`viethq1906/isarcasm_2022_taskA_En`) | 0,86 | 0,31 |

Separuh data uji adalah sarkasme, jadi presisi pada data asli bisa lebih rendah.
Recall yang rendah berarti banyak sarkasme yang tidak terdeteksi.

## Dashboard

Grafik tren dihitung per platform dan mengikuti filter aktif. Platform dengan data
lebih dari satu bulan ditampilkan per bulan. Data X hanya ada pada 18–24 Februari
2023, jadi X ditampilkan per hari. Tren menggambarkan dataset, bukan perubahan
opini masyarakat secara umum. Ringkasan polaritas memakai seluruh data dan tidak
mengikuti filter.

Fitur analisis teks langsung menjalankan model di server Flask, jadi hanya
tersedia di server lokal.

## Validasi dengan label manual

Buat file Excel untuk diberi label oleh manusia:

```powershell
python analysis/evaluate_sentiment.py sample --size 300 --seed 42
```

Sampel berisi 260 komentar acak dan 40 komentar tambahan bertanda sarkasme. Isi
`human_sentiment` dan `human_sarcasm` di `data/annotations/label_manual.xlsx`.
File itu tidak memuat jawaban model, yang disimpan terpisah di
`data/annotations/sentiment_annotations.csv`. File yang sudah ada tidak ditimpa.
Lalu jalankan:

```powershell
python analysis/evaluate_sentiment.py evaluate
```

Accuracy, macro-F1, confusion matrix, precision, recall, dan F1 per kelas dihitung
dari 260 komentar acak. Komentar tambahan hanya dipakai untuk presisi tanda
sarkasme. Hasilnya disimpan di `data/evaluation/sentiment_evaluation.json`.

### Hasil validasi

Label manual diisi oleh satu orang pada 99 komentar: 86 acak dan 13 tambahan
bertanda sarkasme.

| Ukuran | Hasil | Dasar |
| --- | ---: | --- |
| Akurasi sentimen | 41,9% | 86 komentar acak |
| Macro-F1 sentimen | 0,40 | 86 komentar acak |
| Akurasi sarkasme | 59,3% | 86 komentar acak |
| Recall sarkasme | 5,9% (2 dari 34) | 86 komentar acak |
| Presisi tanda sarkasme | 50% (9 dari 18) | 99 komentar |

Sampel ini kecil dan labelnya belum diperiksa orang kedua, jadi hasilnya perlu
dibaca sebagai perkiraan awal. Pemberi label menandai 34 dari 86 komentar acak
sebagai sarkasme, jauh lebih banyak daripada yang ditandai model.

## Publikasi GitHub Pages

Workflow `.github/workflows/pages.yml` menerbitkan versi statis website saat ada
push ke `main` atau `master`, memakai dataset yang sudah ada di `data/processed`.
Alamatnya `https://akbarlingga.github.io/RuangAI/`. Untuk membangunnya secara
lokal, jalankan `python web/build_static.py`; hasilnya ada di `_site`.

## Batasan analisis

- Validasi manual masih kecil, dan akurasi sentimen pada sampel itu hanya 41,9%.
- Model sentimen dilatih dari tweet, sedangkan sebagian data berasal dari Reddit dan
  YouTube. Model juga ditujukan untuk teks bahasa Inggris.
- Topik masih berbasis kata kunci, bukan topic modeling.
- Data X hanya mencakup satu minggu dan sebagian besar dipilih memakai kata kunci
  kekhawatiran, jadi perbandingan antarplatform perlu dibaca hati-hati.
- Sebagian besar data Reddit berasal dari Januari dan Juni 2024.
