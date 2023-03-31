# Network information
LAPTOP_IP = "localhost"

# Camera information
NUM_CAMS = 1

# commands: rover receives on port 5001 and sends on port 5002
# images: each camera uses the next port to send images

# ========================================================

# Import modules
import cv2
import numpy as np
import socket
import time
import struct
from random import randint
import threading
import queue
import json

from RoverSockets import FeedbackSend, ImageSend, CommandReceive, SocketTimeout


"""def listen_function(control_queue):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as recvsock:
        s = ReceiveSocket(recvsock, 5001)

        while True:
            try:
                control_data = s.recv_data()
                if "CONN TEST" not in control_data:
                    control_queue.put(control_data)
            except SocketTimeout as st:
                print(st.message)
                print("Receive: Wait for reconnect")
                # re-initialise the socket connection
                s.socket.listen(1)
                s.accept()
                print("Receive: Reconnected")"""


def main_function(control_queue):
    try:
        command_send = FeedbackSend(LAPTOP_IP)
        command_send.connect()
        img1_send = ImageSend(LAPTOP_IP)
        img1_send.connect()

        img_send_sockets = [img1_send]

        # Set up cameras (at the moment code only works with exactly 2, this will be changed)
        captures = [cv2.VideoCapture(i) for i in range(NUM_CAMS)]
        '''PAYLOAD_STRING = "<H" + "I" * NUM_CAMS + "d"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sendsock:

            # Connect to laptop
            s = SendSocket(sendsock, LAPTOP_IP, 5002, PAYLOAD_STRING)

            while True:
                try:
                    s.connect()
                    break
                except SocketTimeout as st:
                    print(st.message)
            '''

        # Send confirmation message
        msg = {"Connected": True}
        # s.send((msg, [np.array([])] * NUM_CAMS))  # Sends empty arrays as placeholders for images
        command_send.send(msg)
        for img_send in img_send_sockets:
            img_send.send(np.array([]))

        # ======

        prev_time = time.perf_counter()
        freq = 1 / 20

        # Main rover loop
        while True:

            # Unload control instructions
            while not control_queue.empty():
                instruction = control_queue.get()
                if instruction == "QUIT_ROVER":
                    print("Quit instruction received, exiting")
                    for cap in captures:
                        cap.release()
                    command_send.stop()
                    img1_send.stop()
                    raise SystemExit
                else:
                    print(instruction)  # [Temp] Just print out instruction to console

            # Send feedback and images
            if time.perf_counter() - prev_time > freq:

                # [Temp] Feedback
                i = randint(0, 1000)
                if i <= 20:
                    fb = {"Test feedback": f"{i}"}
                else:
                    fb = {}

                # Camera
                frames = []
                for i, cap in enumerate(captures):
                    ret, frame = cap.read()

                    if not ret:
                        print(f"Skipped frame {i}")
                        frame = np.array([])
                    else:
                        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Comment this line out for colour images
                        sf = 0.4  # Scale factor
                        frame = cv2.resize(frame, (0, 0), fx=sf, fy=sf)

                    frames.append(frame)

                    command_send.send(fb)
                    for x, img_send in enumerate(img_send_sockets):
                        img1_send.send(frames[x])
                    # s.send((fb, frames))

                prev_time = time.perf_counter()

    except KeyboardInterrupt:
        print(" KeyboardInterrupt caught")
        for cap in captures:
            cap.release()
        raise SystemExit


if __name__ == "__main__":
    control_queue = queue.Queue(0)

    # thread = threading.Thread(target=listen_function, daemon=True, args=(control_queue,))
    # thread.start()

    command1 = CommandReceive(control_queue, 5001)
    command1.start()

    while run := True:
        run = False
        try:
            main_function(control_queue)
        except SocketTimeout as st:
            print(st.message)
            run = True

