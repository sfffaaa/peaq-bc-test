
import sys
import time
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, transfer_with_tip, get_account_balance
from tools.utils import TOKEN_NUM_BASE, ExtrinsicStack
from tools.pallet_block_reward_test import setup_block_reward

WAIT_BLOCK_NUMBER = 10
COLLATOR_REWARD_RATE = 0.1
WAIT_ONLY_ONE_BLOCK_PERIOD = 12
WAIT_TIME_PERIOD = WAIT_ONLY_ONE_BLOCK_PERIOD * 3
REWARD_PERCENTAGE = 0.5
REWARD_ERROR = 0.0001
TIP = 10 ** 20
FEE_MIN_LIMIT = 30 * 10**9  # 30nPEAQ
FEE_MAX_LIMIT = 90 * 10**9  # 90nPEAQ


# TODO: improve testing fees, by using fee-model, when ready...
def _check_transaction_fee_reward_event(substrate, block_hash, tip):
    for event in substrate.get_events(block_hash):
        if event.value['module_id'] != 'BlockReward' or \
           event.value['event_id'] != 'TransactionFeesDistributed':
            continue
        now_reward = int(str(event['event'][1][1]))
        break
    if not now_reward:
        raise IOError('Cannot find the block event for transaction reward')
    # real_rate = (now_reward - tip) / tip
    fee_wo_tip = now_reward - tip
    # if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
		# raise IOError(f'The fee reward percentage is strange {real_rate} v.s. {REWARD_PERCENTAGE}')
    if fee_wo_tip < FEE_MIN_LIMIT or fee_wo_tip > FEE_MAX_LIMIT:
        raise IOError(f'The transaction fee w/o tip is out of limit: {fee_wo_tip}')
            

# TODO: improve testing fees, by using fee-model, when ready
def _check_transaction_fee_reward_balance(substrate, addr, prev_balance, tip):
    now_balance = get_account_balance(substrate, addr)
    # real_rate = (now_balance - prev_balance) / (tip * COLLATOR_REWARD_RATE) - 1
    # if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
    #     raise IOError(f'The balance is strange {real_rate} v.s. {REWARD_PERCENTAGE}')
    rewards_wo_tip = (now_balance - prev_balance - tip * COLLATOR_REWARD_RATE) / COLLATOR_REWARD_RATE 
    if rewards_wo_tip < FEE_MIN_LIMIT or rewards_wo_tip > FEE_MAX_LIMIT:
        raise IOError(f'The transaction fee w/o tip is out of limit: {rewards_wo_tip}')


def _get_blocks_authored(substrate, addr, block_hash=None) -> int:
    result = substrate.query("ParachainStaking", "BlocksAuthored",
                             [addr], block_hash=block_hash)
    print(result)
    return int(str(result))


def _get_blocks_rewarded(substrate, addr, block_hash=None) -> int:
    result = substrate.query("ParachainStaking", "BlocksRewarded",
                             [addr], block_hash=block_hash)
    print(result)
    return int(str(result))


def _get_block_status(substrate, keypair, bl_hash=None):
    print('====')
    bl_authored = _get_blocks_authored(
        substrate, keypair.ss58_address, bl_hash)
    bl_rewarded = _get_blocks_rewarded(
        substrate, keypair.ss58_address, bl_hash)
    print('====')
    return bl_authored, bl_rewarded


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
            kp_alice = Keypair.create_from_uri('//Alice')
            kp_bob = Keypair.create_from_uri('//Bob')
            ex_stack = ExtrinsicStack(substrate, kp_alice)

            # Setup Block Reward
            setup_block_reward(substrate, kp_alice, pow(10, 18))

            # Extrinsic-stack: increment rewards & claim them
            ex_stack.compose_call("ParachainStaking",
                                  "increment_collator_rewards", [])
            ex_stack.compose_call("ParachainStaking",
                                  "claim_rewards", [])
            
            # Execute once at the beginning, to make sure all rewards have been
            # collected at the beginning of this test (more tests have been
            # run before) - but only if there are rewards to be claimed...
            bl_hash_alice_start = substrate.get_block_hash(None)
            bl_hash_bob_start = bl_hash_alice_start

            bl_authd, bl_rewdd = _get_block_status(
                substrate, kp_alice, bl_hash_alice_start)
            if bl_rewdd < bl_authd:
                bl_hash_alice_start = ex_stack.execute()

            bl_authd, bl_rewdd = _get_block_status(
                substrate, kp_bob, bl_hash_bob_start)
            if bl_rewdd < bl_authd:
                bl_hash_bob_start = ex_stack.execute(kp_bob)

            # Double check that number of authored is equal to rewarded
            bl_authd, bl_rewdd = _get_block_status(
                substrate, kp_alice, bl_hash_alice_start)
            if bl_authd != bl_rewdd:
                raise IOError(f'Alice: blocks authored ({bl_authd}) != \
                              rewarded ({bl_rewdd}), abort test')
            bl_authd, bl_rewdd = _get_block_status(
                substrate, kp_bob, bl_hash_bob_start)
            if bl_authd != bl_rewdd:
                raise IOError(f'Bob: blocks authored ({bl_authd}) != \
                              rewarded ({bl_rewdd}), abort test')

            # Now check the accounts at this moment
            balance_alice_start = get_account_balance(
                substrate, kp_alice.ss58_address, bl_hash_alice_start)
            balance_bob_start = get_account_balance(
                substrate, kp_bob.ss58_address, bl_hash_bob_start)
            bl_auth_alice_start = _get_blocks_rewarded(
                substrate, kp_alice.ss58_address, bl_hash_alice_start)
            bl_auth_bob_start = _get_blocks_rewarded(
                substrate, kp_bob.ss58_address, bl_hash_bob_start)
            
            # Determine reward-rates
            block_reward = substrate.query(
                module='BlockReward',
                storage_function='BlockIssueReward',
            )
            reward_rate = substrate.query(
                module='ParachainStaking',
                storage_function='RewardRateConfig',
            )
            collator_rate = int(str(reward_rate['collator_rate'])) / pow(10, 18)
            block_reward = int(str(block_reward))
            collator_reward = block_reward * collator_rate
            if not block_reward:
                raise IOError('block reward should not be zero')
            if not collator_rate:
                raise IOError('could not determine collator-reward-rate')
            
            # Now wait for round about 3 blocks to be finalized and run
            # extrinsics for both validators again
            print('Waiting for round about 3 blocks to be finalized...')
            time.sleep(WAIT_TIME_PERIOD)
            bl_hash_alice_now = ex_stack.execute()
            bl_hash_bob_now = ex_stack.execute(kp_bob)

            # Check again, that blocks authored is equal to rewarded
            bl_auth_alice_now, bl_rewdd = _get_block_status(
                substrate, kp_alice, bl_hash_alice_now)
            assert bl_auth_alice_now == bl_rewdd
            bl_auth_bob_now, bl_rewdd = _get_block_status(
                substrate, kp_bob, bl_hash_bob_now)
            assert bl_auth_bob_now == bl_rewdd

            # Now compare balances and blocks-authored
            balance_alice_now = get_account_balance(
                substrate, kp_alice.ss58_address, bl_hash_alice_now)
            balance_bob_now = get_account_balance(
                substrate, kp_bob.ss58_address, bl_hash_bob_now)

            # Compare initial balance with current balance
            bl_auth_alice_now = int(str(bl_auth_alice_now))
            bl_auth_alice_start = int(str(bl_auth_alice_start))
            bl_auth_bob_now = int(str(bl_auth_bob_now))
            bl_auth_bob_start = int(str(bl_auth_bob_start))
            diff_balance_alice = balance_alice_now - balance_alice_start
            diff_bl_auth_alice = bl_auth_alice_now - bl_auth_alice_start
            diff_balance_bob = balance_bob_now - balance_bob_start
            diff_bl_auth_bob = bl_auth_bob_now - bl_auth_bob_start

            # Redundancy check for number of finalized blocks
            bl_auth_tot = diff_bl_auth_alice + diff_bl_auth_bob
            bl_num_start = substrate.get_block_number(bl_hash_alice_start)
            bl_num_stop = substrate.get_block_number(bl_hash_alice_now)
            assert bl_num_stop - bl_num_start == bl_auth_tot
            bl_num_start = substrate.get_block_number(bl_hash_bob_start)
            bl_num_stop = substrate.get_block_number(bl_hash_bob_now)
            assert bl_num_stop - bl_num_start == bl_auth_tot

            print(f'Alice: authored-start({bl_auth_alice_start}), authored-now({bl_auth_alice_now})')
            print(f'Alice: balance-start({balance_alice_start}), balance-now({balance_alice_now})')
            print(f'Alice: diff block({diff_bl_auth_alice}), diff balance({diff_balance_alice})')
            print('----')
            print(f'Bob: authored-start({bl_auth_bob_start}), authored-now({bl_auth_bob_now})')
            print(f'Bob: balance-start({balance_bob_start}), balance-now({balance_bob_now})')
            print(f'Bob: diff block({diff_bl_auth_bob}), diff balance({diff_balance_bob})')
            print('----')
            print(f'BlockReward: {block_reward}, CollatorReward: {collator_reward}')

            # Debug:
            rewards_alice = collator_reward * diff_bl_auth_alice
            diff = abs(diff_balance_alice - rewards_alice) / rewards_alice * 100
            print(f'Deviation Alice: {diff}%')
            rewards_bob = collator_reward * diff_bl_auth_bob
            diff = abs(diff_balance_bob - rewards_bob) / rewards_bob * 100
            print(f'Deviation Bob: {diff}%')
            assert diff_balance_alice == rewards_alice
            assert diff_balance_bob == rewards_bob

            print('✅✅✅ block reward test pass')

            # time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

            # for i in range(0, WAIT_BLOCK_NUMBER):
            #     block_info = substrate.get_block_header()
            #     now_hash = block_info['header']['hash']
            #     prev_hash = block_info['header']['parentHash']
            #     extrinsic = substrate.get_block(prev_hash)['extrinsics']
            #     if not len(extrinsic):
            #         raise IOError('Extrinsic list shouldn\'t be zero, maybe in the genesis block')
            #     # The fee of extrinsic in the previous block becomes the reward of this block,
            #     # but we have three default extrinisc
            #     #   timestamp.set
            #     #   dynamicFee.noteMinGasPriceTarget
            #     #   parachainSystem.setValidationData)
            #     elif len(substrate.get_block(prev_hash)['extrinsics']) != 3:
            #         time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)
            #         continue

            #     ex_stack.execute()

            #     now_balance = substrate.query(
            #         "System", "Account", [kp_src.ss58_address], block_hash=now_hash
            #     )['data']['free'].value
            #     previous_balance = substrate.query(
            #         "System", "Account", [kp_src.ss58_address], block_hash=prev_hash
            #     )['data']['free'].value
            #     if now_balance - previous_balance != block_reward * COLLATOR_REWARD_RATE:
            #         raise IOError(f'The block reward {now_balance - previous_balance} is'
            #                       f'not the same as {block_reward * COLLATOR_REWARD_RATE}')
            #     else:
            #         print('✅✅✅block fee reward test pass')
            #         return
            # raise IOError(f'Wait {WAIT_BLOCK_NUMBER}, but all blocks have extrinsic')

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def reward_distribution_test():
    block_reward_test()
    transaction_fee_reward_test()


if __name__ == '__main__':
    reward_distribution_test()
