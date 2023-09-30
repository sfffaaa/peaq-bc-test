import json
import binascii
import os
from peaq.utils import ExtrinsicBatch

GAS_LIMIT = 4294967
TX_SUCCESS_STATUS = 1


def generate_random_hex(num_bytes=16):
    return f'0x{binascii.b2a_hex(os.urandom(num_bytes)).decode()}'


def get_contract(w3, address, file_name):
    with open(file_name) as f:
        abi = json.load(f)

    return w3.eth.contract(address, abi=abi)


def call_eth_transfer_a_lot(substrate, kp_src, eth_src, eth_dst):
    batch = ExtrinsicBatch(substrate, kp_src)
    batch.compose_call(
        'EVM',
        'call',
        {
            'source': eth_src,
            'target': eth_dst,
            'input': '0x',
            'value': '0xffffffffffffffffff0000000000000000000000000000000000000000000000',
            'gas_limit': GAS_LIMIT,
            'max_fee_per_gas': "0xfffffff000000000000000000000000000000000000000000000000000000000",
            'max_priority_fee_per_gas': None,
            'nonce': None,
            'access_list': []
        })
    return batch.execute()


def get_eth_balance(substrate, eth_src):
    return int(substrate.rpc_request("eth_getBalance", [eth_src]).get('result'), 16)


def deploy_contract(w3, kp_src, eth_chain_id, abi_file_name, bytecode):
    with open(abi_file_name) as f:
        abi = json.load(f)

    nonce = w3.eth.get_transaction_count(kp_src.ss58_address)
    tx = w3.eth.contract(
        abi=abi,
        bytecode=bytecode).constructor().build_transaction({
            'from': kp_src.ss58_address,
            'gas': 429496,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': eth_chain_id})

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f'create_contract: {tx_hash.hex()}')
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    address = tx_receipt['contractAddress']
    return address
