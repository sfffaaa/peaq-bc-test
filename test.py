from tools.two_address_substrate_with_extrinsic import pallet_multisig_test
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

if __name__ == '__main__':
    pallet_multisig_test()
    pallet_transaction_test()
    pallet_did_test()
    pallet_rbac_test()
    evm_rpc_test()
    evm_extrinsic_test()
    block_creation_time_test()
    pallet_utility_test()
    pallet_storage_test()
    pallet_block_reward_test()
    reward_distribution_test()
