import os
import sys
from dotenv import load_dotenv, find_dotenv

#load_dotenv(find_dotenv())
load_dotenv()


def get_api_port():
    ''' Returns the port for the API. '''
    API_PORT = int(os.getenv("FASTAPI_PORT"))
    if not API_PORT:
        API_PORT = 8077
    else:
        API_PORT = int(API_PORT)
    return API_PORT


def get_ssl_certs():
    ''' Returns the SSL key and cert. '''
    SSL_KEY = os.getenv("SSL_KEY")
    if SSL_KEY in ["None", ""]:
        SSL_KEY = None
    SSL_CERT = os.getenv("SSL_CERT")
    if SSL_CERT in ["None", ""]:
        SSL_CERT = None
    return SSL_KEY, SSL_CERT


def get_db_path():
    ''' Returns the path to the database. '''
    return os.getenv('DB_PATH')

REGIONS = {
    "AR": "Asia / Russia",
    "EU": "Europe",
    "NA": "North America",
    "SH": "Southern Hemisphere"
}