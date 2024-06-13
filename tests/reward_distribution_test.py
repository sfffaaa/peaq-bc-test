from substrateinterface import SubstrateInterface, Keypair
from peaq.utils import get_chain
from tools.utils import WS_URL, TOKEN_NUM_BASE
from peaq.extrinsic import transfer_with_tip, transfer
from peaq.utils import get_account_balance
from tools.utils import get_event, get_modified_chain_spec
from tools.utils import KP_COLLATOR, KP_GLOBAL_SUDO, PARACHAIN_STAKING_POT
from tools.utils import get_existential_deposit, wait_for_event
from peaq.utils import ExtrinsicBatch
import unittest
import time

WAIT_ONLY_ONE_BLOCK_PERIOD = 12

EOT_FEE_PERCENTAGE = {
    'peaq-network': 0.0,
    'krest-network': 0.0,
    'peaq-dev': 0.0
}
TIP = 10 ** 20
FEE_CONFIG = {
    'peaq-network': {
        'min': 0.1 * 10 ** 15,
        'max': 10 * 10 ** 15,
    },
    'krest-network': {
        'min': 20 * 10 ** 9,
        'max': 90 * 10 ** 9,
    },
    'peaq-dev': {
        'min': 20 * 10 ** 9,
        'max': 90 * 10 ** 9,
    }
}

COLLATOR_DELEGATOR_POT = '5EYCAe5cKPAoFh2HnQQvpKqRYZGqBpaA87u4Zzw89qPE58is'
DIVISION_FACTOR = pow(10, 7)


class TestRewardDistribution(unittest.TestCase):
    _kp_bob = Keypair.create_from_uri('//Bob')
    _kp_eve = Keypair.create_from_uri('//Eve')

    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)
        self._chain_spec = get_chain(self._substrate)
        self._chain_spec = get_modified_chain_spec(self._chain_spec)
        self._fee_percentage = EOT_FEE_PERCENTAGE[self._chain_spec]
        self._collator_percentage = self._get_collator_delegator_precentage()
        while self._substrate.get_block()['header']['number'] == 0:
            time.sleep(WAIT_ONLY_ONE_BLOCK_PERIOD)

    def _get_collator_delegator_precentage(self):
        reward_config = self._substrate.query(
            module='BlockReward',
            storage_function='RewardDistributionConfigStorage',
        )
        collator_number = ((reward_config['collators_delegators_percent']).decode()) / DIVISION_FACTOR
        return collator_number / 100

    def _get_parachain_reward(self, block_hash):
        result = get_event(
            self._substrate,
            block_hash,
            'ParachainStaking', 'Rewarded')
        self.assertIsNotNone(result, 'Rewarded event not found')
        return result.value['attributes'][1]

    def _get_block_issue_reward(self):
        result = get_event(
            self._substrate,
            self._substrate.get_block_hash(),
            'BlockReward', 'BlockRewardsDistributed')
        self.assertIsNotNone(result, 'BlockReward event not found')
        return result.value['attributes']

    def _get_transaction_fee_paid(self, block_hash, fee_type):
        amount = 0
        for event in self._substrate.get_events(block_hash):
            if event.value['module_id'] != 'TransactionPayment' or \
               event.value['event_id'] != 'TransactionFeePaid':
                continue
            if fee_type == 'fee':
                amount += event['event'][1][1].value['actual_fee'] - event['event'][1][1].value['tip']
            elif fee_type == 'tip':
                amount += event['event'][1][1].value['tip']
            else:
                raise IOError('Unknown fee type')
        return amount

    def _check_block_reward_in_event(self, kp_collator, first_receipt, second_receipt, tx_receipt):
        first_new_session_block_hash = self._substrate.get_block_hash(first_receipt.block_number + 1)
        second_new_session_block_hash = self._substrate.get_block_hash(second_receipt.block_number + 1)

        # Check the rewarded and pot balance
        rewarded_number = self._get_parachain_reward(second_new_session_block_hash)
        self.assertNotEqual(rewarded_number, None, 'cannot find the rewarded event')

        pot_transferable_balance = \
            get_account_balance(self._substrate, PARACHAIN_STAKING_POT, second_receipt.block_hash) - \
            get_existential_deposit(self._substrate)

        self.assertEqual(rewarded_number, pot_transferable_balance)

        # Check the block reward + transaction fee (Need to check again...)
        transaction_fee, transaction_tip = 0, 0
        for block_hash in [tx_receipt.block_hash, second_receipt.block_hash]:
            transaction_fee += self._get_transaction_fee_paid(block_hash, 'fee')
            transaction_tip += self._get_transaction_fee_paid(block_hash, 'tip')
        self.assertNotEqual(transaction_fee, 0, 'cannot find the transaction fee event')
        self.assertNotEqual(transaction_tip, 0, 'cannot find the transaction tip event')
        block_len = (second_receipt.block_number + 1) - (first_receipt.block_number + 1)
        block_reward = self._get_block_issue_reward()

        expected_reward = int(int(transaction_fee * (1 + self._fee_percentage)) * self._collator_percentage) + \
            int(transaction_tip * self._collator_percentage) + \
            int(block_reward * block_len * self._collator_percentage)
        print(f'Expected reward: {expected_reward}')
        print(f'Pot transferable balance: {pot_transferable_balance}')
        self.assertAlmostEqual(
            expected_reward * 1.0 / pot_transferable_balance,
            1, 7,
            f'The block reward {expected_reward} is not the same as {pot_transferable_balance} ')

        # Check all collator reward in collators
        first_balance = get_account_balance(self._substrate, kp_collator.ss58_address, first_new_session_block_hash)
        second_balance = get_account_balance(self._substrate, kp_collator.ss58_address, second_new_session_block_hash)
        self.assertEqual(second_balance - first_balance, pot_transferable_balance)

    def _check_transaction_fee_reward_from_sender(self, block_height):
        block_hash = self._substrate.get_block_hash(block_height)
        tx_reward = self._get_transaction_fee_distributed(block_hash)
        self.assertNotEqual(
            tx_reward, None,
            f'Cannot find the block event for transaction reward {tx_reward}')
        tx_fee_ori = self._get_transaction_fee_paid(block_hash, 'fee') + \
            self._get_transaction_fee_paid(block_hash, 'tip')
        self.assertNotEqual(
            tx_fee_ori, None,
            f'Cannot find the block event for transaction reward {tx_fee_ori}')

        self.assertEqual(
            int(tx_reward), int(tx_fee_ori * (1 + self._fee_percentage)),
            f'The transaction fee reward is not correct {tx_fee_ori} v.s. {tx_fee_ori * (1 + self._fee_percentage)}')

    def _get_withdraw_events(self, block_hash, dest):
        events = []
        for event in self._substrate.get_events(block_hash):
            if event.value['module_id'] != 'Balances' or \
               event.value['event_id'] != 'Deposit':
                continue
            if str(event['event'][1][1]['who']) == dest:
                events.append(event['event'][1][1]['amount'].value)
        return events

    def _check_transaction_fee_reward_from_collator(self, block_height):
        block_hash = self._substrate.get_block_hash(block_height)
        tx_reward = self._get_transaction_fee_distributed(block_hash)
        self.assertNotEqual(
            tx_reward, None,
            f'Cannot find the block event for transaction reward {tx_reward}')

        # The latest one is for the transaction withdraw
        events = self._get_withdraw_events(block_hash, COLLATOR_DELEGATOR_POT)

        self.assertAlmostEqual(
            tx_reward * self._collator_percentage / events[-1],
            1, 7,
            f'The transaction fee reward is not correct {events[-1]} v.s. {tx_reward} * {self._collator_percentage}')

    def _check_tx_fee(self, fee):
        fee_min_limit = FEE_CONFIG[self._chain_spec]['min']
        fee_max_limit = FEE_CONFIG[self._chain_spec]['max']
        self.assertGreaterEqual(
            fee, fee_min_limit,
            f'The transaction fee w/o tip is out of limit: {fee} > {fee_min_limit}')
        self.assertLessEqual(
            fee, fee_max_limit,
            f'The transaction fee w/o tip is out of limit: {fee} < {fee_max_limit}')

    def _get_transaction_fee_distributed(self, block_hash):
        result = get_event(
            self._substrate,
            self._substrate.get_block_hash(),
            'BlockReward', 'TransactionFeesDistributed')
        self.assertIsNotNone(result, 'TransactionFeesDistributed event not found')
        return result.value['attributes']

    def test_block_reward(self):
        # Execute
        batch = ExtrinsicBatch(self._substrate, KP_GLOBAL_SUDO)
        batch.compose_sudo_call(
            'ParachainStaking',
            'force_new_round',
            {}
        )
        first_receipt = batch.execute()
        self.assertTrue(first_receipt.is_success)
        tx_receipt = transfer_with_tip(
            self._substrate, self._kp_bob, self._kp_eve.ss58_address,
            1 * TOKEN_NUM_BASE, TIP, 1)
        self.assertTrue(tx_receipt.is_success, f'Failed to transfer: {tx_receipt.error_message}')

        second_receipt = batch.execute()
        self.assertTrue(second_receipt.is_success)
        wait_for_event(self._substrate, 'ParachainStaking', 'Rewarded', {})

        self._check_block_reward_in_event(KP_COLLATOR, first_receipt, second_receipt, tx_receipt)

    def test_transaction_fee_reward_v2(self):
        # Execute
        # Note, the Collator maybe collected by another one
        receipt = transfer(
            self._substrate, self._kp_bob, self._kp_eve.ss58_address, 0)
        self.assertTrue(receipt.is_success, f'Failed to transfer: {receipt.error_message}')
        print(f'Block hash: {receipt.block_hash}')
        block_number = self._substrate.get_block(receipt.block_hash)['header']['number']

        self._check_transaction_fee_reward_from_sender(block_number)
        self._check_transaction_fee_reward_from_collator(block_number)

    def test_transaction_fee_reward(self):
        # Execute
        receipt = transfer_with_tip(
            self._substrate, self._kp_bob, self._kp_eve.ss58_address,
            1 * TOKEN_NUM_BASE, TIP, 1)
        self.assertTrue(receipt.is_success, f'Failed to transfer: {receipt.error_message}')
        print(f'Block hash: {receipt.block_hash}')

        # Check
        fee = self._get_transaction_fee_paid(receipt.block_hash, 'fee')
        self.assertNotEqual(fee, None, f'Cannot find the block event for transaction reward {fee}')

        self._check_tx_fee(fee)
