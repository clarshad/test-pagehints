# ------------------------------------------------------------------
# PageHints-bot
# This module will run the integrated bots for invoice Processing.
#
# (C) 2021 Merlin, Zycus Infotech
# Author: Annu Sachan
# Email: annu.sachan@zycus.com
# ------------------------------------------------------------------
import psutil
import sys
from time import time
import gc
import re
from flask import Flask, request
import json
import logging
import logging.config
import os
import requests
from ValidationError import ValidationError
from line_detection import LineDetection
import xml.etree.ElementTree as ET
import cv2
import concurrent.futures
import numpy as np
from apscheduler.schedulers.background import BackgroundScheduler
from pdf2image import convert_from_bytes, convert_from_path
import torch
torch.set_num_threads(1)
from mmdet.apis import init_detector
from shared_constants import IMAGE_TEMP_PATH, VISUALIZE, LOGGING_CONFIG_PATH, MODEL_CONFIG_FILE_PATH, \
    MODEL_CHECKPOINT_PATH, DELETE_VISUALIZATION_IMAGES, SPACY_SERVER, FETCH_URL, UPDATE_URL
from table_cell_pred import table_cell_prediction
from visualization import visualize
from language_detection import get_language
from read_contents_from_s3 import read, dump_output_s3, get_any
from datetime import datetime
import multiprocessing
manager = multiprocessing.Manager()
s3_manager=manager.dict()


logging.config.fileConfig(LOGGING_CONFIG_PATH)
logging.info("########### eInvoice Bot Started ###############")
pid = os.getpid()
py = psutil.Process(pid)
mu_1 = int(py.memory_info().rss) / 1000000
logging.info("Memory used before running api : {} MB".format(mu_1))
logging.info("CPU percent before api: {}".format(psutil.cpu_percent()))

app = Flask(__name__)

linedetect = LineDetection()

# build the model from a config file and a checkpoint file
model = init_detector(MODEL_CONFIG_FILE_PATH, MODEL_CHECKPOINT_PATH, device="cpu")


# for gpu use the below command
# model = init_detector(MODEL_CONFIG_FILE_PATH, MODEL_CHECKPOINT_PATH)

def delete_folder_content(PATH_TO_PICK_IMAGES_FROM):
        try:
            filelist = os.listdir(PATH_TO_PICK_IMAGES_FROM)
            for f in filelist:
                os.remove(os.path.join(PATH_TO_PICK_IMAGES_FROM, f))
            gc.collect()
        except Exception as e:
            logging.info("Exception in clearing image temp: {}".format(e))

@app.route("/merlin/merlin-ai-invoice-pagehints/pagehints-gunicorn/healthCheck", methods=['GET', 'POST'])
def health_check():
    """
    API method to check if the API is up and running.

    Returns
    -------
    string: Returns Page Hints service is running.

    """
    return "Page Hints service is running"


def page_hints(request_json):
    """
    error message :
    200: success
    501: Problem in dumping response object to S3
    502: An error occurred (ExpiredToken) when calling the GetObject operation: The provided token has expired
    505: Poller error
    """
    try:
        start = time()
        success_status = {"line_success": 1, "table_structure_success": 1, "lang_success":1}
        logging.info("******************************************************")
        poller_json = json.loads(request_json["objectMessage"])
        logging.info("object message is : {}".format(poller_json))
        request_picked_at = datetime.now()
        pdf_location=poller_json["pdfDetails"]["path"]
        xml_location=poller_json["xmlDetails"]["path"]
        if poller_json["pdfDetails"]["bucketName"]!="" and poller_json["xmlDetails"]["bucketName"]!="":
            pdf_content,xml_content=read(poller_json,s3_manager)
            pdf=np.fromstring(pdf_content.read(), np.uint8)
            tree = ET.parse(xml_content)
        elif poller_json["pdfDetails"]["bucketName"]=="" and poller_json["xmlDetails"]["bucketName"]=="":
            pdf = poller_json["pdfDetails"]["path"]
            tree = ET.parse(poller_json["xmlDetails"]["path"])
        else:
            try:
                pdf = poller_json["pdfDetails"]["path"]
                xml_content = get_any(poller_json,s3_manager)
                tree = ET.parse(xml_content)
            except:
                pdf_content=get_any(poller_json,s3_manager)
                pdf=np.fromstring(pdf_content.read(), np.uint8)
                tree = ET.parse(poller_json["xmlDetails"]["path"])
            
        logging.info("succesfully fetched input from s3_bucket")
        request_times_stamp=time()
        if poller_json["pagehintsModelEnabled"]=="True":
            use_table_structure_det = 1 
            logging.info("use_table_structure_det : {}".format(use_table_structure_det))
        else:
            use_table_structure_det = 0
            logging.info("use_table_structure_det : {}".format(use_table_structure_det))  
        file_name = poller_json["invoiceDocumentId"]
        try:
            folder_name = str(file_name.split("/")[-1]) +str("_") +str(request_times_stamp)
        except:
            folder_name = str(file_name +str("_") +str(request_times_stamp))
        folder_name = folder_name.replace(".","_")
        logging.info("temporary file create  :{}".format(folder_name))
        PATH_TO_PICK_IMAGES_FROM=os.path.join(IMAGE_TEMP_PATH,folder_name)
        os.mkdir(PATH_TO_PICK_IMAGES_FROM)
        #tree = ET.parse(xml_content)
        root = tree.getroot()
        xml_pages = root.iter('{http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml}page')
        if poller_json["pdfDetails"]["bucketName"]!="":          
            images = convert_from_bytes(pdf, dpi=300,output_folder=PATH_TO_PICK_IMAGES_FROM,fmt="jpg",grayscale=False,thread_count=1)
        else:
            images = convert_from_path(pdf,dpi=300,output_folder=PATH_TO_PICK_IMAGES_FROM,fmt="jpg",grayscale=False)
        image_name_list = os.listdir(PATH_TO_PICK_IMAGES_FROM)
        image_name_list.sort()
        output_jsons = []
        
        # LANGUAGE DETECTION
        try:
            lang_start_time = time()
            language_for_whole_doc = get_language(root, SPACY_SERVER)
            lang_end_time = time()
            logging.info("Successfully performed language prediction")
            logging.info("time taken for language detection : {} sec".format(lang_end_time - lang_start_time))
        except Exception as e:
            # In case of exception assign None (interpreted as null), Java side will assume english as default lang
            language_for_whole_doc = None
            logging.error("Could not perform language predictions,error : {}".format(e))
            success_status["lang_status"] = 0
        for idx, xml_page in enumerate(xml_pages):
            output_json = dict()
            output_json['pageWidth'], output_json['pageHeight'], output_json['pageResolution'] = int(
                xml_page.attrib["width"]), int(xml_page.attrib["height"]), int(xml_page.attrib['resolution'])
            w = int(xml_page.attrib["width"])
            h = int(xml_page.attrib["height"])
            img_path = os.path.join(PATH_TO_PICK_IMAGES_FROM,image_name_list[idx])
            image = cv2.imread(img_path)
            resized_image = cv2.resize(image, (w, h))
            rn = str(file_name) + "_" + str(idx) + ".jpg"
            resized_path = os.path.join(PATH_TO_PICK_IMAGES_FROM,rn)
            cv2.imwrite(resized_path, resized_image)

            try:
                line_start_time = time()
                output_json['pagePrintedBorderDetail'] = linedetect.get_lines(resized_image)
                line_end_time = time()
                logging.info("Successfully ran line detection for page: {}".format(idx))
                logging.info("time taken for running line detection for page {} is : {}".format(idx, line_end_time - line_start_time))
            except Exception as e1:
                logging.error("Line detection failed for page: {}, exception is  : {}".format(idx, e1))
                success_status["line_success"] = 0
                output_json["pagePrintedBorderDetail"] = {"horizontalLines": list(), "verticalLines": list()}

            if use_table_structure_det:
                try:
                    table_start_time = time()
                    tableRegionList, columnSplitRegionList = table_cell_prediction(rn, model, PATH_TO_PICK_IMAGES_FROM)
                    table_end_time = time()
                    logging.info("Successfully performed table structure detection with cascade tabnet for page :{}".format(idx))
                    logging.info("time taken for table structure detection on page {} : {} sec".format(idx, table_end_time-table_start_time))
                except Exception as e2:
                    logging.error("cascade tabnet table structure detection failed for page :{}, exception is  : {}".format(idx,e2))
                    success_status["table_structure_success"] = 0
            else:
                tableRegionList = [
                    {"bodyRegion": None, "headerRegion": None, "footerRegion": None, "boundedRegion": None}]
                columnSplitRegionList = []

            output_json['tableRegionList'] = tableRegionList
            output_json['columnSplitRegionList'] = columnSplitRegionList
            output_json["languages"] = language_for_whole_doc
            # Populate lang of whole doc on every page
            # TODO in future we might have to find lang per page           

            if VISUALIZE:
                visualize(output_json,rn,PATH_TO_PICK_IMAGES_FROM)

            output_jsons.append(output_json)
        # TODO : ASSUMPTION IF IT RUNS WELL ON ONE OF THE PAGE THEN IT RUNS WELL FOR ALL PAGES
        if success_status["table_structure_success"] == 1 and success_status["line_success"]==1 and success_status["lang_success"]==1:
            response_obj = {'SUCCESS': True, 'MESSAGE': str(success_status), 'DATA': output_jsons,
                            'STATUS_CODE': "MER-PGH-SCS"}
        elif success_status["table_structure_success"] == 1 and success_status["line_success"]==1 and success_status["lang_success"]==0:
            response_obj = {'SUCCESS': True, 'MESSAGE': str(success_status), 'DATA': output_jsons,
                            'STATUS_CODE': "MER-PGH-LANG-FAIL"}
        else:
            response_obj = {'SUCCESS': False, 'MESSAGE': str(success_status), 'DATA': None,
                            'STATUS_CODE': "MER-PGH-01"}

        json_name = file_name + ".pdf" + ".xml_page_hints.json"
        json_dump_loc = os.path.join(PATH_TO_PICK_IMAGES_FROM, json_name)
        with open(json_dump_loc, 'w') as fp:
            json.dump(response_obj, fp, indent=4)

        if DELETE_VISUALIZATION_IMAGES:
            delete_folder_content(PATH_TO_PICK_IMAGES_FROM)
            os.rmdir(PATH_TO_PICK_IMAGES_FROM)
            logging.info("Temporary files deleted : {}".format(folder_name))
        
        try:
            dump_output_s3(poller_json,response_obj,s3_manager)
        except Exception as e:
            logging.info("Error code {0} ,Unable to dump response object in S3 :{1}".format("501",e))

        end = time()
        mu_1 = int(py.memory_info().rss) / 1000000
        temp2 = len(output_jsons)
        cpu_per = psutil.cpu_percent()
        logging.error(
            "For:{}, xml_path:{}, event_id:{}, request_picked_at:{}, use_table_detection:{}, pages:{}, time taken:{}sec, memory after:{}mb, cpu percent after:{}, per page time: {}sec, per page memory: {}mb, per page cpu:{}".format(
                pdf_location, xml_location, request_json["eventId"], request_picked_at, use_table_structure_det, len(output_jsons), end - start, mu_1, cpu_per, (end - start) / temp2, mu_1 / temp2,
                cpu_per / temp2))
        
    except Exception as error:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_message = "{} - in {} at line no. {}".format(str(exc_type) + ": " + str(error), fname, exc_tb.tb_lineno)
        logging.error("Unable to perform prediction : {}".format(error))
        response_obj = {'SUCCESS': False, 'MESSAGE': str(error_message), 'DATA': None,
                            'STATUS_CODE': "MER-PGH-FAIL"} 


    try:  
        #temp_json = poller_json
        if response_obj["SUCCESS"]:
            poller_dump = {'SUCCESS': response_obj["SUCCESS"], 'MESSAGE': response_obj["MESSAGE"], 'FILENAME': poller_json["output"]["path"],
                            'STATUS_CODE': response_obj["STATUS_CODE"]}
        else:
            poller_dump = {'SUCCESS': response_obj["SUCCESS"], 'MESSAGE': response_obj["MESSAGE"], 'FILENAME': "",
                            'STATUS_CODE': response_obj["STATUS_CODE"]}
        ## eventid,tenantId,entityId,errorCode,errorDescription,purpose,status,response -- all are mandatory fields for updating poller as per discussion with anshu
        updateReq = requests.post(UPDATE_URL,json=[{
            "eventId":request_json["eventId"],
            "purpose":request_json["purpose"],
            "entityId":request_json["entityId"],
            "status":"SUCCESS",
            "response":json.dumps(poller_dump),
            "tenantId":request_json["tenantId"]
        }])

        if updateReq.json()['error'] == []:
            logging.error("###### Complete Response Sent ######")

        else:
            logging.error("##### Error in updating the request :{} #####".format(updateReq.json()['error']))
    except Exception as e:
        logging.error("error_code : {0}, error_description : {1},exception in updating request : {2}".format("505","Poller error",e))

    logging.info("final_result : {}".format(poller_dump))

def fetch(job_name, useProcessPool, pollingBatchSize: int, polledTimeoutInMins: int, purposetype: str):
    request = requests.post(FETCH_URL, json={"purpose": purposetype,
                                             "pollingBatchSize": pollingBatchSize,
                                             "polledTimeoutInMins": polledTimeoutInMins})
    
            
    request_json = request.json()
    if request_json['polledTaskEventList'] != [] and request_json['polledTaskEventList']:
        logging.error("PID: {}, GDS msg found: {}".format(os.getpid(), request_json))
        request_json = request_json['polledTaskEventList']   #-----
        values = [job_name]
        if useProcessPool:            
            with concurrent.futures.ProcessPoolExecutor(max_workers=len(values)) as executor:
                executor.map(page_hints, request_json)  #----[request_json]
            executor.shutdown()
        else:            
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(values)) as executor:
                executor.map(page_hints, [request_json])
            executor.shutdown()
        logging.info('RAM memory % used: {}'.format(psutil.virtual_memory()[2]))
        logging.info('RAM Used (MB): {}'.format(psutil.virtual_memory()[3] / 1000000))

with open('../config/scheduler_config.json') as f:
    schedulerConfig = json.load(f)

scheduler = BackgroundScheduler(schedulerConfig["scheduler"])
jobList = schedulerConfig["jobList"]

for job in jobList:
    jobName = job["jobName"]
    cronExpSeconds = job["cronExpSeconds"]
    max_instances = job["max_instances"]
    useProcessPool = job["useProcessPool"]
    pollingBatchSize = job["pollingBatchSize"]
    polledTimeoutInMins = job["polledTimeoutInMins"]
    purposetype = job["purposetype"]
    logging.error(" :: ADDING JOB WITH NAME :: %s ", jobName)
    scheduler.add_job(fetch, "cron", second=cronExpSeconds, name=jobName, max_instances=max_instances,
                      args=[jobName, useProcessPool, pollingBatchSize, polledTimeoutInMins, purposetype])
    logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
    logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)
    logging.error("Purposetype:{}".format(purposetype))
    logging.error("jobname:{}".format(jobName))
scheduler.start()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6001, threaded=True)
    mu_1 = int(py.memory_info().rss) / 1000000
    logging.info("Memory used for running api : {} MB".format(mu_1))
    logging.info("CPU percent after api: {}".format(psutil.cpu_percent()))
    logging.info('RAM memory % used after api: {}'.format(psutil.virtual_memory()[2]))
    logging.info('RAM Used (MB) after api: {}'.format(psutil.virtual_memory()[3] / 1000000))
