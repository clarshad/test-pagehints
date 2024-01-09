import json
import logging
import logging.handlers
from ValidationError import ValidationError
import numpy as np
import gc
import cv2


class LineDetection():
    def __init__(self):
        self.lines = {}

    def get_image(self,j):
        j = cv2.cvtColor(np.asarray(j), cv2.COLOR_BGR2GRAY)
        img_bin = cv2.adaptiveThreshold(j, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 199, 5)
        # Invert the image
        img_bin = 255 - img_bin
        return img_bin

    def lines_image(self,img_bin,kernel):
        # A verticle kernel of (1 X kernel_length), which will detect all the verticle lines from the image.
        ker = cv2.getStructuringElement(cv2.MORPH_RECT, kernel)
        # Morphological operation to detect vertical lines from an image
        temp = cv2.erode(img_bin, ker, iterations=4)
        temp = cv2.dilate(temp, ker, iterations=4)
        return temp

    def horizontal_lines_image(self,img_bin,kernel):
        kernel_length = img_bin.shape[1] // 80
        # A horizontal kernel of (kernel_length X 1), which will help to detect all the horizontal line from the image.
        hori_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel)
        # Morphological operation to detect horizontal lines from an image
        img_temp2 = cv2.erode(img_bin, hori_kernel, iterations=4)
        horizontal_lines_img = cv2.dilate(img_temp2, hori_kernel, iterations=4)
        return horizontal_lines_img

    def detect_lines(self,lines_img):
        edges = cv2.Canny(lines_img, 50, 150, apertureSize=3)
        minLineLength = 100
        lines = cv2.HoughLinesP(image=edges, rho=1, theta=np.pi / 180, threshold=100,
                                         lines=np.array([]), minLineLength=minLineLength, maxLineGap=80)
        return lines

    def detect_horizontal_lines(self,horizontal_lines_img):
        horizontal_edges = cv2.Canny(horizontal_lines_img, 50, 150, apertureSize=3)
        minLineLength = 100
        horizontal_lines = cv2.HoughLinesP(image=horizontal_edges, rho=1, theta=np.pi / 180, threshold=100,
                                           lines=np.array([]), minLineLength=minLineLength, maxLineGap=80)
        return horizontal_lines

    def save_horizontal_lines(self,horizontal_lines):
        try:
            if horizontal_lines is not None:
                for line in horizontal_lines:
                    x1 = int(line[0][0])
                    y1 = int(line[0][1])
                    x2 = int(line[0][2])
                    y2 = int(line[0][3])
                    self.lines['horizontalLines'].append({'pointA': {"x": x1, "y": y1}, 'pointB': {"x": x2, "y": y2}})
                del horizontal_lines
                gc.collect()
        except Exception as ex:
            logging.error(str(ex))

    def save_lines(self,lines,type):
        try:
            if lines is not None:
                for line in lines:
                    x1 = int(line[0][0])
                    y1 = int(line[0][1])
                    x2 = int(line[0][2])
                    y2 = int(line[0][3])
                    self.lines[type].append({'pointA': {"x": x1, "y": y1}, 'pointB': {"x": x2, "y": y2}})
                del lines
                gc.collect()
        except Exception as ex:
            logging.error(str(ex))

    def get_type_lines(self,img,type):
        kernel_length = img.shape[1] // 80
        ker = (1, kernel_length) if type == 'verticalLines' else (kernel_length,1)
        lines_img = self.lines_image(img, ker)
        lines = self.detect_lines(lines_img)
        self.save_lines(lines, type)

    def get_lines(self,j):
        # try:
        self.lines['horizontalLines'] = []
        self.lines['verticalLines'] = []
        img = self.get_image(j)
        self.get_type_lines(img, 'verticalLines')
        self.get_type_lines(img, 'horizontalLines')
        del img,j
        gc.collect()
        cv2.destroyAllWindows()
        return self.lines


