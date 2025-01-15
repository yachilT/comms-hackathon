# client.py
import socket
import struct
import threading
import time

GOOSE = "    __  \n  >(o )___  \n   (  ._> /  \n    `----'   "



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
ERROR = '\033[91m'

# Packet Format Constants
OFFER_PACKET_FORMAT = '!IbHH'
OFFER_PACKET_SIZE = struct.calcsize(OFFER_PACKET_FORMAT)

REQUEST_PACKET_FORMAT = '!IbQ'
REQUEST_PACKET_SIZE = struct.calcsize(REQUEST_PACKET_FORMAT)

PAYLOAD_PACKET_FORMAT = '!IbQQ'
PAYLOAD_PACKET_HEADER_SIZE = struct.calcsize(PAYLOAD_PACKET_FORMAT)


DEBUG_CONTENT = False


def listen_for_offers():
    """
       Listens for broadcast offers over UDP and processes incoming packets with error checking.

       Returns:
           tuple: A tuple containing the sender's IP address (str), UDP port (int), and TCP port (int).

       Raises:
           RuntimeError: For any critical errors during socket operations or data unpacking.
    """
    print(f"{BLUE}[Client]{OFFER_COLOR} Listening for offers...{RESET}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('', BROADCAST_LISTEN_PORT))
            except socket.error as e:
                raise RuntimeError(f"Socket binding failed: {e}")

            while True:
                try:
                    data, addr = s.recvfrom(RECV_BUFFER_SIZE)
                    magic_cookie, msg_type, udp_port, tcp_port = struct.unpack(OFFER_PACKET_FORMAT, data)
                    if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_TYPE:
                        print(
                            f"{BLUE}[Client]{RESET} {OFFER_COLOR}Offer received{RESET} from {ADDR_COLOR}{addr[0]}{RESET} {UDP_DOWNLOAD_COLOR}UDP{RESET} port: {ADDR_COLOR}{udp_port}{RESET} {TCP_DOWNLOAD_COLOR}TCP{RESET} port: {ADDR_COLOR}{tcp_port}{RESET}")
                        return addr[0], udp_port, tcp_port
                    else:
                        print(
                            f"{ERROR}[Error]{RESET} {OFFER_COLOR}Invalid packet received from {ADDR_COLOR}{addr[0]}{RESET}")
                except struct.error as e:
                    print(
                        f"{ERROR}[Error]{RESET} {OFFER_COLOR}Failed to unpack data from {ADDR_COLOR}{addr[0]}{RESET}: {e}")
                except socket.error as e:
                    print(f"{ERROR}[Error]{RESET} {OFFER_COLOR}Socket error while receiving data: {e}")
    except Exception as e:
        print(f"{ERROR}[Client]{RESET} {OFFER_COLOR}Critical error: {e}")


def tcp_download(server_ip, tcp_port, file_size, connection_id):
    """
    Downloads a file over a TCP connection from a specified server.

    Parameters:
    server_ip (str): The IP address of the server to connect to.
    tcp_port (int): The port number on which the server is listening.
    file_size (int): The expected size of the file in bytes.
    connection_id (int): An identifier for this connection (used for logging).

    Returns:
    None
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((server_ip, tcp_port))
                s.sendall(f"{file_size}\n".encode())
                print(
                    f"{BLUE}[Client]{RESET} {TCP_DOWNLOAD_COLOR}TCP{TCP_DOWNLOAD_COLOR} download {ID_COLOR}#{connection_id}{RESET} requested{RESET}")

                start_time = time.time()
                received = 0

                while received < file_size:
                    data = s.recv(BUFFER_SIZE)
                    if not data:
                        raise ConnectionError("Connection lost before file was fully received.")
                    received += len(data)

                duration = time.time() - start_time
                print(
                    f"{BLUE}[Client]{RESET} {TCP_DOWNLOAD_COLOR}TCP{TCP_DOWNLOAD_COLOR} download {ID_COLOR}#{connection_id}{RESET} complete in {METRIC_COLOR}{duration:.2f} seconds{RESET}, total speed: {METRIC_COLOR}{file_size / duration / 1000:.2f} kB/s{RESET}")

            except socket.error as e:
                print(
                    f"{ERROR}[Error]{RESET} {TCP_DOWNLOAD_COLOR}TCP{TCP_DOWNLOAD_COLOR} download {ID_COLOR}#{connection_id}{RESET} failed: {e}")

    except Exception as e:
        print(
            f"{ERROR}[Error]{RESET} {TCP_DOWNLOAD_COLOR}TCP{TCP_DOWNLOAD_COLOR} download {ID_COLOR}#{connection_id}{RESET} encountered an error: {e}")


def udp_download(server_ip, udp_port, file_size, connection_id):
    """
    Downloads a file using UDP from a specified server.

    :param server_ip: The IP address of the server.
    :param udp_port: The UDP port to connect to.
    :param file_size: The size of the file to be downloaded in bytes.
    :param connection_id: An identifier for the connection (for logging purposes).
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                request = struct.pack(REQUEST_PACKET_FORMAT, MAGIC_COOKIE, REQUEST_TYPE, file_size)
            except struct.error as e:
                print(f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}Error in struct packing: {e}{RESET}")
                return

            try:
                s.sendto(request, (server_ip, udp_port))
                print(
                    f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}UDP download {ID_COLOR}#{connection_id}{RESET} requested")
            except socket.error as e:
                print(f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}Failed to send request: {e}{RESET}")
                return

            start_time = time.time()
            received_segments = set()
            total_segments = 0
            data_size = 0

            while True:
                try:
                    s.settimeout(1)
                    data, _ = s.recvfrom(RECV_BUFFER_SIZE)
                    if len(data) >= PAYLOAD_PACKET_HEADER_SIZE:
                        try:
                            _, msg_type, total_segments, segment_number = struct.unpack(PAYLOAD_PACKET_FORMAT, data[
                                                                                                               :PAYLOAD_PACKET_HEADER_SIZE])
                        except struct.error as e:
                            print(f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}Packet unpacking error: {e}{RESET}")
                            continue

                        if msg_type == PAYLOAD_TYPE:
                            if DEBUG_CONTENT:
                                print(
                                    f"{BLUE}[Client]{RESET} Received {UDP_DOWNLOAD_COLOR}UDP{RESET} segment{METRIC_COLOR}{segment_number}{RESET}")
                            received_segments.add(segment_number)
                            data_size += len(data[PAYLOAD_PACKET_HEADER_SIZE:])
                except socket.timeout:
                    break
                except socket.error as e:
                    print(f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}Socket error during receive: {e}{RESET}")
                    break

            duration = time.time() - start_time
            success_rate = (len(received_segments) / total_segments * 100) if total_segments > 0 else 0.0

            print(
                f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}UDP download{RESET} {ID_COLOR}#{connection_id}{RESET} complete in {METRIC_COLOR}{duration:.2f} seconds{RESET}, "
                f"speed: {METRIC_COLOR}{data_size / duration / 1000 :.2f} kB/s{RESET}, with {METRIC_COLOR}{success_rate:.2f}%{RESET} packet success rate{RESET}")

    except Exception as e:
        print(f"{BLUE}[Client]{RESET} {UDP_DOWNLOAD_COLOR}Unexpected error: {e}{RESET}")


def main():
    while True:
        print(f"{UDP_DOWNLOAD_COLOR}{GOOSE}{RESET}")
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