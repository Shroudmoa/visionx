import json
import subprocess
import os
import sys

# USER INPUT
local_net = input("Enter your local network (e.g., 192.168.25.0/24): ").strip()
user_input = input("Paste VPN configuration JSON: ")
target_ip = input("Enter Konnektor IP for health check: ").strip()
child = input("Enter swanctl child name: ").strip()
#one line only
try:
    data = json.loads(user_input)
except json.JSONDecodeError:
    print("Invalid JSON")
    sys.exit(1)

params = {item['name']: item['value'] for item in data['parameters']}

tunnel_ip = params.get('localTunnelIp', '10.0.0.1')
#p1_proposal = "aes128gcm16-prfsha512-ecp256"
#p2_proposal = "aes128gcm16-prfsha512-ecp256"

# 1. Generate the ti-gw.conf for swanctl
# ############################################################################# 
p1_proposals = "aes256-sha512-x25519"
p2_proposals = "aes256-sha512-x25519"

local_tunnel_ip = params.get('localTunnelIp')
remote_open_fd = params.get('openFdNet')
hsk_vkon = params.get('hskVkonNet')
local_id = params['localId']
peer_id = params['peerId']

swanctl_conf = f"""connections {{
    vpn_connection {{
        proposals = {p1_proposals}
        unique = no
        aggressive = no
        version = {params.get('ikeVersion', '2')}
        mobike = no
        remote_addrs = {params['remoteGatewayIp']}
        encap = yes
        dpd_delay = {params.get('dpdRetryInterval', '60')}
        dpd_timeout = {int(params.get('dpdRetryInterval', '60')) * int(params.get('dpdRetryCount', '3'))}
        send_certreq = no
        local-{local_id} {{
            round = 0
            auth = psk
            id = {local_id}
        }}
        remote-{peer_id} {{
            round = 0
            auth = psk
            id = {peer_id}
        }}
        children {{
            {child}_1 {{
                esp_proposals = {p2_proposals}
                sha256_96 = no
                start_action = start
                close_action = start
                dpd_action = start
                mode = tunnel
                policies = yes
                local_ts = {local_net}
                remote_ts = {hsk_vkon}
                rekey_time = {params.get('p2KeyLifetime', '43200')}
            }}
            {child}_2 {{
                esp_proposals = {p2_proposals}
                sha256_96 = no
                start_action = start
                close_action = start
                dpd_action = start
                mode = tunnel
                policies = yes
                local_ts = {local_tunnel_ip}/32
                remote_ts = {remote_open_fd}
                rekey_time = {params.get('p2KeyLifetime', '43200')}
            }}
        }}
    }}
}}
pools {{
}}
secrets {{
    ike-vpn {{
        id-0 = {local_id}
        id-1 = {peer_id}
        secret = {params['pskSec']}
    }}
}}
# Include config snippets
#include conf.d/*.conf
"""





###############################################################################
# 2. Heaclth check script / allsafe project

allsafe = f"""#!/bin/sh

TARGET="{target_ip}"
MAXDOWN=300

# Check connectivity
if ping -c 3 -W 2 $TARGET > /dev/null 2>&1; then
    rm -f /tmp/vpn_fail_time
    exit 0
fi

# Ping failed - check if already tracking failure
FAIL_TIME=$(cat /tmp/vpn_fail_time 2>/dev/null)

if [ -z "$FAIL_TIME" ]; then
    # First failure - record time
    date +%s > /tmp/vpn_fail_time
    exit 0
fi

# Calculate downtime
NOW=$(date +%s)
DIFF=$((NOW - FAIL_TIME))

if [ $DIFF -ge $MAXDOWN ]; then
    echo "VPN down for $DIFF seconds - restarting..."
    rc-service charon restart
    sleep 2
    rm -f /tmp/vpn_fail_time
fi
"""

# 3. use 1. and 2. and place the Config......
###################################################################################################


config_path = "/etc/swanctl/conf.d/ti-gw.conf"
health_check_path = "/root/check_vpn.sh"

print("[*] Writing configuration files...")

with open("ti-gw.conf.tmp", "w") as f:
    f.write(swanctl_conf)
#not in use (actually in use but not needed) might delete later #change later
subprocess.run(["doas", "cp", "ti-gw.conf.tmp", config_path], check=False)
subprocess.run(["doas", "chown", "root:root", config_path], check=False)
subprocess.run(["doas", "chmod", "644", config_path], check=False)
os.remove("ti-gw.conf.tmp")
print(f"âœ“ Generated {config_path}")

# allsafe project => check and change later
with open(health_check_path, "w") as f:
    f.write(allsafe)
subprocess.run(["chmod", "+x", health_check_path], check=False)
print(f"âœ“ Generated {health_check_path}")




####################################################################
#4. basics for VPN setup (IP forwarding, iptables) and cron job for health check

print("\n[*] Configuring sysctl...")

sysctl_file = "/etc/sysctl.conf"

# Read existing 
result = subprocess.run(["doas", "cat", sysctl_file], capture_output=True, text=True)
content = result.stdout if result.returncode == 0 else ""
####check and test later 
# Check if ip_forward is already set
if "net.ipv4.ip_forward" in content:
    # Replace existing line
    new_content = ""
    for line in content.split("\n"):
        if line.startswith("net.ipv4.ip_forward"):
            new_content += "net.ipv4.ip_forward = 1\n"
        else:
            new_content += line + "\n" if line else ""
else:
    # Add new line if needed
    new_content = content + "net.ipv4.ip_forward = 1\n"

# check and change later
with open("sysctl.conf.tmp", "w") as f:
    f.write(new_content)
subprocess.run(["doas", "cp", "sysctl.conf.tmp", sysctl_file], check=False)
os.remove("sysctl.conf.tmp")
subprocess.run(["doas", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)

# Verify and check
result = subprocess.run(["cat", "/proc/sys/net/ipv4/ip_forward"], capture_output=True, text=True)
ip_forward_value = result.stdout.strip()
print(f"âœ“ net.ipv4.ip_forward = {ip_forward_value}")

#######################################################################
#5. iptables new version
print("\n[*] Configuring iptables...")

# Apply rules
#subprocess.run(["doas", "iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"], check=False)
#new era
#subprocess.run(["doas", "iptables", "-t", "nat", "-A", "POSTROUTING", "-s", local_net, "-d", params['openFdNet'], "-j", "SNAT", "--to-source", tunnel_ip], check=False)
#subprocess.run(["doas", "iptables", "-t", "nat", "-A", "POSTROUTING", "-s", local_net, "-d", params['hskVkonNet'], "-j", "SNAT", "--to-source", tunnel_ip], check=False)
#not needed anymore
#subprocess.run(["doas", "iptables", "-A", "FORWARD", "-s", local_net, "-d", params['openFdNet'], "-o", "eth0", "-j", "ACCEPT"], check=False)
#subprocess.run(["doas", "iptables", "-A", "FORWARD", "-s", local_net, "-d", params['hskVkonNet'], "-o", "eth0", "-j", "ACCEPT"], check=False)
#subprocess.run(["doas", "iptables", "-A", "FORWARD", "-s", params['hskVkonNet'], "-d", local_net, "-o", "eth0", "-j", "ACCEPT"], check=False)

#s2s
subprocess.run(["doas", "iptables", "-t", "nat", "-A", "POSTROUTING", "-s", local_net, "-d", params['openFdNet'], "-j", "SNAT", "--to-source", tunnel_ip], check=False)



# Save rules
subprocess.run(["doas", "sh", "-c", "iptables-save > /etc/iptables/rules-save"], check=False)

# sav as a service
subprocess.run(["doas", "rc-update", "add", "iptables"], check=False)
subprocess.run(["doas", "rc-service", "iptables", "start"], check=False)

print("âœ“ iptables configured and persistent")



######################################################################
#6. Cron job 

print("\n[*] Setting up health check cron...")

cron_entry = f"* * * * * {health_check_path}\n"

# check ex
result = subprocess.run(["doas", "crontab", "-l"], capture_output=True, text=True)
existing_cron = result.stdout if result.returncode == 0 else ""

# add if needed
if health_check_path not in existing_cron:
    new_cron = existing_cron + cron_entry if existing_cron else cron_entry
    
    # tmp project => change later not needed
    with open("crontab.tmp", "w") as f:
        f.write(new_cron)
    
    subprocess.run(["doas", "crontab", "crontab.tmp"], check=False)
    os.remove("crontab.tmp")
    print(" Added health check to crontab")
else:
    print("Health check already in crontab")


### load 
#####################################################################
#7. load swanctl as test => not needed but for json/conf systax check


print("\n[*] Loading swanctl configuration...")
result = subprocess.run(["doas", "swanctl", "--load-all"], capture_output=True, text=True)
if result.returncode == 0:
    print(" swanctl config loaded successfully")
else:
    print(f" Warning: {result.stderr}")


####################################################################################################
# 8. Dokumentation and info 

print("\n" + "="*70)
print("(//_^) VPN Configuration Complete")
print("="*70)
print(f" swanctl config: {config_path}")
print(f" Health check: {health_check_path}")
print(f" IP forwarding: enabled (value: {ip_forward_value})")
print(f" iptables: configured and persistent")
print(f"Cron health check: enabled")
print("\nNext steps:")
print(f"  1. You have a Child now! {child}")
print(f"  2. doas reboot")
print(f"  3. After reboot ping {target_ip} should work and the VPN should be up.")


print("="*70)