import sys
import time
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL, ExtrinsicStack

COLLATOR_REWARD_RATE = 0.1
WAIT_TIME_PERIOD = 12 * 3


def setup_block_reward(substrate, kp_src, block_reward):
    ex_stack = ExtrinsicStack(substrate, kp_src)
    ex_stack.compose_sudo_call('BlockReward', 'set_block_issue_reward',
                               {'block_reward': block_reward})
    ex_stack.execute()


def set_max_currency_supply(substrate, kp_src, max_currency_supply):
    ex_stack = ExtrinsicStack(substrate, kp_src)
    ex_stack.compose_sudo_call('BlockReward', 'set_max_currency_supply',
                               {'limit': max_currency_supply})
    ex_stack.execute()


def test_change_block_issue_reward():
    print('---- change block issue reward ----')
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            setup_block_reward(substrate, kp_src, pow(10, 18))

            print('✅✅✅ change block issue reward test pass')
    
    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def test_change_max_currency_supply():
    print('---- change max currency supply!! ----')
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            max_currency_supply = substrate.query(
                module='BlockReward',
                storage_function='MaxCurrencySupply',
            )
            print(f'Current max-currency-supply: {max_currency_supply}')
            new_max_currency_supply = 500
            set_max_currency_supply(substrate, kp_src, new_max_currency_supply)

            time.sleep(WAIT_TIME_PERIOD)

            for event in substrate.get_events():
                if event.value['module_id'] != 'ParachainStaking' or \
                   event.value['event_id'] != 'Rewarded':
                    continue
                now_reward = event['event'][1][1][1]
                if int(str(now_reward)) != 0:
                    raise IOError('Cannot get the correct number')

            set_max_currency_supply(substrate, kp_src, max_currency_supply)

            print('✅✅✅ change max currency supply test pass')

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def pallet_block_reward_test():
    test_change_max_currency_supply()
    test_change_block_issue_reward()


if __name__ == '__main__':
    pallet_block_reward_test()
