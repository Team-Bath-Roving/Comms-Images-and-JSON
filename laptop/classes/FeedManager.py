import numpy as np
import cv2


class FeedManager:
    """
    Manages all the camera feeds (refreshing, positioning, etc)
    """

    def __init__(self, names, ratio, greyscale):
        self.names = names
        self.ratio = ratio

        self.BPP = 1 if greyscale else 3  # bytes per pixel (3 for RGB, 1 for greyscale (or other compression))

    def decode_frame(self, encoded_data):
        """Decodes bytes into a numpy array representing a frame"""
        # If there is no data, return False
        if not encoded_data:
            return False

        flat_frame = np.frombuffer(encoded_data, dtype="uint8")

        j = self.ratio  # 16/9 # known ratio of width/height
        k = flat_frame.shape[0] // self.BPP

        w = int(np.sqrt(k * j))  # here we do some maths to work out width and height
        h = k // w

        frame = flat_frame.reshape(h, w, self.BPP)

        return frame

    def display_feeds(self, encoded_frames):
        """[For test only] Display a window for each camera feed"""

        # Check correct number of frames have been sent through
        if len(encoded_frames) != len(self.names):
            raise Exception("Unexpected number of camera frames")

        # Decode and display frames
        for i, encoded in enumerate(encoded_frames):
            decoded = self.decode_frame(encoded)

            cv2.imshow(self.names[i], decoded)
