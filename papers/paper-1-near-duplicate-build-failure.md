# Reading Notes - Near-Duplicate Build Failure Detection from Continuous Integration Logs

## Identitas Paper

Judul: Near-Duplicate Build Failure Detection from Continuous Integration Logs

Penulis: Mingchen Li, Mika Mantyla, Jesse Nyyssola, Matti Luukkainen

Tahun dan venue: 2025, ACM PROMISE 2025

Topik utama: near-duplicate build failure detection dari log CI/CD.

## Klaim Utama

Paper ini mengklaim bahwa kegagalan build CI/CD yang mirip dengan kegagalan sebelumnya dapat dideteksi menggunakan analisis kemiripan log. Masalah yang diselesaikan adalah developer sering menemukan failure baru yang sebenarnya mirip dengan failure historis, tetapi log CI/CD panjang, noisy, dan tidak langsung reusable sebagai knowledge debugging.

Klaim yang paling relevan untuk proyek TaskFlow adalah bahwa failure log bisa dipakai sebagai basis retrieval. Paper ini tidak hanya melihat status sukses atau gagal, tetapi mencoba menjawab apakah suatu failed run memiliki near-duplicate di histori pipeline. Ini mendukung ide bahwa pipeline TaskFlow tidak cukup hanya memberi status `failed`; pipeline juga perlu membantu developer menemukan failure historis yang relevan.

## Metodologi Paper

Penulis mengumpulkan 410 build logs dari GitHub Actions, terdiri dari 71 failed builds dan 339 passing builds. Dataset berasal dari proyek open source Oodikone, dengan rata-rata sekitar 9.000 baris log per build run dan rentang data sekitar enam bulan. Paper menjelaskan bahwa data lebih lama sulit dikumpulkan karena retensi default log GitHub Actions terbatas.

Near-duplicate failure diberi label berdasarkan failed tests yang sama. Paper lalu membandingkan build logs menggunakan beberapa text distance measures seperti Jaccard distance, cosine similarity, containment distance, dan compression distance. Nilai similarity digabung menggunakan Z-score sum.

Bagian metodologi yang penting adalah filtering log menggunakan Out-of-Vocabulary Detector. Karena banyak baris log failed build sama dengan passing build, paper menggunakan OOVD untuk menonjolkan baris yang lebih failure-relevant. Log juga dipreproses dengan regex masking untuk mengurangi elemen dinamis seperti timestamp dan process ID.

Evaluasi dilakukan dengan Top-K retrieval. Paper memilih K = 5 karena developer tidak realistis membaca terlalu banyak rekomendasi failure historis. Metrik yang digunakan meliputi precision@K dan MAP@K.

## Temuan Kunci

Paper menunjukkan bahwa OOVD filtering meningkatkan hasil retrieval near-duplicate failure. Untuk failed builds, OOVD meningkatkan precision@K dari 0.526 menjadi 0.864 dan MAP@K dari 0.814 menjadi 0.941. Temuan ini berarti retrieval tidak hanya menemukan lebih banyak item relevan, tetapi juga menempatkan item relevan di peringkat atas.

Paper juga menunjukkan bahwa penggunaan seluruh log tanpa filtering kurang efektif karena passing dan failing logs sering berbagi banyak baris umum. Ini penting untuk TaskFlow karena GitHub Actions logs berisi banyak noise seperti setup environment, download dependency, dan output command standar.

## Relevansi Langsung untuk Implementasi TaskFlow

Implementasi TaskFlow mengambil ide utama paper ini: current failure log dibandingkan dengan failure knowledge base, lalu sistem mengambil top-k similar failures. Perbedaannya adalah TaskFlow menggunakan `gemini-embedding-2` untuk semantic embedding, bukan kombinasi distance metrics dan OOVD seperti paper. Namun prinsipnya sama: failure log harus dipreproses dan diretrieval berdasarkan kemiripan.

Keputusan desain yang diambil dari paper ini:

- Failure log perlu dibersihkan sebelum analisis.
- Sistem harus menghasilkan top-k similar failures, bukan hanya satu label.
- Retrieval harus bisa dievaluasi dengan Top-1 dan Top-3 accuracy.
- Failure knowledge base harus menyimpan log, metadata, root cause, dan resolution agar hasil retrieval actionable.
- Pipeline perlu mengekstrak log GitHub Actions sebelum retensi log menghapus data historis.

## Keterbatasan Paper

Paper menggunakan satu proyek open source, sehingga generalisasi ke pipeline lain belum pasti. Label near-duplicate juga berbasis failed tests yang sama, sedangkan TaskFlow memiliki failure category yang lebih beragam seperti coverage gate, Docker build, security scan, PostgreSQL integration, dan smoke test. Paper sendiri menyebut bahwa usefulness retrieval perlu dinilai bersama developer.

Keterbatasan lain adalah pendekatan OOVD bergantung pada vocabulary passing logs. Jika pipeline berubah besar, istilah baru bisa dianggap out-of-vocabulary walaupun bukan failure. Untuk TaskFlow, ini alasan mengapa implementasi awal memilih cleaned log plus embedding similarity yang lebih sederhana untuk demo satu minggu.

## Hal yang Diragukan atau Perlu Dikritisi

Pertanyaan utama dari paper ini adalah apakah near-duplicate berdasarkan failed tests yang sama selalu berarti root cause sama. Dalam praktik CI/CD, dua failure bisa gagal pada step yang sama tetapi root cause berbeda, misalnya `/health` gagal karena port binding atau karena database unreachable. Karena itu, TaskFlow tidak langsung menggunakan top-1 retrieval sebagai diagnosis final. LLM report tetap diminta menampilkan evidence, top-k candidate, dan batasan analisis.

## Implikasi untuk Evaluasi Proyek

Paper ini menjadi dasar evaluasi retrieval. Metrik TaskFlow yang mengikuti paper:

- Top-1 retrieval accuracy.
- Top-3 retrieval accuracy.
- Similarity score.
- Log cleaning effect secara kualitatif.
- Usefulness report bagi developer.

Untuk skala proyek ini, K disederhanakan menjadi 3 agar report tetap ringkas dan cocok dengan konteks demo.

