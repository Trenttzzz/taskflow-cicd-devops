# synthetic-001-coverage-gate

Category: `coverage-gate`

Root cause: total coverage turun di bawah batas 75 persen.

Resolution: jalankan `go test ./... -coverprofile=coverage.out -covermode=atomic`, cek package dengan coverage rendah, lalu tambahkan test pada branch penting yang belum tercakup.

Evidence: log berisi `Coverage 72.8% is below 75%`.
