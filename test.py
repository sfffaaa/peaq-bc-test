from tools.two_address_evm_contract_with_rpc import evm_rpc_test
from tools.pallet_vesting_test import pallet_vesting_test
import pytest


if __name__ == '__main__':
    pytest.main()

    evm_rpc_test()
    pallet_vesting_test()
