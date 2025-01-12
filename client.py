# client.py
import socket
import struct
import threading
import time

MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
UDP_PORT = 30001
TCP_PORT = 30002
BUFFER_SIZE = 1024
RECV_BUFFER_SIZE = 1024  # Standard buffer size for receiving data

# ANSI Color Codes
BLUE = '\033[94m'
RESET = '\033[0m'

# Packet Format Constants
OFFER_PACKET_FORMAT = '!IbHH'
OFFER_PACKET_SIZE = struct.calcsize(OFFER_PACKET_FORMAT)

REQUEST_PACKET_FORMAT = '!IbQ'
REQUEST_PACKET_SIZE = struct.calcsize(REQUEST_PACKET_FORMAT)

PAYLOAD_PACKET_FORMAT = '!IbQQ'
PAYLOAD_PACKET_HEADER_SIZE = struct.calcsize(PAYLOAD_PACKET_FORMAT)

def listen_for_offers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', UDP_PORT))
        while True:
            data, addr = s.recvfrom(RECV_BUFFER_SIZE)
            magic_cookie, msg_type, udp_port, tcp_port = struct.unpack(OFFER_PACKET_FORMAT, data)
            if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_TYPE:
                print(f"{BLUE}[Client] Offer received from {addr[0]} UDP port: {udp_port} TCP port: {tcp_port}{RESET}")
                return addr[0], udp_port, tcp_port

def tcp_download(server_ip, tcp_port, file_size, connection_id):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_ip, tcp_port))
        s.sendall(f"{file_size}\n".encode())
        start_time = time.time()
        received = 0
        while received < file_size:
            data = s.recv(BUFFER_SIZE)
            received += len(data)
        duration = time.time() - start_time
        print(f"{BLUE}[Client] TCP download #{connection_id} complete in {duration:.2f} seconds{RESET}")

def udp_download(server_ip, udp_port, file_size, connection_id):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        request = struct.pack(REQUEST_PACKET_FORMAT, MAGIC_COOKIE, REQUEST_TYPE, file_size)
        s.sendto(request, (server_ip, udp_port))
        start_time = time.time()
        received_segments = set()
        total_segments = 0
        while True:
            try:
                s.settimeout(1)
                data, _ = s.recvfrom(RECV_BUFFER_SIZE)
                if len(data) >= PAYLOAD_PACKET_HEADER_SIZE:
                    _, msg_type, total_segments, segment_number = struct.unpack(PAYLOAD_PACKET_FORMAT, data[:PAYLOAD_PACKET_HEADER_SIZE])
                    if msg_type == PAYLOAD_TYPE:
                        received_segments.add(segment_number)
            except socket.timeout:
                break
        duration = time.time() - start_time
        if total_segments > 0:
            success_rate = (len(received_segments) / total_segments) * 100
        else:
            success_rate = 0.0
        print(f"{BLUE}[Client] UDP download #{connection_id} complete in {duration:.2f} seconds with {success_rate:.2f}% packet success rate{RESET}")

def main():
    file_size = int(input("Enter file size in bytes: "))
    tcp_conn = int(input("Enter number of TCP connections: "))
    udp_conn = int(input("Enter number of UDP connections: "))

    server_ip, udp_port, tcp_port = listen_for_offers()

    for i in range(1, tcp_conn + 1):
        threading.Thread(target=tcp_download, args=(server_ip, tcp_port, file_size, i)).start()
    for i in range(1, udp_conn + 1):
        threading.Thread(target=udp_download, args=(server_ip, udp_port, file_size, i)).start()

if __name__ == "__main__":
    main()