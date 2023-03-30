## For simple polls
- Run `./generate_poll.py` to create a new entry in `poll_config_v2.json`

## For Notary Node elections
- Update the season variable in `./parse_candidates.py`, then run it to get a dict of candidates per region.
- Run `./input_candidate_addresses.py` to enter the candidate adresses for each region.
- Run `./generate_notary_vote.py`