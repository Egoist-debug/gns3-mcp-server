import socket
import time
import sys

def read_until(sock, valid_end_chars, timeout=10.0):
    """Read from socket until one of valid_end_chars is seen or timeout."""
    start = time.time()
    buf = ""
    while time.time() - start < timeout:
        try:
            chunk = sock.recv(1024).decode('utf-8', errors='ignore')
            if not chunk:
                time.sleep(0.1)
                continue
            buf += chunk
            # print(chunk, end='', flush=True) # Debug output
            for end_char in valid_end_chars:
                if end_char in buf.splitlines()[-1]: # Check last line
                    return buf
        except socket.error:
            time.sleep(0.1)
    return buf

def wait_for_boot(sock, timeout=120):
    """Send Enter until we see a prompt."""
    print("Waiting for device to respond...", end='', flush=True)
    start = time.time()
    while time.time() - start < timeout:
        sock.send(b"\r")
        res = read_until(sock, [">", "#", "PC1>", "PC2>", "Laptop1>", "Laptop2>", "[yes/no]:"], timeout=1)
        if res:
             # print(f"[{res}]", end='') # Debug
             pass
        
        if "[yes/no]:" in res:
            print(" Initial Config Dialog detected. Sending 'no'.")
            sock.send(b"no\r")
            time.sleep(5) # Wait for it to proceed
            continue

        if any(c in res for c in [">", "#"]):
            print(" Done.")
            return True
        time.sleep(1)
        print(".", end='', flush=True)
    print(" Timeout!")
    return False

def config_router(host, port):
    print(f"\n--- Configuring Router ({host}:{port}) ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        
        if not wait_for_boot(s):
            print("Router did not respond.")
            s.close()
            return

        cmds = [
            ("enable", "#"),
            ("configure terminal", "(config)#"),
            ("interface GigabitEthernet0/0", "(config-if)#"),
            ("ip address 192.168.1.1 255.255.255.0", "#"),
            ("no shutdown", "#"),
            ("exit", "#"),
            ("interface GigabitEthernet0/1", "(config-if)#"),
            ("ip address 192.168.2.1 255.255.255.0", "#"),
            ("no shutdown", "#"),
            ("end", "#"),
            ("wr mem", "#")
        ]
        
        for cmd, expect in cmds:
            print(f"Sending: {cmd}")
            s.send(f"{cmd}\r".encode())
            # Simple wait for the command to be processed
            time.sleep(0.5)
            # Read whatever comes back
            try:
                out = s.recv(4096).decode('utf-8', errors='ignore')
                # print(out)
            except socket.timeout:
                pass
            
        s.close()
        print("Router configured.")
    except Exception as e:
        print(f"Error configuring router: {e}")

def config_vpcs(port, ip, gateway, name):
    print(f"\n--- Configuring {name} (Port {port}) ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('localhost', port))
        
        # Wake up
        s.send(b"\r")
        time.sleep(0.5)
        s.recv(1024) 
        
        # IP Config
        cmd = f"ip {ip} {gateway}"
        print(f"Sending: {cmd}")
        s.send(f"{cmd}\r".encode())
        
        # Wait for potential duplicate IP check or apply
        time.sleep(2)
        try:
            out = s.recv(4096).decode('utf-8', errors='ignore')
            print(f"Output: {out.strip()}")
        except:
            pass
            
        s.close()
    except Exception as e:
        print(f"Error configuring {name}: {e}")

def test_ping(port, target_ip):
    print(f"\n--- Testing Ping from Port {port} to {target_ip} ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(('localhost', port))
        time.sleep(1)
        s.recv(4096) # Clear buffer
        
        cmd = f"ping {target_ip}"
        print(f"Sending: {cmd}")
        s.send(f"{cmd}\r".encode())
        
        # Read output loop
        output = ""
        start = time.time()
        while time.time() - start < 15: # 15s timeout for ping
            try:
                chunk = s.recv(1024).decode('utf-8', errors='ignore')
                output += chunk
                sys.stdout.write(chunk)
                sys.stdout.flush()
                
                if "icmp_seq=5" in output or "timeout" in output or "Destination host unreachable" in output:
                     break
            except socket.timeout:
                break
            except Exception as e:
                print(e)
                break
        
        print("\nPing Finished.")
        s.close()
    except Exception as e:
        print(f"Error testing ping: {e}")

if __name__ == "__main__":
    # R1: 192.168.74.128:5006
    config_router("192.168.74.128", 5006)
    
    # Laptop1: 5002
    config_vpcs(5002, "192.168.1.2/24", "192.168.1.1", "Laptop1")
    
    # Laptop2: 5004
    config_vpcs(5004, "192.168.2.2/24", "192.168.2.1", "Laptop2")
    
    print("\nWaiting 5 seconds for network convergence...")
    time.sleep(5)
    
    # Ping Laptop1 -> Laptop2
    test_ping(5002, "192.168.2.2")
