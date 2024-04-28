import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from tools.utils import set_max_currency_supply, set_block_reward_configuration, get_existential_deposit
from peaq.utils import ExtrinsicBatch, get_account_balance
from tools.utils import KP_GLOBAL_SUDO, PARACHAIN_STAKING_POT
import unittest

COLLATOR_REWARD_RATE = 0.1
WAIT_TIME_PERIOD = 12 * 3


class TestPalletBlockReward(unittest.TestCase):

    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL)
        self.kp_src = Keypair.create_from_uri('//Alice')

    def test_config(self):
        set_value = {
            'treasury_percent': 10000000,
            'depin_incentivization_percent': 20000000,
            'collators_delegators_percent': 30000000,
            'depin_staking_percent': 40000000,
            'coretime_percent': 50000000,
            'subsidization_pool_percent': 850000000,
        }
        previous_value = self.substrate.query(
            module='BlockReward',
            storage_function='RewardDistributionConfigStorage',
        )
        receipt = set_block_reward_configuration(self.substrate, set_value)
        self.assertTrue(receipt.is_success,
                        'cannot setup the block reward configuration')
        now_value = self.substrate.query(
            module='BlockReward',
            storage_function='RewardDistributionConfigStorage',
        )
        self.assertEqual(set_value, now_value)

        # TODO: dependency... If error occurs, it will not be reset.
        # Reset
        recepit = set_block_reward_configuration(
            self.substrate,
            {k: int(str(previous_value[k])) for k in set_value.keys()})
        self.assertTrue(recepit.is_success,
                        'cannot setup the block reward configuration')

    def test_over_max_currency_supply(self):
        max_currency_supply = self.substrate.query(
            module='BlockReward',
            storage_function='MaxCurrencySupply',
        )
        print(f'Current max-currency-supply: {max_currency_supply}')
        new_max_currency_supply = 500

        receipt = set_max_currency_supply(self.substrate, new_max_currency_supply)
        self.assertTrue(receipt.is_success, f'cannot setup the receipt: {receipt.error_message}')

        batch = ExtrinsicBatch(self.substrate, KP_GLOBAL_SUDO)
        batch.compose_sudo_call(
            'ParachainStaking',
            'force_new_round',
            {}
        )
        receipt = batch.execute()
        self.assertTrue(receipt.is_success)

        receipt = batch.execute()
        self.assertTrue(receipt.is_success)

        transferable_balance = \
            get_account_balance(self.substrate, PARACHAIN_STAKING_POT, receipt.block_hash) - \
            get_existential_deposit(self.substrate)

        time.sleep(12 * 2)
        next_block_hash = self.substrate.get_block_hash(receipt.block_number + 1)

        for event in self.substrate.get_events(next_block_hash):
            if event.value['module_id'] != 'ParachainStaking' or \
               event.value['event_id'] != 'Rewarded':
                continue
            now_reward = event['event'][1][1][1]
            self.assertEqual(now_reward, transferable_balance)

        # TODO: dependency... If error occurs, it will not be reset.
        # reset
        receipt = set_max_currency_supply(self.substrate, max_currency_supply)
        self.assertTrue(receipt.is_success, f'cannot setup the receipt: {receipt.error_message}')
