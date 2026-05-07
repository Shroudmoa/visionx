import os
import subprocess


#change later => no bash scripts, just commands in python
def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


print("\nSYSCTL CHECK")
with open("/proc/sys/net/ipv4/ip_forward", "r") as f:
    val = f.read().strip()

if val == "1":
    print("[OK] IP forwarding enabled")
else:
    print("[MISSING] IP forwarding disabled")

print("\n IPTABLES RULE FILE ")
if os.path.exists("/etc/iptables/rules-save"):
    print("[OK] iptables rules-save exists")
else:
    print("[MISSING] iptables rules-save")

print("\nCRON CHECK ")
cron = run(["crontab", "-l"])

if "* * * * * /root/check_vpn.sh" in cron.stdout:
    print("[OK] check_vpn cron installed")
else:
    print("[MISSING] check_vpn cron missing")

print("\nIPTABLES CHECK (FORWARD)")
forward = run(["doas", "iptables", "-L", "FORWARD", "-n", "--line-numbers"])
print(forward.stdout if forward.stdout else forward.stderr)

print("\n IPTABLES CHECK (NAT)")
nat = run(["doas", "iptables", "-t", "nat", "-L", "-n", "--line-numbers"])
print(nat.stdout if nat.stdout else nat.stderr)


print("\n ")