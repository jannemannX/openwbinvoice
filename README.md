# openWB invoice

This is a simple invoice generator for [openWB](https://openwb.de/main/). It generates a PDF invoice for the current month and then sends it to the email address configured in the config file.

## Pre-requisites
- [Python 3](https://www.python.org/downloads/)
- Pip modules: `pip install -r requirements.txt`
- openWB running on the same local network as the invoice generator

## Usage
- Edit the config file `config.yml` to match your needs
- Run `python3 openwb_invoice.py`
- You might want to run it as a cron job, e.g. at the third day of each month to generate the invoice for the previous month
    - `crontab -e`
    - `0 0 3 * * python3 /path/to/openwb_invoice.py`
