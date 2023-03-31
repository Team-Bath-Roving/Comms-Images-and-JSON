"""Config"""
# Network information
ROVER_IP = "localhost"

# Camera information
NUM_CAMS = 1
CAM_NAMES = ["Cam 1"]
# ASPECT_RATIO = 16 / 9  # rover camera aspect ratio
ASPECT_RATIO = 640/480  # my computer aspect ratio
CAM_GREYSCALE = False

# ========================================================

# Import modules
from base64 import encode
import struct
import socket
import time
import json
import threading
import queue
import cv2

from classes.FeedManager import FeedManager
# from classes.ActionHandler import ActionHandler
from classes.Sockets import SocketTimeout, SendSocket, CameraReceive, FeedbackReceive, ControlSend


# commands: rover receives on port 5001 and sends on port 5002
# images: each camera uses the next port to send images

# Listening for rover signals
"""def listen_function(fb_queue, img_queue):
    PAYLOAD_STRING = "<H" + "I" * NUM_CAMS + "d"
    PAYLOAD_SIZE = struct.calcsize(PAYLOAD_STRING)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as recvsock:

            s = ReceiveSocket(recvsock, 5002)
            overflow = b""

            while True:
                try:
                    # Unpack the size of the encoded feedback and images
                    encoded_sizes, overflow = s.recv_data(PAYLOAD_SIZE, overflow)
                    # split the initial data received into the timestamp and the sizes
                    sizes = struct.unpack(PAYLOAD_STRING, encoded_sizes)

                    timestamp = sizes[-1]
                    # print(f"transmitted in {(time.time() - timestamp)/1000} ms")

                    # Receive and decode feedback, then queue if not empty
                    encoded_feedback, overflow = s.recv_data(sizes[0], overflow)
                    fb = json.loads(encoded_feedback.decode())
                    if fb: fb_queue.put(fb)

                    # Receive encoded image frames
                    for size in sizes[1:-1]:
                        encoded_img, overflow = s.recv_data(size, overflow)
                        img_queue.put(encoded_img)

                except SocketTimeout as st:
                    print(st.message)
                    print("Receive: Wait for reconnect")
                    # re-initialise the socket connection
                    s.socket.listen(1)
                    s.accept()
                    print("Receive: Reconnected")"""


# Pygame function
def pygame_function(fb_queue, img1_queue):
    # Set up send socket
    send_sock = ControlSend(ROVER_IP)
    send_sock.connect()

    # Loop until user end the program
    done = False

    # Create instance of FeedManager and set up CameraFeeds
    fm = FeedManager(CAM_NAMES, ASPECT_RATIO, CAM_GREYSCALE)

    # Encoded frames received from rover
    encoded_frames = [False] * NUM_CAMS

    while not done:

        # Displaying rover feedback
        while not fb_queue.empty():
            print(fb_queue.get())  # [Temp] Just print out feedback to console

        # Displaying camera feeds
        if img1_queue.full():
            encoded_frames = [img1_queue.get() for _ in range(NUM_CAMS)]

        fm.display_feeds(encoded_frames)

        # send connection test message, this makes sure that the rover receive function is active
        send_sock.send({"CONN TEST": 0})

        if cv2.waitKey(1) == ord("r"):
            print("send control message")
            send_sock.send({"FORWARD": 0.2, "SCOOP": -0.6})  # To test sending control message

        elif cv2.waitKey(1) == ord("q"):
            send_sock.send("QUIT_ROVER")
            print("Quitting code")
            break

    raise SystemExit


# Running the program
if __name__ == "__main__":
    fb_queue = queue.Queue(0)
    img1_queue = queue.Queue(NUM_CAMS)

    # thread = threading.Thread(target=listen_function, daemon=True, args=(fb_queue, img_queue,))
    # thread.start()

    feedback1 = FeedbackReceive(fb_queue, 5002)
    feedback1.start()
    img1 = CameraReceive(img1_queue, 5003)
    img1.start()

    while run := True:
        run = False
        try:
            pygame_function(fb_queue, img1_queue)
        except SocketTimeout as st:
            print(st.message)
            run = True
