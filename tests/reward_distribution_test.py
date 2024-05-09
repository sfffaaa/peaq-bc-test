import time
import pytest

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, TOKEN_NUM_BASE
from peaq.extrinsic import transfer, transfer_with_tip
from peaq.utils import get_account_balance
from tools.utils import get_event
from tools.utils import KP_COLLATOR
import unittest
# from tests.utils_func import restart_parachain_and_runtime_upgrade
from tests import utils_func as TestUtils

WAIT_BLOCK_NUMBER = 10
WAIT_ONLY_ONE_BLOCK_PERIOD = 12
REWARD_PERCENTAGE = 0.5
REWARD_ERROR = 0.0001
TIP = 10 ** 20
FEE_MIN_LIMIT = 30 * 10**9  # 30nPEAQ
FEE_MAX_LIMIT = 90 * 10**9  # 90nPEAQ

COLLATOR_DELEGATOR_POT = '5EYCAe5cKPAoFh2HnQQvpKqRYZGqBpaA87u4Zzw89qPE58is'
DIVISION_FACTOR = pow(10, 7)


class TestRewardDistribution(unittest.TestCase):
    _kp_bob = Keypair.create_from_uri('//Bob')
    _kp_eve = Keypair.create_from_uri('//Eve')

    # @classmethod
    # def setUpClass(cls):
    #     restart_parachain_and_runtime_upgrade()

    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)

    def get_collator_delegator_precentage(self):
        reward_config = self._substrate.query(
            module='BlockReward',
            storage_function='RewardDistributionConfigStorage',
        )
        collator_number = ((reward_config['collators_delegators_percent']).decode()) / DIVISION_FACTOR
        return collator_number / 100

    def get_block_issue_reward(self):
        result = get_event(
            self._substrate,
            self._substrate.get_block_hash(),
            'BlockReward', 'BlockRewardsDistributed')
        self.assertIsNotNone(result, 'BlockReward event not found')
        return result.value['attributes']

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

    def _get_withdraw_events(self, block_hash, dest):
        events = []
        for event in self._substrate.get_events(block_hash):
            if event.value['module_id'] != 'Balances' or \
               event.value['event_id'] != 'Deposit':
                continue
            if str(event['event'][1][1]['who']) == dest:
                events.append(event['event'][1][1]['amount'].value)
        return events

    def _check_transaction_fee_reward_from_collator(self, block_height, collator_percentage):
        block_hash = self._substrate.get_block_hash(block_height)
        tx_reward = self.get_transaction_fee_distributed(block_hash)
        self.assertNotEqual(
            tx_reward, None,
            f'Cannot find the block event for transaction reward {tx_reward}')

        # The latest one is for the transaction withdraw
        events = self._get_withdraw_events(block_hash, COLLATOR_DELEGATOR_POT)

        self.assertAlmostEqual(
            tx_reward * collator_percentage / events[-1],
            1, 7,
            f'The transaction fee reward is not correct {events[-1]} v.s. {tx_reward} * {collator_percentage}')

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
    def _check_transaction_fee_reward_balance(self, addr, prev_balance, now_balance, tip, block_reward, collator_percentage):
        # real_rate = (now_balance - prev_balance) / (tip * COLLATOR_REWARD_RATE) - 1
        # if real_rate > REWARD_PERCENTAGE + REWARD_ERROR or real_rate < REWARD_PERCENTAGE - REWARD_ERROR:
        #     raise IOError(f'The balance is strange {real_rate} v.s. {REWARD_PERCENTAGE}')
        rewards_wo_tip = (now_balance - prev_balance - tip * collator_percentage - block_reward * collator_percentage) / collator_percentage
        self.assertGreaterEqual(
            rewards_wo_tip, FEE_MIN_LIMIT,
            f'The transaction fee w/o tip is out of limit: {rewards_wo_tip} > {FEE_MIN_LIMIT}')
        self.assertLessEqual(
            rewards_wo_tip, FEE_MAX_LIMIT,
            f'The transaction fee w/o tip is out of limit: {rewards_wo_tip} < {FEE_MAX_LIMIT}')

    def _check_block_reward_in_event(self, kp_src, block_reward, collator_percentage):
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
            event = self._get_event(now_hash, 'Balances', 'Transfer')
            if event is None or str(event[1][1]['to']) != kp_src.ss58_address:
                print(f'The event is {event}, or the receiver is not {kp_src.ss58_address}')
                time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)
                continue

            now_balance = get_account_balance(self._substrate, kp_src.ss58_address, block_hash=now_hash)
            previous_balance = get_account_balance(self._substrate, kp_src.ss58_address, block_hash=prev_hash)
            self.assertEqual(now_balance - previous_balance, block_reward * collator_percentage,
                             f'The block reward {now_balance - previous_balance} is '
                             f'not the same as {block_reward * collator_percentage}')
            return True
        return False

    def test_block_reward(self):
        # Setup
        collator_percentage = self.get_collator_delegator_precentage()
        print(f'Collator percentage: {collator_percentage}')
        while self._substrate.get_block()['header']['number'] == 0:
            time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

        # Execute
        # While we extend the max supply, the block reward should apply
        # Check
        block_reward = self.get_block_issue_reward()
        self.assertNotEqual(block_reward, 0, 'block reward should not be zero')

        time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

        self.assertTrue(
            self._check_block_reward_in_event(KP_COLLATOR, block_reward, collator_percentage),
            'Did not find the block reward event')

    def test_transaction_fee_reward_v1(self):
        kp_bob = self._kp_bob
        kp_eve = self._kp_eve

        # setup
        collator_percentage = self.get_collator_delegator_precentage()
        while self._substrate.get_block()['header']['number'] == 0:
            time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

        # Execute
        # Note, the Collator maybe collected by another one
        receipt = transfer(
            self._substrate, kp_bob, kp_eve.ss58_address, 0)
        self.assertTrue(receipt.is_success, f'Failed to transfer: {receipt.error_message}')
        print(f'Block hash: {receipt.block_hash}')
        block_number = self._substrate.get_block(receipt.block_hash)['header']['number']
        self._check_transaction_fee_reward_from_sender(block_number)
        self._check_transaction_fee_reward_from_collator(block_number, collator_percentage)

    @pytest.mark.skipif(TestUtils.is_runtime_upgrade_test() is True, reason='Skip for runtime upgrade test')
    def test_transaction_fee_reward(self):
        kp_bob = self._kp_bob
        kp_eve = self._kp_eve

        # setup
        collator_percentage = self.get_collator_delegator_precentage()
        while self._substrate.get_block()['header']['number'] == 0:
            time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

        block_reward = self.get_block_issue_reward()
        print(f'Current reward: {block_reward}')

        # Execute
        receipt = transfer_with_tip(
            self._substrate, kp_bob, kp_eve.ss58_address,
            1 * TOKEN_NUM_BASE, TIP, 1)
        self.assertTrue(receipt.is_success, f'Failed to transfer: {receipt.error_message}')
        print(f'Block hash: {receipt.block_hash}')

        # Check
        self._check_transaction_fee_reward_event(receipt.block_hash, TIP)
        next_height = self._substrate.get_block(receipt.block_hash)['header']['number'] + 1
        while self._substrate.get_block()['header']['number'] < next_height:
            time.sleep(12)
        prev_balance = get_account_balance(self._substrate, KP_COLLATOR.ss58_address, block_hash=receipt.block_hash)

        now_block_hash = self._substrate.get_block_hash(next_height)
        now_balance = get_account_balance(self._substrate, KP_COLLATOR.ss58_address, block_hash=now_block_hash)

        self._check_transaction_fee_reward_balance(
            KP_COLLATOR.ss58_address, prev_balance, now_balance, TIP, block_reward, collator_percentage)
