import ipaddress
import socket
import subprocess
from typing import List


def _collect_ipv4_candidates() -> List[str]:
    candidates: List[str] = []

    # Candidate set from host/network interfaces.
    try:
        host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
        candidates.extend(host_ips)
    except OSError:
        pass

    # Candidate from default route decision.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 80))
        candidates.append(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()

    # Candidates from common macOS network interfaces.
    for iface in ("en0", "en1"):
        try:
            ip = subprocess.check_output(
                ["ipconfig", "getifaddr", iface],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if ip:
                candidates.append(ip)
        except Exception:
            pass

    # De-duplicate while preserving order.
    seen = set()
    uniq: List[str] = []
    for ip in candidates:
        if ip not in seen:
            seen.add(ip)
            uniq.append(ip)
    return uniq


def _is_usable_lan_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False

    if not isinstance(addr, ipaddress.IPv4Address):
        return False

    if addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_unspecified:
        return False

    # Exclude synthetic/benchmark ranges that may come from VPN/proxy adapters.
    if addr in ipaddress.ip_network("198.18.0.0/15"):
        return False

    # Prefer RFC1918 private addresses for local network join links.
    return addr.is_private


def get_lan_ip() -> str:
    candidates = _collect_ipv4_candidates()
    usable = [ip for ip in candidates if _is_usable_lan_ip(ip)]
    if usable:
        # Prefer common home/office LAN ranges in stable order.
        for ip in usable:
            if ip.startswith("192.168."):
                return ip
        for ip in usable:
            if ip.startswith("10."):
                return ip
        for ip in usable:
            if ip.startswith("172."):
                second = int(ip.split(".")[1])
                if 16 <= second <= 31:
                    return ip
        return usable[0]
    return "127.0.0.1"
