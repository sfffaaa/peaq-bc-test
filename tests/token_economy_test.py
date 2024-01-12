import unittest

from substrateinterface import SubstrateInterface
from tools.utils import WS_URL
from peaq.utils import get_block_height, get_block_hash, get_chain
from tests.utils_func import restart_parachain_and_runtime_upgrade
from tools.runtime_upgrade import wait_until_block_height


import pprint
pp = pprint.PrettyPrinter(indent=4)

STATE_INFOS = [{
    'module': 'ParachainStaking',
    'storage_function': 'MaxSelectedCandidates',
    'type': {
        'peaq-dev': 4,
        'agung-network': 4,
        'krest-network': 4,
        # However: in the krest-forked-chain, it should be 16 by sending the extrinsic for the fork chain
        'krest-network-fork': 16,
        'peaq-network': 4
    }
}, {
    'module': 'ParachainStaking',
    'storage_function': 'Round',
    'type': {
        'peaq-dev': {'length': 10},
        'agung-network': {'length': 600},
        'krest-network': {'length': 1200},
        'peaq-network': {'length': 600},
    }
}, {
    'module': 'BlockReward',
    'storage_function': 'BlockIssueReward',
    'almost': True,
    'type': {
        'peaq-dev': 1 * 10 ** 18,
        'agung-network': 79098670000000008192,
        'krest-network': 3.80517503805 * 10 ** 18,
        'peaq-network': 79098670000000008192,
    }
}, {
    'module': 'BlockReward',
    'storage_function': 'MaxCurrencySupply',
    'almost': True,
    'type': {
        'peaq-dev': 4200000000 * 10 ** 18,
        'agung-network': 4200000000 * 10 ** 18,
        'krest-network': 400000000 * 10 ** 18,
        'peaq-network': 4200000000 * 10 ** 18,
    }
}, {
    'module': 'BlockReward',
    'storage_function': 'RewardDistributionConfigStorage',
    'type': {
        # It's special case because below is percentage,
        # and then you have to divide by 1000000000
        'peaq-dev': {
            'treasury_percent': 200000000,
            'dapps_percent': 250000000,
            'collators_percent': 100000000,
            'lp_percent': 250000000,
            'machines_percent': 100000000,
            'parachain_lease_fund_percent': 100000000
        },
        'agung-network': {
            'treasury_percent': 200000000,
            'dapps_percent': 250000000,
            'collators_percent': 100000000,
            'lp_percent': 250000000,
            'machines_percent': 100000000,
            'parachain_lease_fund_percent': 100000000
        },
        'krest-network': {
            'treasury_percent': 150000000,
            'dapps_percent': 150000000,
            'collators_percent': 300000000,
            'lp_percent': 150000000,
            'machines_percent': 150000000,
            'parachain_lease_fund_percent': 100000000
        },
        'peaq-network': {
            'treasury_percent': 200000000,
            'dapps_percent': 250000000,
            'collators_percent': 100000000,
            'lp_percent': 250000000,
            'machines_percent': 100000000,
            'parachain_lease_fund_percent': 100000000
        }
    }
}]


CONSTANT_INFOS = [{
    'module': 'ParachainStaking',
    'storage_function': 'MaxCollatorsPerDelegator',
    'type': {
        'peaq-dev': 1,
        'agung-network': 1,
        'krest-network': 1,
        'peaq-network': 1,
    }
}, {
    'module': 'ParachainStaking',
    'storage_function': 'MaxDelegationsPerRound',
    'type': {
        'peaq-dev': 1,
        'agung-network': 1,
        'krest-network': 1,
        'peaq-network': 1,
    }
}, {
    'module': 'ParachainStaking',
    'storage_function': 'MaxDelegatorsPerCollator',
    'type': {
        'peaq-dev': 25,
        'agung-network': 25,
        'krest-network': 25,
        'peaq-network': 25,
    }
}, {
    'module': 'ParachainStaking',
    'storage_function': 'MaxTopCandidates',
    'type': {
        'peaq-dev': 16,
        'agung-network': 16,
        'krest-network': 128,
        'peaq-network': 16,
    }
}, {
    'module': 'ParachainStaking',
    'storage_function': 'MinCollatorCandidateStake',
    'type': {
        'peaq-dev': 32000,
        'agung-network': 32000,
        'krest-network': 50000 * 10 ** 18,
        'peaq-network': 32000,
    }
}, {
    'module': 'ParachainStaking',
    'storage_function': 'MinCollatorStake',
    'type': {
        'peaq-dev': 32000,
        'agung-network': 32000,
        'krest-network': 50000 * 10 ** 18,
        'peaq-network': 32000,
    }
}, {
    'module': 'ParachainStaking',
    'storage_function': 'MinDelegation',
    'type': {
        'peaq-dev': 20000,
        'agung-network': 20000,
        'krest-network': 100 * 10 ** 18,
        'peaq-network': 20000,
    }
}, {
    'module': 'ParachainStaking',
    'storage_function': 'MinDelegatorStake',
    'type': {
        'peaq-dev': 20000,
        'agung-network': 20000,
        'krest-network': 100 * 10 ** 18,
        'peaq-network': 20000,
    }
}]


class TokenEconomyTest(unittest.TestCase):

    def get_modified_chain_spec(self):
        if 'peaq-dev-fork' == self._chain_spec:
            return 'peaq-dev'
        if 'krest-network-fork' == self._chain_spec:
            return 'krest-network'
        if 'peaq-network-fork' == self._chain_spec:
            return 'peaq-network'

    def get_info(self, test_type):
        if self._chain_spec not in test_type:
            return test_type[self.get_modified_chain_spec()]
        else:
            return test_type[self._chain_spec]

    @classmethod
    def setUpClass(cls):
        restart_parachain_and_runtime_upgrade()

    def setUp(self):
        restart_parachain_and_runtime_upgrade()
        wait_until_block_height(SubstrateInterface(url=WS_URL), 1)
        self._substrate = SubstrateInterface(url=WS_URL)
        current_height = get_block_height(self._substrate)
        self._block_hash = get_block_hash(self._substrate, current_height)
        self._chain_spec = get_chain(self._substrate)

    def test_chain_states(self):
        for test in STATE_INFOS:
            module = test['module']
            storage_function = test['storage_function']
            result = self._substrate.query(
                module=module,
                storage_function=storage_function,
                params=[],
                block_hash=self._block_hash,
            )

            golden_data = self.get_info(test['type'])
            if isinstance(golden_data, dict):
                for k, v in golden_data.items():
                    self.assertEqual(result.value[k], v, f'{result.value} != {k}: {v}, {storage_function}')
            else:
                if 'almost' in test and test['almost']:
                    self.assertAlmostEqual(result.value / golden_data, 1, 7, msg=f'{result.value} != {test}')
                else:
                    self.assertEqual(result.value, golden_data, f'{result.value} != {test}')

    def test_constants(self):
        for test in CONSTANT_INFOS:
            module = test['module']
            storage_function = test['storage_function']
            result = self._substrate.get_constant(
                module,
                storage_function,
                self._block_hash,
            )

            golden_data = self.get_info(test['type'])
            self.assertEqual(result.value, golden_data, f'{result.value} != {test}')
