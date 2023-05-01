#!/usr/bin/env python3
import sqlite3
import const
from lib_logger import logger

DB_PATH = const.get_db_path()

# Create table if not existing
def create_tbl(table='voting'):
    try:
        logger.info(f'Creating table {table} in {DB_PATH}')
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
            if len(cursor.fetchall()) == 0 :
                logger.warning(f'Table {table} does not exist! Creating it...')
                cursor.execute(f"CREATE TABLE {table} ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT, \
                            coin text, \
                            address text, \
                            category int, \
                            option text, \
                            txid text, \
                            amount real, \
                            blockheight int, \
                            blocktime int, \
                            UNIQUE(txid, address) \
                        ) \
                ")
            conn.commit()
    except Exception as e:
        logger.info(e)


def connect_sqlite(DB):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    return conn, cursor


def get_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return cursor.fetchall()


def get_row(cursor, table):
    cursor.execute(f"SELECT * FROM {table};")
    return cursor.fetchone()


def get_rows(cursor, table):
    cursor.execute(f"SELECT * FROM {table};")
    return cursor.fetchall()


def get_column_names(row):
    return row.keys()


def get_table_info(cursor, table):
    cursor.execute(f'pragma table_info({table})')
    return cursor.fetchall()


def get_table_row(cursor, table):
    cursor.execute(f'pragma table_info({table})')
    return cursor.fetchall()


def view_table_info(cursor, table):
    info = get_table_info(cursor, table)
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


class VoteTXIDs():
    def __init__(self, coin, address=None, category=None, option=None, final_block=None):
        self.coin = coin
        self.address = address
        self.category = category
        self.option = option
        self.final_block = final_block

    def get_recent_votes(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            constraints = [f"coin='{self.coin}'"]
            if self.final_block:
                constraints.append(f"blockheight <= {self.final_block}")
            if self.address:
                constraints.append(f"address='{self.address}'")
            sql = f"SELECT * FROM voting WHERE {' AND '.join(constraints)} ORDER BY blocktime desc LIMIT 100;"
            cursor.execute(sql)
            data = cursor.fetchall()
            try:
                recent = [dict(i) for i in data]
                return recent
            except:
                return []


    def get_num_votes(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if not self.final_block:
                if self.address:
                    cursor.execute(f"SELECT COUNT(*) FROM voting WHERE coin='{self.coin}' AND address='{self.address}' ORDER BY blocktime desc LIMIT 100;")
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM voting WHERE coin='{self.coin}' ORDER BY blocktime desc LIMIT 100;")
                try:
                    return cursor.fetchone()[0]
                except:
                    return 0
            else:
                if self.address:
                    cursor.execute(f"SELECT COUNT(*) FROM voting WHERE coin='{self.coin}' AND blockheight <= {self.final_block} AND address='{self.address}' ORDER BY blocktime desc LIMIT 100;")
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM voting WHERE coin='{self.coin}' AND blockheight <= {self.final_block} ORDER BY blocktime desc LIMIT 100;")
                try:
                    return cursor.fetchone()[0]
                except:
                    return 0


    def get_sum_votes(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if not self.final_block:
                if self.address:
                    cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND address='{self.address}' ORDER BY blocktime desc LIMIT 100;")
                else:
                    cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' ORDER BY blocktime desc LIMIT 100;")
                try:
                    return round(cursor.fetchone()[0],6)
                except:
                    return 0
            else:
                if self.address:
                    cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND address='{self.address}' AND blockheight <= {self.final_block} ORDER BY blocktime desc LIMIT 100;")
                else:
                    cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND blockheight <= {self.final_block} ORDER BY blocktime desc LIMIT 100;")
                try:
                    return round(cursor.fetchone()[0],6)
                except:
                    return 0


    def get_txids(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if not self.final_block:
                if self.address and self.category and self.option:
                    cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND option='{self.option} AND address='{self.address}' ';")
                elif self.category and self.option:
                    cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND address='{self.option}' ';")
                elif self.category:
                    cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}';")
                else:
                    cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}';")
                return cursor.fetchall()
            else:
                if self.address and self.category and self.option:
                    cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND option='{self.option} AND address='{self.address}'  AND blockheight <= {self.final_block};")
                elif self.category and self.option:
                    cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND address='{self.option}'  AND blockheight <= {self.final_block};")
                elif self.category:
                    cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND blockheight <= {self.final_block};")
                else:
                    cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND blockheight <= {self.final_block};")
                return cursor.fetchall()
    
    def get_txids_count(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if self.address and self.category and self.option:
                cursor.execute(f"SELECT COUNT(txid) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND option='{self.option} AND address='{self.address}' ';")
            elif self.category and self.option:
                cursor.execute(f"SELECT COUNT(txid) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND address='{self.option}' ';")
            elif self.category:
                cursor.execute(f"SELECT COUNT(txid) FROM voting WHERE coin='{self.coin}' AND category='{self.category}';")
            else:
                cursor.execute(f"SELECT COUNT(txid) FROM voting WHERE coin='{self.coin}';")
            try:
                return cursor.fetchone()[0]
            except:
                return 0
    
    def get_txids_sum(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if self.address and self.category and self.option:
                cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND option='{self.option} AND address='{self.address}' ';")
            elif self.category and self.option:
                cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND address='{self.option}' ';")
            elif self.category:
                cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND category='{self.category}';")
            else:
                cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}';")
            return cursor.fetchone()[0]

    def get_txids_before(self, blockheight):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if self.address and self.category and self.option:
                cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND option='{self.option} AND address='{self.address}' ' AND blockheight < {blockheight};")
            elif self.category and self.option:
                cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND address='{self.option}' ' AND blockheight < {blockheight};")
            elif self.category:
                cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND blockheight < {blockheight};")
            else:
                cursor.execute(f"SELECT * FROM voting WHERE coin='{self.coin}' AND blockheight < {blockheight};")
            return cursor.fetchall()
    
    def get_txids_count_before(self, blockheight):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if self.address and self.category and self.option:
                cursor.execute(f"SELECT COUNT(txid) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND option='{self.option} AND address='{self.address}' ' AND blockheight < {blockheight};")
            elif self.category and self.option:
                cursor.execute(f"SELECT COUNT(txid) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND address='{self.option}' ' AND blockheight < {blockheight};")
            elif self.category:
                cursor.execute(f"SELECT COUNT(txid) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND blockheight < {blockheight};")
            else:
                cursor.execute(f"SELECT COUNT(txid) FROM voting WHERE coin='{self.coin}' AND blockheight < {blockheight};")
            return cursor.fetchone()[0]
    
    def get_txids_sum_before(self, blockheight):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if self.address and self.category and self.option:
                cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND option='{self.option} AND address='{self.address}' ' AND blockheight < {blockheight};")
            elif self.category and self.option:
                cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND address='{self.option}' ' AND blockheight < {blockheight};")
            elif self.category:
                cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND category='{self.category}' AND blockheight < {blockheight};")
            else:
                cursor.execute(f"SELECT SUM(amount) FROM voting WHERE coin='{self.coin}' AND blockheight < {blockheight};")
            return cursor.fetchone()[0]
    
    def get_sum_by_address(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT address, SUM(amount) as votes FROM voting WHERE coin='{self.coin}' GROUP BY address;")
            return cursor.fetchall()
    
    def get_candidate_rows(self, candidate, region):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            sql = f"SELECT * from voting WHERE coin='{self.coin}' AND category='{region}' AND option='{candidate}';"
            cursor.execute(sql)
            return cursor.fetchall()

    def get_addresses_list(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            sql = f"SELECT DISTINCT address from voting WHERE coin='{self.coin}';"
            cursor.execute(sql)
            data = cursor.fetchall()
            try:
                addresses = [i[0] for i in data]
                return addresses
            except:
                return []

    def get_txids_list(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            sql = f"SELECT DISTINCT txid from voting WHERE coin='{self.coin}';"
            data = cursor.fetchall()
            try:
                txids = [i[0] for i in data]
                return txids
            except:
                return []
    


class VoteRow():
    def __init__(self, coin=None, address=None, category=None, option=None,
                txid=None, blockheight=None, amount=None, blocktime=None):
        self.coin = coin
        self.address = address
        self.category = category
        self.option = option
        self.txid = txid
        self.blockheight = blockheight
        self.amount = amount
        self.blocktime = blocktime

    def insert(self):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(f"INSERT INTO voting (coin,address,category,option,txid,blockheight,amount,blocktime) \
                                VALUES ('{self.coin}', '{self.address}', '{self.category}', '{self.option}', '{self.txid}', \
                                        {self.blockheight}, {self.amount}, {self.blocktime});")
                conn.commit()
                logger.info(f"Inserted {self.txid} for {self.option}_{self.category} ({self.address}) into voting table")
        except Exception as e:
            pass
            # logger.warning(e)
                    

    def update(self):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE voting SET blockheight={self.blockheight}, amount={self.amount}, blocktime={self.blocktime} WHERE coin='{self.coin}' AND txid='{self.txid}';")
            conn.commit()
        
    def delete_txid(self):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if self.txid:
                cursor.execute(f"DELETE FROM voting WHERE txid='{self.txid}';")
                conn.commit()

    def delete_invalid_blocks(self):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if self.blockheight and self.coin:
                cursor.execute(f"DELETE FROM voting WHERE coin='{self.coin}' AND blockheight > {self.blockheight};")
                conn.commit()
        
    def delete_coin(self):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if self.txid:
                cursor.execute(f"DELETE FROM voting WHERE coin='{self.coin}';")
                conn.commit()
        