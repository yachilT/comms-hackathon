# client.py
import socket
import struct
import threading
import time

from server import TCP_PORT

MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
BROADCAST_LISTEN_PORT = 30003
BUFFER_SIZE = 1024
RECV_BUFFER_SIZE = 1024  # Standard buffer size for receiving data

# ANSI Color Codes
BLUE = '\033[94m'
COLORS = ['\033[90m', '\033[91m', '\033[92m', '\033[93m', '\033[95m', '\033[96m', '\033[97m']
UDP_DOWNLOAD_COLOR = COLORS[3]
TCP_DOWNLOAD_COLOR = COLORS[1]

ADDR_COLOR = '\033[036m'
METRIC_COLOR = COLORS[2]
ID_COLOR = COLORS[5]
OFFER_COLOR = COLORS[4]
DATA_COLOR = BLUE

RESET = '\033[0m'

# Packet Format Constants
OFFER_PACKET_FORMAT = '!IbHH'
OFFER_PACKET_SIZE = struct.calcsize(OFFER_PACKET_FORMAT)

REQUEST_PACKET_FORMAT = '!IbQ'
REQUEST_PACKET_SIZE = struct.calcsize(REQUEST_PACKET_FORMAT)

PAYLOAD_PACKET_FORMAT = '!IbQQ'
PAYLOAD_PACKET_HEADER_SIZE = struct.calcsize(PAYLOAD_PACKET_FORMAT)


DEBUG_CONTENT = False

def listen_for_offers():
    print(f"{BLUE}[Client]{OFFER_COLOR} Listening for offers...{RESET}")
    with (socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', BROADCAST_LISTEN_PORT))
        while True:
            data, addr = s.recvfrom(RECV_BUFFER_SIZE)
            magic_cookie, msg_type, udp_port, tcp_port = struct.unpack(OFFER_PACKET_FORMAT, data)
            if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_TYPE:
                print(f"{BLUE}[Client]{RESET} {OFFER_COLOR}Offer received{RESET} from {ADDR_COLOR}{addr[0]}{RESET} {UDP_DOWNLOAD_COLOR}UDP{RESET} port: {ADDR_COLOR}{udp_port}{RESET} {TCP_DOWNLOAD_COLOR}TCP{RESET} port: {ADDR_COLOR}{tcp_port}{RESET}")
                return addr[0], udp_port, tcp_port

def tcp_download(server_ip, tcp_port, file_size, connection_id):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_ip, tcp_port))
        s.sendall(f"{file_size}\n".encode())
        print(f"{BLUE}[Client]{RESET} {TCP_DOWNLOAD_COLOR}TCP{TCP_DOWNLOAD_COLOR} download {ID_COLOR}#{connection_id}{RESET} requested{RESET}")
        start_time = time.time()
        received = 0
        while received < file_size:
            data = s.recv(BUFFER_SIZE)
            received += len(data)
        duration = time.time() - start_time
        print(f"{BLUE}[Client]{RESET} {TCP_DOWNLOAD_COLOR}TCP{TCP_DOWNLOAD_COLOR} download {ID_COLOR}#{connection_id}{RESET} complete in {METRIC_COLOR}{duration:.2f} seconds{RESET}, total speed: {METRIC_COLOR}{file_size / duration / 1000:.2f} kB/s{RESET}")

def udp_download(server_ip, udp_port, file_size, connection_id):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        request = struct.pack(REQUEST_PACKET_FORMAT, MAGIC_COOKIE, REQUEST_TYPE, file_size)
        s.sendto(request, (server_ip, udp_port))
        print(f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}UDP download {ID_COLOR}#{connection_id}{RESET} requested")
        start_time = time.time()
        received_segments = set()
        total_segments = 0
        data_size = 0
        while True:
            try:
                s.settimeout(1)
                data, _ = s.recvfrom(RECV_BUFFER_SIZE)
                if len(data) >= PAYLOAD_PACKET_HEADER_SIZE:
                    _, msg_type, total_segments, segment_number = struct.unpack(PAYLOAD_PACKET_FORMAT, data[:PAYLOAD_PACKET_HEADER_SIZE])
                    if msg_type == PAYLOAD_TYPE:
                        if DEBUG_CONTENT:
                            print(f"{BLUE}[Client]{RESET} Received {UDP_DOWNLOAD_COLOR}UDP{RESET} segment{METRIC_COLOR}{segment_number}{RESET}")
                        received_segments.add(segment_number)
                        data_size += len(data[PAYLOAD_PACKET_HEADER_SIZE:])
            except socket.timeout:
                break
        duration = time.time() - start_time
        if total_segments > 0:
            success_rate = (len(received_segments) / total_segments) * 100
        else:
            success_rate = 0.0
        print(f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}UDP download{RESET} {ID_COLOR}#{connection_id}{RESET} complete in {METRIC_COLOR}{duration:.2f} seconds{RESET}, speed: {METRIC_COLOR}{data_size / duration / 1000 :.2f} kB/s{RESET}, with {METRIC_COLOR}{success_rate:.2f}%{RESET} packet success rate{RESET}")

def main():
    while True:
        file_size = int(input("Enter file size in bytes: "))
        tcp_conn = int(input("Enter number of TCP connections: "))
        udp_conn = int(input("Enter number of UDP connections: "))

        server_ip, udp_port, tcp_port = listen_for_offers()
        udp_threads = []
        tcp_threads = []
        for i in range(1, tcp_conn + 1):
            tcp_threads.append(threading.Thread(target=tcp_download, args=(server_ip, tcp_port, file_size, i)))

        for i in range(1, udp_conn + 1):
            udp_threads.append(threading.Thread(target=udp_download, args=(server_ip, udp_port, file_size, i)))

        for t in tcp_threads:
            t.start()

        for t in udp_threads:
            t.start()

        for t in tcp_threads:
            t.join()

        for t in udp_threads:
            t.join()

        print(f"{BLUE}[Client]{RESET} All transfers complete, listening to {OFFER_COLOR}offer requests{RESET}")


if __name__ == "__main__":
    main()