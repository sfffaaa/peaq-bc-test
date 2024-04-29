import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
# from tools.utils import wait_for_event
from enum import StrEnum


# BASE_INFLATION_PARAMETERS = {
#                 'effective_inflation_rate': 35000000,
#                 'effective_disinflation_rate': 900000000,
# },

INFLATION_CONFIG = {
            'base_inflation_parameters': {
                'effective_inflation_rate': 35000000,
                'effective_disinflation_rate': 900000000,
                },
            'inflation_stagnation_rate': 10000000,
            'inflation_stagnation_year': 13,
}

RECALCULATION_AFTER = 365 * 24 * 60 * 60 / 12


class InflationState(StrEnum):
    InflationConfiguration = 'InflationConfiguration',
    YearlyInflationParameters = 'YearlyInflationParameters',
    BlockRewards = 'BlockRewards',
    CurrentYear = 'CurrentYear',
    RecalculationAt = 'RecalculationAt'


class TestPalletInflationManager(unittest.TestCase):

    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL)
        self.kp_src = Keypair.create_from_uri('//Alice')

    # Fetches storage at latest block unless a blocknumber is provided
    def _fetch_pallet_storage(self, storage_name, block_number=None):
        block_hash = self.substrate.get_block(block_number=block_number)['header']['hash'] if block_number >= 0 else None

        return self.substrate.query(
            module='InflationManager',
            storage_function=storage_name,
            block_hash=block_hash
        ).value

    def test_genesis(self):
        # Set the inflation configuration
        onchain_inflation_config = self._fetch_pallet_storage(InflationState.InflationConfiguration, 0)
        onchain_base_inflation_parameters = self._fetch_pallet_storage(InflationState.YearlyInflationParameters, 0)
        onchain_year = self._fetch_pallet_storage(InflationState.CurrentYear, 0)

        self.assertEqual(INFLATION_CONFIG, onchain_inflation_config)
        self.assertEqual(INFLATION_CONFIG['base_inflation_parameters'], onchain_base_inflation_parameters)
        self.assertEqual(onchain_year, 1)
