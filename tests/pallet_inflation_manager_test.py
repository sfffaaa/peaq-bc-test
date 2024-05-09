import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
# from tools.utils import wait_for_event
from enum import Enum

# Expected InflationConfiguration at genesis
INFLATION_CONFIG = {
            'inflation_parameters': {
                'inflation_rate': 35000000,
                'disinflation_rate': 900000000,
                },
            'inflation_stagnation_rate': 10000000,
            'inflation_stagnation_year': 13,
}

# Expected InflationParameters at genesis
INFLATION_PARAMETERS = {
    'inflation_rate': 35000000,
    'disinflation_rate': 1000000000,
}

# Expected recalculation target at genesis
RECALCULATION_AFTER = 2628000


class InflationState(Enum):
    InflationConfiguration = 'InflationConfiguration',
    YearlyInflationParameters = 'InflationParameters',
    BlockRewards = 'BlockRewards',
    CurrentYear = 'CurrentYear',
    RecalculationAt = 'DoRecalculationAt'


class TestPalletInflationManager(unittest.TestCase):
    # Fetches storage at latest block unless a blocknumber is provided
    def _fetch_pallet_storage(self, storage_name, block_number=None):
        block_hash = self.substrate.get_block(block_number=block_number)['header']['hash'] if block_number >= 0 else None

        return self.substrate.query(
            module='InflationManager',
            storage_function=storage_name,
            block_hash=block_hash
        ).value

    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL)
        self.kp_src = Keypair.create_from_uri('//Alice')

    def test_genesis_state(self):
        # If it's forked chain, we shouldn't test
        # Set the inflation configuration
        onchain_inflation_config = self._fetch_pallet_storage(InflationState.InflationConfiguration, 0)
        onchain_base_inflation_parameters = self._fetch_pallet_storage(InflationState.YearlyInflationParameters, 0)
        onchain_year = self._fetch_pallet_storage(InflationState.CurrentYear, 0)
        onchain_do_recalculation_at = self._fetch_pallet_storage(InflationState.RecalculationAt, 0)

        self.assertEqual(INFLATION_CONFIG, onchain_inflation_config)
        self.assertEqual(INFLATION_PARAMETERS, onchain_base_inflation_parameters)
        self.assertEqual(onchain_year, 1)
        self.assertEqual(onchain_do_recalculation_at, RECALCULATION_AFTER)
