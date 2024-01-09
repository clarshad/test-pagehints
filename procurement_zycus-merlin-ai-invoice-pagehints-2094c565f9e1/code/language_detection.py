import xml.etree.ElementTree as ET
from bs4 import NavigableString
from bs4 import BeautifulSoup
import requests
import logging
from time import time



def spacy_post(text, SPACY_SERVER):
    # spacy_url = "http://10.30.31.146:45296/spacy/language_detection"
    # print(SPACY_SERVER+"language_detection")
    payload = {"text": text}
    response = requests.post(SPACY_SERVER + "language_detection", json=payload)
    if response.status_code == 200:
        response = response.json()
    else:
        logging.error("Spacy Server is down! Please re-run the Bot with server up.")
    return response



def get_text(page):
    text = ''
    for item in page.children:
        # if type(item) == <class 'bs4.element.NavigableString'>:
        if item.name == 'block':
            for block in item.children:
                if block.name == 'text':
                    for txt in block.children:
                        if txt.name == 'par':
                            text += '\n'
                            for par in txt.children:
                                if isinstance(par, NavigableString):
                                    continue
                                else:
                                    # print(par.name)
                                    for line in par.children:
                                        # print(line.name)
                                        text += ' '
                                        for format in line.children:
                                            if isinstance(format, NavigableString):
                                                continue
                                            else:
                                                # print(format.name)
                                                text += format.text
    return text


def get_language(root, SPACY_SERVER):
    top_two_languages = list()
    try:
        preprocess_start = time()
        ET.register_namespace("", "http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml")
        xmlstr = ET.tostring(root, encoding='unicode', method='xml')
        xml = BeautifulSoup(xmlstr, 'html.parser')
        pages = xml.findAll("page")
        text = ""
        for page in pages:
            text += " " + get_text(page)
        preprocess_end = time()
        logging.info("Time taken for spacy preprocessing is {}".format(preprocess_end-preprocess_start))
        request_start = time()
        response = spacy_post(text, SPACY_SERVER)
        request_end = time()
        logging.info("Time taken to get response from spacy api is {}".format(request_end-request_start))
        top_two_languages = response['lang']
    except Exception as e:
        logging.error("exception in lang detection : {}".format(e))

    return top_two_languages
