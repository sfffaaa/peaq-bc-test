import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import transfer, calculate_evm_account, calculate_evm_addr, SCALE_CODEC
from tools.peaq_eth_utils import call_eth_transfer_a_lot, get_contract, generate_random_hex
from tools.utils import WS_URL, ETH_URL, ETH_CHAIN_ID
from web3 import Web3


import pprint
pp = pprint.PrettyPrinter(indent=4)
GAS_LIMIT = 4294967


KEY = generate_random_hex()
VALUE = '0x01'
NEW_VALUE = '0x10'
KP_SRC = Keypair.create_from_uri('//Alice')
DID_ADDRESS = '0x0000000000000000000000000000000000000800'
ETH_PRIVATE_KEY = '0xa2899b053679427c8c446dc990c8990c75052fd3009e563c6a613d982d6842fe'
VALIDITY = 1000
ABI_FILE = 'ETH/did/did.sol.json'


def _eth_add_attribute(w3, contract, eth_kp_src, kp_src, key, value):
    nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
    tx = contract.functions.add_attribute(kp_src.public_key, key, value, VALIDITY).build_transaction({
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
    print('✅ eth_add_attribute, Success')
    return tx_receipt['blockNumber']


def _eth_update_attribute(w3, contract, eth_kp_src, kp_src, key, value):
    nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
    tx = contract.functions.update_attribute(kp_src.public_key, key, value, VALIDITY).build_transaction({
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
    print('✅ eth_update_attribute, Success')
    return tx_receipt['blockNumber']


def _eth_remove_attribute(w3, contract, eth_kp_src, kp_src, key):
    nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
    tx = contract.functions.remove_attribute(kp_src.public_key, key).build_transaction({
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
    print('✅ eth_remove_attribute, Success')
    return tx_receipt['blockNumber']


def bridge_did_test():
    w3 = Web3(Web3.HTTPProvider(ETH_URL))

    with SubstrateInterface(url=WS_URL, type_registry=SCALE_CODEC) as substrate:
        eth_src = calculate_evm_addr(KP_SRC.ss58_address)
        token_num = 10000 * pow(10, 15)
        transfer(substrate, KP_SRC, calculate_evm_account(eth_src), token_num)
        eth_kp_src = Keypair.create_from_private_key(ETH_PRIVATE_KEY, crypto_type=KeypairType.ECDSA)
        call_eth_transfer_a_lot(substrate, KP_SRC, eth_src, eth_kp_src.ss58_address.lower())

        contract = get_contract(w3, DID_ADDRESS, ABI_FILE)

        block_idx = _eth_add_attribute(w3, contract, eth_kp_src, KP_SRC, KEY, VALUE)
        data = contract.functions.read_attribute(KP_SRC.public_key, KEY).call()
        assert(f'0x{data[0].hex()}' == KEY)
        assert(f'0x{data[1].hex()}' == VALUE)
        event = contract.events.AddAttribute.create_filter(fromBlock=block_idx, toBlock=block_idx)
        events = event.get_all_entries()
        assert(f"{events[0]['args']['sender'].upper()}" == f"0X{eth_kp_src.public_key.hex().upper()}")
        assert(f"{events[0]['args']['did_account'].hex()}" == f"{KP_SRC.public_key.hex()}")
        assert(f"0x{events[0]['args']['name'].hex()}" == f"{KEY}")
        assert(f"0x{events[0]['args']['value'].hex()}" == f"{VALUE}")
        assert(f"{events[0]['args']['validity']}" == f"{VALIDITY}")

        block_idx = _eth_update_attribute(w3, contract, eth_kp_src, KP_SRC, KEY, NEW_VALUE)
        data = contract.functions.read_attribute(KP_SRC.public_key, KEY).call()
        assert(f'0x{data[0].hex()}' == KEY)
        assert(f'0x{data[1].hex()}' == NEW_VALUE)

        event = contract.events.UpdateAttribute.create_filter(fromBlock=block_idx, toBlock=block_idx)
        events = event.get_all_entries()
        assert(f"{events[0]['args']['sender'].upper()}" == f"0X{eth_kp_src.public_key.hex().upper()}")
        assert(f"{events[0]['args']['did_account'].hex()}" == f"{KP_SRC.public_key.hex()}")
        assert(f"0x{events[0]['args']['name'].hex()}" == f"{KEY}")
        assert(f"0x{events[0]['args']['value'].hex()}" == f"{NEW_VALUE}")
        assert(f"{events[0]['args']['validity']}" == f"{VALIDITY}")

        block_idx = _eth_remove_attribute(w3, contract, eth_kp_src, KP_SRC, KEY)
        try:
            data = contract.functions.read_attribute(KP_SRC.public_key, KEY).call()
            print('data still can be found')
            assert(0)
        except ValueError:
            pass

        event = contract.events.RemoveAttribte.create_filter(fromBlock=block_idx, toBlock=block_idx)
        events = event.get_all_entries()
        assert(f"{events[0]['args']['did_account'].hex()}" == f"{KP_SRC.public_key.hex()}")
        assert(f"0x{events[0]['args']['name'].hex()}" == f"{KEY}")

        print('Passssss test_did_bridge')


if __name__ == '__main__':
    bridge_did_test()
