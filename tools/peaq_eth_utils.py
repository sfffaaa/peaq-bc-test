from tools.utils import show_extrinsic
import json
import binascii
import os

GAS_LIMIT = 4294967


def generate_random_hex(num_bytes=16):
    return f'0x{binascii.b2a_hex(os.urandom(num_bytes)).decode()}'


def get_contract(w3, address, file_name):
    with open(file_name) as f:
        abi = json.load(f)

    return w3.eth.contract(address, abi=abi)


def call_eth_transfer_a_lot(substrate, kp_src, eth_src, eth_dst):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    call = substrate.compose_call(
        call_module='EVM',
        call_function='call',
        call_params={
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

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'evm_call')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError
