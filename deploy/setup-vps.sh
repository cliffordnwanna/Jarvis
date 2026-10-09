#!/bin/bash
set -e

echo "=== JARVIS v3 VPS Hardening ==="

# System update
apt-get update && apt-get upgrade -y

# Required packages
apt-get install -y \
  python3.11 python3.11-venv python3-pip \
  nodejs npm git curl ufw fail2ban \
  unattended-upgrades apt-listchanges aide

# Auto security updates
dpkg-reconfigure -plow unattended-upgrades

# --- FIREWALL ---
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "UFW enabled. Only ports 22, 80, 443 are open."

# --- FAIL2BAN ---
systemctl enable fail2ban
systemctl start fail2ban

cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = ssh
maxretry = 3
bantime = 3600
findtime = 600
EOF

systemctl restart fail2ban
echo "Fail2ban configured. 3 failed SSH attempts = 1 hour ban."

# --- SSH HARDENING ---
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd
echo "SSH hardened. Password auth off. Root login off."

# --- MINER DETECTION CRON ---
cat > /etc/cron.d/miner-watch << 'EOF'
*/5 * * * * root ps aux | grep -E "(xmrig|minerd|cryptonight|stratum+tcp)" | grep -v grep && echo "SUSPICIOUS PROCESS DETECTED" | logger -t security-alert
EOF
echo "Miner watch cron installed."

# --- FILE INTEGRITY (AIDE) ---
aideinit
mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db
echo "0 3 * * * root /usr/bin/aide --check 2>&1 | logger -t aide-check" >> /etc/crontab
echo "AIDE integrity monitoring initialized."

# --- INSTALL CADDY ---
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update && apt-get install -y caddy
systemctl enable caddy
echo "Caddy installed."

# --- PM2 + LOG ROTATION ---
npm install -g pm2
echo "PM2 installed."

# pm2-logrotate caps each process's log file size and keeps a bounded
# number of rotated copies, so jarvis-backend/jarvis-frontend/jarvis-voice
# logs can't silently fill the disk over weeks of uptime. Run as the
# deploy user (not root) so it manages deploy's own PM2 daemon.
sudo -u deploy pm2 install pm2-logrotate
sudo -u deploy pm2 set pm2-logrotate:max_size 10M
sudo -u deploy pm2 set pm2-logrotate:retain 7
sudo -u deploy pm2 set pm2-logrotate:compress true
echo "pm2-logrotate installed (10MB max per log, 7 rotations kept, compressed)."

# --- APP DIRECTORY ---
mkdir -p /home/deploy/apps
chown -R deploy:deploy /home/deploy/apps

echo ""
echo "=== Hardening complete ==="
echo "Next steps:"
echo "  1. As deploy user: git clone your repo to /home/deploy/apps/jarvis"
echo "  2. Upload .env files via scp"
echo "  3. Run deploy/install.sh"
