# VM auto-refresh setup (one time, ~5 minutes)

Assumes Ubuntu/Debian; adjust package commands otherwise.

## 1. Dependencies

```bash
sudo apt-get update && sudo apt-get install -y git python3-pip curl
pip3 install pandas openpyxl lxml zipcodes
```

## 2. Deploy key (lets the VM push to this repo and nothing else)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/va_deserts_deploy -N "" -C "va-deserts-vm"
cat ~/.ssh/va_deserts_deploy.pub
```

Copy the output → GitHub repo → Settings → Deploy keys → Add deploy key → paste, **check "Allow write access"**.

```bash
cat >> ~/.ssh/config <<'EOF'
Host github-va-deserts
  HostName github.com
  IdentityFile ~/.ssh/va_deserts_deploy
EOF
```

## 3. Clone

```bash
git clone git@github-va-deserts:<YOUR_GITHUB_USERNAME>/va-claims-help-deserts.git ~/va-claims-help-deserts
cd ~/va-claims-help-deserts
git config user.name "va-deserts-bot"
git config user.email "dan77450@hotmail.com"
chmod +x vm/refresh.sh
```

## 4. Test once by hand

```bash
~/va-claims-help-deserts/vm/refresh.sh
```

First run downloads the static inputs (~65 MB) into `~/.cache/va-deserts`; later runs reuse them.

## 5. Cron (Tuesdays 12:00 UTC — MMWR posts Mondays)

```bash
(crontab -l 2>/dev/null; echo '0 12 * * 2 ~/va-claims-help-deserts/vm/refresh.sh >> ~/va-deserts-refresh.log 2>&1') | crontab -
```

That's it. Each run refreshes the rosters, grabs the newest MMWR, rebuilds the dataset and map, archives a dated roster snapshot to `snapshots/`, and pushes only when something changed — GitHub Pages redeploys automatically.

## Notes

- If VA changes the MMWR layout (it has ~15 times since 2009), `extract_mmwr_state.py` may fail — the cron log will show it and the site simply stays on the last good data.
- `snapshots/` grows ~6 MB/week. Prune or `git lfs` it if the repo gets heavy.
- Static inputs (VetPop, crosswalks) update rarely; delete them from `~/.cache/va-deserts` to force re-download (VetPop refreshes annually).
