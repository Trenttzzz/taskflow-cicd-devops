# Controlled Failure Scenarios

Dokumen ini mendefinisikan skenario failure terkontrol yang dipakai untuk mengukur retrieval dan report AI Failure Intelligence. Semua log di folder `evaluations/controlled-failure-logs/` adalah log kecil yang disusun dari pola failure pipeline TaskFlow, bukan raw log produksi.

| Scenario ID | Log File | Expected Category | Tujuan |
| --- | --- | --- | --- |
| coverage-gate | `controlled-failure-logs/coverage-gate.log` | `coverage-gate` | Menguji apakah sistem mengenali coverage di bawah 75 persen. |
| coverage-gate-unicode | `controlled-failure-logs/coverage-gate-unicode.log` | `coverage-gate` | Menguji coverage failure dengan karakter unicode pada nama file. |
| coverage-gate-new-package | `controlled-failure-logs/coverage-gate-new-package.log` | `coverage-gate` | Menguji coverage failure pada package baru. |
| docker-build | `controlled-failure-logs/docker-build.log` | `docker-build` | Menguji failure pada Docker build atau path build yang salah. |
| docker-build-go-mod | `controlled-failure-logs/docker-build-go-mod.log` | `docker-build` | Menguji failure Docker build karena dependency Go tidak tersedia. |
| docker-build-copy-path | `controlled-failure-logs/docker-build-copy-path.log` | `docker-build` | Menguji failure Docker build karena path file salah. |
| postgres-timeout | `controlled-failure-logs/postgres-timeout.log` | `integration-postgres` | Menguji koneksi PostgreSQL gagal pada integration test. |
| postgres-auth | `controlled-failure-logs/postgres-auth.log` | `integration-postgres` | Menguji PostgreSQL integration failure karena authentication gagal. |
| postgres-migration | `controlled-failure-logs/postgres-migration.log` | `integration-postgres` | Menguji PostgreSQL integration failure karena migration/schema mismatch. |
| security-scan | `controlled-failure-logs/security-scan.log` | `security-scan` | Menguji finding dari govulncheck/gosec. |
| security-gosec | `controlled-failure-logs/security-gosec.log` | `security-scan` | Menguji security failure dari rule gosec. |
| security-govulncheck | `controlled-failure-logs/security-govulncheck.log` | `security-scan` | Menguji security failure dari govulncheck. |
| smoke-test-health | `controlled-failure-logs/smoke-test-health.log` | `smoke-test-health` | Menguji smoke test `/health` gagal karena service tidak ready. |
| smoke-test-stats | `controlled-failure-logs/smoke-test-stats.log` | `smoke-test-health` | Menguji smoke test endpoint `/stats` gagal. |
| smoke-test-container-crash | `controlled-failure-logs/smoke-test-container-crash.log` | `smoke-test-health` | Menguji smoke test gagal karena container exit. |

Evaluasi ini melengkapi demo live. Hasilnya tidak diklaim sebagai bukti generalisasi produksi karena jumlah skenario kecil dan masih controlled logs. Metrik yang dipakai adalah deskriptif: Top-1 accuracy, Top-3 accuracy, similarity score, jumlah OOVD-inspired lines, dan exact sign test terbatas untuk membandingkan dua mode retrieval pada repeated controlled trials.
