## Install
Run `./setup.sh` to generate a `docker-compose.yaml` file and associated launch files.
Run `start.sh` to start the chains and the API.


## Adding new KIP votes
- Run `./generate_poll.py` to create a new entry in `poll_config.json`

## Adding a Notary Node election
- Update the season variable in `./parse_candidates.py`, then run it to get a dict of candidates per region.
- Run `./input_candidate_addresses.py` to enter the candidate adresses for each region.
- Run `./generate_notary_vote.py`

