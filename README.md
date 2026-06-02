# TaskFlow API — Source Code PBL CI/CD

Proyek Go ini adalah **source code untuk Problem-Based Learning** mata kuliah
Operasional Pengembang (DevOps), Pertemuan 9: CI/CD Pipeline.

## Quick Start

```bash
# Cara 1: Full stack dengan Docker Compose (tidak perlu Go terinstall)
docker compose up -d
curl http://localhost:8080/health

# Cara 2: Development lokal (butuh Go 1.22+)
cp .env.example .env          # edit DATABASE_URL jika perlu
make db-up                    # start postgres
make test                     # unit test (tanpa DB)
make test-integration         # integration test (butuh DB aktif)
make build                    # compile binary
./bin/taskflow-api
```

## Kubernetes Deployment (Week 12)

Folder `kubernetes/` berisi manifest dasar untuk menjalankan TaskFlow di Kubernetes:

| File | Keterangan |
|------|------------|
| `kubernetes/namespace-dev.yaml` | Namespace development: `taskflow-dev` |
| `kubernetes/namespace-prod.yaml` | Namespace production: `taskflow-prod` |
| `kubernetes/deployment.yaml` | Deployment `taskflow-api` dengan 2 replica dan rolling update |
| `kubernetes/service.yaml` | Service `NodePort` pada port `30080` |

Deploy ke cluster:

```bash
kubectl apply -f kubernetes/namespace-dev.yaml
kubectl apply -f kubernetes/namespace-prod.yaml
kubectl apply -f kubernetes/deployment.yaml -n taskflow-prod
kubectl apply -f kubernetes/service.yaml -n taskflow-prod
```

Verifikasi:

```bash
kubectl get namespaces
kubectl get all -n taskflow-prod
kubectl get deployment taskflow-api -n taskflow-prod
kubectl get service taskflow-api -n taskflow-prod
```

Untuk Minikube, akses aplikasi dengan:

```bash
curl http://$(minikube ip):30080
```

Untuk GKE, akses melalui external IP node jika firewall TCP `30080` sudah dibuka:

```bash
curl http://<NODE_EXTERNAL_IP>:30080
```

> Catatan: manifest awal memakai image placeholder `hashicorp/http-echo:latest` agar validasi Kubernetes mudah dilakukan. Pada tahap integrasi CI/CD, image ini akan diganti dengan image GHCR hasil pipeline GitHub Actions.

## Makefile Targets

| Target | Keterangan |
|--------|------------|
| `make vet` | Analisis statis `go vet` |
| `make test` | Unit test (tanpa database) |
| `make test-race` | Unit test + race detector |
| `make test-cover` | Coverage report |
| `make test-integration` | Integration test (butuh `DATABASE_URL`) |
| `make build` | Compile binary ke `bin/taskflow-api` |
| `make docker-build` | Multi-stage Docker image |
| `make docker-push` | Push image ke registry |
| `make docker-stable` | Tag image sebagai `:stable` |
| `make rollback ROLLBACK_TAG=sha-xxxxx` | Rollback ke versi tertentu |
| `make db-up` | Start postgres via Docker Compose |
| `make up` | Start full stack (postgres + app) |

## API Endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/health` | Health check |
| GET | `/api/v1/tasks` | List task (`?status=todo\|in_progress\|done`) |
| POST | `/api/v1/tasks` | Buat task baru |
| GET | `/api/v1/tasks/{id}` | Ambil task |
| PUT | `/api/v1/tasks/{id}` | Update task |
| DELETE | `/api/v1/tasks/{id}` | Hapus task |
| GET | `/api/v1/stats` | Statistik |

## Environment Variables

| Variable | Default | Keterangan |
|----------|---------|------------|
| `DATABASE_URL` | *(kosong)* | Jika tidak di-set → pakai MemoryRepository |
| `PORT` | `8080` | Port server |

## Arsitektur

```
cmd/server/main.go          ← Entry point
internal/
  handler/handler.go        ← HTTP layer (Go 1.22 routing)
  service/service.go        ← Business logic
  repository/
    repository.go           ← Interface
    memory.go               ← In-memory (unit test)
    postgres.go             ← PostgreSQL via pgx/v5 (production)
  model/task.go             ← Struct & types
  validator/validator.go    ← Input validation
migrations/001_create_tasks.sql  ← Skema database
```

> **Catatan untuk mahasiswa**: Kode ini mengandung **3 bug yang disengaja**.
> Lihat `pbl-cicd-problem.md` untuk detail skenario dan instruksi lengkap.
