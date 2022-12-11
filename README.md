# openWB invoice

This is a simple invoice generator for openWB. It generates a PDF invoice for the current month and then sends it to the email address configured in the config file.

## Requirements
- [Python 3](https://www.python.org/downloads/)
- Pip modules: `pip install -r requirements.txt`
- openWB running on the same local network as the invoice generator
- An email account to send the invoice from, the account must allow login over password only

## Usage
- Edit the config file `config.yml` to match your needs
- Run `python3 openwb_invoice.py`
- You might want to run it as a cron job, e.g. at the third day of each month to generate the invoice for the previous month
    - `crontab -e`
    - `0 0 3 * * python3 /path/to/openwb_invoice.py`
