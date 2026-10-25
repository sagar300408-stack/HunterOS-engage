import socket
import sys

def check_tcp(host, port, name):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect((host, port))
        s.close()
        print(f"[TCP CHECK] {name} ({host}:{port}): CONNECTED (ONLINE)")
        return True
    except Exception as e:
        print(f"[TCP CHECK] {name} ({host}:{port}): CONNECTION REFUSED ({e})")
        return False

if __name__ == "__main__":
    pg_ok = check_tcp("127.0.0.1", 5432, "PostgreSQL")
    redis_ok = check_tcp("127.0.0.1", 6379, "Redis")
    print(f"Summary: PG={pg_ok}, Redis={redis_ok}")
