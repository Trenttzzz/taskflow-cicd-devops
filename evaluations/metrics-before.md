# Metrics Before Enhancement

## Baseline yang Dievaluasi

Baseline adalah pipeline TaskFlow sebelum AI Failure Intelligence. Pipeline sudah menjalankan CI, test, coverage gate, security scan, Docker build, dan smoke test. Namun ketika failure terjadi, output utama masih berupa raw GitHub Actions log dan status job.

Baseline tidak memiliki:

- failure knowledge base,
- semantic retrieval,
- top-k similar failures,
- AI-generated root cause summary,
- debugging steps berbasis evidence,
- artifact khusus failure intelligence.

## Baseline Workflow

Alur sebelum enhancement:

```text
Pipeline gagal
  -> GitHub Actions menandai job failed
  -> developer membuka raw log
  -> developer mencari error manual
  -> developer menebak kategori failure
  -> developer menentukan debugging steps sendiri
```

## Baseline Metrics

| Metrik | Nilai Baseline | Catatan |
| --- | ---: | --- |
| AI call saat success | 0 | Tidak ada AI layer |
| AI call saat failure | 0 | Tidak ada AI layer |
| Top-1 retrieval accuracy | N/A | Tidak ada retrieval |
| Top-3 retrieval accuracy | N/A | Tidak ada retrieval |
| Similar failure recommendation | Tidak tersedia | Developer harus mengingat failure historis sendiri |
| Root cause summary artifact | Tidak tersedia | Hanya raw log |
| Debugging steps artifact | Tidak tersedia | Harus disusun manual |
| Evidence extraction | Manual | Developer membaca raw log |
| Pipeline overhead AI | 0 detik | Karena belum ada AI layer |

## Baseline Controlled Failure

Controlled failure yang digunakan untuk membandingkan baseline adalah coverage gate failure. Cuplikan log:

```text
Run go test ./... -coverprofile=coverage.out -covermode=atomic
ok   github.com/taskflow/api/internal/handler      0.041s  coverage: 68.4% of statements
ok   github.com/taskflow/api/internal/service      0.025s  coverage: 72.1% of statements
total:                                          (statements) 72.8%
Total coverage: 72.8%
Coverage 72.8% is below 75%
Error: Process completed with exit code 1.
```

Pada baseline, developer bisa menyimpulkan bahwa coverage gate gagal, tetapi kesimpulan itu murni dari pembacaan manual. Tidak ada rekomendasi failure serupa atau report otomatis.

## Risiko Baseline

Risiko utama baseline adalah lambatnya diagnosis ketika log panjang. Pada failure sederhana seperti coverage gate, diagnosis manual masih mudah. Namun pada failure yang lebih noisy seperti Docker build, PostgreSQL timeout, atau smoke test failure, developer perlu membaca lebih banyak log dan mungkin mengulang investigasi yang sudah pernah dilakukan.

Baseline juga tidak menyimpan knowledge dari failure sebelumnya. Setelah failure diperbaiki, insight debugging tidak otomatis menjadi reusable knowledge untuk pipeline berikutnya.

