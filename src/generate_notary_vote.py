#!/usr/bin/env python3
import os
import lib_json
import lib_notary_vote

script_path = os.path.realpath(os.path.dirname(__file__))

season = lib_notary_vote.enforce_input("Which season is the vote for? ", True)

candidates = lib_notary_vote.parse_candidates(season)
lib_json.write_jsonfile_data(f"{script_path}/candidates.json", candidates)

poll_config = lib_json.get_jsonfile_data(f"{script_path}/poll_config.json")
if not poll_config:
    poll_config = {}
poll_config = lib_notary_vote.add_notary_vote_to_poll_config(candidates, poll_config)
print(candidates)
print(poll_config)
lib_json.write_jsonfile_data(f'{script_path}/poll_config.json', poll_config)


