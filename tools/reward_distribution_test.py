
import sys
import time
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, transfer_with_tip, TOKEN_NUM_BASE, get_account_balance
from tools.pallet_block_reward_test import setup_block_reward

WAIT_BLOCK_NUMBER = 10
COLLATOR_REWARD_RATE = 0.1
WAIT_ONLY_ONE_BLOCK_PERIOD = 12
WAIT_TIME_PERIOD = WAIT_ONLY_ONE_BLOCK_PERIOD * 3
REWARD_PERCENTAGE = 0.5
REWARD_ERROR = 0.0001
TIP = 10 ** 20


def _check_transaction_fee_reward_event(substrate, block_hash, tip):
    for event in substrate.get_events(block_hash):
        if event.value['module_id'] != 'BlockReward' or \
           event.value['event_id'] != 'TransactionFeesDistributed':
            continue
        now_reward = int(str(event['event'][1][1]))
        break
    if not now_reward:
        raise IOError('Cannot find the block event for transaction reward')
    real_rate = (now_reward - tip) / tip
    if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
        raise IOError(f'The fee reward percentage is strange {real_rate} v.s. {REWARD_PERCENTAGE}')


def _check_transaction_fee_reward_balance(substrate, addr, prev_balance, tip):
    now_balance = get_account_balance(substrate, addr)
    real_rate = (now_balance - prev_balance) / (tip * COLLATOR_REWARD_RATE) - 1
    if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
        raise IOError(f'The balance is strange {real_rate} v.s. {REWARD_PERCENTAGE}')


def transaction_fee_reward_test():
    print('---- transaction reward test!! ----')
    try:
        kp_src = Keypair.create_from_uri('//Alice')
        kp_bob = Keypair.create_from_uri('//Bob')
        kp_charlie = Keypair.create_from_uri('//Charlie')

        with SubstrateInterface(url=WS_URL) as substrate:
            block_reward = substrate.query(
                module='BlockReward',
                storage_function='BlockIssueReward',
            )
            print(f'Current reward: {block_reward}')
            new_set_reward = 0
            setup_block_reward(substrate, kp_src, new_set_reward)

            time.sleep(WAIT_TIME_PERIOD)
            prev_balance = get_account_balance(substrate, kp_src.ss58_address)
            receipt = transfer_with_tip(
                substrate, kp_bob, kp_charlie.ss58_address,
                1 * TOKEN_NUM_BASE, TIP, 1)

            _check_transaction_fee_reward_event(substrate, receipt.block_hash, TIP)
            time.sleep(WAIT_TIME_PERIOD)
            _check_transaction_fee_reward_balance(substrate, kp_src.ss58_address, prev_balance, TIP)

            setup_block_reward(substrate, kp_src, block_reward)
            print('✅✅✅transaction fee reward test pass')

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


# This test depends on the previous status, therefore, it's better to sleep about 3 blocks.
def block_reward_test():
    print('---- block reward test!! ----')
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            block_reward = substrate.query(
                module='BlockReward',
                storage_function='BlockIssueReward',
            )
            block_reward = int(str(block_reward))
            print(f'Current reward: {block_reward}')
            if not block_reward:
                raise IOError('block reward should not be zero')

            time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

            for i in range(0, WAIT_BLOCK_NUMBER):
                block_info = substrate.get_block_header()
                now_hash = block_info['header']['hash']
                prev_hash = block_info['header']['parentHash']
                extrinsic = substrate.get_block(prev_hash)['extrinsics']
                if not len(extrinsic):
                    raise IOError('Extrinsic list shouldn\'t be zero, maybe in the genesis block')
                # The fee of extrinsic in the previous block becomes the reward of this block,
                # but we have three default extrinisc
                #   timestamp.set
                #   dynamicFee.noteMinGasPriceTarget
                #   parachainSystem.setValidationData)
                elif len(substrate.get_block(prev_hash)['extrinsics']) != 3:
                    time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)
                    continue

                now_balance = substrate.query(
                    "System", "Account", [kp_src.ss58_address], block_hash=now_hash
                )['data']['free'].value
                previous_balance = substrate.query(
                    "System", "Account", [kp_src.ss58_address], block_hash=prev_hash
                )['data']['free'].value
                if now_balance - previous_balance != block_reward * COLLATOR_REWARD_RATE:
                    raise IOError(f'The block reward {now_balance - previous_balance} is'
                                  f'not the same as {block_reward * COLLATOR_REWARD_RATE}')
                else:
                    print('✅✅✅block fee reward test pass')
                    return
            raise IOError(f'Wait {WAIT_BLOCK_NUMBER}, but all blocks have extrinsic')

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def reward_distribution_test():
    block_reward_test()
    transaction_fee_reward_test()


if __name__ == '__main__':
    reward_distribution_test()
