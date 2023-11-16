#!/usr/bin/env python3
import os
import time
import sqlite3
from lib.config import ConfigFastAPI
from lib.json_utils import write_jsonfile_data, get_jsonfile_data

class SqliteDB():
    def __init__(self, config):
        self.db_path = config.SQLITEDB_PATH
        self.tables_config =  config.SQLITEDB_TABLES
        if os.path.exists(self.db_path):
            # Initialize configured tables
            for table_name in self.tables_config:
                if table_name not in ["table_name", "table_template"]:
                    self.create_tables(table_name)
        else:
            print(f"Database file does not exist: {self.db_path}")

    # Connect to SQLite DB    
    def connect_sqlite(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor

    # Create table if not existing
    def create_tables(self, table_name):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            if len(cursor.fetchall()) == 0 :
                if table_name not in self.tables_config:
                    print('Table is not configured in table_config.json!')
                else:
                    print('Table does not exist, creating it...')
                    sql = f"CREATE TABLE {table_name} ("
                    columns = []
                    for column in self.tables_config[table_name]:
                        column_sql = f"{column['column_name']} {column['type']}"
                        if column['primary_key']:
                            sql += "PRIMARY KEY"
                        if column['not_null']:
                            sql += "NOT NULL"
                        if column['unique']:
                            sql += "UNIQUE"
                        if column['autoincrement']:
                            sql += "AUTOINCREMENT"
                        columns.append(column_sql)
                    sql += ", ".join(columns)
                    sql += ")"
                    cursor.execute(sql)
                    conn.commit()

    def get_tables(self, cursor):
        ''' Returns a list of tables in the database. '''
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return cursor.fetchall()

    def get_row(self, cursor, table):
        ''' Returns the first row of a table.'''
        cursor.execute(f"SELECT * FROM {table};")
        return cursor.fetchone()

    def get_rows(self, cursor, table):
        ''' Returns all rows of a table.'''
        cursor.execute(f"SELECT * FROM {table};")
        return cursor.fetchall()

    def get_column_names(self, row):
        ''' Returns a list of column names from a row. '''
        return row.keys()

    def get_table_info(self, cursor, table):
        ''' Returns a list of tuples with table info.'''
        cursor.execute(f'pragma table_info({table})')
        return cursor.fetchall()

    def view_table_info(self, cursor, table):
        ''' Prints table info in a nice format. '''
        info = self.get_table_info(cursor, table)
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


if __name__ == '__main__':
    db = SqliteDB()
    db.create_tables()
