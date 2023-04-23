#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
import lib.json_utils as json_utils


class ConfigFastAPI():
    ''' Class for API configuration. '''
    def __init__(self) -> None:
        load_dotenv()
        
        self.FAUCET_COINS = self.get_faucet_coins()

        # AtomicDEX Environment Variables
        self.ATOMICDEX_IP = self.get_atomicdex_api()
        self.ATOMICDEX_PORT = self.get_atomicdex_port()
        self.ATOMICDEX_USERPASS = self.get_atomicdex_userpass()
        
        # SQLite Environment Variables
        self.SQLITEDB_PATH = self.get_sqlitedb_path()
        self.SQLITEDB_TABLES = json_utils.get_jsonfile_data('config/table_config.json')

        # FastAPI Environment Variables
        self.SUBDOMAIN = self.get_subdomain()
        self.API_HOST = self.get_api_host()
        self.API_PORT = self.get_api_port()
        self.API_TAGS = self.get_api_tags()
        self.API_URL = self.get_api_url()
        self.API_METADATA = self.get_api_metadata()
        self.CORS_ORIGINS = self.get_cors_origins()
        self.SSL_KEY, self.SSL_CERT = self.get_ssl_certs()

        # Return the class as a dictionary
        self.as_dict = self.__dict__

    def get_api_host(self):
        ''' Returns the host IP for the API. '''
        API_HOST = os.getenv("FASTAPI_HOST")
        if not API_HOST: return "127.0.0.1"
        else: return API_HOST
        
    def get_api_port(self):
        ''' Returns the port for the API. '''
        API_PORT = os.getenv("FASTAPI_PORT")
        if not API_PORT: return 8088
        else: return int(API_PORT)

    def get_ssl_certs(self):
        ''' Returns the SSL key and cert. '''
        SSL_KEY = os.getenv("SSL_KEY")
        if SSL_KEY in ["None", ""]:
            SSL_KEY = None
        SSL_CERT = os.getenv("SSL_CERT")
        if SSL_CERT in ["None", ""]:
            SSL_CERT = None
        return SSL_KEY, SSL_CERT

    def get_faucet_coins(self):
        ''' Returns a list of faucet coins. '''
        try:
            return os.getenv('FAUCET_COINS').split(" ")
        except Exception as e:
            return []

    def get_sqlitedb_path(self):
        ''' Returns the path to the SQLite DB. '''
        path = os.getenv('SQLITEDB_PATH')
        if not path:
            if not os.path.exists("db"):
                os.mkdir("db")
            path = "db/fastapi.db"
        return path

    def get_atomicdex_api(self):
        ''' Returns the AtomicDEX IP'''
        return os.getenv('ATOMICDEX_IP')

    def get_atomicdex_port(self):
        ''' Returns the AtomicDEX port'''
        try:
            return int(os.getenv('ATOMICDEX_PORT'))
        except Exception as e:
            return 7783

    def get_atomicdex_userpass(self):
        ''' Returns the AtomicDEX userpass'''
        return os.getenv('ATOMICDEX_USERPASS')

    def get_subdomain(self):
        ''' Returns the API subdomain'''
        return os.getenv('SUBDOMAIN')
    
    def get_api_url(self):
        ''' Returns the API URL'''
        return f"https://{self.SUBDOMAIN}:{self.API_PORT}"
    
    def get_api_metadata(self):
        ''' Returns the API metadata tags'''
        return {
            "title": "API Template",
            "description": "Template for FastAPI",
            "version": "0.1.0",
            "contact": {
                "name": "Komodo Platform",
                "url": "https://komodoplatform.com",
                "email": "smk@komodoplatform.com",
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT",
            }
        }
    
    def get_api_tags(self):
        ''' Returns the API tags'''
        return [
            {
                "name": "data",
                "description": "Returns data from json file.",
            }
        ]

    def get_cors_origins(self):
        ''' Returns the CORS origins'''
        CORS_ORIGINS = ["http://localhost:3000"]
        if os.getenv("CORS_ORIGINS"):
            CORS_ORIGINS += os.getenv("CORS_ORIGINS").split(" ")
        return CORS_ORIGINS
