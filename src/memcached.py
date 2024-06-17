#!/usr/bin/env python3
import os
import time
import json
from pymemcache.client.base import PooledClient
from lib_logger import logger, timed
import lib_json
from dotenv import load_dotenv
script_path = os.path.realpath(os.path.dirname(__file__))

load_dotenv()
MEMCACHE_LIMIT = 250 * 1024 * 1024  # 250 MB


class JsonSerde(object):  # pragma: no cover
    def serialize(self, key, value):
        if isinstance(value, str):
            return value.encode("utf-8"), 1
        return json.dumps(value).encode("utf-8"), 2

    def deserialize(self, key, value, flags):
        if flags == 1:
            return value.decode("utf-8")
        if flags == 2:
            return json.loads(value.decode("utf-8"))
        raise Exception("Unknown serialization format")


try:  # pragma: no cover
    MEMCACHE = PooledClient(
        ("memcached", 11211),
        serde=JsonSerde(),
        timeout=10,
        max_pool_size=50,
        ignore_exc=True,
    )
    MEMCACHE.set("foo", "bar", 60)
    if os.getenv("IS_TESTING") == "True":
        MEMCACHE.set("testing", True, 3600)
    logger.info("Connected to memcached docker container")

except Exception as e:  # pragma: no cover
    logger.muted(e)
    MEMCACHE = PooledClient(
        ("localhost", 11211),
        serde=JsonSerde(),
        timeout=10,
        max_pool_size=50,
        ignore_exc=True,
    )
    logger.info("Connected to memcached on localhost")
    if os.getenv("IS_TESTING") == "True":
        MEMCACHE.set("testing", True, 3600)

MEMCACHE.cache_memlimit = MEMCACHE_LIMIT


def stats():  # pragma: no cover
    return MEMCACHE.stats()


def set_polls(data):  # pragma: no cover
    if data is not None:
        if isinstance(data, dict):
            MEMCACHE.set("polls", data, 600)


def get_polls():  # pragma: no cover
    try:
        data = MEMCACHE.get("polls")
        if data is None:
            data = lib_json.get_jsonfile_data(f'{script_path}/poll_config.json')
        return data
    except Exception as e:
        return {}
