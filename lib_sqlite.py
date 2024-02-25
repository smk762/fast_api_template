#!/usr/bin/env python3
import os
import sys
import sqlite3
from dotenv import load_dotenv
from datetime import timezone
from lib_logger import logger
import sqlite3


script_dir = os.path.abspath( os.path.dirname( __file__ ) )

def get_sqlite(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        logger.error(e)
    return conn


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
    print(f"\n\n## {table}\n")
    print('|{:^10s}|{:^21s}|{:^18s}|{:^11s}|{:^14s}|{:^13s}|'.format(
        "-"*10,
        "-"*21,
        "-"*18,
        "-"*11,
        "-"*14,
        "-"*13,
        )    
    )
    print('|{:^10s}|{:^21s}|{:^18s}|{:^11s}|{:^14s}|{:^13s}|'.format(
        "ID",
        "Name",
        "Type",
        "NotNull",
        "DefaultVal",
        "PrimaryKey"
        )
    )
    print('|{:^10s}|{:^21s}|{:^18s}|{:^11s}|{:^14s}|{:^13s}|'.format(
        "-"*10,
        "-"*21,
        "-"*18,
        "-"*11,
        "-"*14,
        "-"*13,
        )    
    )

    for i in info:
        print('|{:^10s}|{:^21s}|{:^18s}|{:^11s}|{:^14s}|{:^13s}|'.format(
            f'{i[0]}',
            f'{i[1]}',
            f'{i[2]}',
            f'{i[3]}',
            f'{i[4]}',
            f'{i[5]}'
        )
    )


def delete_electrum_coin(coin):
    try:
        sql = f"DELETE FROM electrum_status WHERE coin = '{coin}';"
        conn = get_sqlite(f"{script_dir}/electrum_status.db")
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        print(f"{coin} removed from database")
    except Exception as e:
        print(e)
        print(sql)

def get_db_coins():
    try:
        sql = f"SELECT DISTINCT coin FROM electrum_status;"
        conn = get_sqlite(f"{script_dir}/electrum_status.db")
        cursor = conn.cursor()
        cursor.execute(sql)
        resp = []
        for i in cursor.fetchall():
            resp.append(i[0])
        return resp
    except Exception as e:
        print(e)
        print(sql)


def update_electrum_row(row):
    try:
        print(f"adding {row} added yo from database")
        sql = f"INSERT INTO electrum_status \
                    (coin, server, protocol, result, last_connection) \
                VALUES (?, ?, ?, ?, ?) \
                ON CONFLICT (server) DO UPDATE \
                SET result='{row[3]}', last_connection='{row[4]}';"
        conn = get_sqlite(f"{script_dir}/electrum_status.db")
        cursor = conn.cursor()
        cursor.execute(sql, row)
        conn.commit()
        print(f"{row} added yo from database")
    except Exception as e:
        print(e)
        print(sql)


def update_electrum_row_failed(row):
    try:
        sql = f"INSERT INTO electrum_status    \
                    (coin,                     \
                    server,                    \
                    protocol,                  \
                    result,                    \
                    last_connection)           \
                VALUES (?, ?, ?, ?, ?)         \
                ON CONFLICT (server) DO UPDATE \
                SET result='{row[3]}';"
        conn = get_sqlite(f"{script_dir}/electrum_status.db")
        cursor = conn.cursor()
        cursor.execute(sql, row)
        conn.commit()
    except Exception as e:
        print(e)
        print(sql)


def get_electrum_status_data():
    conn = get_sqlite(f"{script_dir}/electrum_status.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM electrum_status ORDER BY coin").fetchall()
    return rows

def create_tables():
    sql = "CREATE TABLE electrum_status (   \
        id INTEGER PRIMARY KEY,             \
        coin TEXT NOT NULL,                 \
        server TEXT NOT NULL UNIQUE,        \
        protocol TEXT NOT NULL,             \
        result TEXT,                        \
        last_connection INTEGER);"
    conn = get_sqlite(f"{script_dir}/electrum_status.db")
    cursor = conn.cursor()
    cursor.execute(sql)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "create_tables":
            create_tables()
    else:
        data = get_electrum_status_data()
        resp = [{k: item[k] for k in item.keys()} for item in data]
        for row in resp:
            print(str(row))


