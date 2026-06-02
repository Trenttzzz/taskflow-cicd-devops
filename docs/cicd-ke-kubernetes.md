# Integrasi CI/CD ke Kubernetes

## Tujuan

Menghubungkan pipeline GitHub Actions dari tugas CI/CD sebelumnya dengan cluster Kubernetes. Setelah push ke branch `main`, pipeline menjalankan CI, build Docker image, push image ke GHCR, lalu memperbarui image pada Deployment Kubernetes secara otomatis.

## Alur Pipeline

```text
Developer push ke main
        |
        v
GitHub Actions
        |
        +-- CI matrix Go 1.21, 1.22, 1.23
        +-- Security scan
        +-- Build dan push Docker image ke GHCR
        +-- Tag stable
        +-- Deploy to Kubernetes
        +-- Telegram notification
        |
        v
GKE Deployment taskflow-api memakai image SHA terbaru
```

## Konfigurasi Workflow

Job deploy ditambahkan ke `.github/workflows/ci-cd.yml`:

```yaml
deploy-kubernetes:
  name: Deploy to Kubernetes
  runs-on: ubuntu-latest
  needs: [cd]
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

Alasan memakai `needs: [cd]`: deployment hanya boleh terjadi setelah job CD berhasil membuild dan mempush image ke GHCR. Jika build atau push image gagal, job deploy tidak berjalan.

Image yang dipakai:

```text
ghcr.io/trenttzzz/taskflow-cicd-devops:sha-<short-sha>
```

## Secrets yang Dibutuhkan

Workflow membutuhkan secret:

```text
KUBECONFIG_BASE64
GCP_SA_KEY
```

`KUBECONFIG_BASE64` berisi kubeconfig cluster GKE dalam format base64.

`GCP_SA_KEY` berisi JSON key Service Account Google Cloud yang diberi akses ke GKE. Secret ini dibutuhkan agar `gke-gcloud-auth-plugin` bisa melakukan autentikasi dari GitHub Actions.

## Perbaikan Auth GKE

Saat deploy pertama, job gagal karena runner GitHub belum memiliki `gke-gcloud-auth-plugin`. Error yang muncul:

```text
executable gke-gcloud-auth-plugin not found
```

Perbaikannya adalah menambahkan setup Google Cloud SDK dan komponen GKE auth plugin:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}

- name: Setup Google Cloud SDK
  uses: google-github-actions/setup-gcloud@v2
  with:
    install_components: gke-gcloud-auth-plugin
```

## Hasil

Pipeline GitHub Actions berhasil sampai job `Deploy to Kubernetes`.

![CI/CD Kubernetes success](../img/ci-cd-kubernetes.png)

Pada screenshot terlihat job berikut sukses:

- CI Go 1.21
- CI Go 1.22
- CI Go 1.23
- Security Scan
- CD - Docker Build & Push
- Tag Stable
- Deploy to Kubernetes
- Telegram Notification

## Jawaban Pertanyaan Tugas

### Apa yang terjadi jika job build gagal?

Deployment ke Kubernetes tidak berjalan. Job `deploy-kubernetes` memakai:

```yaml
needs: [cd]
```

Jadi kalau job CD gagal, deploy otomatis dibatalkan.

### Mengapa memakai `needs: [cd]`?

Karena Deployment Kubernetes harus memakai image yang sudah berhasil dibuild dan dipush ke GHCR. Tanpa dependency ini, job deploy bisa berjalan sebelum image tersedia.

### Apa bedanya dengan deploy manual lama?

Cara lama membutuhkan manusia untuk SSH ke server, stop container lama, pull image baru, dan menjalankan container lagi. Cara baru membuat proses itu otomatis:

```text
push kode -> CI/CD -> build image -> push GHCR -> kubectl set image -> rolling update
```

Dengan cara baru, deployment lebih konsisten, bisa diaudit dari GitHub Actions, dan Kubernetes menangani rolling update agar aplikasi tetap tersedia.

## Verifikasi Manual Setelah Pipeline

Setelah job deploy selesai, cek cluster:

```bash
kubectl get pods -n taskflow-prod
kubectl get deployment taskflow-api -n taskflow-prod
kubectl get deployment taskflow-api -n taskflow-prod -o jsonpath='{.spec.template.spec.containers[0].image}'
echo ""
```

Berhasil jika Pod `Running`, Deployment `READY 2/2`, dan image mengandung tag SHA commit terbaru.
