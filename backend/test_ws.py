import socket

def test_websocket():
    req = (
        "GET /ws/chat/6/ HTTP/1.1\\r\\n"
        "Host: localhost:8000\\r\\n"
        "Upgrade: websocket\\r\\n"
        "Connection: Upgrade\\r\\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\\r\\n"
        "Sec-WebSocket-Version: 13\\r\\n\\r\\n"
    )
    
    try:
        s = socket.create_connection(('localhost', 8000), timeout=5)
        s.sendall(req.encode())
        
        response = s.recv(4096).decode(errors='replace')
        print("--- SERVER RESPONSE ---")
        print(response)
        s.close()
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_websocket()
