#!/bin/sh

set -e

echo "[+] Starte Alpine Setup..."

if [ "$(id -u)" -ne 0 ]; then
  echo "Bitte als root ausführen (su -)"
  exit 1
fi

apk update
apk add doas

# Repos
cat > /etc/apk/repositories <<EOF
http://dl-cdn.alpinelinux.org/alpine/edge/main
http://dl-cdn.alpinelinux.org/alpine/edge/community
EOF

apk update
doas apk add vim nano iptables strongswan fastfetch make cmake ninja gcc g++

# doas config
cat > /etc/doas.conf <<EOF
permit persist :wheel
EOF

# user
adduser -D vm
adduser -D ti-gw
adduser vm wheel
adduser ti-gw wheel
