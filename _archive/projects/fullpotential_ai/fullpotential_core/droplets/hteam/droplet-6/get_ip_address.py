"""
Quick script to find your computer's IP address for mobile testing.

Run this to find your IP address, then access the app from your phone:
http://YOUR_IP:8000
"""

import socket


def get_local_ip():
    """Get the local IP address of this computer."""
    try:
        # Connect to a remote server to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Unable to determine IP"


if __name__ == "__main__":
    ip = get_local_ip()
    print("=" * 50)
    print("Your IP Address for Mobile Testing:")
    print("=" * 50)
    print(f"\nIP Address: {ip}")
    print(f"\nAccess from phone (same WiFi):")
    print(f"http://{ip}:8000")
    print("\n" + "=" * 50)
    print("\nMake sure Chainlit is running with:")
    print("chainlit run app.py -w --host 0.0.0.0")
    print("=" * 50)
