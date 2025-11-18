#!/usr/bin/env python3
"""
DNS IPv4解決スクリプト
GitHub ActionsでIPv4アドレスを強制的に取得する
"""
import socket
import sys

def resolve_ipv4(hostname):
    """
    ホスト名をIPv4アドレスに解決
    """
    try:
        # IPv4のみを取得（AF_INET）
        result = socket.getaddrinfo(
            hostname,
            None,
            socket.AF_INET,  # IPv4のみ
            socket.SOCK_STREAM
        )

        if result:
            ipv4 = result[0][4][0]
            return ipv4
        else:
            return None

    except Exception as e:
        print(f"Error resolving {hostname}: {e}", file=sys.stderr)
        return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python resolve_ipv4.py <hostname>", file=sys.stderr)
        sys.exit(1)

    hostname = sys.argv[1]
    ipv4 = resolve_ipv4(hostname)

    if ipv4:
        print(ipv4)
        sys.exit(0)
    else:
        print(f"Failed to resolve {hostname}", file=sys.stderr)
        sys.exit(1)
