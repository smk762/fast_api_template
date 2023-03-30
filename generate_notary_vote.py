#!/usr/bin/env python3
import lib_json
import lib_notary_vote


season = lib_notary_vote.enforce_input("Which season is the vote for? ", True)

candidates = lib_notary_vote.parse_candidates(season)
lib_json.write_jsonfile_data("candidates.json", candidates)

candidates = lib_notary_vote.input_candidate_addresses(candidates)
lib_json.write_jsonfile_data("candidates.json", candidates)

poll_config = lib_json.get_jsonfile_data("poll_config_v2.json")
poll_config = lib_notary_vote.add_notary_vote_to_poll_config(candidates, poll_config)
lib_json.write_jsonfile_data("poll_config_v2.json", poll_config)


