import socket
import json
import time
import struct
import threading


class SocketTimeout(Exception):
    """
	Custom Exception to catch when a socket is disconnected
	"""

    def __init__(self, message=""):
        self.message = message


class SendSocket:
    """
	Handles sending of information over socket
	"""

    def __init__(self, target, port, payload_string):
        self.socket = None
        self.target = target
        self.port = port
        self.payload_string = payload_string

    def connect(self):
        """Connects/ reconnects socket to target"""
        if self.socket is None:
            self.start()

        try:
            self.socket.connect((self.target, self.port))
        except ConnectionRefusedError:
            raise SocketTimeout("Connect: Rover connection refused, reconnecting...")
        print(f"Send socket connected to port {self.port}")

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def stop(self):
        self.socket.close()

    def send(self, data):
        """Decode, calculate sizes and send feedback + camera frames"""
        fb, imgs = data
        encoded_fb = json.dumps(fb).encode()
        fb_size = len(encoded_fb)

        encoded_imgs = [img.tobytes() for img in imgs]
        img_sizes = [len(img) for img in encoded_imgs]

        sizes = struct.pack(self.payload_string, fb_size, *img_sizes, time.time())

        try:
            self.socket.sendall(sizes + encoded_fb + b"".join(encoded_imgs))
        except ConnectionResetError:
            raise SocketTimeout("Send: Rover connection closed, waiting to reconnect...")


class ControlSend(SendSocket):
    def __init__(self, target, port=5001, payload_string="<Hd"):
        super().__init__(target, port, payload_string)

    def send(self, message):
        """Decode, calculate sizes and send feedback"""
        encoded_message = json.dumps(message).encode()
        message_size = len(encoded_message)

        sizes = struct.pack(self.payload_string, message_size, time.time())

        try:
            self.socket.sendall(sizes + encoded_message)
        except ConnectionResetError:
            raise SocketTimeout("Send: Rover connection closed, waiting to reconnect...")


class ReceiveSocket:
    """
	Handles receiving information over socket
	"""

    def __init__(self, port, payload_string):
        self.socket = None
        self.port = port
        self.conn = None

        self.running = False

        self.overflow = b""
        self.payload_string = payload_string
        self.payload_size = struct.calcsize(self.payload_string)

    def accept(self):
        """Connects/ reconnects to incoming traffic"""
        if self.socket is None:
            print("No open socket to connect to")
            return
        self.conn, _ = self.socket.accept()
        print(f"Receive socket connected to port {self.port}")

    def recv_data(self, size=None):
        """Receive encoded data of specified size over socket"""
        if size is None:
            size = self.payload_size

        data = self.overflow
        start_time = time.perf_counter()

        while len(data) < size:
            try:
                data += self.conn.recv(4096)
            except ConnectionResetError:
                raise SocketTimeout("Receive: Connection reset")

            if time.perf_counter() - start_time > 0.5 and False:  # temporarily disable this function
                raise SocketTimeout("Receive: Timeout")

        self.overflow = data[size:]
        return data[:size]

    def start(self):
        self.running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def process_data(self, data):
        return

    def receive_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.socket:

            # set socket options and get incoming connections
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(("", self.port))
            self.socket.listen(1)
            self.accept()

            while self.running:
                try:
                    # Unpack the size of the encoded feedback and images
                    encoded_sizes = self.recv_data()
                    # split the initial data received into the timestamp and the sizes
                    data = struct.unpack(self.payload_string, encoded_sizes)

                    self.process_data(data)

                except SocketTimeout as st:
                    print(st.message)
                    print("Receive: Wait for reconnect")
                    # re-initialise the socket connection
                    self.socket.listen(1)
                    self.accept()
                    print("Receive: Reconnected")


class FeedbackReceive(ReceiveSocket):
    def __init__(self, fb_queue, port=5002, payload_string="<Hd"):
        super().__init__(port, payload_string)

        self.fb_queue = fb_queue

    def process_data(self, data):
        timestamp = data[-1]
        # print(f"transmitted in {(time.time() - timestamp)/1000} ms")

        # Receive and decode feedback, then queue if not empty
        encoded_feedback = self.recv_data(data[0])
        fb = json.loads(encoded_feedback.decode())
        if fb:
            self.fb_queue.put(fb)


class CameraReceive(ReceiveSocket):
    def __init__(self, img_queue, port=5003, payload_string="Id"):
        super().__init__(port, payload_string)

        self.img_queue = img_queue

    def process_data(self, data):
        timestamp = data[-1]

        # Receive encoded image frames
        encoded_img = self.recv_data(data[0])
        self.img_queue.put(encoded_img)
