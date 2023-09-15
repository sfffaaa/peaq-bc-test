from substrateinterface import SubstrateInterface, Keypair, KeypairType
from peaq.eth import calculate_evm_account_hex, calculate_evm_addr, calculate_evm_account
from peaq.extrinsic import transfer
from tools.utils import WS_URL, ETH_URL
from peaq.eth import get_eth_chain_id
from tools.peaq_eth_utils import call_eth_transfer_a_lot, get_contract, generate_random_hex
from tools.peaq_eth_utils import TX_SUCCESS_STATUS
from web3 import Web3

import unittest


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
TOKEN_NUM = 10000 * pow(10, 15)


def _calcualte_evm_basic_req(substrate, w3, addr):
    return {
        'from': addr,
        'gas': GAS_LIMIT,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': w3.eth.get_transaction_count(addr),
        'chainId': get_eth_chain_id(substrate)
    }


def _eth_add_item(substrate, w3, contract, eth_kp_src, item_type, item):
    tx = contract.functions.add_item(item_type, item).build_transaction(
        _calcualte_evm_basic_req(substrate, w3, eth_kp_src.ss58_address)
    )

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_receipt


def _eth_update_item(substrate, w3, contract, eth_kp_src, item_type, item):
    tx = contract.functions.update_item(item_type, item).build_transaction(
        _calcualte_evm_basic_req(substrate, w3, eth_kp_src.ss58_address)
    )

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_receipt


class TestBridgeStorage(unittest.TestCase):

    def setUp(self):
        self._eth_src = calculate_evm_addr(KP_SRC.ss58_address)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._substrate = SubstrateInterface(url=WS_URL)
        self._eth_kp_src = Keypair.create_from_private_key(ETH_PRIVATE_KEY, crypto_type=KeypairType.ECDSA)
        self._account = calculate_evm_account_hex(self._eth_kp_src.ss58_address)

    def check_item_from_event(self, event, account, item_type, item):
        events = event.get_all_entries()
        self.assertEqual(f"0x{events[0]['args']['account'].hex()}", account)
        self.assertEqual(f"0x{events[0]['args']['item_type'].hex()}", f"{item_type}")
        self.assertEqual(f"0x{events[0]['args']['item'].hex()}", f"{item}")

    def test_bridge_storage(self):
        substrate = self._substrate
        eth_src = self._eth_src
        w3 = self._w3
        eth_kp_src = self._eth_kp_src
        account = self._account

        # setup
        transfer(substrate, KP_SRC, calculate_evm_account(eth_src), TOKEN_NUM)
        receipt = call_eth_transfer_a_lot(substrate, KP_SRC, eth_src, eth_kp_src.ss58_address.lower())
        self.assertTrue(receipt.is_success, f'Failed to transfer token to {eth_kp_src.ss58_address}')

        contract = get_contract(w3, STORAGE_ADDRESS, ABI_FILE)

        # Execute: Add
        tx_receipt = _eth_add_item(substrate, w3, contract, eth_kp_src, ITEM_TYPE, ITEM)
        self.assertEqual(tx_receipt['status'], TX_SUCCESS_STATUS)
        block_idx = tx_receipt['blockNumber']

        # Cehck
        data = contract.functions.get_item(account, ITEM_TYPE).call()
        self.assertEqual(f'0x{data.hex()}', ITEM)
        event = contract.events.ItemAdded.create_filter(fromBlock=block_idx, toBlock=block_idx)
        self.check_item_from_event(event, account, ITEM_TYPE, ITEM)

        # Executed: Update
        tx_receipt = _eth_update_item(substrate, w3, contract, eth_kp_src, ITEM_TYPE, NEW_ITEM)
        self.assertEqual(tx_receipt['status'], TX_SUCCESS_STATUS)
        block_idx = tx_receipt['blockNumber']

        # Check
        data = contract.functions.get_item(account, ITEM_TYPE).call()
        self.assertEqual(f'0x{data.hex()}', NEW_ITEM)
        event = contract.events.ItemUpdated.create_filter(fromBlock=block_idx, toBlock=block_idx)
        self.check_item_from_event(event, account, ITEM_TYPE, NEW_ITEM)
