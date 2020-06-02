#!/usr/bin/env python3

import logging
import argparse
import os
import colorlog
import inspect
import requests
import pprint
import eospy.cleos
import eospy.keys
SCRIPT_PATH = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))

parser = argparse.ArgumentParser()
parser.add_argument("-v",
                    '--verbose',
                    action="store_true",
                    dest="verbose",
                    help='Print logged info to screen')
parser.add_argument("-d",
                    '--debug',
                    action="store_true",
                    dest="debug",
                    help='Print debug info')
parser.add_argument('-l',
                    '--log_file',
                    default='{}.log'.format(
                        os.path.basename(__file__).split('.')[0]),
                    help='Log file')
parser.add_argument('-u',
                    '--api_endpoint',
                    default='https://api.eosmetal.io',
                    help='EOSIO API endpoint URI')
parser.add_argument('-k',
                    '--key',
                    default='{}/oracle.key'.format(SCRIPT_PATH),
                    help='Path to a file with the Private key')
parser.add_argument('-o',
                    '--owner',
                    default='eosmetaliobp',
                    help='Account pushing the value')
args = parser.parse_args()

VERBOSE = args.verbose
DEBUG = args.debug
LOG_FILE = args.log_file
API_ENDPOINT = args.api_endpoint
KEY_FILE = args.key
OWNER = args.owner

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s%(reset)s')
if DEBUG:
    logger.setLevel(logging.DEBUG)
if VERBOSE:
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

fh = logging.FileHandler(LOG_FILE)
logger.addHandler(fh)
fh.setFormatter(formatter)

pp = pprint.PrettyPrinter(indent=4)

SCRIPT_PATH = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))

cleos = eospy.cleos.Cleos(url=API_ENDPOINT)

SYMBOLS = [
    {
        'wax_symbol': 'BTC-WAXP',
        'oracle_symbol': "waxpbtc",
        'multiplier': 100000000
    },
    {
        'wax_symbol': 'USD-WAXP',
        'oracle_symbol': "waxpusd",
        'multiplier': 10000
    },
]


def push_quotes(quotes, key):
    data = cleos.abi_json_to_bin('delphioracle', 'write', {
        "quotes": quotes,
        "owner": OWNER
    })
    trx = {
        "actions": [{
            "account": "delphioracle",
            "name": "write",
            "authorization": [{
                "actor": OWNER,
                "permission": "delphi"
            }],
            "data": data['binargs']
        }]
    }
    return cleos.push_transaction(trx, key, broadcast=True)


def get_last_tick(symbol):
    try:
        result = requests.get(
            'https://api.bittrex.com/api/v1.1/public/getticker?market={}'.
            format(symbol)).json()
        pp.pprint(result)
        if not result['success']:
            logger.critical('Error getting tick from bittrex: {}'.format(
                result['message']))
            return None
        return result['result']['Last']
    except Exception as e:
        logger.critical('Error getting tick from bittrex: {}'.format(e))
        return None


def main():
    quotes = []
    try:
        with open(KEY_FILE, 'r') as keyfile:
            key = keyfile.read().replace('\n', '')
    except Exception as e:
        logger.critical('Error reading private key file: {}'.format(e))

    for symbol in SYMBOLS:
        try:
            tick = get_last_tick(symbol['wax_symbol'])
            tick = int(tick * symbol['multiplier'])
        except Exception as e:
            logger.critical(
                'Error getting last tick from Kraken: {}'.format(e))
        quotes.append({'value': tick, 'pair': symbol['oracle_symbol']})

    pp.pprint(quotes)

    try:
        resp = push_quotes(quotes, key)
    except Exception as e:
        logger.critical('Error pushing transaction: {}'.format(e))


if __name__ == "__main__":
    main()
