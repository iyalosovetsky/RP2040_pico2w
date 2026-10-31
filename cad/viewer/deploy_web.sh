#!/usr/bin/env bash
# Publish the arm viewer to https://web.ibotz.space/roboruka/
# zen4 serves ~/www with a static nginx container (web-static, port 8091); ibotz2's nginx
# proxies web.ibotz.space to it over the VPN with the usual *.ibotz.space Google login.
# Run after export_parts.py / any viewer change.
set -euo pipefail
cd "$(dirname "$0")"
ssh zen4 'mkdir -p ~/www/roboruka/vendor'
rsync -a --delete roboruka.html zen4:www/roboruka/index.html
rsync -a parts.js zen4:www/roboruka/parts.js
rsync -a --delete vendor/ zen4:www/roboruka/vendor/
# first run: start the container (no-op if it is already there)
ssh zen4 'docker inspect web-static >/dev/null 2>&1 || docker run -d --name web-static --restart unless-stopped \
  -p 8091:80 -v "$HOME/www:/usr/share/nginx/html:ro" nginx:1.19.2-alpine'
echo "deployed: https://web.ibotz.space/roboruka/"
