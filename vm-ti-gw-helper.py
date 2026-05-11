#!/usr/bin/env python3
import subprocess
import os
import time
import socket
import concurrent.futures
from datetime import datetime
try:
    import pyperclip
except ImportError:
    pyperclip = None


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

def about():
    print("TI-Gateway Helper Script")
    print("Version 1.0")
    print("Wünsche/Probleme an rmi/moa")
    
def installation_report():

    tests = [
        "VDSM",
        "Einlesen",
        "KIM",
        "eRezept"
    ]

    results = {}

    konnektor_ip = input("Konnektor IP/Subnetz (z.B. 192.168.10.15/24): ").strip()

    print("\nAlles getestet? (VDSM, Einlesen, KIM, eRezept)")
    overall = input("y oder n: ").strip().lower()

    if overall == "y":

        for test in tests:
            results[test] = {
                "status": "OK",
                "reason": ""
            }

    else:

        print("\nWas hat NICHT geklappt?")
        print("Mehrere Nummern mit Komma trennen\n")

        for idx, test in enumerate(tests, start=1):
            print(f"{idx} = {test}")

        selection = input("\nAuswahl: ").strip()

        failed = set()

        for item in selection.split(","):
            item = item.strip()

            if item in ["1", "2", "3", "4"]:
                failed.add(tests[int(item) - 1])

        for test in tests:

            if test in failed:

                reason = input(f"Grund für '{test}': ")

                results[test] = {
                    "status": "NICHT OK",
                    "reason": reason
                }

            else:

                results[test] = {
                    "status": "OK",
                    "reason": ""
                }

    hostname = socket.gethostname()

    output = []
    output.append(
        f"ti-gw-installation auf "
        f"(vm@{hostname}) "
        f"mit der Konnektor-IP {konnektor_ip} abgeschlossen.\n"
    )

    output.append("Testübersicht:")

    for idx, test in enumerate(tests, start=1):

        status = results[test]["status"]

        if status == "OK":
            output.append(f"{idx}. {test}: OK")

        else:
            output.append(
                f"{idx}. {test}: NICHT OK "
                f"= {results[test]['reason']}"
            )

    output.append(f"\nZeitpunkt: {datetime.now()}")

    final_text = "\n".join(output)

    print("\n" + "=" * 60)
    print(final_text)
    print("=" * 60)

    if pyperclip:
        try:
            pyperclip.copy(final_text)
            print("\n[+] Ausgabe wurde ins Clipboard kopiert.")
        except Exception as e:
            print(f"\n[!] Clipboard Fehler: {e}")
    else:
        print(
            "\n[!] pyperclip nicht installiert.\n"
            "Installieren mit:\n"
            "pip install pyperclip"
        )





#########################################################
def cls():
    os.system('cls' if os.name == 'nt' else 'clear')
COL_DARK = "\x1b[38;5;54m"
COL_PURPLE = "\x1b[38;5;99m"
COL_RESET = "\x1b[0m"
COL_BOLD = "\x1b[1m"
def animated_logo():
    logo = [
" _    _ _      _                              "       ,
"| |  | (_)    (_)                                    ",
"| |  | |_  ___ _  ___  ____  ____   ____ _   _ _   _ ",
" \ \/ /| |/___) |/ _ \|  _ \|    \ / _  ( \ / | \ / )",
"  \  / | |___ | | |_| | | | | | | ( ( | |) X ( ) X ( ",
"   \/  |_(___/|_|\___/|_| |_|_|_|_|\_||_(_/ \_|_/ \_)",
"                                                    ",
    ]
    for i in range(2):
        for color in [COL_DARK, COL_PURPLE]:
            cls()
            print(color + COL_BOLD)
            for line in logo:
                print(" " * 6 + line)
            print(f"\n   Visionmaxx GmbH - V1.0")
            print(COL_RESET)
            time.sleep(0.25)

def main():
    cls()
    animated_logo()
    print("1. Setup")
    print("2. Monitoring")
    print("3. Logs anzeigen")
    print("4. Installationsreport erstellen")
    print("5. About")
    
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
    elif option == "4":
        installation_report()
    elif option == "5":
        about()


if __name__ == "__main__":
    main()
