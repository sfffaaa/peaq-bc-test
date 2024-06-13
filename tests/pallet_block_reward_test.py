from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from tools.utils import set_block_reward_configuration
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
