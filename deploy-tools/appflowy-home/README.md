# Sovereign AppFlowy "My Brain" — home-server kit

Stand up your OWN AppFlowy Cloud on hardware you physically own, reachable from
desktop + iPhone via a private Tailscale mesh (nothing exposed to the internet).
Data lives in your home, encrypted, backed up by you, export-portable.

This is the same AppFlowy-Cloud stack we run on 162 — packaged for a home box.

---

## 0. Hardware (YOUR purchase — money is your call)
Pick one:
- **Mini-PC (recommended):** Beelink / Minisforum, 16–32 GB RAM, ~$300–450, + a 1 TB SSD.
- **NAS:** Synology DS224+ / UGREEN DXP (has a Docker app) + 2 drives (mirror).
- **Raspberry Pi 5** + NVMe SSD (~$120) — fine for AppFlowy alone.

Need: 8 GB+ RAM, an SSD (not just an SD card), wired ethernet.

## 1. OS + Docker
Mini-PC/Pi: install **Ubuntu Server 24.04** (or Debian). Then:
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # re-login after
```
(NAS: enable the built-in Container/Docker package instead.)

## 2. Encrypt the data disk (sovereignty)
Before storing anything, encrypt the disk holding Docker volumes:
```bash
# on a fresh data disk /dev/sdX — DESTROYS it:
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup open /dev/sdX cryptdata
sudo mkfs.ext4 /dev/mapper/cryptdata
sudo mkdir -p /srv/appflowy && sudo mount /dev/mapper/cryptdata /srv/appflowy
```

## 3. Deploy AppFlowy Cloud
```bash
cd /srv/appflowy
git clone https://github.com/AppFlowy-IO/AppFlowy-Cloud.git
cd AppFlowy-Cloud
cp deploy.env .env
bash /path/to/this-kit/setup.sh   # fills secrets + your account + locks signups
docker compose up -d
```
`setup.sh` (in this kit) generates strong secrets, sets `FQDN` to your Tailscale
name, creates your admin account, and sets `GOTRUE_DISABLE_SIGNUP=true` so ONLY
you can log in.

## 4. Private access from anywhere — Tailscale (the sovereign move)
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```
Install Tailscale on your desktop + iPhone too (same account). Your box gets a
name like `brain.tailXXXX.ts.net`. **Nothing is open to the internet** — only
your own devices on the mesh can reach it.
- TLS on the tailnet: `sudo tailscale cert brain.tailXXXX.ts.net` → point nginx at it.

## 5. Connect the app
AppFlowy (desktop + iPhone) → **Settings → Cloud Settings → Self-hosted Cloud** →
enter `https://brain.tailXXXX.ts.net` → restart → log in. Synced, sovereign.

## 6. Backups you hold (see `backup.sh`)
Nightly: `pg_dump` of postgres + `mc mirror` of minio → a second drive + an
off-site copy (another location / encrypted cloud you control). Test a restore.

## 7. Data portability (no lock-in)
AppFlowy exports pages to **Markdown/CSV** anytime — your brain is never trapped.

---

**Sovereignty summary:** your hardware · encrypted disk · private-mesh access
(zero internet exposure) · your backups · export-portable. About as sovereign
as it gets short of air-gapped.

Migrating your existing 162 workspace here later: `pg_dump` the workspace + copy
its minio objects, or export→re-import via Markdown.
