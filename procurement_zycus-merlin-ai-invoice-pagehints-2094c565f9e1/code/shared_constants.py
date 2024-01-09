import configparser
import os

config_filename = "../config/config_page_hints.INI"
config = configparser.ConfigParser()
config.read(config_filename)


awsS3ValutUrl = config.get('Aws', 'awsS3ValutUrl')
awsS3ValutToken = config.get('Aws', 'awsS3ValutToken')

WORKSPACE_FOLDER_PATH = config.get('Paths', 'WORKSPACE_FOLDER_PATH')
if not os.path.exists(WORKSPACE_FOLDER_PATH):
    os.mkdir(WORKSPACE_FOLDER_PATH)

IMAGE_TEMP_PATH = os.path.join(WORKSPACE_FOLDER_PATH, 'image_temp')
if not os.path.exists(IMAGE_TEMP_PATH):
    os.mkdir(IMAGE_TEMP_PATH)

MODEL_CONFIG_FILE_PATH = config.get('Paths', 'MODEL_CONFIG_FILE_PATH')
MODEL_CHECKPOINT_PATH = os.path.join(os.environ.get('MODEL_DIRECTORY'), config.get('Paths', 'MODEL_CHECKPOINT_PATH'))
LOGGING_CONFIG_PATH = config.get('Paths', 'LOGGING_CONFIG_PATH')

VISUALIZE = int(config.get('Constants', 'VISUALIZE'))
SCORE_THRESHOLD = float(config.get('Constants', 'SCORE_THRESHOLD'))
DELETE_VISUALIZATION_IMAGES = int(config.get('Constants', 'DELETE_VISUALIZATION_IMAGES'))
SPACY_SERVER = os.environ.get("MERLIN_AI_SPACY_URL") + config.get('SPACY', 'SPACY_SERVER')
FETCH_URL = config.get('Fetch', 'FETCH_URL')
UPDATE_URL = config.get('Fetch','UPDATE_URL')