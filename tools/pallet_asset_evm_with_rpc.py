import sys
sys.path.append('./')

import json
from web3 import Web3
import eth_utils

from tools.pallet_assets_test import get_valid_asset_id, create_asset, get_asset_balance, mint, destroy, set_metadata
from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import transfer as token_transfer, calculate_evm_account, WS_URL, ETH_URL
from tools.two_address_evm_contract_with_rpc import MNEMONIC

old_checksum_func = eth_utils.address.is_checksum_address


def pallet_asset_evm_test():
    print('---- pallet_asset_evm_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as conn:
            asset_id = get_valid_asset_id(conn)

            kp_sudo = Keypair.create_from_uri('//Alice')
            kp_admin = Keypair.create_from_uri('//Bob')
            create_asset(conn, kp_sudo, kp_admin, asset_id)
            metadata = ('name', 'symbol', 10)
            set_metadata(conn, kp_sudo, asset_id, metadata[0], metadata[1], metadata[2])

            kp_eth_src = Keypair.create_from_mnemonic(MNEMONIC[0], crypto_type=KeypairType.ECDSA)
            substrate_eth_addr = calculate_evm_account(kp_eth_src.ss58_address.lower())
            token_transfer(conn, kp_sudo, substrate_eth_addr, 10)

            balance_src = get_asset_balance(conn, substrate_eth_addr, asset_id)['balance'].value
            mint_number = 10000
            mint(conn, kp_admin, substrate_eth_addr, asset_id, mint_number)
            assert(get_asset_balance(conn, substrate_eth_addr, asset_id)['balance'].value == balance_src + mint_number)

            w3 = Web3(Web3.HTTPProvider(ETH_URL))
            contract_addr = '0xffffffff{0:0{1}x}'.format(asset_id, 32)
            print(f'Contract: {contract_addr}')
            with open('ETH/erc20/abi') as f:
                abi = json.load(f)

            # Monkey patch because the address is not the checksum address
            old_func = eth_utils.address.is_checksum_address
            eth_utils.address.is_checksum_address = lambda x: True
            contract = w3.eth.contract(contract_addr, abi=abi)
            eth_utils.address.is_checksum_address = old_func

            # Check all
            assert(contract.functions.decimals().call() == metadata[2])
            assert(contract.functions.name().call() == metadata[0])
            assert(contract.functions.symbol().call() == metadata[1])
            assert(contract.functions.totalSupply().call() == mint_number)
            assert(contract.functions.balanceOf(kp_eth_src.ss58_address.lower()).call() == mint_number)

            destroy(conn, kp_sudo, asset_id)
            assert(asset_id == get_valid_asset_id(conn))

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    pallet_asset_evm_test()
