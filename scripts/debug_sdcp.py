import socket
import struct
import os
import sys
import base64
import hashlib
import time
import json
import urllib.parse

# --- Minimal WebSocket Implementation ---

def create_ws_key():
    key = os.urandom(16)
    return base64.b64encode(key).decode('utf-8')

def ws_handshake(sock, host, port, path="/websocket"):
    key = create_ws_key()
    headers = [
        f"GET {path} HTTP/1.1",
        f"Host: {host}:{port}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Version: 13",
        "\r\n"
    ]
    request = "\r\n".join(headers).encode('utf-8')
    sock.sendall(request)
    
    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Server closed connection during handshake")
        response += chunk
    
    if b"101 Switching Protocols" not in response:
        print(f"Handshake Response: {response.decode('utf-8', errors='ignore')}")
        raise ConnectionError("Handshake failed")
    return True

def ws_send_text(sock, text):
    data = text.encode('utf-8')
    length = len(data)
    
    # Frame format: FIN=1, RSV=0, Opcode=1 (text) -> 0x81
    header = bytearray([0x81])
    
    # Mask bit = 1
    if length <= 125:
        header.append(length | 0x80)
    elif length <= 65535:
        header.append(126 | 0x80)
        header.extend(struct.pack("!H", length))
    else:
        header.append(127 | 0x80)
        header.extend(struct.pack("!Q", length))
        
    mask_key = os.urandom(4)
    header.extend(mask_key)
    
    masked_data = bytearray(length)
    for i in range(length):
        masked_data[i] = data[i] ^ mask_key[i % 4]
        
    sock.sendall(header + masked_data)

def ws_recv_frame(sock):
    header = sock.recv(2)
    if not header: return None
    
    b1, b2 = header
    fin = b1 & 0x80
    opcode = b1 & 0x0F
    masked = b2 & 0x80
    payload_len = b2 & 0x7F
    
    if payload_len == 126:
        payload_len = struct.unpack("!H", sock.recv(2))[0]
    elif payload_len == 127:
        payload_len = struct.unpack("!Q", sock.recv(8))[0]
        
    if masked:
        mask_key = sock.recv(4)
        
    data = b""
    while len(data) < payload_len:
        chunk = sock.recv(payload_len - len(data))
        if not chunk: break
        data += chunk
        
    if masked:
        unmasked = bytearray(len(data))
        for i in range(len(data)):
            unmasked[i] = data[i] ^ mask_key[i % 4]
        data = unmasked
        
    return opcode, data

# --- Main Script ---

def load_env_file():
    # Look for .env in current and parent dir
    locations = ['.env', '../.env']
    for loc in locations:
        if os.path.exists(loc):
            try:
                with open(loc, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'): continue
                        if '=' in line:
                            k, v = line.split('=', 1)
                            os.environ[k.strip()] = v.strip().strip("'").strip('"')
                print(f"Loaded {loc}")
                return
            except: pass
    print("Warning: .env not found")

def check_udp_discovery(index):
    # SDCP Discovery: Send "M99999" to port 3000
    print(f"[{index}] Sending UDP Broadcast 'M99999' to port 3000...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(5)
    
    found_id = None
    
    try:
        # Send Broadcast
        message = b"M99999"
        sock.sendto(message, ('<broadcast>', 3000))
        
        print(f"[{index}] Listening for UDP response on port 3000 (5s)...")
        start_time = time.time()
        while time.time() - start_time < 5:
            try:
                data, addr = sock.recvfrom(4096)
                text = data.decode('utf-8', errors='ignore')
                print(f"[{index}] UDP from {addr}: {text}")
                
                if text.strip().startswith('{'):
                    try:
                        j = json.loads(text)
                        # Check multiple locations for MainboardID
                        # It might be in Data.MainboardID or just MainboardID
                        mb_id = j.get('Data', {}).get('MainboardID') or j.get('MainboardID')
                        
                        if mb_id:
                            print(f"[{index}] *** FOUND MainboardID: {mb_id} ***")
                            found_id = mb_id
                            return found_id # Return immediately if found
                    except: pass
            except socket.timeout:
                pass
            except Exception as e:
                print(f"[{index}] UDP Recv Error: {e}")
                break
    except Exception as e:
        print(f"[{index}] UDP Send Error: {e}")
    finally:
        sock.close()
    return found_id

if __name__ == "__main__":
    load_env_file()
    print("--- SDCP Debug Tool (Zero Dependency) ---")
    
    # Try discovery to get Mainboard ID
    # We'll valid try to use the first one found for all, 
    # OR ideally we match IP. But for now let's just get ANY ID.
    global_mainboard_id = check_udp_discovery(0)
    
    if global_mainboard_id:
        print(f"Using MainboardID: {global_mainboard_id} for tests.")
    else:
        print("No MainboardID found via UDP. Will try generic requests (might fail).")

    for i in range(1, 4):
        # Pass mainboard ID if we have it? 
        # For now, let's update check_sdcp to take an optional ID
        # We need to hack the loop above to pass it.
        # But check_sdcp signature is fixed. 
        # Let's just use the global variable or modify check_sdcp in-place.
        pass 
        
    # Re-define check_sdcp call or cleaner approach:
    # Actually, let's just modify the loop below to pass it if I modify the function signature.
    # But I can't easily change the signature in this patch verify easily without rewriting check_sdcp header.
    # So I will use a global or re-read it.
    
    # Wait, I can just modify the loop implementation in `if __name__` block.
    # But check_sdcp needs to be updated to USE it.
    
    pass

# Redefine check_sdcp to include mainboard_id logic
# (To save tool calls, I'm bundling the function re-definition and the main block update here)

def check_sdcp(index, mainboard_id=None):
    url_env = f"PRINTER_{index}_URL"
    base_url = os.getenv(url_env)
    
    if not base_url:
        print(f"[{index}] No {url_env} found.")
        return

    host = "unknown"
    try:
        if "://" in base_url:
            host = base_url.split("://")[1].split("/")[0].split(":")[0]
        else:
            host = base_url.split(":")[0]
    except:
        pass
        
    port = 3030
    print(f"[{index}] Sending WebSocket handshake to {host}:{port}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        ws_handshake(sock, host, port)
        print(f"[{index}] Handshake Success! Sending status request...")
        
        topic_status = "sdcp/request/status"
        if mainboard_id:
            topic_status = f"sdcp/request/{mainboard_id}/status" # Guessing topic format
        
        cmds_to_try = []
        
        # 1. With MainboardID if available
        if mainboard_id:
             cmds_to_try.append(json.dumps({
                "Id": f"{int(time.time()*1000)}", 
                "Topic": f"sdcp/request/{mainboard_id}", # Another guess
                "Data": {"Cmd": "GetStatus", "MainboardID": mainboard_id} 
            }))
             cmds_to_try.append(json.dumps({
                "Id": f"{int(time.time()*1000)+1}", 
                "Topic": "sdcp/request/status",
                "Data": {"Cmd": "GetStatus", "MainboardID": mainboard_id, "From": "Client"} 
            }))

        # 2. Generic Fallbacks
        cmds_to_try.extend([
            json.dumps({
                "Id": f"{int(time.time()*1000)+10}", 
                "Topic": "sdcp/request/status",
                "Data": {"Cmd": "GetStatus"} 
            }),
             json.dumps({
                "Id": f"{int(time.time()*1000)+11}", 
                "Topic": "sdcp/request/status",
                "Data": {"Cmd": 0} 
            })
        ])

        print(f"[{index}] Sending {len(cmds_to_try)} command variations...")
        for cmd in cmds_to_try:
            print(f"[{index}] >> {cmd}")
            ws_send_text(sock, cmd)
            time.sleep(1.0)
        
        print(f"[{index}] Listening for 10 seconds...")
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                opcode, data = ws_recv_frame(sock)
                if opcode == 0x8:
                    print(f"[{index}] Server sent Close frame")
                    break
                if opcode == 0x1:
                    text = data.decode('utf-8')
                    print(f"[{index}] RECV: {text[:200]}...") # Truncate for sanity
            except socket.timeout:
                pass
            except Exception as e:
                print(f"[{index}] Read Error: {e}")
                break
                
        sock.close()
    except Exception as e:
        print(f"[{index}] Failed: {e}")

if __name__ == "__main__":
    load_env_file()
    print("--- SDCP Debug Tool (Zero Dependency) ---")
    
    mb_id = check_udp_discovery(0)
    
    if mb_id:
        print(f"Using MainboardID: {mb_id} for tests.")
    else:
        print("No MainboardID found via UDP. Will try generic requests.")

    for i in range(1, 4):
        check_sdcp(i, mb_id)
