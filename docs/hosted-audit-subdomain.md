# Hosted audit subdomain: `audit.govbase.dev`

Goal: serve the GovAI Rust audit service (Docker Compose backend, port `8088`) at the public HTTPS origin `https://audit.govbase.dev`.

Constraints:

- Reverse proxy only (no app logic changes)
- No extra services beyond the existing audit backend
- HTTPS termination at the proxy
- The audit backend works with plain Postgres providers (for example Railway); it does not require Supabase `auth.users`.

---

## DNS setup

Create an A record:

- `audit.govbase.dev` → `<your server public IP>`

---

## Reverse proxy (Nginx)

Install Nginx on the server and configure a site for `audit.govbase.dev` that proxies all traffic to the local audit service:

- Upstream: `127.0.0.1:8088`
- Route: all paths (`/`) to the upstream

Full example config (drop into `/etc/nginx/sites-available/audit.govbase.dev` and symlink into `sites-enabled`):

```nginx
server {
  listen 80;
  listen [::]:80;
  server_name audit.govbase.dev;

  location / {
    proxy_pass http://127.0.0.1:8088;
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## HTTPS setup (Certbot)

Use Certbot with the Nginx plugin:

```bash
sudo certbot --nginx -d audit.govbase.dev
```

After issuance, Certbot will install the TLS server block and manage renewals.

---

## Required environment

Ensure the audit service has API keys enabled (example key for verification):

- `GOVAI_API_KEYS=test-key`

In Docker Compose, this should be set on the audit service container environment.

---

## Start command (Docker Compose)

From the repo root on the server:

```bash
docker compose up -d --build
```

---

## Verification (public HTTPS)

Health endpoints:

```bash
curl -sS https://audit.govbase.dev/health
curl -sS https://audit.govbase.dev/status
```

Auth test (replace `<uuid>`):

```bash
curl -sS -H "Authorization: Bearer test-key" \
  "https://audit.govbase.dev/compliance-summary?run_id=<uuid>"
```

Expected:

- no `401`
- valid JSON response body
