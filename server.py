# server.py
import socket
import threading
import struct
import time
#import netifaces
# import tqdm
# from tqdm import tqdm

MAX_ERROR_COUNT = 5
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
UDP_PORT = 30001
OFFER_PORT = 30003
TCP_PORT = 30002
BUFFER_SIZE = 1024
RECV_BUFFER_SIZE = 1024  # Standard buffer size for receiving data
# ANSI Color Codes
GREEN = '\033[92m'
ERROR = '\033[91m'
RESET = '\033[0m'

# Packet Format Constants
OFFER_PACKET_FORMAT = '!IbHH'
OFFER_PACKET_SIZE = struct.calcsize(OFFER_PACKET_FORMAT)

REQUEST_PACKET_FORMAT = '!IbQ'
REQUEST_PACKET_SIZE = struct.calcsize(REQUEST_PACKET_FORMAT)

PAYLOAD_PACKET_FORMAT = '!IbQQ'
PAYLOAD_PACKET_HEADER_SIZE = struct.calcsize(PAYLOAD_PACKET_FORMAT)

CONTENT_DEBUG = False

def get_broadcast_address():
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        try:
            # Get network details for each interface
            details = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in details:  # Check for IPv4 configuration
                ipv4_info = details[netifaces.AF_INET][0]
                broadcast = ipv4_info['broadcast']
                return broadcast
        except KeyError:
            continue
    return None

def send_offers():
    error_count = 0
    broadcast_addr = get_broadcast_address()
    offer_message = struct.pack(OFFER_PACKET_FORMAT, MAGIC_COOKIE, OFFER_TYPE, UDP_PORT, TCP_PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:

        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while error_count < MAX_ERROR_COUNT:
            try:
                s.sendto(offer_message, (broadcast_addr, OFFER_PORT))
                print(f"{GREEN}[Server] Offer sent:{RESET}")
                time.sleep(1)
            except Exception as e:
                error_count += 1
                print(f"[Server] {ERROR}Error{RESET} sending offer: {e}")
        print(f"[Server] Offer sending stopped.")


def send_offers():
    """
    Broadcasts offer packets over UDP to potential clients.

    The function continuously sends offer messages to the network's broadcast address
    until either a maximum number of consecutive errors (`MAX_ERROR_COUNT`) is reached
    or the server is manually stopped. The offer message includes essential connection
    details packed according to `OFFER_PACKET_FORMAT`.

    Error Handling:
    - Handles errors in retrieving the broadcast address.
    - Handles errors during offer message packing.
    - Handles socket creation and configuration errors.
    - Handles errors during packet transmission.
    """
    error_count = 0
    try:
        broadcast_addr = get_broadcast_address()
    except Exception as e:
        print(f"{ERROR}Failed to get broadcast address: {e}{RESET}")
        return

    try:
        offer_message = struct.pack(OFFER_PACKET_FORMAT, MAGIC_COOKIE, OFFER_TYPE, UDP_PORT, TCP_PORT)
    except struct.error as e:
        print(f"{ERROR}Error packing offer message: {e}{RESET}")
        return

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except socket.error as e:
                print(f"{ERROR}[Error] Failed to set socket options: {e}{RESET}")
                return

            while error_count < MAX_ERROR_COUNT:
                try:
                    s.sendto(offer_message, (broadcast_addr, OFFER_PORT))
                    print(f"{GREEN}[Server] Offer sent.{RESET}")
                    time.sleep(1)
                except socket.error as e:
                    error_count += 1
                    print(f"{ERROR}[Error] server sending offer: {e}{RESET}")
                except Exception as e:
                    error_count += 1
                    print(f"{ERROR}[Error] Server Unexpected error: {e}{RESET}")
            print(f"{ERROR}[Error] Server Offer sending stopped after {error_count} errors.{RESET}")
    except socket.error as e:
        print(f"{ERROR}[Error] Socket creation failed: {e}{RESET}")


def handle_tcp_client(conn, addr, file_size):
    """
    Handles a TCP client connection by sending a specified amount of data.

    Parameters:
    conn (socket.socket): The socket object representing the client connection.
    addr (tuple): The address of the connected client.
    file_size (int): The size of the data (in bytes) to send to the client.

    Raises:
    ValueError: If file_size is not a positive integer.
    ConnectionError: If an error occurs during data transmission.
    """
    try:
        if not isinstance(file_size, int) or file_size <= 0:
            raise ValueError("file_size must be a positive integer.")

        print(f"{GREEN}[Server] TCP connection from {addr}{RESET}")
        data = b'x' * file_size  # Create a data payload of specified size
        conn.sendall(data)
    except (socket.error, ConnectionError) as e:
        print(f"{ERROR}[Error] Error sending data to {addr}: {e}{RESET}")
    except ValueError as ve:
        print(f"{ERROR}[Error] Invalid file size: {ve}{RESET}")
    finally:
        conn.close()  # Ensure the connection is closed
        print(f"[Server] Connection with {addr} closed.{RESET}")


def handle_udp_client(addr, file_size):
    """
    Handles UDP file transfer to a client.

    Parameters:
    addr (tuple): The address of the client as (IP, port).
    file_size (int): The size of the file to be sent in bytes.

    This function splits the file into UDP packets and sends them to the client.
    """
    try:
        # Create UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            data_size = BUFFER_SIZE - PAYLOAD_PACKET_HEADER_SIZE
            if data_size <= 0:
                raise ValueError("BUFFER_SIZE must be greater than PAYLOAD_PACKET_HEADER_SIZE.")

            total_segments = file_size // data_size
            last_segment_size = file_size % data_size
            total_segments_to_send = total_segments + (1 if last_segment_size > 0 else 0)

            for segment in range(total_segments):
                try:
                    payload = struct.pack(
                        PAYLOAD_PACKET_FORMAT,
                        MAGIC_COOKIE,
                        PAYLOAD_TYPE,
                        total_segments_to_send,
                        segment
                    ) + b'x' * data_size

                    udp_socket.sendto(payload, addr)

                    if CONTENT_DEBUG:
                        print(
                            f"{GREEN}[Server] Sent UDP packet {segment + 1}/{total_segments_to_send} with size {len(payload)} bytes.{RESET}")
                except Exception as e:
                    print(f"Error sending segment {segment}: {e}")

            if last_segment_size > 0:
                try:
                    payload = struct.pack(
                        PAYLOAD_PACKET_FORMAT,
                        MAGIC_COOKIE,
                        PAYLOAD_TYPE,
                        total_segments_to_send,
                        total_segments
                    ) + b'x' * last_segment_size
                    udp_socket.sendto(payload, addr)
                    if CONTENT_DEBUG:
                        print(f"{GREEN}[Server] Sent last UDP packet with size {len(payload)} bytes.{RESET}")
                except Exception as e:
                    print(f"Error sending last segment: {e}")

            print(f"{GREEN}[Server] UDP transfer to {addr} completed.{RESET}")

    except ValueError as ve:
        print(f"{ERROR}[ValueError]: {ve}")
    except socket.error as se:
        print(f"{ERROR}[Socket error]: {se}")
    except Exception as e:
        print(f"[ERROR][Unexpected error]: {e}")
def tcp_listener():
    """
    Starts a TCP server that listens for incoming connections and handles clients in separate threads.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', TCP_PORT))
            s.listen()
            print(f"{GREEN}[Server] TCP server listening on port {TCP_PORT}{RESET}")
            while True:
                try:
                    conn, addr = s.accept()
                    print(f"{GREEN}[Server] Connection accepted from {addr}{RESET}")
                    file_size_data = conn.recv(RECV_BUFFER_SIZE)
                    if not file_size_data:
                        print(f"{ERROR}[Error] No data received from {addr}, closing connection.{RESET}")
                        conn.close()
                        continue
                    try:
                        file_size = int(file_size_data.decode().strip())
                    except ValueError:
                        print(f"{ERROR}[Error] Invalid file size received from {addr}, closing connection.{RESET}")
                        conn.close()
                        continue
                    threading.Thread(target=handle_tcp_client, args=(conn, addr, file_size)).start()
                except Exception as e:
                    print(f"{ERROR}[Error] Error accepting connection: {e}{RESET}")
    except Exception as e:
        print(f"{ERROR}[Error] Failed to start TCP server: {e}{RESET}")

def udp_listener():
    """
    Starts a UDP server that listens for incoming requests and spawns threads to handle valid packets.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.bind(('', UDP_PORT))
                print(f"{GREEN}[Server] UDP server listening on port {UDP_PORT}{RESET}")
            except socket.error as e:
                print(f"{ERROR}[Error] Failed to bind UDP socket: {e}")
                return

            while True:
                try:
                    data, addr = s.recvfrom(RECV_BUFFER_SIZE)
                    if len(data) >= REQUEST_PACKET_SIZE:
                        unpacked_data = struct.unpack(REQUEST_PACKET_FORMAT, data[:REQUEST_PACKET_SIZE])
                        if unpacked_data[0:2] == (MAGIC_COOKIE, REQUEST_TYPE):
                            print(f"{GREEN}[Server] UDP request received from {addr}{RESET}")
                            file_size = unpacked_data[2]
                            threading.Thread(target=handle_udp_client, args=(addr, file_size)).start()
                        else:
                            print(f"[Warning] Invalid request from {addr}")
                    else:
                        print(f"[Warning] Received packet too small from {addr}")
                except struct.error as e:
                    print(f"{ERROR}[Error] Failed to unpack data from {addr}: {e}")
                except socket.error as e:
                    print(f"{ERROR}[Error] Socket error: {e}")
    except Exception as e:
        print(f"{ERROR}[Error] Unexpected error: {e}")

def main():
    offer = threading.Thread(target=send_offers)
    tcp_listen = threading.Thread(target=tcp_listener)
    udp_listen = threading.Thread(target=udp_listener)

    offer.start()
    tcp_listen.start()
    udp_listen.start()

    tcp_listen.join()
    udp_listen.join()
    offer.join()


if __name__ == "__main__":
    main()