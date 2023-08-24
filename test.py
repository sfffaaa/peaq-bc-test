import sys

from tools.pallet_multisig_test import pallet_multisig_test
from tools.two_address_substrate_with_extrinsic import pallet_transaction_test
from tools.two_address_substrate_with_extrinsic import pallet_did_test
from tools.pallet_rbac_test import pallet_rbac_test
from tools.two_address_evm_contract_with_extrinsic import evm_extrinsic_test
from tools.two_address_evm_contract_with_rpc import evm_rpc_test
from tools.block_creation_time_test import block_creation_time_test
from tools.pallet_utility_test import pallet_utility_test
from tools.pallet_storage_test import pallet_storage_test
from tools.pallet_block_reward_test import pallet_block_reward_test
from tools.reward_distribution_test import reward_distribution_test
from tools.pallet_treasury_test import pallet_treasury_test
from tools.pallet_vesting_test import pallet_vesting_test
from tools.bridge_did_test import bridge_did_test
from tools.bridge_storage_test import bridge_storage_test
from tools.zenlink_dex_test import zenlink_dex_test

def parse_args():
    if len(sys.argv) < 2:
        return []
    tests = sys.argv[1:]
    for idx, tst in enumerate(tests):
        if tst[-3:] == '.py':
            tst = tst[:-3]
        if tst[-2:] != '()':
            tst = tst + '()'
        tests[idx] = tst
    return tests


if __name__ == '__main__':
    tests = parse_args()
    if not tests:
        pallet_multisig_test()
        pallet_transaction_test()
        pallet_did_test()
        pallet_rbac_test()
        evm_rpc_test()
        evm_extrinsic_test()
        pallet_utility_test()
        pallet_storage_test()
        pallet_block_reward_test()
        reward_distribution_test()
        pallet_treasury_test()
        pallet_vesting_test()
        bridge_did_test()
        bridge_storage_test()
        zenlink_dex_test()
        block_creation_time_test()
    else:
        for test in tests:
            exec(test)

