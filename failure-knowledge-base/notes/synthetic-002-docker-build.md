# synthetic-002-docker-build

Category: `docker-build`

Root cause: Docker build tidak menemukan target source atau output build yang diharapkan.

Resolution: verifikasi path `./cmd/server`, konteks Docker build, dan perintah `go build` di Dockerfile.

Evidence: log berisi `stat /build/cmd/server: directory not found`.
