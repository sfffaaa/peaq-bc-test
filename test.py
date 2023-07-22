from tools.pallet_multisig_test import pallet_multisig_test
from tools.two_address_substrate_with_extrinsic import pallet_transaction_test
from tools.two_address_substrate_with_extrinsic import pallet_did_test
from tools.two_address_evm_contract_with_extrinsic import evm_extrinsic_test
from tools.two_address_evm_contract_with_rpc import evm_rpc_test
from tools.pallet_utility_test import pallet_utility_test
from tools.pallet_storage_test import pallet_storage_test
from tools.pallet_block_reward_test import pallet_block_reward_test
from tools.reward_distribution_test import reward_distribution_test
from tools.pallet_treasury_test import pallet_treasury_test
from tools.pallet_vesting_test import pallet_vesting_test
from tools.bridge_storage_test import bridge_storage_test
import pytest


if __name__ == '__main__':
    pytest.main()

    pallet_multisig_test()
    pallet_transaction_test()
    pallet_did_test()
    evm_rpc_test()
    evm_extrinsic_test()
    pallet_utility_test()
    pallet_storage_test()
    pallet_block_reward_test()
    reward_distribution_test()
    pallet_treasury_test()
    pallet_vesting_test()
    bridge_storage_test()
