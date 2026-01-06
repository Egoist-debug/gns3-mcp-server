import socket
import sys
import time

HOST = "192.168.74.128"
PORT = 5006

def main():
    print(f"Connecting to {HOST}:{PORT}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.settimeout(2.0)
        
        print("Connected. Listening for 30 seconds...")
        start = time.time()
        while time.time() - start < 30:
            try:
                data = s.recv(1024)
                if data:
                    print(f"Received: {data}") # Raw bytes
                else:
                    time.sleep(0.1)
            except socket.timeout:
                # Send Enter every 5 seconds if silent
                if int(time.time()) % 5 == 0:
                    s.send(b"\r")
                pass
            except Exception as e:
                print(f"Error: {e}")
                break
                
        s.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    main()

