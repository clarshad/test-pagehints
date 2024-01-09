import cv2
import json
import os

from shared_constants import IMAGE_TEMP_PATH, SCORE_THRESHOLD


def display_image(img):
    """
    Just for visualization
    :param img: cv2 image
    :return: None
    """
    cv2.namedWindow("image", cv2.WINDOW_NORMAL)
    cv2.imshow('image', img)
    k = cv2.waitKey(0) & 0xFF
    # wait for ESC key to exit
    if k == 27:
        cv2.destroyAllWindows()
    cv2.destroyAllWindows()


def visualize(predicted_page, original_img_name, path):
    img_path = os.path.join(path, original_img_name)
    img_rgb = cv2.imread(img_path)

    for w in predicted_page["columnSplitRegionList"]:
        l = int(w['l'])
        t = int(w['t'])
        r = int(w['r'])
        b = int(w['b'])
        if float(w["confidenceScore"]) > SCORE_THRESHOLD:
            img_rgb = cv2.rectangle(img_rgb, (l, t), (r, b), (0, 0, 255), 2)
            # cv2.putText(img_rgb, str(w["confidenceScore"]), (l,t - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
        else:
            pass
            # img_rgb = cv2.rectangle(img_rgb, (l,t), (r,b), (218,165,32), 2)
            # cv2.putText(img_rgb, str(w["confidenceScore"]), (round(l,1),round(t,1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

    for table in predicted_page["tableRegionList"]:
        if table["boundedRegion"]:
            l = int(table["boundedRegion"]['l'])
            t = int(table["boundedRegion"]['t'])
            r = int(table["boundedRegion"]['r'])
            b = int(table["boundedRegion"]['b'])
            if float(table["boundedRegion"]["confidenceScore"]) > SCORE_THRESHOLD:
                img_rgb = cv2.rectangle(img_rgb, (l, t), (r, b), (0, 255, 0), 2)
            else:
                pass
               
    for vert_line in predicted_page["pagePrintedBorderDetail"]["verticalLines"]:
        # print(vert_line)
        # pointA is bottom and pointB is top, so pointB is the start point and pointA is the end point for opencv
        x0 = vert_line["pointB"]["x"]
        y0 = vert_line["pointB"]["y"]
        x1 = vert_line["pointA"]["x"]
        y1 = vert_line["pointA"]["y"]
        # cv2.line(img, start_point, end_point, color, thickness)
        cv2.line(img_rgb, (x0, y0), (x1, y1), (255, 0, 0), 2)

    for hor_line in predicted_page["pagePrintedBorderDetail"]["horizontalLines"]:
        x0 = hor_line["pointB"]["x"]
        y0 = hor_line["pointB"]["y"]
        x1 = hor_line["pointA"]["x"]
        y1 = hor_line["pointA"]["y"]
        # cv2.line(img, start_point, end_point, color, thickness)
        cv2.line(img_rgb, (x0, y0), (x1, y1), (255, 168, 0), 2)

    plotted_name = "all_plotted_" + str(original_img_name)
    plotted_path = os.path.join(path, plotted_name)
    cv2.imwrite(plotted_path, img_rgb)
    cv2.destroyAllWindows()
