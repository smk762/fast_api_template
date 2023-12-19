import os
from dotenv import load_dotenv
import lib.json_utils as json_utils

script_path = os.path.realpath(os.path.dirname(__file__))

class ConfigFastAPI:
    """Class for API configuration."""

    def __init__(self) -> None:
        load_dotenv()

        self.FAUCET_COINS = self.get_faucet_coins()

        # SQLite Environment Variables
        self.SQLITEDB_PATH = self.get_sqlitedb_path()
        self.SQLITEDB_TABLES = json_utils.get_jsonfile_data("config/table_config.json")

        # FastAPI Environment Variables
        self.FASTAPI = {
            "HOST": os.getenv("HOST") or "127.0.0.1",
            "SUBDOMAIN": os.getenv("SUBDOMAIN"),
            "PORT": self.int_or_none(os.getenv("FASTFASTAPI_PORT")) or 8088,
            "USE_MIDDLEWARE": os.getenv("USE_MIDDLEWARE") == "True",
            "CORS_ORIGINS": "*",
            "TAGS": self.get_FASTAPI_TAGS(),
            "METADATA": self.get_FASTAPI_METADATA(),
            "SSL_KEY": os.getenv("SSL_KEY") or None,
            "SSL_CERT": os.getenv("SSL_CERT") or None,
        }
        self.FASTAPI.update(
            {
                "FASTAPI_URL": f"https://{self.FASTAPI['SUBDOMAIN']}:{self.FASTAPI['PORT']}"
            }
        )
        if os.getenv("CORS_ORIGINS"):
            self.FASTAPI.update({"CORS_ORIGINS": os.getenv("CORS_ORIGINS").split(" ")})

        self.API_KEYS = {}
        self.API_SECRETS = {}
        self.API_URLS = {}
        for k, v in os.environ.items():
            self.API_KEYS.update({k.replace("_APIKEY", ""): v})
            self.API_SECRETS.update({k.replace("_SECRET", ""): v})
            if k.contains("_BASEURL"):
                if v.endswith("/"):
                    v = v[:-1]
                self.API_URLS.update({k.replace("_BASEURL", ""): v})

        self.KOMODEFI = {
            "IP": os.getenv("KOMODEFI_IP") or "127.0.0.1",
            "PORT": self.int_or_none(os.getenv("KOMODEFI_PORT")) or 7783,
            "USERPASS": os.getenv("KOMODEFI_USERPASS") or "RpcUserP@assw0rd",
        }

    def int_or_none(self, value):
        """Returns an integer or None."""
        try:
            return int(value)
        except:
            return None

    def get_faucet_coins(self):
        """Returns a list of faucet coins."""
        try:
            return os.getenv("FAUCET_COINS").split(" ")
        except Exception as e:
            return []

    def get_sqlitedb_path(self):
        """Returns the path to the SQLite DB."""
        path = os.getenv("SQLITEDB_PATH")
        if not path:
            path = f"{script_path}/db"
            if not os.path.exists(path):
                os.mkdir(path)
        return path

    def get_FASTAPI_METADATA(self):
        """Returns the API metadata tags"""
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
            },
        }

    def get_FASTAPI_TAGS(self):
        """Returns the API tags"""
        return [
            {
                "name": "data",
                "description": "Returns data from json file.",
            }
        ]


if __name__ == "__main__":
    pass
