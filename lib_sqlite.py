#!/usr/bin/env python3
import os
import sys
import sqlite3
from dotenv import load_dotenv
from datetime import timezone
from lib_logger import logger
import sqlite3


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


def update_electrum_row(row):
    try:
        sql = f"INSERT INTO electrum_status \
                    (coin, electrum, ssl, status, response, last_connection) \
                VALUES (?, ?, ?, ?, ?, ?) \
                ON CONFLICT (electrum) DO UPDATE \
                SET status='{row[3]}', response='{row[4]}', last_connection='{row[5]}';"
        conn = get_sqlite("electrum_status.db")
        cursor = conn.cursor()
        cursor.execute(sql, row)
        conn.commit()
    except Exception as e:
        print(e)
        print(sql)


def update_electrum_row_failed(row):
    try:
        sql = f"INSERT INTO electrum_status \
                    (coin, electrum, ssl, status, response) \
                VALUES (?, ?, ?, ?, ?) \
                ON CONFLICT (electrum) DO UPDATE \
                SET status='{row[3]}', response='{row[4]}';"
        conn = get_sqlite("electrum_status.db")
        cursor = conn.cursor()
        cursor.execute(sql, row)
        conn.commit()
    except Exception as e:
        print(e)
        print(sql)


def get_electrum_status_data():
    conn = get_sqlite("electrum_status.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM electrum_status ORDER BY coin").fetchall()
    return rows

def create_tables():
    sql = "CREATE TABLE electrum_status (   \
        id INTEGER PRIMARY KEY,              \
        coin TEXT NOT NULL,                   \
        electrum TEXT NOT NULL UNIQUE,         \
        ssl BOOLEAN NOT NULL,         \
        status TEXT,                            \
        response TEXT,                           \
        last_connection INTEGER);"
    conn = get_sqlite("electrum_status.db")
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


