#!/usr/bin/env python3
import subprocess
import os
import time
import socket
import concurrent.futures


BASE_URL = "https://vm-tiaas.visionmaxx.net"

BASE_URL2 = "https://wl-ti-gateway-nutzerportal-pu.wlcle.org"

TOKEN_PATH = "./token"

PORTS = [4742, 443, 8500, 636, 53, 9500]
TEST_IP = "100.102.8.6"
TEST_PORT = 465


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_reachability():
    print("wl-ti-gateway-nutzerportal-pu.wlcle.org erreicht...")
    code, _, _ = run_cmd(f"curl -Is {BASE_URL2} --max-time 5")
    return code == 0


def download_token(kundennummer):
    url = f"{BASE_URL}/ti-gw/tokens/{kundennummer}/token_{kundennummer}"
#    url = f"{BASE_URL}/ti-gw/tokens/ru-token/token_{kundennummer}"

    print(f"Lade Token von {url}")
    code, _, err = run_cmd(f"curl -f -L {url} -o {TOKEN_PATH}")
    if code != 0:
        print(err)
    return code == 0
############################################################new era
def check_ports_socket_parallel(host="127.0.0.1", show_only_problems=False):
    print(f"Port Status ({host}):")

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(lambda p: check_single_port(host, p), PORTS))

    for port, ok in sorted(results):
        if ok:
            if not show_only_problems:
                print(f"OK     Port {port} erreichbar")
        else:
            print(f"ERROR  Port {port} nicht erreichbar")


def check_single_port(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        result = s.connect_ex((host, port))
        return port, (result == 0)
    finally:
        s.close()

#################################################################new era


def install_gateway():
    print("Starte Installation...")
    cmd = """sudo ./ti-gw-installer-linux.run \
--serviceName ti-gw-secunet \
--prefix /home/vm/tigw \
--base64String $(cat ./token) \
--clientType device \
--installermode normal \
--enable-components clientService,gatewayMode \
--mode unattended \
--updateTimeslot 22,Europe/Berlin"""
    return run_cmd(cmd)
###change later
def getips():
    ips = []

    code, out, err = run_cmd("ip -4 addr show")

    if code != 0:
        print("Fehler beim Abrufen der IPs:", err)
        return ips

    for line in out.splitlines():
        line = line.strip()
        if line.startswith("inet "):
            ip = line.split()[1].split("/")[0]
            ips.append(ip)

    return ips
###change later


def get_ipv4_addresses():
    print("IPv4 Adressen:")

    code, out, err = run_cmd("ip -4 addr show")

    if code != 0:
        print("Fehler beim Abrufen der IPs:", err)
        return

    found = False
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("inet "):
            ip = line.split()[1].split("/")[0]
            print(" -", ip)
            found = True

    if not found:
        print("Keine IPv4 Adresse gefunden")



def test_connection():
    try:
        sock = socket.create_connection((TEST_IP, TEST_PORT), timeout=5)
        sock.close()
        print(f"OK     Verbindung zu {TEST_IP}:{TEST_PORT}")
    except Exception:
        print(f"ERROR  Verbindung zu {TEST_IP}:{TEST_PORT}")

#####################
def monitor_loop2():
    while True:
        os.system("clear")

        ips = getips()

        print("IPv4 Adressen:")
        for ip in ips:
            print(" -", ip)

        print("\nPort Checks:")
        for ip in ips:
            check_ports_socket_parallel(ip, show_only_problems=False)
        
        print("\nfachdienstliche Verbindung:")
        test_connection()

        print("\n10 Sek loop\n")

        time.sleep(10)




def show_logs():
    log_dir = "/home/vm/tigw/data/logs/"
    if not os.path.exists(log_dir):
        print("/home/vm/tigw/data/logs nicht gefunden")
        return

    files = os.listdir(log_dir)
    for i, f in enumerate(files):
        print(f"{i}: {f}")

    choice = input("Datei auswÃƒÂ¤hlen: ")
    try:
        file = files[int(choice)]
        os.system(f"nano {os.path.join(log_dir, file)}")
    except Exception:
        print("UngÃƒÂ¼ltige Auswahl")


def main():
    print("1. Setup")
    print("2. Monitoring")
    print("3. Logs anzeigen")

    option = input("Auswahl: ")

    if option == "1":
        if not check_reachability():
            print("wl-ti-gateway-nutzerportal-pu.wlcle.org wurde nicht erreicht!")
            return

        kundennummer = input("Kundennummer: ")

        if not download_token(kundennummer):
            print("Token Download fehlgeschlagen")
            return

        code, out, err = install_gateway()
        print(out if out else err)

        get_ipv4_addresses()
    elif option == "2":
        
        monitor_loop2()

    elif option == "3":
        show_logs()


if __name__ == "__main__":
    main()
