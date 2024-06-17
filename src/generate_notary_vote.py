#!/usr/bin/env python3
import os
from datetime import datetime as dt
import lib_json
import lib_notary_vote

script_path = os.path.realpath(os.path.dirname(__file__))

if __name__ == '__main__':
    current_year = dt.now().year
    season = int(current_year) - 2016
    vote_chain = f"VOTE{current_year}"
    poll_config = lib_json.get_jsonfile_data(f"{script_path}/poll_config.json")
    url = f"https://raw.githubusercontent.com/KomodoPlatform/NotaryNodes/master/season{season}/candidates.json"
    candidates = requests.get(url).json()
    poll_config = lib_notary_vote.update_notary_vote(candidates, poll_config, vote_chain)
    lib_json.write_jsonfile_data(f'{script_path}/poll_config.json', poll_config)
