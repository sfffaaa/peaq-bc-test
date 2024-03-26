import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from tools.utils import set_max_currency_supply, set_block_reward_configuration
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

        time.sleep(WAIT_TIME_PERIOD)

        for event in self.substrate.get_events():
            if event.value['module_id'] != 'ParachainStaking' or \
               event.value['event_id'] != 'Rewarded':
                continue
            now_reward = event['event'][1][1][1]
            self.assertEqual(int(str(now_reward)), 0)

        # reset
        receipt = set_max_currency_supply(self.substrate, max_currency_supply)
        self.assertTrue(receipt.is_success, f'cannot setup the receipt: {receipt.error_message}')
