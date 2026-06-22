# Evaluation Analysis

## Ringkasan Hasil

Evaluasi awal menunjukkan bahwa AI Failure Intelligence sudah bekerja untuk skenario coverage gate failure, 15 repeated controlled failure scenarios, dan satu live GitHub Actions failure demo. Sistem berhasil membedakan success path dan failure path. Pada success path, sistem tidak memanggil embedding API atau LLM API. Pada failure path dengan `GEMINI_API_KEY`, sistem membuat embedding index, mengambil top-3 similar failures, dan menghasilkan report dari `gemini-3.1-flash-lite`.

Untuk skenario coverage gate lokal, retrieval berhasil menempatkan kategori yang benar sebagai rank 1. Similarity top-1 adalah 0.8830 untuk `synthetic-001-coverage-gate`. Report yang dihasilkan juga konsisten dengan evidence log, yaitu coverage 72.8 persen di bawah threshold 75 persen. Pada evaluasi 15 repeated controlled scenarios, mode `full_cleaned_log` menghasilkan Top-1 accuracy 15/15 dan Top-3 accuracy 15/15. Mode `oovd_focused_log` menghasilkan Top-1 accuracy 14/15 dan Top-3 accuracy 15/15. Pada live GitHub Actions demo, coverage aktual 78.9 persen gagal terhadap threshold demo 101 persen, dan retrieval menempatkan `coverage-gate` sebagai Top-1 dengan similarity 0.8329.

## Apakah Enhancement Menjawab Gap?

Enhancement menjawab gap utama secara teknis. Sebelum enhancement, pipeline hanya memberi raw log dan status failure. Setelah enhancement, pipeline dapat menghasilkan:

- kategori failure yang paling mirip,
- similarity score,
- likely root cause,
- evidence dari log,
- debugging steps.

Hal ini sesuai dengan arah Li et al. (2025), yaitu menggunakan log similarity untuk menemukan near-duplicate build failure. TaskFlow belum mereplikasi OOVD model penuh, tetapi sudah menerapkan log cleaning, semantic embedding retrieval, dan OOVD-inspired filtering ringan.

Enhancement juga sesuai dengan argumen Saidani et al. (2022) bahwa historical CI data dapat menjadi input AI automation. TaskFlow tidak melakukan build prediction, tetapi menggunakan failure history sebagai knowledge base untuk diagnosis.

## Analisis Success Path

Success path penting karena sistem tidak boleh memanggil AI secara berlebihan. Hasil pengujian menunjukkan:

```text
Pipeline succeeded. No AI failure analysis needed.
Pipeline sukses. Embedding API dan LLM API tidak dipanggil.
```

Ini sesuai dengan keputusan desain. AI layer hanya aktif saat ada failure, sehingga biaya, latency, dan noise tetap terkendali.

## Analisis Failure Path

Failure path berhasil menjalankan seluruh alur inti:

```text
failure status -> embedding index -> retrieval -> LLM report
```

Retrieval juga masuk akal. Input log menunjukkan coverage di bawah threshold, dan top-1 result adalah `coverage-gate`. Rank 2 dan rank 3 memiliki similarity sekitar 0.70, tetapi kategorinya tidak tepat. Ini wajar karena knowledge base masih kecil dan semua synthetic logs berbagi konteks CI/CD. Dengan real logs dan lebih banyak kategori, pemisahan similarity diharapkan menjadi lebih jelas.

Evaluasi kemudian diperluas ke 15 repeated controlled scenarios. Setiap kategori utama memiliki tiga variasi log agar evaluasi tidak hanya mengulang satu contoh per kategori. Pada mode `full_cleaned_log`, semua skenario menghasilkan top-1 category yang sesuai dengan expected category. Ini menunjukkan bahwa knowledge base awal cukup kuat untuk kategori dasar pipeline TaskFlow, meskipun hasil ini belum boleh dianggap sebagai generalisasi produksi.

## Analisis OOVD-Inspired Filtering

Implementasi baru menambahkan OOVD-inspired filtering ringan. Berbeda dari Li et al. (2025), sistem ini tidak melatih OOVD model dari passing logs. Sebagai gantinya, script cleaning memakai vocabulary CI umum dan memberi score pada baris yang memiliki token tidak biasa. Hasilnya disimpan sebagai JSON agar bisa diperiksa dan dipakai oleh LLM report.

Jumlah OOVD-inspired lines pada base controlled scenarios adalah:

| Scenario | OOVD Lines |
| --- | ---: |
| coverage-gate | 2 |
| docker-build | 6 |
| postgres-timeout | 4 |
| security-scan | 5 |
| smoke-test-health | 5 |

Sinyal ini membantu menonjolkan baris yang lebih failure-relevant, seperti `coverprofile`, `buildx failed`, `connection refused`, `reachable vulnerability`, dan `Failed to connect to localhost`. Ini adalah kompromi praktis antara paper dan scope final project: idenya mengikuti OOVD, tetapi implementasinya tetap ringan dan tanpa dependency baru.

OOVD-focused query juga dievaluasi sebagai mode retrieval terpisah. Hasilnya Top-1 accuracy 14/15 dan Top-3 accuracy 15/15. Satu miss terjadi pada variasi `smoke-test-container-crash`, ketika OOVD-focused query menempatkan `integration-postgres` sebagai Top-1 dan kategori benar `smoke-test-health` sebagai rank 2. Ini memperjelas posisi OOVD-inspired filtering: berguna untuk menonjolkan suspicious lines dan membantu report, tetapi belum lebih baik daripada full cleaned log sebagai query retrieval utama.

## Analisis Repeated Trial dan Exact Sign Test

Repeated trial di sini berarti satu kategori failure diuji dengan beberapa variasi log terkontrol. Tujuannya bukan mengklaim dataset besar, tetapi mengurangi risiko evaluasi yang terlalu bergantung pada satu contoh.

Perbandingan berpasangan antara `full_cleaned_log` dan `oovd_focused_log` menghasilkan:

| Metric | Full Wins | OOVD Wins | Ties | Exact Sign Test p-value |
| --- | ---: | ---: | ---: | ---: |
| Top-1 correctness | 1 | 0 | 14 | 1.0000 |
| Top-3 correctness | 0 | 0 | 15 | 1.0000 |

Hasil ini tidak menunjukkan improvement statistik dari OOVD-focused query. Hampir semua trial tie, sehingga p-value hanya menjadi catatan deskriptif bahwa tidak ada bukti perbedaan pada dataset kecil ini.

## Analisis Report

Report LLM tidak mengarang root cause di luar evidence. Pada controlled coverage failure, report menyebut coverage 72.8 persen, threshold 75 persen, dan command test coverage yang relevan. Pada live GitHub Actions demo, report menyebut coverage 78.9 persen di bawah threshold 101 persen dan menandai threshold tersebut sebagai misconfiguration. Suggested debugging steps juga actionable.

Keterbatasannya adalah report masih bergantung pada cleaned log. Jika log collection dari GitHub Actions gagal atau log terlalu sedikit, report akan menjadi fallback atau menyatakan evidence belum cukup.

## Perbandingan Before vs After

| Aspek | Before | After |
| --- | --- | --- |
| Failure detection | Ada | Ada |
| Similar failure retrieval | Tidak ada | Ada |
| Knowledge base | Tidak ada | Ada |
| Root cause report | Tidak ada | Ada |
| Evidence extraction | Manual | Otomatis dari cleaned log |
| Debugging steps | Manual | Dibuat oleh LLM berdasarkan evidence |
| AI call saat success | Tidak ada | 0 call |
| Failure artifact | Raw logs saja | AI report dan similar failures JSON |
| OOVD-style signal | Tidak ada | Ada, OOVD-inspired JSON |

## Keterbatasan Evaluasi

Evaluasi saat ini sudah mencakup local controlled failure dan satu live GitHub Actions failure demo. Lima belas skenario lokal mengukur stabilitas retrieval, sedangkan live demo membuktikan integrasi pipeline dan artifact `ai-reports` benar-benar berjalan di GitHub Actions. Namun jumlah live failure masih kecil, sehingga klaim produksi tetap harus dibatasi.

Skenario yang disarankan:

| Skenario | Cara Memicu | Expected Category |
| --- | --- | --- |
| Coverage gate failure | Naikkan threshold coverage sementara atau kurangi test | coverage-gate |
| PostgreSQL integration failure | Ubah `DATABASE_URL` pada branch test | integration-postgres |
| Smoke test health failure | Ubah endpoint health sementara pada branch test | smoke-test-health |

Jika ingin memperkuat evaluasi lebih lanjut, lakukan dua live run tambahan dan simpan:

- current failed log,
- `similar-failures.json`,
- `failure-intelligence-report.md`,
- durasi job `failure-intelligence`,
- apakah top-1 dan top-3 sesuai.

## Kesimpulan Evaluasi

MVP AI Failure Intelligence sudah berhasil. Sistem tidak memanggil AI saat success dan berhasil menghasilkan AI report saat failure dengan real API key. Retrieval pada 15 repeated controlled scenarios menghasilkan Top-1 accuracy 15/15 dan Top-3 accuracy 15/15 untuk full cleaned log. Live GitHub Actions failure demo juga berhasil mengambil category `coverage-gate` sebagai Top-1 dengan similarity 0.8329. OOVD-inspired filtering menghasilkan sinyal tambahan yang dapat diperiksa, tetapi evaluasi menunjukkan mode tersebut lebih tepat dipakai sebagai pendukung report daripada pengganti query retrieval utama.
