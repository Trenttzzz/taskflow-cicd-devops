# synthetic-005-smoke-test-health

Category: `smoke-test-health`

Root cause: container aktif tetapi endpoint `/health` gagal karena aplikasi belum ready atau dependency database bermasalah.

Resolution: cek `docker logs taskflow-api`, port `8080`, `DATABASE_URL`, dan hasil health check database.

Evidence: log berisi `curl: (22)` dan `database ping failed`.
