Deps:
- `sudo apt install python3-pip`
- `pip3 install -r requirements.txt`

Run `python3 lib_sqlite.py create_table` to initialise the sqlite DB.
Run `python3 lib_scan.py scan` to manually scan the electrums (if API is running, this will happen ever 10 minutes).