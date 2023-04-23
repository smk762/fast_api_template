## Installation

Run the `./install` script to:
- install the required python packages & apt packages
- Create & populate a .env file.
- Setup systemd services for the api.
- Generate a self-signed SSL certificate for the api.
- Create an Nginx server block for the api.

The .env contains the following:



## Usage
- For alert bots, set these to run periodically via crontab. For example, to send alerts ever 4 hours, add an entry like `0 */4 * * * /home/smk/dragonhound_bots/discord/electrum-status.py`