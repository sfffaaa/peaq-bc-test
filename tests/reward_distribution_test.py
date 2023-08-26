import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, transfer_with_tip, TOKEN_NUM_BASE, get_account_balance, transfer
from tools.utils import set_max_currency_supply, setup_block_reward
from tools.utils import KP_COLLATOR
import unittest
import pytest

WAIT_BLOCK_NUMBER = 10
COLLATOR_REWARD_RATE = 0.1
WAIT_ONLY_ONE_BLOCK_PERIOD = 12
WAIT_TIME_PERIOD = WAIT_ONLY_ONE_BLOCK_PERIOD * 3
REWARD_PERCENTAGE = 0.5
REWARD_ERROR = 0.0001
TIP = 10 ** 20
FEE_MIN_LIMIT = 30 * 10**9  # 30nPEAQ
FEE_MAX_LIMIT = 90 * 10**9  # 90nPEAQ


class TestRewardDistribution(unittest.TestCase):
    _kp_bob = Keypair.create_from_uri('//Bob')
    _kp_charlie = Keypair.create_from_uri('//Charlie')

    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)

    def get_block_issue_reward(self):
        block_reward = self._substrate.query(
            module='BlockReward',
            storage_function='BlockIssueReward',
        )
        return int(str(block_reward))

    def get_parachain_reward(self, block_hash):
        event = self._get_event(block_hash, 'ParachainStaking', 'Rewarded')
        if not event:
            return None
        return int(str(event[1][1][1]))

    def get_transaction_payment_fee_paid(self, block_hash):
        event = self._get_event(block_hash, 'TransactionPayment', 'TransactionFeePaid')
        if not event:
            return None
        return int(str(event[1][1]['actual_fee']))

    def get_transaction_fee_distributed(self, block_hash):
        event = self._get_event(block_hash, 'BlockReward', 'TransactionFeesDistributed')
        if not event:
            return None
        return int(str(event[1][1]))

    def _get_event(self, block_hash, pallet, event_name):
        for event in self._substrate.get_events(block_hash):
            if event.value['module_id'] != pallet or \
               event.value['event_id'] != event_name:
                continue
            return event['event']
        return None

    def _check_transaction_fee_reward_from_sender(self, block_height):
        block_hash = self._substrate.get_block_hash(block_height)
        tx_reward = self.get_transaction_fee_distributed(block_hash)
        self.assertNotEqual(
            tx_reward, None,
            f'Cannot find the block event for transaction reward {tx_reward}')
        tx_fee_ori = self.get_transaction_payment_fee_paid(block_hash)
        self.assertNotEqual(
            tx_fee_ori, None,
            f'Cannot find the block event for transaction reward {tx_fee_ori}')

        self.assertEqual(
            int(tx_reward), int(tx_fee_ori * (1 + REWARD_PERCENTAGE)),
            f'The transaction fee reward is not correct {tx_fee_ori} v.s. {tx_fee_ori * (1 + REWARD_PERCENTAGE)}')

    def _check_transaction_fee_reward_from_collator(self, block_height):
        block_hash = self._substrate.get_block_hash(block_height)
        tx_reward = self.get_transaction_fee_distributed(block_hash)
        self.assertNotEqual(
            tx_reward, None,
            f'Cannot find the block event for transaction reward {tx_reward}')
        if self._substrate.get_block()['header']['number'] != block_height + 1:
            time.sleep(12)

        next_block_hash = self._substrate.get_block_hash(block_height + 1)
        next_reward = self.get_parachain_reward(next_block_hash)
        self.assertNotEqual(
            next_reward, None,
            f'Cannot find the block event for transaction reward {next_reward}')
        print(f'tx_reward: {tx_reward}, next_reward: {next_reward}, out: {tx_reward * COLLATOR_REWARD_RATE / next_reward}')
        self.assertAlmostEquals(
            tx_reward * COLLATOR_REWARD_RATE / next_reward,
            1, 7,
            f'The transaction fee reward is not correct {next_reward} v.s. {tx_reward}')

    # TODO: improve testing fees, by using fee-model, when ready...
    def _check_transaction_fee_reward_event(self, block_hash, tip):
        now_reward = self.get_transaction_fee_distributed(block_hash)
        self.assertNotEqual(now_reward, None, f'Cannot find the block event for transaction reward {now_reward}')

        # real_rate = (now_reward - tip) / tip
        fee_wo_tip = now_reward - tip
        # if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
        # raise IOError(f'The fee reward percentage is strange {real_rate} v.s. {REWARD_PERCENTAGE}')
        self.assertGreaterEqual(
            fee_wo_tip, FEE_MIN_LIMIT,
            f'The transaction fee w/o tip is out of limit: {fee_wo_tip} > {FEE_MIN_LIMIT}')

        self.assertLessEqual(
            fee_wo_tip, FEE_MAX_LIMIT,
            f'The transaction fee w/o tip is out of limit: {fee_wo_tip} < {FEE_MAX_LIMIT}')

    # TODO: improve testing fees, by using fee-model, when ready
    def _check_transaction_fee_reward_balance(self, addr, prev_balance, tip):
        now_balance = get_account_balance(self._substrate, addr)
        # real_rate = (now_balance - prev_balance) / (tip * COLLATOR_REWARD_RATE) - 1
        # if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
        #     raise IOError(f'The balance is strange {real_rate} v.s. {REWARD_PERCENTAGE}')
        rewards_wo_tip = (now_balance - prev_balance - tip * COLLATOR_REWARD_RATE) / COLLATOR_REWARD_RATE
        self.assertGreaterEqual(
            rewards_wo_tip, FEE_MIN_LIMIT,
            f'The transaction fee w/o tip is out of limit: {rewards_wo_tip} > {FEE_MIN_LIMIT}')
        self.assertLessEqual(
            rewards_wo_tip, FEE_MAX_LIMIT,
            f'The transaction fee w/o tip is out of limit: {rewards_wo_tip} < {FEE_MAX_LIMIT}')

    def _extend_max_supply(self, substrate):
        total_issuance = substrate.query(
            module='Balances',
            storage_function='TotalIssuance',
        )
        receipt = set_max_currency_supply(substrate, int(str(total_issuance)) * 3)
        return receipt

    def _check_block_reward_in_event(self, kp_src, block_reward):
        for i in range(0, WAIT_BLOCK_NUMBER):
            block_info = self._substrate.get_block_header()
            now_hash = block_info['header']['hash']
            prev_hash = block_info['header']['parentHash']
            extrinsic = self._substrate.get_block(prev_hash)['extrinsics']

            self.assertNotEqual(len(extrinsic), 0, 'Extrinsic list shouldn\'t be zero, maybe in the genesis block')
            # The fee of extrinsic in the previous block becomes the reward of this block,
            # but we have three default extrinisc
            #   timestamp.set
            #   dynamicFee.noteMinGasPriceTarget
            #   parachainSystem.setValidationData)
            if len(self._substrate.get_block(prev_hash)['extrinsics']) != 3:
                time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)
                continue

            now_balance = get_account_balance(self._substrate, kp_src.ss58_address, block_hash=now_hash)
            previous_balance = get_account_balance(self._substrate, kp_src.ss58_address, block_hash=prev_hash)
            self.assertEqual(now_balance - previous_balance, block_reward * COLLATOR_REWARD_RATE,
                             f'The block reward {now_balance - previous_balance} is '
                             f'not the same as {block_reward * COLLATOR_REWARD_RATE}')
            return True
        return False

    def test_block_reward(self):
        # Setup
        receipt = setup_block_reward(self._substrate, 10000)
        self.assertTrue(receipt.is_success, f'Failed to set block reward: {receipt.error_message}')
        receipt = self._extend_max_supply(self._substrate)
        self.assertTrue(receipt.is_success, f'Failed to extend max supply: {receipt.error_message}')

        # Execute
        # While we extend the max supply, the block reward should apply
        # Check
        block_reward = self.get_block_issue_reward()
        self.assertNotEqual(block_reward, 0, 'block reward should not be zero')

        time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

        self.assertTrue(
            self._check_block_reward_in_event(KP_COLLATOR, block_reward), 'Did not find the block reward event')

    def test_transaction_fee_reward_v1(self):
        kp_bob = self._kp_bob
        kp_charlie = self._kp_charlie

        # setup
        receipt = self._extend_max_supply(self._substrate)
        self.assertTrue(receipt.is_success, f'Failed to extend max supply: {receipt.error_message}')

        block_reward = self.get_block_issue_reward()
        print(f'Current reward: {block_reward}')
        new_set_reward = 0
        receipt = setup_block_reward(self._substrate, new_set_reward)
        self.assertTrue(receipt.is_success, f'Failed to set block reward: {receipt.error_message}')

        time.sleep(WAIT_TIME_PERIOD)

        # Execute
        receipt = transfer(
            self._substrate, kp_bob, kp_charlie.ss58_address, 0)
        self.assertTrue(receipt.is_success, f'Failed to transfer: {receipt.error_message}')
        print(f'Block hash: {receipt.block_hash}')
        self._check_transaction_fee_reward_from_sender(receipt.block_number)
        self._check_transaction_fee_reward_from_collator(receipt.block_number)

        # Reset
        receipt = setup_block_reward(self._substrate, block_reward)
        self.assertTrue(receipt.is_success, f'Failed to set block reward: {receipt.error_message}')

    def test_transaction_fee_reward(self):
        kp_bob = self._kp_bob
        kp_charlie = self._kp_charlie

        # setup
        receipt = self._extend_max_supply(self._substrate)
        self.assertTrue(receipt.is_success, f'Failed to extend max supply: {receipt.error_message}')

        block_reward = self.get_block_issue_reward()
        print(f'Current reward: {block_reward}')
        new_set_reward = 0
        receipt = setup_block_reward(self._substrate, new_set_reward)
        self.assertTrue(receipt.is_success, f'Failed to set block reward: {receipt.error_message}')

        time.sleep(WAIT_TIME_PERIOD)
        prev_balance = get_account_balance(self._substrate, KP_COLLATOR.ss58_address)

        # Execute
        receipt = transfer_with_tip(
            self._substrate, kp_bob, kp_charlie.ss58_address,
            1 * TOKEN_NUM_BASE, TIP, 1)
        self.assertTrue(receipt.is_success, f'Failed to transfer: {receipt.error_message}')
        print(f'Block hash: {receipt.block_hash}')

        # Check
        self._check_transaction_fee_reward_event(receipt.block_hash, TIP)
        time.sleep(WAIT_TIME_PERIOD)
        self._check_transaction_fee_reward_balance(
            KP_COLLATOR.ss58_address, prev_balance, TIP)

        # Reset
        receipt = setup_block_reward(self._substrate, block_reward)
        self.assertTrue(receipt.is_success, f'Failed to set block reward: {receipt.error_message}')
