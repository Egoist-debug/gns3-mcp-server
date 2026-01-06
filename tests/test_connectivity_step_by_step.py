import socket
import time
import sys

# Hosts
R1_HOST = "192.168.74.128"
R1_PORT = 5006
L1_PORT = 5002
L2_PORT = 5004

def send_and_read(sock, cmd, wait=1):
    sock.send(f"{cmd}\r".encode())
    time.sleep(wait)
    try:
        return sock.recv(4096).decode('utf-8', errors='ignore')
    except:
        return ""

def check_router():
    print("\n--- Checking Router Interfaces ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((R1_HOST, R1_PORT))
        s.send(b"\r")
        time.sleep(1)
        s.recv(1024)
        
        out = send_and_read(s, "show ip interface brief", 2)
        print(out)
        s.close()
    except Exception as e:
        print(f"Error checking router: {e}")

def check_vpcs(port, name, target_ip):
    print(f"\n--- Checking {name} Ping to {target_ip} ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        
        # Clear buffer
        s.settimeout(0.5)
        try:
             while s.recv(1024): pass
        except:
             pass
        s.settimeout(10)
        
        cmd = f"ping {target_ip}"
        print(f"Sending: {cmd}")
        s.send(f"{cmd}\r".encode())
        
        output = ""
        start = time.time()
        while time.time() - start < 10:
            try:
                chunk = s.recv(1024).decode('utf-8', errors='ignore')
                output += chunk
                sys.stdout.write(chunk)
                sys.stdout.flush()
                if "icmp_seq" in chunk or "timeout" in chunk or "host" in chunk:
                    # Continue reading a bit more
                    pass
            except socket.timeout:
                break
            except:
                break
        s.close()
    except Exception as e:
        print(f"Error checking {name}: {e}")

if __name__ == "__main__":
    check_router()
    check_vpcs(L1_PORT, "Laptop1", "192.168.1.1") # Ping Gateway
    check_vpcs(L2_PORT, "Laptop2", "192.168.2.1") # Ping Gateway
    check_vpcs(L1_PORT, "Laptop1", "192.168.2.2") # Ping Laptop2
