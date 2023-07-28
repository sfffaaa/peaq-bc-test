import sys
sys.path.append('./')
import json

from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import SCALE_CODEC, transfer, calculate_evm_account, calculate_evm_addr
from tools.utils import WS_URL, ETH_URL, get_eth_chain_id
from tools.peaq_eth_utils import call_eth_transfer_a_lot
from tools.peaq_eth_utils import get_eth_balance, get_contract
from tools.peaq_eth_utils import TX_SUCCESS_STATUS
from web3 import Web3
import unittest

import pprint
pp = pprint.PrettyPrinter(indent=4)

ERC_TOKEN_TRANSFER = 34
HEX_STR = '1111'
GAS_LIMIT = 4294967
TOKEN_NUM = 10000 * pow(10, 15)
ABI_FILE = 'ETH/identity/abi'


MNEMONIC = [
    'trouble kangaroo brave step craft valve have dash unique vehicle melt broccoli',
    # 0x434DB4884Fa631c89E57Ea04411D6FF73eF0E297
    'lunar hobby hungry vacant imitate silly amused soccer face census keep kiwi',
    # 0xC5BDf22635Df81f897C1BB2B24b758dEB21f522d,
]


def send_eth_token(w3, kp_src, kp_dst, token_num, eth_chain_id):
    nonce = w3.eth.get_transaction_count(kp_src.ss58_address)
    # gas = web3.to_wei(Decimal('0.000000005'), 'ether')
    gas = GAS_LIMIT
    tx = {
        'from': kp_src.ss58_address,
        'to': kp_dst.ss58_address,
        'value': token_num,
        'gas': gas,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': nonce,
        'chainId': eth_chain_id
    }
    signed_txn = w3.eth.account.sign_transaction(tx, private_key=kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_receipt


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


def get_contract_data(w3, address, filename):
    contract = get_contract(w3, address, filename)
    data = contract.functions.memoryStored().call()
    return data.hex()


def call_copy(w3, address, kp_src, eth_chain_id, file_name, data):
    contract = get_contract(w3, address, file_name)

    nonce = w3.eth.get_transaction_count(kp_src.ss58_address)
    tx = contract.functions.callDatacopy(bytes.fromhex(data)).build_transaction({
        'from': kp_src.ss58_address,
        'gas': GAS_LIMIT,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': nonce,
        'chainId': eth_chain_id})

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f'call: {tx_hash.hex()}')
    w3.eth.wait_for_transaction_receipt(tx_hash)
    return True


class TestEVMEthRPC(unittest.TestCase):
    def setUp(self):
        self._conn = SubstrateInterface(url=WS_URL, type_registry=SCALE_CODEC)
        self._eth_chain_id = get_eth_chain_id(self._conn)
        self._kp_src = Keypair.create_from_uri('//Alice')
        self._eth_src = calculate_evm_addr(self._kp_src.ss58_address)
        self._kp_eth_src = Keypair.create_from_mnemonic(MNEMONIC[0], crypto_type=KeypairType.ECDSA)
        self._kp_eth_dst = Keypair.create_from_mnemonic(MNEMONIC[1], crypto_type=KeypairType.ECDSA)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._eth_deposited_src = calculate_evm_account(self._eth_src)

    def test_evm_rpc_transfer(self):
        conn = self._conn
        eth_chain_id = self._eth_chain_id
        kp_src = self._kp_src
        eth_src = self._eth_src
        kp_eth_src = self._kp_eth_src
        kp_eth_dst = self._kp_eth_dst
        eth_deposited_src = self._eth_deposited_src
        w3 = self._w3

        # Setup
        transfer(conn, kp_src, eth_deposited_src, TOKEN_NUM)

        call_eth_transfer_a_lot(conn, kp_src, eth_src, kp_eth_src.ss58_address.lower())
        eth_after_balance = get_eth_balance(conn, kp_eth_src.ss58_address)
        print(f'dst ETH balance: {eth_after_balance}')

        block = w3.eth.get_block('latest')
        self.assertNotEqual(block['number'], 0)

        token_num = 10000000
        dst_eth_before_balance = w3.eth.get_balance(kp_eth_dst.ss58_address)

        print(f'before, dst eth: {dst_eth_before_balance}')
        src_eth_balance = w3.eth.get_balance(kp_eth_src.ss58_address)
        print(f'src eth: {src_eth_balance}')

        # Execute -> Call eth transfer
        tx_receipt = send_eth_token(w3, kp_eth_src, kp_eth_dst, token_num, eth_chain_id)
        self.assertEqual(tx_receipt['status'], TX_SUCCESS_STATUS, f'send eth token failed: {tx_receipt}')

        # Check
        dst_eth_after_balance = w3.eth.get_balance(kp_eth_dst.ss58_address)
        print(f'after, dst eth: {dst_eth_after_balance}')
        # In empty account, the token_num == token_num - enssential num
        self.assertGreater(dst_eth_after_balance, dst_eth_before_balance,
                           f'{dst_eth_after_balance} <= {dst_eth_before_balance}')

    def test_evm_rpc_identity_contract(self):
        conn = self._conn
        eth_chain_id = self._eth_chain_id
        kp_src = self._kp_src
        eth_src = self._eth_src
        kp_eth_src = self._kp_eth_src
        eth_deposited_src = self._eth_deposited_src
        w3 = self._w3

        transfer(conn, kp_src, eth_deposited_src, TOKEN_NUM)

        call_eth_transfer_a_lot(conn, kp_src, eth_src, kp_eth_src.ss58_address.lower())

        with open('ETH/identity/bytecode') as f:
            bytecode = f.read().strip()

        # Execute -> Deploy contract
        address = deploy_contract(w3, kp_eth_src, eth_chain_id, ABI_FILE, bytecode)
        self.assertNotEqual(address, None, 'contract address is None')

        # Check
        data = get_contract_data(w3, address, ABI_FILE)
        self.assertEqual(data, '', f'contract data is not empty {data}.hex()')

        # Execute -> Call set
        self.assertTrue(call_copy(w3, address, kp_eth_src, eth_chain_id, ABI_FILE, HEX_STR))

        out = get_contract_data(w3, address, ABI_FILE)
        self.assertEqual(out, HEX_STR, 'call copy failed')
