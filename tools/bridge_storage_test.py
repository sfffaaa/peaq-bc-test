import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import transfer, calculate_evm_account, calculate_evm_addr, SCALE_CODEC, calculate_evm_account_hex
from tools.utils import WS_URL, ETH_URL, ETH_CHAIN_ID
from tools.peaq_eth_utils import call_eth_transfer_a_lot, get_contract, generate_random_hex
from web3 import Web3


import pprint
pp = pprint.PrettyPrinter(indent=4)
GAS_LIMIT = 4294967


ITEM_TYPE = generate_random_hex()
ITEM = '0x01'
NEW_ITEM = '0x10'
KP_SRC = Keypair.create_from_uri('//Alice')
STORAGE_ADDRESS = '0x0000000000000000000000000000000000000801'
ETH_PRIVATE_KEY = '0xa2899b053679427c8c446dc990c8990c75052fd3009e563c6a613d982d6842fe'
ABI_FILE = 'ETH/storage/storage.sol.json'


def _eth_add_item(w3, contract, eth_kp_src, item_type, item):
    nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
    tx = contract.functions.add_item(item_type, item).build_transaction({
        'from': eth_kp_src.ss58_address,
        'gas': GAS_LIMIT,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': nonce,
        'chainId': ETH_CHAIN_ID})

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if tx_receipt['status'] != 1:
        print(tx_receipt)
        raise IOError
    print('✅ eth_add_item, Success')
    return tx_receipt['blockNumber']


def _eth_update_item(w3, contract, eth_kp_src, item_type, item):
    nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
    tx = contract.functions.update_item(item_type, item).build_transaction({
        'from': eth_kp_src.ss58_address,
        'gas': GAS_LIMIT,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': nonce,
        'chainId': ETH_CHAIN_ID})

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if tx_receipt['status'] != 1:
        print(tx_receipt)
        raise IOError
    print('✅ eth_update_item, Success')
    return tx_receipt['blockNumber']


def bridge_storage_test():
    w3 = Web3(Web3.HTTPProvider(ETH_URL))

    with SubstrateInterface(url=WS_URL, type_registry=SCALE_CODEC) as substrate:
        eth_src = calculate_evm_addr(KP_SRC.ss58_address)
        token_num = 10000 * pow(10, 15)
        transfer(substrate, KP_SRC, calculate_evm_account(eth_src), token_num)
        eth_kp_src = Keypair.create_from_private_key(ETH_PRIVATE_KEY, crypto_type=KeypairType.ECDSA)
        call_eth_transfer_a_lot(substrate, KP_SRC, eth_src, eth_kp_src.ss58_address.lower())

        contract = get_contract(w3, STORAGE_ADDRESS, ABI_FILE)

        block_idx = _eth_add_item(w3, contract, eth_kp_src, ITEM_TYPE, ITEM)
        account = calculate_evm_account_hex(eth_kp_src.ss58_address)
        data = contract.functions.get_item(account, ITEM_TYPE).call()
        assert(f'0x{data.hex()}' == ITEM)
        event = contract.events.ItemAdded.create_filter(fromBlock=block_idx, toBlock=block_idx)
        events = event.get_all_entries()
        assert(f"0x{events[0]['args']['account'].hex()}" == account)
        assert(f"0x{events[0]['args']['item_type'].hex()}" == f"{ITEM_TYPE}")
        assert(f"0x{events[0]['args']['item'].hex()}" == f"{ITEM}")

        block_idx = _eth_update_item(w3, contract, eth_kp_src, ITEM_TYPE, NEW_ITEM)
        data = contract.functions.get_item(account, ITEM_TYPE).call()
        assert(f'0x{data.hex()}' == NEW_ITEM)

        event = contract.events.ItemUpdated.create_filter(fromBlock=block_idx, toBlock=block_idx)
        events = event.get_all_entries()
        assert(f"0x{events[0]['args']['account'].hex()}" == account)
        assert(f"0x{events[0]['args']['item_type'].hex()}" == f"{ITEM_TYPE}")
        assert(f"0x{events[0]['args']['item'].hex()}" == f"{NEW_ITEM}")

        print('Passssss test_did_bridge')


if __name__ == '__main__':
    bridge_storage_test()
