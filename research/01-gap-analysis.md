# Gap Analysis - AI Failure Intelligence for CI/CD

## Ringkasan Gap

Pipeline TaskFlow sudah mampu mendeteksi kegagalan melalui CI, security scan, Docker build, dan smoke test. Namun pipeline masih lemah dalam menggunakan kembali knowledge dari failure sebelumnya. Ketika pipeline gagal, developer masih harus membaca log mentah, mencari bagian error yang relevan, mengingat apakah error serupa pernah terjadi, lalu menyimpulkan root cause secara manual.

Gap final yang diselesaikan proyek ini adalah:

> Pipeline CI/CD sudah mendeteksi failure, tetapi belum menyediakan failure intelligence yang menghubungkan current failure dengan failure historis atau synthetic validated failure knowledge, serta belum menghasilkan report debugging yang evidence-based.

## Dasar dari Paper Utama

Li et al. (2025) secara eksplisit menyebut masalah near-duplicate build failures, yaitu kondisi ketika developer menemukan build failure baru yang sebenarnya mirip dengan failure sebelumnya. Paper tersebut menunjukkan bahwa log CI/CD dapat dianalisis untuk menemukan build failure yang mirip. Mereka juga menekankan bahwa log CI/CD panjang dan noisy, sehingga perlu preprocessing dan filtering sebelum similarity analysis.

Temuan yang paling penting adalah penggunaan Top-K retrieval untuk membantu developer melihat candidate failure yang mirip. Dengan OOVD filtering, paper melaporkan precision@K meningkat dari 0.526 menjadi 0.864 dan MAP@K meningkat dari 0.814 menjadi 0.941. Ini mendukung keputusan TaskFlow untuk membuat top-k similar failure retrieval, bukan hanya mengirim notifikasi failure biasa.

## Dasar dari Paper Pendukung

Saidani et al. (2022) menunjukkan bahwa histori CI build dapat dimanfaatkan untuk automation berbasis AI. Paper tersebut memperkenalkan DL-CIBuild yang menggunakan LSTM-RNN untuk memprediksi build failure dari urutan build outcome historis. Evaluasinya memakai 91.330 build records dari 10 proyek open source.

Relevansi paper ini untuk TaskFlow bukan pada replikasi LSTM, melainkan pada argumen bahwa data historis CI/CD memiliki nilai operasional. Paper ini juga menyoroti masalah data imbalance dan concept drift. Dalam konteks TaskFlow, real failed logs masih sedikit, sehingga knowledge base awal memakai synthetic validated logs untuk mengurangi cold-start.

## Gap pada Pipeline TaskFlow Sebelum Enhancement

Sebelum enhancement, pipeline hanya memberi sinyal seperti:

```text
job failed
step failed
exit code 1
coverage below threshold
curl failed
```

Sinyal tersebut cukup untuk mendeteksi bahwa pipeline gagal, tetapi belum cukup untuk mempercepat diagnosis. Developer masih perlu membuka raw log dan mencari sendiri:

- step apa yang gagal,
- kategori failure apa yang paling mungkin,
- apakah failure serupa pernah terjadi,
- evidence log mana yang mendukung root cause,
- command debugging apa yang sebaiknya dijalankan.

## Gap Data

GitHub Actions logs bersifat sementara dan noisy. Li et al. (2025) menyebut bahwa mereka hanya dapat mengumpulkan data historis dalam rentang terbatas karena retensi log GitHub Actions. Ini menjadi alasan TaskFlow perlu mengekstrak failure logs dan menyimpannya ulang sebagai knowledge base.

Pada tahap implementasi saat ini, TaskFlow sudah memiliki synthetic validated logs untuk lima kategori awal:

- coverage gate,
- Docker build,
- PostgreSQL integration timeout,
- security scan,
- smoke test health.

Implementasi terbaru menutup gap pengumpulan dengan mengarsipkan cleaned failure log secara otomatis ke branch `failure-history`. Entry baru tetap provisional dengan `validated: false`, sehingga belum masuk embedding index sampai developer mengonfirmasi category, root cause, dan resolution. Live verification branch archive tetap perlu dilakukan setelah workflow terbaru dijalankan di GitHub Actions.

## Gap Evaluasi

Sebelum enhancement, tidak ada metrik retrieval karena sistem tidak melakukan retrieval. Setelah enhancement, sistem bisa dievaluasi dengan:

- Top-1 retrieval accuracy,
- Top-3 retrieval accuracy,
- similarity score,
- pipeline overhead,
- diagnosis time reduction,
- report usefulness score.

Metrik tersebut mengikuti arah evaluasi Li et al. (2025), khususnya Top-K retrieval. Untuk scope TaskFlow, K dibuat menjadi 3 agar report tetap ringkas dan mudah dibaca.

## Pernyataan Gap Final

Pipeline TaskFlow membutuhkan AI Failure Intelligence karena status failure saja tidak cukup untuk mempercepat debugging. Berdasarkan Li et al. (2025), near-duplicate build failure dapat ditemukan dari log similarity analysis. Berdasarkan Saidani et al. (2022), histori CI/CD dapat dimanfaatkan untuk automation berbasis AI. Proyek ini menggabungkan kedua insight tersebut menjadi sistem practical: cleaned failure log diubah menjadi embedding, dibandingkan dengan failure knowledge base, lalu LLM membuat report root cause dan debugging steps berbasis evidence.
