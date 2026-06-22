# synthetic-004-security-scan

Category: `security-scan`

Root cause: security gate menemukan vulnerability atau finding yang memblokir pipeline.

Resolution: baca artifact `govulncheck-report.json` dan `gosec-report.json`, lalu upgrade dependency atau perbaiki source yang dilaporkan.

Evidence: log berisi `Security scan found blocking findings`.
