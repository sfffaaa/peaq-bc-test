import sys
sys.path.append('./')
import json

from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import show_extrinsic, SCALE_CODEC, transfer, calculate_evm_account, calculate_evm_addr
from tools.utils import WS_URL, ETH_URL
from web3 import Web3

import pprint
pp = pprint.PrettyPrinter(indent=4)

ERC_TOKEN_TRANSFER = 34
CHAIN_ID = 9999
HEX_STR = '1111'


MNEMONIC = [
    'trouble kangaroo brave step craft valve have dash unique vehicle melt broccoli',
    # 0x434DB4884Fa631c89E57Ea04411D6FF73eF0E297
    'lunar hobby hungry vacant imitate silly amused soccer face census keep kiwi',
    # 0xC5BDf22635Df81f897C1BB2B24b758dEB21f522d,
    'mansion dynamic turkey army feel rescue choose achieve hurdle gentle phrase pair',
    # 0xe3D5bca5420d451885bA73035F4F06d10cd72eb5,
]


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
            'gas_limit': 4294967294,
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


def send_eth_token(w3, kp_src, kp_dst, token_num):
    nonce = w3.eth.getTransactionCount(kp_src.ss58_address)
    # gas = web3.toWei(Decimal('0.000000005'), 'ether')
    gas = 4294967294
    price = 1000
    print(token_num + gas * price)
    tx = {
        'from': kp_src.ss58_address,
        'to': kp_dst.ss58_address,
        'value': token_num,
        'gas': gas,
        'maxFeePerGas': w3.toWei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.toWei(2, 'gwei'),
        'nonce': nonce,
        'chainId': CHAIN_ID
    }
    signed_txn = w3.eth.account.sign_transaction(tx, private_key=kp_src.private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if tx_receipt['status'] != 1:
        print(tx_receipt)
        raise IOError
    print('✅ send_eth_token, Success')


def deploy_contract(w3, kp_src):
    with open('ETH/identity/bytecode') as f:
        bytecode = f.read().strip()

    with open('ETH/identity/abi') as f:
        abi = json.load(f)

    nonce = w3.eth.get_transaction_count(kp_src.ss58_address)
    tx = w3.eth.contract(
        abi=abi,
        bytecode=bytecode).constructor().buildTransaction({
            'from': kp_src.ss58_address,
            'gas': 4294967294,
            'maxFeePerGas': w3.toWei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.toWei(2, 'gwei'),
            'nonce': nonce,
            'chainId': CHAIN_ID})

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=kp_src.private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    address = tx_receipt['contractAddress']
    if not address:
        raise IOError('Contract deploy fails')
    print('✅ deploy, Success')
    return address


def call_copy(w3, address, kp_src):
    with open('ETH/identity/abi') as f:
        abi = json.load(f)

    contract = w3.eth.contract(address, abi=abi)
    data = contract.functions.memoryStored().call()
    assert(data == b'')

    nonce = w3.eth.get_transaction_count(kp_src.ss58_address)
    tx = contract.functions.callDatacopy(HEX_STR).buildTransaction({
        'from': kp_src.ss58_address,
        'gas': 4294967294,
        'maxFeePerGas': w3.toWei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.toWei(2, 'gwei'),
        'nonce': nonce,
        'chainId': CHAIN_ID})

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=kp_src.private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    w3.eth.waitForTransactionReceipt(tx_hash)

    data = contract.functions.memoryStored().call()
    assert(data.hex() == HEX_STR)
    print('✅ call_copy, Success')


def evm_rpc_test():
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL, type_registry=SCALE_CODEC) as conn:
            # print('Check the get balance')
            kp_src = Keypair.create_from_uri('//Alice')
            eth_src = calculate_evm_addr(kp_src.ss58_address)

            token_num = 10000 * pow(10, 15)
            transfer(conn, kp_src, calculate_evm_account(eth_src), token_num)

            kp_eth_src = Keypair.create_from_mnemonic(MNEMONIC[0], crypto_type=KeypairType.ECDSA)

            call_eth_transfer_a_lot(conn, kp_src, eth_src, kp_eth_src.ss58_address.lower())
            eth_after_balance = int(conn.rpc_request("eth_getBalance", [kp_eth_src.ss58_address]).get('result'), 16)
            print(f'dst ETH balance: {eth_after_balance}')

            w3 = Web3(Web3.HTTPProvider(ETH_URL))
            block = w3.eth.get_block('latest')
            assert(block['number'] != 0)

            kp_eth_dst = Keypair.create_from_mnemonic(MNEMONIC[1], crypto_type=KeypairType.ECDSA)

            token_num = 10000000
            dst_eth_before_balance = w3.eth.get_balance(kp_eth_dst.ss58_address)
            print(f'before, dst eth: {dst_eth_before_balance}')
            # Call eth transfer
            src_eth_balance = w3.eth.get_balance(kp_eth_src.ss58_address)
            print(f'src eth: {src_eth_balance}')
            send_eth_token(w3, kp_eth_src, kp_eth_dst, token_num)
            dst_eth_after_balance = w3.eth.get_balance(kp_eth_dst.ss58_address)
            print(f'after, dst eth: {dst_eth_after_balance}')
            # In empty account, the token_num == token_num - enssential num
            assert(dst_eth_after_balance > dst_eth_before_balance)

            address = deploy_contract(w3, kp_eth_src)
            call_copy(w3, address, kp_eth_src)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    evm_rpc_test()
