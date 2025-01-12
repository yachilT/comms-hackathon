# server.py
import socket
import threading
import struct
import time
# import tqdm
# from tqdm import tqdm

MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
UDP_PORT = 30001
TCP_PORT = 30002
BUFFER_SIZE = 1024
RECV_BUFFER_SIZE = 1024  # Standard buffer size for receiving data
INADDR_BROAD = '192.168.215.255'
# ANSI Color Codes
GREEN = '\033[92m'
RESET = '\033[0m'

# Packet Format Constants
OFFER_PACKET_FORMAT = '!IbHH'
OFFER_PACKET_SIZE = struct.calcsize(OFFER_PACKET_FORMAT)

REQUEST_PACKET_FORMAT = '!IbQ'
REQUEST_PACKET_SIZE = struct.calcsize(REQUEST_PACKET_FORMAT)

PAYLOAD_PACKET_FORMAT = '!IbQQ'
PAYLOAD_PACKET_HEADER_SIZE = struct.calcsize(PAYLOAD_PACKET_FORMAT)

CONTENT_DEBUG = False
def send_offers():
    offer_message = struct.pack(OFFER_PACKET_FORMAT, MAGIC_COOKIE, OFFER_TYPE, UDP_PORT, TCP_PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            s.sendto(offer_message, (INADDR_BROAD, UDP_PORT))
            print(f"{GREEN}[Server] Offer sent: {offer_message} {RESET}")
            time.sleep(1)

def handle_tcp_client(conn, addr, file_size):
    print(f"{GREEN}[Server] TCP connection from {addr}{RESET}")
    data = b'x' * file_size
    conn.sendall(data)
    conn.close()

def handle_udp_client(addr, file_size):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        data_size = (BUFFER_SIZE - PAYLOAD_PACKET_HEADER_SIZE)
        total_segments = file_size // data_size
        last_segment_size = file_size % data_size
        for segment in range(total_segments):
            payload = struct.pack(PAYLOAD_PACKET_FORMAT, MAGIC_COOKIE, PAYLOAD_TYPE, total_segments + (1 if last_segment_size > 0 else 0), segment) + b'x' * data_size
            if CONTENT_DEBUG:
                print(f"{GREEN}[Server] sending udp packet with size {len(payload)} completed.{RESET}")
            udp_socket.sendto(payload, addr)
        if last_segment_size > 0:
            payload = struct.pack(PAYLOAD_PACKET_FORMAT, MAGIC_COOKIE, PAYLOAD_TYPE, total_segments + 1, total_segments) + b'x' * last_segment_size
            udp_socket.sendto(payload, addr)
        print(f"{GREEN}[Server] UDP transfer to {addr} completed.{RESET}")

def tcp_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', TCP_PORT))
        s.listen()
        print(f"{GREEN}[Server] TCP server listening on port {TCP_PORT}{RESET}")
        while True:
            conn, addr = s.accept()
            file_size = int(conn.recv(RECV_BUFFER_SIZE).decode().strip())
            threading.Thread(target=handle_tcp_client, args=(conn, addr, file_size)).start()

def udp_listener():
    with (socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s):
        s.bind(('', UDP_PORT))
        print(f"{GREEN}[Server] UDP server listening on port {UDP_PORT}{RESET}")
        while True:
            data, addr = s.recvfrom(RECV_BUFFER_SIZE)
            if len(data) >= REQUEST_PACKET_SIZE and \
                struct.unpack(REQUEST_PACKET_FORMAT, data[:REQUEST_PACKET_SIZE])[0:2] == (MAGIC_COOKIE, REQUEST_TYPE):

                print(f"{GREEN}[Server] UDP request received from {addr}{RESET}")
                file_size = struct.unpack(REQUEST_PACKET_FORMAT, data[:REQUEST_PACKET_SIZE])[2]
                threading.Thread(target=handle_udp_client, args=(addr, file_size)).start()

def main():
    threading.Thread(target=send_offers).start()
    threading.Thread(target=tcp_listener).start()
    threading.Thread(target=udp_listener).start()

if __name__ == "__main__":
    main()