# from tools.pallet_assets_test import pallet_assets_test
from tools.two_address_substrate_with_extrinsic import pallet_multisig_test
from tools.two_address_substrate_with_extrinsic import pallet_transaction_test
from tools.two_address_substrate_with_extrinsic import pallet_did_test
from tools.pallet_rbac_rpc_test import pallet_rbac_rpc_test
# from tools.test_batchall import pallet_batchall_test
from tools.two_address_evm_contract_with_extrinsic import evm_extrinsic_test
from tools.two_address_evm_contract_with_rpc import evm_rpc_test
from tools.block_creation_time_test import block_creation_time_test
# from tools.pallet_asset_evm_with_rpc import pallet_asset_evm_test
from tools.pallet_utility_test import pallet_utility_test

if __name__ == '__main__':
    # pallet_batchall_test()
    pallet_multisig_test()
    pallet_transaction_test()
    pallet_did_test()
    pallet_rbac_rpc_test()
    # pallet_assets_test()
    evm_rpc_test()
    evm_extrinsic_test()
    # pallet_asset_evm_test()
    block_creation_time_test()
    pallet_utility_test()
