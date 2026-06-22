# synthetic-003-postgres-timeout

Category: `integration-postgres`

Root cause: test integration gagal karena koneksi PostgreSQL timeout atau refused.

Resolution: cek service container PostgreSQL, `DATABASE_URL`, port `5432`, health check, dan migrasi database.

Evidence: log berisi `context deadline exceeded` dan `connect: connection refused`.
