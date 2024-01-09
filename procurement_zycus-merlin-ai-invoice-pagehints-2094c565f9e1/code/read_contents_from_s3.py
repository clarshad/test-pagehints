import boto3
import os
import hvac
import json
from time import time
from datetime import datetime
from shared_constants import awsS3ValutUrl,awsS3ValutToken
import sys
sys.path.insert(0,'../config')
import logging


if os.path.exists("/etc/ssl/certs"):
    cert_path = "/etc/ssl/certs"
    key_path = "/etc/ssl/certs"
else:
    logging.info("certificate paths are not present")


class Aws_Client:
    
    def fetch_aws_client(self,awsS3ValutUrl,awsS3ValutToken,poller_json):
        try:
            vault_client = hvac.Client(url= awsS3ValutUrl,
                    token=awsS3ValutToken,
                    cert=(cert_path, key_path),
                    verify=cert_path)
            creds_response = vault_client.secrets.aws.generate_credentials(poller_json['awsBucketRole'])
            aws_creds_last_fetched = datetime.now()
            resp={"aws_client_tokens":creds_response,"aws_creds_last_fetched":aws_creds_last_fetched,'status':'Success'}
            logging.info("Succesfully fetched creds from vault")
        except Exception as e:
            resp= {'status':'Failed'}
            logging.info("Exception occured in fetching creds from vault {}".format(e))
        return resp

    # def s3_update(self,poller_json,s3_manager):
    #     resp_fetch_aws_client=self.fetch_aws_client(awsS3ValutUrl,awsS3ValutToken,poller_json)
    #     creds_generated_timestamp = datetime.now()
    #     if resp_fetch_aws_client['status']=='Success':
    #         s3_manager[poller_json['awsRegion']]=resp_fetch_aws_client
    #TODO add creds generated log in above function and delete from below


    def get_client(self,s3_manager,poller_json):
        if poller_json['awsRegion'] not in s3_manager.keys():
            s3_manager[poller_json['awsRegion']]={}
            resp_fetch_aws_client=self.fetch_aws_client(awsS3ValutUrl,awsS3ValutToken,poller_json)
            creds_generated_timestamp_1 = datetime.now()
            if resp_fetch_aws_client['status']=='Success':
                s3_manager[poller_json['awsRegion']]=resp_fetch_aws_client
            logging.info("s3_manager new region - {0} found and creds generated at {1}".format(poller_json['awsRegion'],creds_generated_timestamp_1))    
        elif (86399-((s3_manager[poller_json['awsRegion']]['aws_creds_last_fetched']-datetime.now()).seconds)) > 0.85*s3_manager[poller_json['awsRegion']]['aws_client_tokens']['lease_duration']:  
            #86399 is the total no of sec in 24 hours
            resp_fetch_aws_client=self.fetch_aws_client(awsS3ValutUrl,awsS3ValutToken,poller_json)
            creds_generated_timestamp = datetime.now()
            if resp_fetch_aws_client['status']=='Success':
                s3_manager[poller_json['awsRegion']]=resp_fetch_aws_client
            logging.info("s3_manager region {0} already exist and creds expired, generated new creds at {1}: ".format(poller_json['awsRegion'],creds_generated_timestamp)) 
        else:
            logging.info("s3_manager region - {} exist and creds are still valid".format(poller_json['awsRegion']))    
        return s3_manager

aws_client=Aws_Client()

def get_aws_tokens(s3_manager_dict,poller_json):
    ACCESS_KEY=s3_manager_dict[poller_json['awsRegion']]['aws_client_tokens']['data']['access_key']
    SECRET_KEY=s3_manager_dict[poller_json['awsRegion']]['aws_client_tokens']['data']['secret_key']
    SESSION_TOKEN=s3_manager_dict[poller_json['awsRegion']]['aws_client_tokens']['data']['security_token']
    return ACCESS_KEY,SECRET_KEY,SESSION_TOKEN


def read(poller_json,s3_manager):
    for i in range(2):
        s3_manager_dict=aws_client.get_client(s3_manager,poller_json)
        ACCESS_KEY,SECRET_KEY,SESSION_TOKEN = get_aws_tokens(s3_manager_dict,poller_json)
        aws_client_= boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN,region_name=poller_json['awsRegion'])
        file_read_start = time()
        data_pdf = aws_client_.get_object(Bucket=poller_json["pdfDetails"]["bucketName"], Key=poller_json["pdfDetails"]["path"])
        contents_pdf = data_pdf['Body']
        data_xml=aws_client_.get_object(Bucket= poller_json["xmlDetails"]["bucketName"], Key=poller_json["xmlDetails"]["path"])
        contents_xml=data_xml['Body']
        file_read_end = time()
        logging.info("Time taken to read files from s3 is {}".format(file_read_end-file_read_start))
        if contents_pdf and contents_xml:
            logging.info("Successfully fetched contents from s3 in retry number {}".format(i))
            break
    
    return contents_pdf,contents_xml


def dump_output_s3(poller_json,resp_obj,s3_manager_dict):
    if poller_json['awsRegion'] not in  s3_manager_dict.keys():
        s3_manager_dict=aws_client.get_client(s3_manager_dict,poller_json)
        ACCESS_KEY,SECRET_KEY,SESSION_TOKEN = get_aws_tokens(s3_manager_dict,poller_json)
    else:
        ACCESS_KEY,SECRET_KEY,SESSION_TOKEN = get_aws_tokens(s3_manager_dict,poller_json)
    s3 = boto3.resource('s3',aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN,region_name=poller_json['awsRegion'])
    s3object = s3.Object(poller_json["output"]["bucketName"], poller_json["output"]["path"])
    time_dump_start = time()
    s3object.put(
        Body=(bytes(json.dumps(resp_obj).encode('UTF-8')))
    )
    time_dump_end = time()
    logging.info("successfully pushed response object to s3")
    logging.info("time taken to push files to s3 is : {}".format(time_dump_end-time_dump_start))

def get_any(poller_json,s3_manager):
    for i in range(2):
        s3_manager_dict=aws_client.get_client(s3_manager,poller_json)
        ACCESS_KEY,SECRET_KEY,SESSION_TOKEN = get_aws_tokens(s3_manager_dict,poller_json)
        aws_client_= boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN,region_name=poller_json['awsRegion'])
        file_read_start = time()
        if poller_json["pdfDetails"]["bucketName"]!="":
            data_pdf = aws_client_.get_object(Bucket=poller_json["pdfDetails"]["bucketName"], Key=poller_json["pdfDetails"]["path"])
            contents_pdf = data_pdf['Body']
            return contents_pdf
        elif poller_json["xmlDetails"]["bucketName"]!="":
            data_xml=aws_client_.get_object(Bucket= poller_json["xmlDetails"]["bucketName"], Key=poller_json["xmlDetails"]["path"])
            contents_xml=data_xml['Body']
            return contents_xml
        file_read_end = time()
        logging.info("Time taken to read files from s3 is {}".format(file_read_end-file_read_start))
        logging.info("Successfully fetched contents from s3 in retry number {}".format(i))
        