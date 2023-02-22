import sys
import time
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL

COLLATOR_REWARD_RATE = 0.1
WAIT_TIME_PERIOD = 12 * 3
# from tools.pallet_assets_test import pallet_assets_test


def setup_block_reward(substrate, kp_src, block_reward):
    payload = substrate.compose_call(
        call_module='BlockReward',
        call_function='set_block_issue_reward',
        call_params={
            'block_reward': block_reward
        }
    )

    call = substrate.compose_call(
        call_module='Sudo',
        call_function='sudo',
        call_params={
            'call': payload.value,
        }
    )

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    if not receipt.is_success:
        raise IOError('cannot setup the receipt')
    show_extrinsic(receipt, 'set reward')


def set_max_currency_supply(substrate, kp_src, max_currency_supply):
    payload = substrate.compose_call(
        call_module='BlockReward',
        call_function='set_max_currency_supply',
        call_params={
            'limit': max_currency_supply
        }
    )

    call = substrate.compose_call(
        call_module='Sudo',
        call_function='sudo',
        call_params={
            'call': payload.value,
        }
    )

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    if not receipt.is_success:
        raise IOError('cannot setup the receipt')
    show_extrinsic(receipt, 'set max_currency_supply')


def pallet_change_block_reward():
    print('---- change block reward!! ----')
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            block_reward = substrate.query(
                module='BlockReward',
                storage_function='BlockIssueReward',
            )
            print(f'Current reward: {block_reward}')
            new_set_reward = 500
            setup_block_reward(substrate, kp_src, new_set_reward)

            time.sleep(WAIT_TIME_PERIOD)

            for event in substrate.get_events():
                if event.value['module_id'] != 'ParachainStaking' or \
                   event.value['event_id'] != 'Rewarded':
                    continue
                now_reward = event['event'][1][1][1]
                if int(str(now_reward)) * 1 / COLLATOR_REWARD_RATE != new_set_reward:
                    print(f'{int(str(now_reward)) * 10} v.s. {new_set_reward}')
                    raise IOError('Cannot get the correct number')

            setup_block_reward(substrate, kp_src, block_reward)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def pallet_change_max_currency_supply():
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

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def pallet_block_reward_tests():
    pallet_change_block_reward()
    pallet_change_max_currency_supply()


if __name__ == '__main__':
    pallet_block_reward_tests()
