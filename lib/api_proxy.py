#!/usr/bin/env python3
import os
import time
import sqlite3
from lib.const import ConfigFastAPI
from lib.json_utils import write_jsonfile_data, get_jsonfile_data

def get_data():
    return {"Hello": "World"}