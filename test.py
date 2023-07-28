from tools.two_address_evm_contract_with_extrinsic import evm_extrinsic_test
from tools.two_address_evm_contract_with_rpc import evm_rpc_test
from tools.reward_distribution_test import reward_distribution_test
from tools.pallet_vesting_test import pallet_vesting_test
from tools.bridge_storage_test import bridge_storage_test
import pytest


if __name__ == '__main__':
    pytest.main()

    evm_rpc_test()
    evm_extrinsic_test()
    reward_distribution_test()
    pallet_vesting_test()
    bridge_storage_test()
