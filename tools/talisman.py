from substrateinterface import SubstrateInterface
from peaq.utils import get_account_balance
import time
import logging


BALANCE_ADDRESS = '5Gn1mqSNNXJ3KpFWFPGY5ZrXUTWV3ooqihaZjsBndDz9uYwM'
URL = 'wss://wss-krest.peaq.network'
PERIOD_TIME = 6

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    while True:
        start_time = time.time()
        logging.info('-- Before checking')
        with SubstrateInterface(url=URL) as substrate:
            logging.info('-- Connect over')
            balance = get_account_balance(substrate, BALANCE_ADDRESS)
            logging.info(f'-- show balance {balance}')
        end_time = time.time()
        logging.info('-- After checking')
        logging.info(f'Elapsed time: {end_time - start_time}')
        time.sleep(PERIOD_TIME)
