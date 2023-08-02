from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from tools.utils import transfer, calculate_evm_account, calculate_evm_addr
from tools.peaq_eth_utils import get_eth_balance
from tools.payload import user_extrinsic_send
import unittest

import pprint
pp = pprint.PrettyPrinter(indent=4)

ERC_TOKEN_TRANSFER = 34
GAS_LIMIT = 4294967
TOKEN_NUM = 10000 * pow(10, 2)
ETH_DST_ADDR = '0x8eaf04151687736326c9fea17e25fc5287613693'
# Which is calculated in advance
ETH_ALICE_SLOT_ADDR = '0x045c0350b9cf0df39c4b40400c965118df2dca5ce0fbcf0de4aafc099aea4a14'
ETH_BOB_SLOT_ADDR = '0xe15f03c03b19c474c700f0ded08fa4d431a189d91588b86c3ef774970f504892'
ERC20_BYTECODE_FILE = 'ETH/erc20/bytecode'


def get_byte_code_from_file(file):
    with open(file, 'r') as f:
        bytecode = f.readline()
    return bytecode


# For the ERC 20 token
# https://github.com/paritytech/frontier/blob/master/template/examples/contract-erc20/truffle/contracts/MyToken.json#L259
@user_extrinsic_send
def create_constract(substrate, kp_src, eth_src, erc20_bytecode):
    return substrate.compose_call(
        call_module='EVM',
        call_function='create',
        call_params={
            'source': eth_src,
            'init': erc20_bytecode,
            'value': '0x0000000000000000000000000000000000000000000000000000000000000000',
            'gas_limit': GAS_LIMIT,
            'max_fee_per_gas': "0xfffffff000000000000000000000000000000000000000000000000000000000",
            'max_priority_fee_per_gas': None,
            'nonce': None,
            'access_list': []
        })


def get_deployed_contract(substrate, receipt):
    created_event = [_ for _ in substrate.get_events(receipt.block_hash)
                     if _['event'].value['event_id'] == 'Created'][0]
    return created_event.value['attributes']['address']


@user_extrinsic_send
def call_eth_transfer(substrate, kp_src, eth_src, eth_dst):
    return substrate.compose_call(
        call_module='EVM',
        call_function='call',
        call_params={
            'source': eth_src,
            'target': eth_dst,
            'input': '0x',
            'value': '0xffff000000000000000000000000000000000000000000000000000000000000',
            'gas_limit': GAS_LIMIT,
            'max_fee_per_gas': "0xffffffff00000000000000000000000000000000000000000000000000000000",
            'max_priority_fee_per_gas': None,
            'nonce': None,
            'access_list': []
        })


@user_extrinsic_send
def transfer_erc20_token(substrate, kp_src, eth_src, eth_dst, contract_addr):
    return substrate.compose_call(
        call_module='EVM',
        call_function='call',
        call_params={
            'target': contract_addr,
            'source': eth_src,
            'input': f'0xa9059cbb000000000000000000000000{eth_dst.lower()[2:]}00000000000000000000000000000000000000000000000000000000000000{hex(ERC_TOKEN_TRANSFER)[2:]}',  # noqa: E501
            'value': '0x0000000000000000000000000000000000000000000000000000000000000000',
            'gas_limit': GAS_LIMIT,
            'max_fee_per_gas': "0xfffffff000000000000000000000000000000000000000000000000000000000",
            'max_priority_fee_per_gas': None,
            'nonce': None,
            'access_list': []
        })


def get_erc20_balance(conn, contract_addr, slot_addr):
    return int(conn.query("EVM", "AccountStorages", [contract_addr, slot_addr])[2:], 16)


def get_eth_contract_code(conn, contract_addr):
    return conn.query("EVM", "AccountCodes", [contract_addr])


class TestEVMSubstrateExtrinsic(unittest.TestCase):
    def setUp(self):
        self._conn = SubstrateInterface(url=WS_URL)
        self._kp_src = Keypair.create_from_uri('//Alice')
        self._eth_src = calculate_evm_addr(self._kp_src.ss58_address)
        self._eth_deposited_src = calculate_evm_account(self._eth_src)

    def test_evm_substrate_transfer(self):
        conn = self._conn
        kp_src = self._kp_src
        eth_src = self._eth_src

        # Setup
        transfer(conn, kp_src, self._eth_deposited_src, TOKEN_NUM)

        eth_balance = get_eth_balance(conn, eth_src)
        print(f'src ETH balance: {eth_balance}')
        self.assertNotEqual(eth_balance, 0)

        eth_before_balance = get_eth_balance(conn, ETH_DST_ADDR)
        print(f'dst ETH balance: {eth_before_balance}')

        # Execute
        receipt = call_eth_transfer(conn, kp_src, eth_src, ETH_DST_ADDR)
        self.assertTrue(receipt.is_success, f'call eth transfer failed: {receipt.error_message}')

        # Check
        eth_after_balance = get_eth_balance(conn, ETH_DST_ADDR)
        self.assertGreaterEqual(
            eth_after_balance, eth_before_balance,
            f'eth_after_balance: {eth_after_balance}, eth_before_balance: {eth_before_balance}')
        print(f'dst ETH balance: {eth_after_balance}')

    def test_evm_substrate_contract_test(self):
        conn = self._conn
        kp_src = self._kp_src
        eth_src = self._eth_src

        # Setup
        # transfer(conn, kp_src, self._eth_deposited_src, TOKEN_NUM)
        erc20_byte_code = get_byte_code_from_file(ERC20_BYTECODE_FILE)

        # Execute -> Deploy contract
        receipt = create_constract(conn, kp_src, eth_src, erc20_byte_code)
        self.assertTrue(receipt.is_success, f'create contract failed: {receipt.error_message}')

        # Check
        contract_addr = get_deployed_contract(conn, receipt)
        self.assertNotEqual(contract_addr, None, f'contract_addr: {contract_addr} should not None')

        eth_code = get_eth_contract_code(conn, contract_addr)
        self.assertNotEqual(eth_code, bytearray(b''), f'eth_code: {eth_code} should not None')

        print(f'ETH code: {eth_code[:30]}')
        print(f'Contract addr: {contract_addr}')

        # Setup --> Transfer ERC20 token to other
        prev_src_erc20 = get_erc20_balance(conn, contract_addr, ETH_ALICE_SLOT_ADDR)
        print(f'Alice\'s before ERC20 token: {prev_src_erc20}')

        # Execute --> Transfer ERC20 token to other
        receipt = transfer_erc20_token(conn, kp_src, eth_src, ETH_DST_ADDR, contract_addr)
        self.assertTrue(receipt.is_success, f'transfer erc20 token failed: {receipt.error_message}')

        # Check --> Transfer ERC20 token to other
        after_src_erc20 = get_erc20_balance(conn, contract_addr, ETH_ALICE_SLOT_ADDR)
        print(f'Alice\'s after ERC20 token: {after_src_erc20}')
        self.assertEqual(after_src_erc20 + ERC_TOKEN_TRANSFER, prev_src_erc20)

        after_dst_erc20 = get_erc20_balance(conn, contract_addr, ETH_BOB_SLOT_ADDR)
        print(f'Bob\'s after ERC20 token: {after_dst_erc20}')
        self.assertEqual(after_dst_erc20, ERC_TOKEN_TRANSFER)
