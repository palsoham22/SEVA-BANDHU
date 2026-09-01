import socket

def test_websocket():
    req = (
        "GET /ws/chat/6/ HTTP/1.1\\r\\n"
        "Host: 127.0.0.1:8001\\r\\n"
        "Upgrade: websocket\\r\\n"
        "Connection: Upgrade\\r\\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\\r\\n"
        "Sec-WebSocket-Version: 13\\r\\n\\r\\n"
    )
    
    try:
        s = socket.create_connection(('127.0.0.1', 8001), timeout=5)
        s.sendall(req.encode())
        
        response = s.recv(4096).decode(errors='replace')
        print("--- SERVER RESPONSE ---")
        print(response)
        s.close()
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_websocket()
