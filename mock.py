#!/usr/bin/env python3
import socket
import threading
import time

PORTS = [4742, 443, 8500, 636, 53, 9500]
HOST = "127.0.0.1"

mock_sockets = []


def create_mock_server(port):
    """Create a fake listening socket on a port for testing"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((HOST, port))
        s.listen(5)
        print(f"✓ Mock server listening on {HOST}:{port}")
        return s
    except Exception as e:
        print(f"✗ Failed to bind port {port}: {e}")
        return None


def accept_connections(sock, port):
    """Accept incoming connections on the mock socket"""
    try:
        while True:
            try:
                conn, addr = sock.accept()
                conn.close()
            except:
                break
    except:
        pass


def main():
    print("=" * 50)
    print("Mock Gateway Server - For Testing")
    print("=" * 50)
    print(f"\nStarting mock servers on {HOST}...\n")

    # Create mock servers on all ports
    for port in PORTS:
        s = create_mock_server(port)
        if s:
            mock_sockets.append(s)
            # Start thread to accept connections
            t = threading.Thread(target=accept_connections, args=(s, port), daemon=True)
            t.start()

    print(f"\n{'=' * 50}")
    print("Mock servers running. Press Ctrl+C to stop.")
    print("=" * 50)
    print("\nNow run your main script in another terminal!")
    print("You should see all ports as OK.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down mock servers...")
        for s in mock_sockets:
            s.close()
        print("Done!")


if __name__ == "__main__":
    main()
