
import sys
import time
import traceback
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

DEBUG = True


# Prints messages to terminal only when DEBUG=True
def _debugprint(msg: str):
    if DEBUG:
        print(msg)


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
    result = int(str(substrate.query(
        "ParachainStaking", "AverageBlockReward", block_hash=block_hash)))
    _debugprint(f'AverageBlockReward: {result} [{type(result)}]')
    return result


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


# def _get_staking_factor(substrate) -> float:
#     staking_factor = substrate.query(
#         'BlockReward', 'RewardDistributionConfigStorage')
#     staking_factor = staking_factor['collators_percent']
#     staking_factor = int(str(staking_factor))
#     staking_factor = staking_factor / pow(10, 9)
#     return staking_factor


# def _get_reward_rates(substrate):
#     _debugprint('---- Rewarding-Status ----')
#     staking_factor = _get_staking_factor(substrate)
#     block_reward = _get_block_issue_reward(substrate)
#     collator_rate = _get_collator_rate(substrate)
#     if not block_reward:
#         raise IOError('block reward should not be zero')
#     if not collator_rate:
#         raise IOError('could not determine collator-reward-rate')
#     if not staking_factor:
#         raise IOError('Staking percentage should not be zero')
#     staking_rewards = int(block_reward * staking_factor)
#     collator_rewards = int(staking_rewards * collator_rate)
#     _debugprint(f'BlockIssueReward: {block_reward} [{type(block_reward)}]')
#     _debugprint(f'StakingRate: {staking_factor} [{type(staking_factor)}]')
#     _debugprint(f'CollatorRate: {collator_rate} [{type(collator_rate)}]')
#     _debugprint('-- -- -- -- -- -- -- -- --')
#     _debugprint(f'StakingRewards: {staking_rewards} [{type(staking_rewards)}]')
#     _debugprint(f'CollatorRewards: {collator_rewards} [{type(collator_rewards)}]')
#     _debugprint('--------------------------')
#     return collator_rewards, staking_rewards


def block_reward_test_setup(substrate, kp_src):
    ex_stack = ExtrinsicStack(substrate, kp_src)
    issue_number = pow(10, 19)
    # Setup block issue number
    ex_stack.compose_sudo_call('BlockReward', 'set_block_issue_reward',
                               {'block_reward': issue_number})
    ex_stack.compose_sudo_call('ParachainStaking', 
                               'reset_average_reward_to', {"balance": 0})
    # ex_stack.execute_n_clear(wait_for_finalization=True)
    # Get current rates and reset average-reward-register
    # ex_stack.compose_sudo_call(
    #     "ParachainStaking", 'reset_average_reward_to', {"balance": 0})
    ex_stack.execute(wait_for_finalization=True)

    # Double check, that average-block-reward is correct
    avg_bl_reward = _get_average_block_reward(substrate)
    print(f'BlockIssueReward: {issue_number}, AverageBlockReward: {avg_bl_reward}')

    # collator_reward, staking_rewards = _get_reward_rates(substrate)
    # _debugprint(f'AvgBlReward {avg_bl_reward} == staking_rewards {staking_rewards}')
    # assert avg_bl_reward == staking_rewards
    
    # return collator_reward


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
    prev_balance = get_account_balance(substrate, kp_src.ss58_address)
    receipt = transfer_with_tip(
        substrate, kp_bob, kp_charlie.ss58_address,
        1 * TOKEN_NUM_BASE, TIP, 1)

    _check_transaction_fee_reward_event(substrate, receipt.block_hash, TIP)
    time.sleep(WAIT_TIME_PERIOD)
    _check_transaction_fee_reward_balance(substrate, kp_src.ss58_address, prev_balance, TIP)

    setup_block_reward(substrate, kp_src, block_reward)
    print('✅✅✅transaction fee reward test pass')


# This test depends on the previous status, therefore, it's better to sleep about 3 blocks.
def block_reward_test(substrate):
    print('---- block reward test!! ----')

    kp_alice = Keypair.create_from_uri('//Alice')
    kp_bob = Keypair.create_from_uri('//Bob')
    ex_stack = ExtrinsicStack(substrate, kp_alice)

    # Do tricky test setup (issue-number & average-reward-register)
    # collator_reward = block_reward_test_setup(substrate, kp_alice)
    block_reward_test_setup(substrate, kp_alice)

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
    avg_bl_reward_alice = _get_average_block_reward(substrate, bl_hash_alice_now)
    avg_cl_reward_alice = int(avg_bl_reward_alice * collator_rate)
    exp_rewards_alice = avg_cl_reward_alice * diff_bl_auth_alice
    avg_bl_reward = _get_average_block_reward(substrate, bl_hash_bob_now)
    exp_rewards_bob = int(avg_bl_reward * collator_rate) * diff_bl_auth_bob
    if DEBUG:
        bl_before = _get_block_hash_before(substrate, bl_hash_alice_now)
        bl_auth_alice_now2, bl_rewdd_alice2, rewards_alice2 = _get_block_status(
            substrate, kp_alice, bl_before)
        print(f'Before: {bl_auth_alice_now2}, {bl_rewdd_alice2}, {rewards_alice2}')
        print(f'Now: {bl_auth_alice_now}, {bl_rewdd_alice}, {rewards_alice}')
        print(f'{avg_bl_reward_alice} * {collator_rate} = {avg_cl_reward_alice}')

        bl_nr_start = substrate.get_block_number(bl_hash_alice_start)
        bl_nr_stop = substrate.get_block_number(bl_hash_alice_now)
        print(f'Alice: Blocks authored {diff_bl_auth_alice} in range '
              + f'{bl_nr_start}-{bl_nr_stop}')
        diff = abs(rewards_alice - exp_rewards_alice) / exp_rewards_alice * 100
        print(f'Expected: {exp_rewards_alice}, Got: {rewards_alice}')
        print(f'Deviation Alice: {diff:.2f}%')
        bl_nr_start = substrate.get_block_number(bl_hash_bob_start)
        bl_nr_stop = substrate.get_block_number(bl_hash_bob_now)
        print(f'Alice: Blocks authored {diff_bl_auth_alice} in range '
              + f'{bl_nr_start}-{bl_nr_stop}')
        diff = abs(rewards_bob - exp_rewards_bob) / exp_rewards_bob * 100
        print(f'Expected: {exp_rewards_bob}, Got: {rewards_bob}')
        print(f'Deviation Bob: {diff:.2f}%')
    assert exp_rewards_alice == rewards_alice
    assert exp_rewards_bob == rewards_bob

    # TODO
    # Now compare balances and blocks-authored
    # balance_alice_start = get_account_balance(
    #     substrate, kp_alice.ss58_address, bl_hash_alice_start)
    # balance_bob_start = get_account_balance(
    #     substrate, kp_bob.ss58_address, bl_hash_bob_start)
    # balance_alice_now = get_account_balance(
    #     substrate, kp_alice.ss58_address, bl_hash_alice_now)
    # balance_bob_now = get_account_balance(
    #     substrate, kp_bob.ss58_address, bl_hash_bob_now)
    # diff_balance_alice = balance_alice_now - balance_alice_start
    # diff_balance_bob = balance_bob_now - balance_bob_start
    # TODO remove
    # print(f'Alice: balance-start({balance_alice_start}), balance-now({balance_alice_now})')
    # print(f'Bob: balance-start({balance_bob_start}), balance-now({balance_bob_now})')

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


def average_block_reward_test(substrate):
    print('---- average block reward test!! ----')

    # Setup a block-issue-reward and reset average-block-reward
    kp_alice = Keypair.create_from_uri('//Alice')
    block_reward_test_setup(substrate, kp_alice)

    avg_bl_reward_start = _get_average_block_reward(substrate)

    # Wait a certain time, e.g. 3 blocks
    print('Waiting for round about 3 blocks to be finalized...')
    time.sleep(WAIT_TIME_PERIOD)

    # Check, that average-block-reward is unchanged
    avg_bl_reward_stop = _get_average_block_reward(substrate)

    diff = abs(avg_bl_reward_stop - avg_bl_reward_start)
    _debugprint(f'AverageBlockReward change: {diff}')
    assert diff < FEE_MAX_LIMIT

    print('✅✅✅ average block reward test pass')


def reward_distribution_test():
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            average_block_reward_test(substrate)
            block_reward_test(substrate)
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
