from mmdet.apis import init_detector, inference_detector
from time import time
import os
import logging
import cv2
import numpy as np
import gc

from shared_constants import IMAGE_TEMP_PATH, SCORE_THRESHOLD


def basicTransform(img):
    _, mask = cv2.threshold(img, 220, 255, cv2.THRESH_BINARY_INV)
    img = cv2.bitwise_not(mask)
    return img


def smudge_img(image_loc, smudge_im_path):
    # Split the 3 channels into Blue,Green and Red
    img = cv2.imread(image_loc)
    # Split the 3 channels into Blue,Green and Red
    b, g, r = cv2.split(img)

    # Apply Basic Transformation
    b = basicTransform(b)
    r = basicTransform(r)
    g = basicTransform(g)

    # Perform the distance transform algorithm
    b = cv2.distanceTransform(b, cv2.DIST_L2, 5)  # ELCUDIAN
    g = cv2.distanceTransform(g, cv2.DIST_L1, 5)  # LINEAR
    r = cv2.distanceTransform(r, cv2.DIST_C, 5)  # MAX

    # Normalize
    r = cv2.normalize(r, r, 0, 1.0, cv2.NORM_MINMAX)
    g = cv2.normalize(g, g, 0, 1.0, cv2.NORM_MINMAX)
    b = cv2.normalize(b, b, 0, 1.0, cv2.NORM_MINMAX)

    # Merge the channels
    dist = cv2.merge((b, g, r))
    dist = cv2.normalize(dist, dist, 0, 4.0, cv2.NORM_MINMAX)
    dist = cv2.cvtColor(dist, cv2.COLOR_BGR2GRAY)

    # In order to save as jpg, or png, we need to handle the Data
    # format of image
    data = dist.astype(np.float64) / 4.0
    data = 1800 * data  # Now scale by 1800
    dist = data.astype(np.uint16)

    # Save to destination
    cv2.imwrite(smudge_im_path, dist)


def format_result_classwise_new(result):
    # Classes in models are  :('bordered', 'cell', 'borderless')
    res_cell = []
    res_table = []

    for r in result[0][0]:
        if r[4] * 100 > SCORE_THRESHOLD:
            temp = {"l": int(r[0]), "t": int(r[1]), "r": int(r[2]), "b": int(r[3]), "confidenceScore": str(r[4] * 100),
                    "content": None}
            res_table.append(temp)

    for r in result[0][1]:
        if r[4] * 100 > SCORE_THRESHOLD:
            temp = {"l": int(r[0]), "t": int(r[1]), "r": int(r[2]), "b": int(r[3]),
                    "confidenceScore": str(r[4] * 100), "content": None}
            res_cell.append(temp)

    for r in result[0][2]:
        if r[4] * 100 > SCORE_THRESHOLD:
            temp = {"l": int(r[0]), "t": int(r[1]), "r": int(r[2]), "b": int(r[3]),
                    "confidenceScore": str(r[4] * 100), "content": None}
            res_table.append(temp)

    tableRegionList = list()
    for r in res_table:
        tableRegionList.append({"bodyRegion": r, "headerRegion": None, "footerRegion": None, "boundedRegion": r})

    if len(tableRegionList) == 0:
        tableRegionList = [{"bodyRegion": None, "headerRegion": None, "footerRegion": None, "boundedRegion": None}]

    if len(res_cell) == 0:
        columnSplitRegionList = list()
    else:
        columnSplitRegionList = res_cell

    return tableRegionList, columnSplitRegionList


def table_cell_prediction(original_img_name, model, path):
    try:
        image_n = original_img_name
        image_loc = os.path.join(path, image_n)
        smudge_in = "smudge_" + str(original_img_name)
        smudge_im_path = os.path.join(path, smudge_in)
        # image_n = original_img_name
        # image_loc = os.path.join(IMAGE_TEMP_PATH, image_n)
        # smudge_in = "smudge_" + str(original_img_name)
        # smudge_im_path = os.path.join(IMAGE_TEMP_PATH, smudge_in)
        smudge_start = time()
        smudge_img(image_loc, smudge_im_path)
        smudge_end = time()
        logging.info("time taken for smudge process is {}".format(smudge_end-smudge_start))
        inference_start = time()
        result = inference_detector(model, smudge_im_path)
        inference_end = time()
        logging.info("time taken for cascade inference is {}".format(inference_end-inference_start))
        format_start = time()
        tableRegionList, columnSplitRegionList = format_result_classwise_new(result)
        gc.collect()
        format_end = time()
        logging.info("time for formatting the cascade result is : {}".format(format_end-format_start))
    except Exception as e:
        logging.error("Exception in running table structure detection :{}".format(e))
        tableRegionList = [{"bodyRegion": None, "headerRegion": None, "footerRegion": None, "boundedRegion": None}]
        columnSplitRegionList = []
    return tableRegionList, columnSplitRegionList
