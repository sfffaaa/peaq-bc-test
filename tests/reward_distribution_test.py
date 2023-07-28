import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, transfer_with_tip, TOKEN_NUM_BASE, get_account_balance
from tools.utils import set_max_currency_supply, setup_block_reward
import unittest

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

    _kp_src = Keypair.create_from_uri('//Alice')
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

    def get_transaction_fee_distributed(self, block_hash):
        for event in self._substrate.get_events(block_hash):
            if event.value['module_id'] != 'BlockReward' or \
               event.value['event_id'] != 'TransactionFeesDistributed':
                continue
            return int(str(event['event'][1][1]))
        return None

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

    def _extend_max_supply(self, substrate, sudo_key):
        total_issuance = substrate.query(
            module='Balances',
            storage_function='TotalIssuance',
        )
        receipt = set_max_currency_supply(substrate, sudo_key, int(str(total_issuance)) * 3)
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
        kp_src = self._kp_src

        # Setup
        receipt = setup_block_reward(self._substrate, kp_src, 10000)
        self.assertTrue(receipt.is_success, f'Failed to set block reward: {receipt.error_message}')
        receipt = self._extend_max_supply(self._substrate, kp_src)
        self.assertTrue(receipt.is_success, f'Failed to extend max supply: {receipt.error_message}')

        # Execute
        # While we extend the max supply, the block reward should apply
        # Check
        block_reward = self.get_block_issue_reward()
        self.assertNotEqual(block_reward, 0, 'block reward should not be zero')

        time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

        self.assertTrue(self._check_block_reward_in_event(kp_src, block_reward), 'Did not find the block reward event')

    def test_transaction_fee_reward(self):
        kp_src = self._kp_src
        kp_bob = self._kp_bob
        kp_charlie = self._kp_charlie

        # setup
        receipt = self._extend_max_supply(self._substrate, kp_src)
        self.assertTrue(receipt.is_success, f'Failed to extend max supply: {receipt.error_message}')

        block_reward = self.get_block_issue_reward()
        print(f'Current reward: {block_reward}')
        new_set_reward = 0
        receipt = setup_block_reward(self._substrate, kp_src, new_set_reward)
        self.assertTrue(receipt.is_success, f'Failed to set block reward: {receipt.error_message}')

        time.sleep(WAIT_TIME_PERIOD)
        prev_balance = get_account_balance(self._substrate, kp_src.ss58_address)

        # Execute
        receipt = transfer_with_tip(
            self._substrate, kp_bob, kp_charlie.ss58_address,
            1 * TOKEN_NUM_BASE, TIP, 1)
        print(f'Block hash: {receipt.block_hash}')

        # Check
        self._check_transaction_fee_reward_event(receipt.block_hash, TIP)
        time.sleep(WAIT_TIME_PERIOD)
        self._check_transaction_fee_reward_balance(kp_src.ss58_address, prev_balance, TIP)

        # Reset
        receipt = setup_block_reward(self._substrate, kp_src, block_reward)
        self.assertTrue(receipt.is_success, f'Failed to set block reward: {receipt.error_message}')
