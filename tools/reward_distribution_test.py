
import sys
import time
import traceback
sys.path.append('./')

import numpy as np
import matplotlib.pyplot as plt

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
CLAIM_REWARDS_FEE_MAX = 10**17  # 10 PEAQ-CENT
TOLERANCE_REWARDS_PERCENT = 0.1

DEBUG = False


# NOTE-1: Currently we are not able to calculate the transaction-fees
#   accurately. Some of the following tests should be more extensive, but
#   cannot be extended due to the missing capability of calculating accurate
#   transaction-fees. As soon we are capable of accurate calculation, this
#   should be extended.


# Prints messages to terminal only when DEBUG=True
def _debugprint(msg: str):
    if DEBUG:
        print(msg)


# TODO: See NOTE-1
def _check_transaction_fee_reward_event(substrate, block_hash, tip):
    for event in substrate.get_events(block_hash):
        if event.value['module_id'] != 'BlockReward' or \
           event.value['event_id'] != 'TransactionFeesReceived':
            continue
        now_reward = int(str(event['event'][1][1]))
        break
    if not now_reward:
        raise IOError('Cannot find the block event for transaction reward')
    # TODO: See NOTE-1
    # real_rate = (now_reward - tip) / tip
    # fee_wo_tip = now_reward
    # if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
	    # raise IOError(f'The fee reward percentage is strange {real_rate} v.s. {REWARD_PERCENTAGE}')
    # if fee_wo_tip < FEE_MIN_LIMIT or fee_wo_tip > FEE_MAX_LIMIT:
    #     raise IOError(f'The transaction fee w/o tip is out of limit: {fee_wo_tip}')


# TODO: See NOTE-1
def _check_transaction_fee_reward_balance(substrate, addr, prev_balance, tip):
    now_balance = get_account_balance(substrate, addr)
    # TODO: See NOTE-1
    # real_rate = (now_balance - prev_balance) / (tip * COLLATOR_REWARD_RATE) - 1
    # if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
    #     raise IOError(f'The balance is strange {real_rate} v.s. {REWARD_PERCENTAGE}')
    rewards_wo_tip = (now_balance - prev_balance - tip * COLLATOR_REWARD_RATE) / COLLATOR_REWARD_RATE 
    if rewards_wo_tip < FEE_MIN_LIMIT or rewards_wo_tip > FEE_MAX_LIMIT:
        raise IOError(f'The transaction fee w/o tip is out of limit: {rewards_wo_tip}')


def _get_blocks_authored(substrate, addr, block_hash=None) -> int:
    result = int(str(substrate.query(
        "ParachainStaking", "BlocksAuthored", [addr], block_hash=block_hash)))
    _debugprint(f'BlocksAuthored: {result} [{type(result)}]')
    return result


def _get_blocks_rewarded(substrate, addr, block_hash=None) -> int:
    result = int(str(substrate.query(
        "ParachainStaking", "BlocksRewarded", [addr], block_hash=block_hash)))
    _debugprint(f'BlocksRewarded: {result} [{type(result)}]')
    return result


def _get_unclaimed_rewards(substrate, addr, block_hash=None) -> int:
    result = int(str(substrate.query(
        "ParachainStaking", "Rewards", [addr], block_hash=block_hash)))
    _debugprint(f'Rewards: {result} [{type(result)}]')
    return result


def _get_average_block_reward(substrate, block_hash=None) -> int:
    avg_cfg = substrate.query(
        "BlockReward", "AverageSelectorConfig", block_hash=block_hash)
    rew_cfg = substrate.query(
        "BlockReward", "RewardDistributionConfigStorage",
        block_hash=block_hash)
    staking_rate = int(str(rew_cfg["collators_percent"])) / 1000000000
    if avg_cfg == "DiAvgDaily":
        register = "DailyBlockReward"
    elif avg_cfg == "":
        register = "DailyBlockReward"
    elif avg_cfg == "":
        register = "DailyBlockReward"
    else:
        raise IOError("unknown BlockReward::AverageSelectorConfig")
    result = substrate.query(
            "BlockReward", register, block_hash=block_hash)
    avg_bl_rew = int(int(str(result["avg"])) * staking_rate)

    _debugprint(f'AverageBlockReward: {result} [{type(result)}]')
    return avg_bl_rew


def _get_block_status(substrate, keypair: Keypair, bl_hash=None):
    _debugprint('==== Block-Status ====')
    bl_authored = _get_blocks_authored(
        substrate, keypair.ss58_address, bl_hash)
    bl_rewarded = _get_blocks_rewarded(
        substrate, keypair.ss58_address, bl_hash)
    rewards = _get_unclaimed_rewards(
        substrate, keypair.ss58_address, bl_hash)
    _debugprint('======================')
    return bl_authored, bl_rewarded, rewards


def _get_collator_rate(substrate) -> float:
    reward_rate = substrate.query(
        'ParachainStaking', 'RewardRateConfig')
    return int(str(reward_rate['collator_rate'])) / pow(10, 18)


def _get_block_issue_reward(substrate) -> int:
    return int(str(substrate.query(
        'BlockReward', 'BlockIssueReward')))


def _get_block_hash_before(substrate, bl_hash):
    header = substrate.get_block_header(bl_hash)
    return header['header']['parentHash']


def _get_staking_factor(substrate) -> float:
    staking_factor = substrate.query(
        'BlockReward', 'RewardDistributionConfigStorage')
    staking_factor = staking_factor['collators_percent']
    staking_factor = int(str(staking_factor))
    staking_factor = staking_factor / pow(10, 9)
    return staking_factor


# This method collects data from a certain storage for the last n_blocks backwards
# beginning from block with hash bl_hash. It creates a graph afterwars.
def create_graph_on_storage(substrate: SubstrateInterface,
                            query_fcn,
                            bl_hash: str = None,
                            n_blocks: int = 10,
                            ylabel: str = None):
    data = np.empty(n_blocks)
    bl_num = np.empty(n_blocks)
    for i in reversed(range(0, n_blocks)):
        data[i] = query_fcn(substrate, bl_hash)
        bl_num[i] = substrate.get_block_number(bl_hash)
        bl_hash = _get_block_hash_before(substrate, bl_hash)

    # Plot collected data
    plt.plot(bl_num, data)
    plt.xlabel('BlockNumber')
    plt.ylabel(ylabel)
    plt.grid()
    plt.show()


def reward_distribution_test_setup(substrate, kp_src) -> int:
    print('---- Reward Distribution Test Setup ----')

    issue_number = pow(10, 19)
    staking_fac = _get_staking_factor(substrate)
    avg = int(issue_number * staking_fac)
    _debugprint(f'issue_number: {issue_number}, '
                f'staking_fac: {staking_fac} -> avg: {avg}')

    # Setup block issue number
    ex_stack = ExtrinsicStack(substrate, kp_src)
    ex_stack.compose_sudo_call('BlockReward', 'set_block_issue_reward',
                               {'block_reward': issue_number})
    bl_hash = ex_stack.execute()

    # TODO: See NOTE-1
    # Validate average-reward-reset
    # avg_now = _get_average_block_reward(substrate, bl_hash)
    # tst_condition = abs(avg_now - avg) < FEE_MAX_LIMIT
    # if not tst_condition:
    #     print(f'expected average {avg} != AverageBlockReward {avg_now} !!!')
    # assert tst_condition

    # print('✅✅✅ Reward Distribution Test Setup done')
    print('✅ Reward Distribution Test Setup done')

    return bl_hash


def transaction_fee_reward_test(substrate):
    print('---- transaction reward test!! ----')

    kp_src = Keypair.create_from_uri('//Alice')
    kp_bob = Keypair.create_from_uri('//Bob')
    kp_charlie = Keypair.create_from_uri('//Charlie')

    block_reward = _get_block_issue_reward(substrate)
    print(f'Current reward: {block_reward}')
    new_set_reward = 0
    setup_block_reward(substrate, kp_src, new_set_reward)

    time.sleep(WAIT_TIME_PERIOD)
    # TODO: See NOTE-1
    # prev_balance = get_account_balance(substrate, kp_src.ss58_address)
    receipt = transfer_with_tip(
        substrate, kp_bob, kp_charlie.ss58_address,
        1 * TOKEN_NUM_BASE, TIP, 1)

    _check_transaction_fee_reward_event(substrate, receipt.block_hash, TIP)
    time.sleep(WAIT_TIME_PERIOD)
    # TODO: See NOTE-1
    # _check_transaction_fee_reward_balance(substrate, kp_src.ss58_address, prev_balance, TIP)

    setup_block_reward(substrate, kp_src, block_reward)
    print('✅✅✅ transaction fee reward test pass')


# This test depends on the previous status, therefore, it's better to sleep about 3 blocks.
def block_reward_test(substrate):
    print('---- block reward test!! ----')

    kp_alice = Keypair.create_from_uri('//Alice')
    kp_bob = Keypair.create_from_uri('//Bob')
    ex_stack = ExtrinsicStack(substrate, kp_alice)

    # Extrinsic-stack: increment rewards & claim them
    ex_stack.compose_call("ParachainStaking",
                          "increment_collator_rewards", [])
    ex_stack.compose_call("ParachainStaking",
                          "claim_rewards", [])

    # Execute once at the beginning, to make sure all rewards have been
    # collected at the beginning of this test (more tests have been
    # run before) - but only if there are rewards to be claimed...
    bl_hash_alice_start = substrate.get_block_hash(None)
    bl_authd, bl_rewdd, _ = _get_block_status(
        substrate, kp_alice, bl_hash_alice_start)
    if bl_rewdd < bl_authd:
        bl_hash_alice_start = ex_stack.execute()

    bl_hash_bob_start = substrate.get_block_hash(None)
    bl_authd, bl_rewdd, _ = _get_block_status(
        substrate, kp_bob, bl_hash_bob_start)
    if bl_rewdd < bl_authd:
        bl_hash_bob_start = ex_stack.execute(kp_bob)

    # Debug: Double check that number of authored is equal to rewarded
    if DEBUG:
        bl_authd, bl_rewdd, rewards = _get_block_status(
            substrate, kp_alice, bl_hash_alice_start)
        if bl_authd != bl_rewdd:
            raise IOError(f'Alice: blocks authored ({bl_authd}) != \
                          rewarded ({bl_rewdd}), abort test')
        if rewards != 0:
            raise IOError(f'Alice rewards should be claimed ={rewards}')
        bl_authd, bl_rewdd, rewards = _get_block_status(
            substrate, kp_bob, bl_hash_bob_start)
        if bl_authd != bl_rewdd:
            raise IOError(f'Bob: blocks authored ({bl_authd}) != \
                          rewarded ({bl_rewdd}), abort test')
        if rewards != 0:
            raise IOError(f'Alice rewards should be claimed ={rewards}')

    # Now check the accounts at this moment
    bl_auth_alice_start = _get_blocks_rewarded(
        substrate, kp_alice.ss58_address, bl_hash_alice_start)
    bl_auth_bob_start = _get_blocks_rewarded(
        substrate, kp_bob.ss58_address, bl_hash_bob_start)
    
    # Now wait for round about 3 blocks to be finalized and run
    # extrinsics for both validators again
    print('Waiting for round about 3 blocks to be finalized...')
    time.sleep(WAIT_TIME_PERIOD)
    # Only increment rewards to check these without Tx-Fees
    ex_stack.stack.pop()
    bl_hash_alice_now = ex_stack.execute()
    bl_hash_bob_now = ex_stack.execute(kp_bob)

    # Check, blocks authored = blocks rewarded, and rewards != 0
    bl_auth_alice_now, bl_rewdd_alice, rewards_alice = _get_block_status(
        substrate, kp_alice, bl_hash_alice_now)
    bl_auth_bob_now, bl_rewdd_bob, rewards_bob = _get_block_status(
        substrate, kp_bob, bl_hash_bob_now)
    diff_bl_auth_alice = bl_auth_alice_now - bl_auth_alice_start
    diff_bl_auth_bob = bl_auth_bob_now - bl_auth_bob_start
    assert bl_auth_alice_now == bl_rewdd_alice
    if diff_bl_auth_alice > 0:
        assert rewards_alice != 0
    assert bl_auth_bob_now == bl_rewdd_bob
    if diff_bl_auth_bob > 0:
        assert rewards_bob != 0

    # Check collator-rewards in reward-register
    collator_rate = _get_collator_rate(substrate)
    bl_hash_before = _get_block_hash_before(substrate, bl_hash_alice_now)
    avg_bl_reward_alice = _get_average_block_reward(substrate, bl_hash_before)
    avg_cl_reward_alice = int(avg_bl_reward_alice * collator_rate)
    exp_rewards_alice = avg_cl_reward_alice * diff_bl_auth_alice
    bl_hash_before = _get_block_hash_before(substrate, bl_hash_bob_now)
    avg_bl_reward_bob = _get_average_block_reward(substrate, bl_hash_before)
    exp_rewards_bob = int(avg_bl_reward_bob * collator_rate) * diff_bl_auth_bob
    diff_alice = abs(rewards_alice - exp_rewards_alice) / exp_rewards_alice * 100
    diff_bob = abs(rewards_bob - exp_rewards_bob) / exp_rewards_bob * 100
    if DEBUG and (diff_alice > TOLERANCE_REWARDS_PERCENT):
        bl_nr_start = substrate.get_block_number(bl_hash_alice_start)
        bl_nr_stop = substrate.get_block_number(bl_hash_alice_now)
        print(f'Alice: Blocks authored {diff_bl_auth_alice} in range '
              + f'{bl_nr_start}-{bl_nr_stop}')
        print(f'Expected: {exp_rewards_alice}, Got: {rewards_alice}')
        print(f'Deviation Alice: {diff_alice:.2f}%')
        bl_nr_start = substrate.get_block_number(bl_hash_bob_start)
        bl_nr_stop = substrate.get_block_number(bl_hash_bob_now)
        print(f'Bob: Blocks authored {diff_bl_auth_alice} in range '
              + f'{bl_nr_start}-{bl_nr_stop}')
        print(f'Expected: {exp_rewards_bob}, Got: {rewards_bob}')
        print(f'Deviation Bob: {diff_bob:.2f}%')
        create_graph_on_storage(substrate, _get_average_block_reward,
                                bl_hash=bl_hash_alice_now)
    assert diff_alice <= TOLERANCE_REWARDS_PERCENT
    assert diff_bob <= TOLERANCE_REWARDS_PERCENT

    # Now claim rewards & compare balances
    ex_stack.clear()
    ex_stack.compose_call("ParachainStaking",
                          "claim_rewards", [])
    bl_hash_alice_now2 = ex_stack.execute()
    bl_hash_bob_now2 = ex_stack.execute(kp_bob)

    balance_alice_start = get_account_balance(
        substrate, kp_alice.ss58_address, bl_hash_alice_start)
    balance_bob_start = get_account_balance(
        substrate, kp_bob.ss58_address, bl_hash_bob_start)
    balance_alice_now = get_account_balance(
        substrate, kp_alice.ss58_address, bl_hash_alice_now2)
    balance_bob_now = get_account_balance(
        substrate, kp_bob.ss58_address, bl_hash_bob_now2)
    diff_balance_alice = balance_alice_now - balance_alice_start
    diff_balance_bob = balance_bob_now - balance_bob_start
    diff_alice = exp_rewards_alice - diff_balance_alice
    diff_bob = exp_rewards_bob - diff_balance_bob
    if DEBUG and (diff_alice > FEE_MAX_LIMIT):
        print(f'Balance Alice: expected({exp_rewards_alice}), got({diff_balance_alice})')
        print(f'Balance Bob: expected({exp_rewards_bob}), got({diff_balance_bob})')
    assert diff_alice <= CLAIM_REWARDS_FEE_MAX
    assert diff_bob <= CLAIM_REWARDS_FEE_MAX

    print('✅✅✅ block reward test pass')


def average_block_reward_test(substrate: SubstrateInterface):
    print('---- average block reward test!! ----')

    avg_bl_reward_start = _get_average_block_reward(substrate)

    # Wait a certain time, e.g. 3 blocks
    print('Waiting for round about 3 blocks to be finalized...')
    time.sleep(WAIT_TIME_PERIOD)

    # Check, that average-block-reward is unchanged
    avg_bl_reward_stop = _get_average_block_reward(substrate)

    diff = abs(avg_bl_reward_stop - avg_bl_reward_start)
    _debugprint(f'AverageBlockReward change: {diff}')

    # Here we should assert and just fail, but because this is a
    # non-trivial topic, we analyze it directly deeper and fail then
    if diff >= FEE_MAX_LIMIT:
        print('Test will fail, start deeper analysis')
        # Take care, that we don't start before block number 12
        print('Waiting for 10 blocks to be finalised...')
        bl_hsh = substrate.get_block_hash(None)
        bl_num = substrate.get_block_number(bl_hsh)
        bl_num_end = bl_num + 9
        while bl_num < bl_num_end:
            time.sleep(1)
            bl_hsh = substrate.get_block_hash(None)
            bl_num = substrate.get_block_number(bl_hsh)
        print(f'{bl_hsh} {type(bl_hsh)}')
        create_graph_on_storage(
            substrate, _get_average_block_reward, bl_hash=bl_hsh)
    assert diff < FEE_MAX_LIMIT

    print('✅✅✅ average block reward test pass')


def reward_distribution_test():
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            # Centralised test setup
            kp_alice = Keypair.create_from_uri('//Alice')
            reward_distribution_test_setup(substrate, kp_alice)
            # Run all the tests
            # average_block_reward_test(substrate)
            # block_reward_test(substrate)
            transaction_fee_reward_test(substrate)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running \
              'start_local_substrate_node.sh' first")
        sys.exit()

    except AssertionError:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        _, line, func, _ = tb_info[1]
        print(f'🔥 Test/{func}, Failed in line {line}')


if __name__ == '__main__':
    reward_distribution_test()
