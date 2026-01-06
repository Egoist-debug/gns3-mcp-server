import socket
import time

HOST = "192.168.74.128"
PORT = 5006

def bounce_interface():
    print("Bouncing Gi0/0...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.send(b"\r")
        time.sleep(1)
        
        cmds = [
            "configure terminal",
            "interface GigabitEthernet0/0",
            "shutdown",
            "no shutdown",
            "end",
            "show ip interface brief"
        ]
        
        for cmd in cmds:
            s.send(f"{cmd}\r".encode())
            time.sleep(1)
            
        # Read output
        out = s.recv(4096).decode('utf-8', errors='ignore')
        print(out)
        s.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    bounce_interface()

