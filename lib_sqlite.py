#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
from dotenv import load_dotenv
from datetime import timezone
from lib_logger import logger
import sqlite3
import time


script_dir = os.path.abspath( os.path.dirname( __file__ ) )


class StatusDB():
    def __init__(self):
        self.path = f"{script_dir}/electrum_status.db"
        self._conn = None
        self._cursor = None
        self.create_tables()
        

    @property
    def conn(self):
        """ create a database connection to a SQLite database """
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(self.path)
                self._conn.row_factory = sqlite3.Row
            except sqlite3.Error as e:
                logger.error(e)
        return self._conn
    
    @property
    def cursor(self):
        if self._cursor is None:
            self._cursor = self.conn.cursor()
        return self._cursor

    def delete_electrum_coin(self, coin):
        try:
            sql = f"DELETE FROM electrum_status WHERE coin = '{coin}';"
            self.cursor.execute(sql)
            self.conn.commit()
            logger.info(f"{coin} removed from database")
        except Exception as e:
            logger.warning(f"{sql} | {e}")

    def delete_electrum_server(self, server):
        try:
            sql = f"DELETE FROM electrum_status WHERE server = '{server}';"
            self.cursor.execute(sql)
            self.conn.commit()
            logger.info(f"{server} removed from database")
        except Exception as e:
            logger.warning(f"{sql} | {e}")

    def get_db_coins(self):
        try:
            sql = f"SELECT DISTINCT coin FROM electrum_status;"
            self.cursor.execute(sql)
            return [i[0] for i in self.cursor.fetchall()]
        except Exception as e:
            logger.warning(f"{sql} | {e}")
            
    def get_db_servers(self):
        try:
            sql = f"SELECT DISTINCT server FROM electrum_status;"
            self.cursor.execute(sql)
            return [i[0] for i in self.cursor.fetchall()]
        except Exception as e:
            logger.warning(f"{sql} | {e}")

    def update_server_status(self, data):
        try:
            if data['port'] != "":
                server = f"{data['url']}:{data['port']}"
            else:
                server = data['url']
            row = (
                data['coin'],
                data['category'],
                server,
                data['protocol'],
                data['result'],
                int(data['blockheight']),
                int(data['last_connection']),
                json.dumps(data['contact'])
            )
            sql = f"INSERT INTO electrum_status \
                        (coin, category, server, protocol, result, blockheight, last_connection, contact) \
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?) \
                    ON CONFLICT (coin, server, protocol) DO UPDATE \
                    SET result=excluded.result, blockheight=excluded.blockheight, last_connection=excluded.last_connection, contact=excluded.contact;"
            self.cursor.execute(sql, row)
            self.conn.commit()
            logger.loop(f"{row} added to database")
        except Exception as e:
            logger.error(f"{sql} | {e}")

    def update_server_status_failed(self, data):
        try:
            if data['port'] != "":
                server = f"{data['url']}:{data['port']}"
            else:
                server = data['url']
            row = (
                data['coin'],
                data['category'],
                server,
                data['protocol'],
                data['result'],
                int(data['blockheight']),
                int(data['last_connection']),
                json.dumps(data['contact'])
            )
            sql = f"INSERT INTO electrum_status    \
                        (coin, category, server, protocol, result, blockheight, last_connection, contact) \
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?) \
                    ON CONFLICT (coin, server, protocol) DO UPDATE \
                    SET result=excluded.result, contact=excluded.contact;"
            self.cursor.execute(sql, row)
            self.conn.commit()
            logger.warning(f"{row} added to database FAILED")
        except Exception as e:
            logger.error(f"{sql} | {e}")

    def purge_old_rows(self, days=7):
        try:
            cutoff_ts = int(time.time()) - (int(days) * 86400)
            sql = "DELETE FROM electrum_status WHERE last_connection IS NOT NULL AND last_connection > 0 AND last_connection < ?;"
            self.cursor.execute(sql, (cutoff_ts,))
            deleted = self.cursor.rowcount
            self.conn.commit()
            logger.info(f"Purged {deleted} rows older than {days} days")
        except Exception as e:
            logger.warning(f"{sql} | {e}")

    def get_electrum_status_data(self):
        sql = "SELECT * FROM electrum_status ORDER BY coin"
        r = self.cursor.execute(sql).fetchall()
        resp = []
        for i in r:
            i = dict(i)
            i['contact'] = json.loads(i['contact'])
            resp.append(i)
        return resp

    def create_tables(self):
        try:
            sql = "CREATE TABLE electrum_status (   \
                id INTEGER PRIMARY KEY,             \
                coin TEXT NOT NULL,                 \
                category TEXT NOT NULL,             \
                server TEXT NOT NULL,               \
                protocol TEXT NOT NULL,             \
                result TEXT,                        \
                blockheight INTEGER,                \
                last_connection INTEGER,            \
                contact TEXT,                       \
                UNIQUE(coin, server, protocol));"
            self.cursor.execute(sql)
        except:
            pass

    def get_tables(self):
        sql = "SELECT name FROM sqlite_master WHERE type='table';"
        return self.cursor.execute().fetchall()
        

    def get_row(self, table):
        sql = f"SELECT * FROM {table};"
        self.cursor.execute(sql).fetchone()

    def get_rows(self, table):
        sql = f"SELECT * FROM {table};"
        self.cursor.execute(sql).fetchall()

    def get_column_names(self, row):
        return row.keys()

    def get_table_info(self, table):
        sql = f'pragma table_info({table})'
        self.cursor.execute(sql).fetchall()
        return self.cursor

    def view_table_info(self, table):
        info = self.get_table_info(table)
        logger.info(f"\n\n## {table}\n")
        logger.info('|{:^10s}|{:^21s}|{:^18s}|{:^11s}|{:^14s}|{:^13s}|'.format(
            "-"*10,
            "-"*21,
            "-"*18,
            "-"*11,
            "-"*14,
            "-"*13,
            )    
        )
        logger.info('|{:^10s}|{:^21s}|{:^18s}|{:^11s}|{:^14s}|{:^13s}|'.format(
            "ID",
            "Name",
            "Type",
            "NotNull",
            "DefaultVal",
            "PrimaryKey"
            )
        )
        logger.info('|{:^10s}|{:^21s}|{:^18s}|{:^11s}|{:^14s}|{:^13s}|'.format(
            "-"*10,
            "-"*21,
            "-"*18,
            "-"*11,
            "-"*14,
            "-"*13,
            )    
        )

        for i in info:
            logger.info('|{:^10s}|{:^21s}|{:^18s}|{:^11s}|{:^14s}|{:^13s}|'.format(
                f'{i[0]}',
                f'{i[1]}',
                f'{i[2]}',
                f'{i[3]}',
                f'{i[4]}',
                f'{i[5]}'
            )
        )



if __name__ == '__main__':
    data = get_electrum_status_data()
    resp = [{k: item[k] for k in item.keys()} for item in data]
    for row in resp:
        logger.info(str(row))


