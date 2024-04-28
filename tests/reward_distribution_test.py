from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, TOKEN_NUM_BASE
from peaq.extrinsic import transfer_with_tip
from peaq.utils import get_account_balance
from tools.utils import KP_COLLATOR, KP_GLOBAL_SUDO, PARACHAIN_STAKING_POT
from tools.utils import get_existential_deposit, wait_for_event
from peaq.utils import ExtrinsicBatch
import unittest
from tests.utils_func import restart_parachain_and_runtime_upgrade

COLLATOR_REWARD_RATE = 0.1
REWARD_PERCENTAGE = 0.5
REWARD_ERROR = 0.0001
TIP = 10 ** 20
FEE_MIN_LIMIT = 30 * 10**9  # 30nPEAQ
FEE_MAX_LIMIT = 90 * 10**9  # 90nPEAQ


def batch_compose_block_reward(batch, block_reward):
    batch.compose_sudo_call(
        'BlockReward',
        'set_block_issue_reward',
        {
            'block_reward': block_reward
        }
    )


def batch_compose_reward_distribution(batch, collator_reward_rate):
    batch.compose_sudo_call(
        'BlockReward',
        'set_configuration',
        {
            'reward_distro_params': {
                'treasury_percent': 0,
                'depin_incentivization_percent': 0,
                'collators_delegators_percent': 1000000000 * collator_reward_rate,
                'depin_staking_percent': 0,
                'coretime_percent': 0,
                'subsidization_pool_percent': 1000000000 * (1 - collator_reward_rate),
            }
        }
    )


def batch_extend_max_supply(substrate, batch):
    total_issuance = substrate.query(
        module='Balances',
        storage_function='TotalIssuance',
    )
    batch.compose_sudo_call('BlockReward', 'set_max_currency_supply', {
        'limit': int(str(total_issuance)) * 3
    })


class TestRewardDistribution(unittest.TestCase):
    _kp_bob = Keypair.create_from_uri('//Bob')
    _kp_eve = Keypair.create_from_uri('//Eve')

    @classmethod
    def setUpClass(cls):
        restart_parachain_and_runtime_upgrade()

    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)

    def get_block_issue_reward(self):
        block_reward = self._substrate.query(
            module='BlockReward',
            storage_function='BlockIssueReward',
        )
        return int(str(block_reward))

    def get_parachain_reward(self, block_hash):
        event = None
        for event in self._substrate.get_events(block_hash):
            if event.value['module_id'] != 'ParachainStaking' or \
               event.value['event_id'] != 'Rewarded':
                continue
            event = event['event']
            break

        if not event:
            return None
        return int(str(event[1][1][1]))

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

    def _check_block_reward_in_event(self, kp_collator, block_reward):
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
        first_new_session_block_hash = self._substrate.get_block_hash(first_receipt.block_number + 1)
        second_new_session_block_hash = self._substrate.get_block_hash(second_receipt.block_number + 1)

        # Check the rewarded and pot balance
        rewarded_number = self.get_parachain_reward(second_new_session_block_hash)
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
        self.assertEqual(
            pot_transferable_balance,
            # transaction fee + tip + block reward
            int(int(transaction_fee * (1 + REWARD_PERCENTAGE)) * COLLATOR_REWARD_RATE) +
            int(transaction_tip * COLLATOR_REWARD_RATE) +
            int(block_reward * block_len * COLLATOR_REWARD_RATE)
        )

        # Check all collator reward in collators
        first_balance = get_account_balance(self._substrate, kp_collator.ss58_address, first_new_session_block_hash)
        second_balance = get_account_balance(self._substrate, kp_collator.ss58_address, second_new_session_block_hash)
        self.assertEqual(second_balance - first_balance, pot_transferable_balance)

    def test_block_reward(self):
        # Setup
        batch = ExtrinsicBatch(self._substrate, KP_GLOBAL_SUDO)
        batch_compose_block_reward(batch, 10000)
        batch_extend_max_supply(self._substrate, batch)
        batch_compose_reward_distribution(batch, COLLATOR_REWARD_RATE)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Cannot execute the block reward extrinsic {receipt}')

        # Execute
        # While we extend the max supply, the block reward should apply
        # Check
        block_reward = self.get_block_issue_reward()
        self.assertNotEqual(block_reward, 0, 'block reward should not be zero')

        self._check_block_reward_in_event(KP_COLLATOR, block_reward)
