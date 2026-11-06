# Laporan Komposisi dan Keseimbangan Data Multi-Platform
**Proyek Data Mining**: Analisis Sentimen dan Identifikasi Topik Kekhawatiran Masyarakat terhadap Perkembangan AI di Media Sosial  
**Tanggal Eksekusi**: 2026-11-06 13:07:29 UTC  
**Konfigurasi**: `LANG_MODE = en_only`, `TARGET_PER_PLATFORM = 2000`

---

## 1. Ringkasan Keseimbangan 3 Platform (Target 33.3% per Platform)

| Platform | Data Mentah | Lolos Seleksi | Dataset Final | Proporsi Final | Rentang Waktu |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **YouTube** | 3,704 | 3,628 | **2,000** | **33.3%** | 2024-02-18 s/d 2026-11-05 |
| **Reddit** | 2,300 | 2,007 | **2,000** | **33.3%** | 2024-01-01 s/d 2025-07-01 |
| **X (Twitter)** | 2,315 | 2,124 | **2,000** | **33.3%** | 2023-02-18 s/d 2023-02-24 |
| **TOTAL** | **8,319** | **7,759** | **6,000** | **100.0%** | **Seimbang Sempurna** |

---

## 2. Rincian Pembersihan & Filter (Data Pipeline Hygiene)

| Platform | Terbuang: Noise/Pendek | Terbuang: Duplikat ID | Terbuang: Duplikat Teks | Terbuang: Non-Inggris |
| :--- | :---: | :---: | :---: | :---: |
| **YouTube** | 5 | 0 | 62 | 9 |
| **Reddit** | 157 | 0 | 7 | 129 |
| **X** | 7 | 0 | 183 | 1 |

---

## 3. Distribusi Sentimen (RoBERTa)

| platform   |   Negatif |   Netral |   Positif |
|:-----------|----------:|---------:|----------:|
| Reddit     |       839 |      872 |       289 |
| X          |       516 |      969 |       515 |
| YouTube    |       933 |      678 |       389 |

### Deteksi Sarkasme

| platform   |   Tidak |   Ya |
|:-----------|--------:|-----:|
| Reddit     |    1906 |   94 |
| X          |    1904 |   96 |
| YouTube    |    1863 |  137 |

---

## 4. Distribusi Topik Terbanyak per Platform

|                                           |   count |
|:------------------------------------------|--------:|
| ('Reddit', 'Lainnya')                     |    1403 |
| ('Reddit', 'Pekerjaan')                   |     187 |
| ('Reddit', 'Pendidikan')                  |     105 |
| ('Reddit', 'Hak cipta dan kreator')       |      44 |
| ('X', 'Pekerjaan')                        |     531 |
| ('X', 'Pendidikan')                       |     477 |
| ('X', 'Lainnya')                          |     232 |
| ('X', 'Risiko sosial dan etika')          |     184 |
| ('YouTube', 'Lainnya')                    |     996 |
| ('YouTube', 'Pekerjaan')                  |     479 |
| ('YouTube', 'Lingkungan dan sumber daya') |     115 |
| ('YouTube', 'Manfaat dan produktivitas')  |      63 |
