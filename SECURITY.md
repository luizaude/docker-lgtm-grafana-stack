## Security policy

This repository is intended for **local-only playground/testing**.

### Reporting vulnerabilities

If you discover a security issue, please open a GitHub issue with:

- A clear description and reproduction steps
- Affected component(s) (Grafana/Loki/Mimir/Tempo/Alloy, demo apps, scripts)
- Version(s) involved (image tags from `docker-compose.yml`)

### Hardening notes (if you ever adapt this beyond local use)

- Disable Grafana anonymous admin access (`GRAFANA_ANONYMOUS_ENABLED=false`)
- Set strong credentials in `.env`
- Do not expose Loki/Mimir/Tempo/Grafana directly to the internet without auth and TLS
- Reconsider mounting `/var/run/docker.sock` into Alloy (high impact)
