# State of the Art - AI for CI/CD Failure Intelligence

## Landscape Masalah

CI/CD modern sudah sangat baik dalam automation build, test, scan, dan deployment. Namun sebagian besar pipeline masih memberi feedback dalam bentuk status dan raw log. Dalam praktik DevSecOps, feedback seperti ini belum cukup karena developer masih harus melakukan diagnosis manual.

Riset terbaru bergerak ke dua arah yang relevan. Arah pertama adalah similarity-based failure retrieval, yaitu mencari failure historis yang mirip dengan current failure. Arah kedua adalah predictive CI intelligence, yaitu memanfaatkan histori build untuk memprediksi outcome atau failure pattern.

## Near-Duplicate Failure Retrieval

Li et al. (2025) memperkenalkan near-duplicate build failure detection dari CI logs. Paper ini berada sangat dekat dengan proyek TaskFlow karena sama-sama bekerja pada log CI/CD dan sama-sama menggunakan top-k retrieval. Paper tersebut menggunakan data GitHub Actions, melakukan preprocessing log, menerapkan OOVD filtering, lalu menghitung similarity untuk menemukan failure yang relevan.

State of the art dari paper ini menunjukkan bahwa:

- failure logs bisa dibandingkan secara otomatis,
- log perlu dibersihkan dari noise,
- Top-K recommendation relevan untuk developer,
- filtering failure-relevant lines meningkatkan retrieval quality.

TaskFlow mengadaptasi prinsip tersebut, tetapi mengganti metode similarity menjadi embedding-based semantic similarity dengan `gemini-embedding-2`. Perubahan ini dipilih karena knowledge base TaskFlow kecil, kategori failure beragam, dan semantic embedding lebih mudah digunakan untuk log pendek atau ringkasan failure.

TaskFlow juga menambahkan OOVD-inspired filtering ringan. Implementasi ini tidak melatih OOVD model dari passing logs seperti paper, tetapi memakai vocabulary CI umum untuk memberi score pada baris yang mengandung token tidak biasa. Outputnya digunakan sebagai sinyal tambahan untuk report, bukan sebagai classifier utama.

## CI Build Failure Prediction

Saidani et al. (2022) memperkenalkan DL-CIBuild untuk memprediksi CI build failure menggunakan LSTM-RNN. Paper ini menunjukkan bahwa historical CI data memiliki pola temporal yang bisa dipelajari. Evaluasinya jauh lebih besar daripada TaskFlow, yaitu 91.330 builds dari 10 proyek.

State of the art dari paper ini menunjukkan bahwa:

- histori CI/CD dapat dipakai untuk automation berbasis AI,
- failed builds memiliki nilai informasi tinggi,
- class imbalance adalah masalah penting,
- model training membutuhkan data besar, tuning, dan evaluasi serius.

TaskFlow tidak mengimplementasikan prediksi LSTM karena dataset lokal belum cukup. Namun paper ini mendukung keputusan bahwa failure history tidak boleh hilang sebagai raw logs sementara. Failure history perlu dijadikan knowledge base.

## Posisi TaskFlow dalam State of the Art

TaskFlow mengambil posisi sebagai practical adaptation, bukan full replication. Sistem yang dibuat bukan model prediksi build outcome, tetapi failure intelligence layer setelah failure terjadi.

Arsitektur TaskFlow:

```text
Pipeline failure
  -> collect failed log
  -> clean and mask log
  -> embed current failure with gemini-embedding-2
  -> compare with knowledge base embeddings
  -> retrieve top-3 similar failures
  -> generate report with gemma-4-31b-it
```

Sistem ini lebih kecil daripada arsitektur paper, tetapi langsung terintegrasi dengan pipeline GitHub Actions yang sudah ada. Fokusnya bukan meningkatkan predictive accuracy, melainkan meningkatkan feedback quality setelah failure.

## Perbandingan dengan Paper

| Aspek | Li et al. 2025 | Saidani et al. 2022 | TaskFlow |
| --- | --- | --- | --- |
| Input utama | GitHub Actions logs | Travis CI build outcomes | GitHub Actions failure logs |
| Tujuan | Near-duplicate retrieval | Build failure prediction | Failure retrieval dan AI report |
| Teknik utama | OOVD filtering, log similarity | LSTM-RNN, GA tuning | Gemini embedding, cosine similarity, Gemma report |
| Evaluasi | precision@K, MAP@K | AUC, F1, accuracy | Top-1, Top-3, similarity, repeated controlled trials |
| Kebutuhan data | Banyak failed dan passing logs | 91.330 builds | Knowledge base kecil dan bertahap |
| Output | Similar build failures | Prediksi pass/fail | Debugging report berbasis evidence |

## Novelty pada Konteks Tugas

Nilai tambah TaskFlow bukan pada klaim membuat algoritma baru. Nilai tambahnya adalah integrasi praktis ke pipeline DevSecOps:

- AI hanya dipanggil saat failure.
- Embedding dan LLM memakai satu API key.
- Retrieval tetap terukur dan tidak sepenuhnya diserahkan ke LLM.
- LLM hanya menjadi explanation layer.
- Knowledge base memisahkan synthetic validated logs dan real logs.
- Report menjadi artifact pipeline dan dapat dikirim ke Telegram.

## Batas State of the Art yang Tidak Diambil

TaskFlow tidak mengambil beberapa bagian dari paper karena tidak realistis untuk scope satu minggu:

- Tidak training LSTM.
- Tidak membuat OOVD model penuh dari passing logs; yang dibuat adalah OOVD-inspired filtering ringan.
- Tidak melakukan statistical significance test skala paper; yang dilakukan hanya exact sign test deskriptif pada repeated controlled trials kecil.
- Tidak menggunakan ribuan historical build records.
- Tidak membuat vector database eksternal.

Keputusan ini menjaga implementasi tetap sederhana, reproducible, dan bisa didemokan live.
