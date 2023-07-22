import sys
sys.path.append('./')
import unittest

from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import transfer, calculate_evm_account, calculate_evm_addr, SCALE_CODEC
from tools.peaq_eth_utils import call_eth_transfer_a_lot, get_contract, generate_random_hex
from tools.utils import WS_URL, ETH_URL, get_eth_chain_id
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


class TestBridgeDid(unittest.TestCase):

    def _eth_add_attribute(self, contract, eth_kp_src, kp_src, key, value):
        w3 = self.w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.add_attribute(kp_src.public_key, key, value, VALIDITY).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self.eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(tx_receipt['status'], 1)
        print('✅ eth_add_attribute, Success')
        return tx_receipt['blockNumber']

    def _eth_update_attribute(self, contract, eth_kp_src, kp_src, key, value):
        w3 = self.w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.update_attribute(kp_src.public_key, key, value, VALIDITY).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self.eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(tx_receipt['status'], 1)
        print('✅ eth_update_attribute, Success')
        return tx_receipt['blockNumber']

    def _eth_remove_attribute(self, contract, eth_kp_src, kp_src, key):
        w3 = self.w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.remove_attribute(kp_src.public_key, key).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self.eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(tx_receipt['status'], 1)
        print('✅ eth_remove_attribute, Success')
        return tx_receipt['blockNumber']

    def setUp(self):
        self.w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self.substrate = SubstrateInterface(url=WS_URL, type_registry=SCALE_CODEC)
        self.eth_chain_id = get_eth_chain_id(self.substrate)

    def test_bridge_did(self):
        eth_src = calculate_evm_addr(KP_SRC.ss58_address)
        token_num = 10000 * pow(10, 15)
        transfer(self.substrate, KP_SRC, calculate_evm_account(eth_src), token_num)
        eth_kp_src = Keypair.create_from_private_key(ETH_PRIVATE_KEY, crypto_type=KeypairType.ECDSA)
        call_eth_transfer_a_lot(self.substrate, KP_SRC, eth_src, eth_kp_src.ss58_address.lower())

        contract = get_contract(self.w3, DID_ADDRESS, ABI_FILE)

        block_idx = self._eth_add_attribute(contract, eth_kp_src, KP_SRC, KEY, VALUE)
        data = contract.functions.read_attribute(KP_SRC.public_key, KEY).call()
        self.assertEqual(f'0x{data[0].hex()}', KEY)
        self.assertEqual(f'0x{data[1].hex()}', VALUE)

        event = contract.events.AddAttribute.create_filter(fromBlock=block_idx, toBlock=block_idx)
        events = event.get_all_entries()
        self.assertEqual(f"{events[0]['args']['sender'].upper()}", f"0X{eth_kp_src.public_key.hex().upper()}")
        self.assertEqual(f"{events[0]['args']['did_account'].hex()}", f"{KP_SRC.public_key.hex()}")
        self.assertEqual(f"0x{events[0]['args']['name'].hex()}", f"{KEY}")
        self.assertEqual(f"0x{events[0]['args']['value'].hex()}", f"{VALUE}")
        self.assertEqual(f"{events[0]['args']['validity']}", f"{VALIDITY}")

        block_idx = self._eth_update_attribute(contract, eth_kp_src, KP_SRC, KEY, NEW_VALUE)
        data = contract.functions.read_attribute(KP_SRC.public_key, KEY).call()
        self.assertEqual(f'0x{data[0].hex()}', KEY)
        self.assertEqual(f'0x{data[1].hex()}', NEW_VALUE)

        event = contract.events.UpdateAttribute.create_filter(fromBlock=block_idx, toBlock=block_idx)
        events = event.get_all_entries()
        self.assertEqual(f"{events[0]['args']['sender'].upper()}", f"0X{eth_kp_src.public_key.hex().upper()}")
        self.assertEqual(f"{events[0]['args']['did_account'].hex()}", f"{KP_SRC.public_key.hex()}")
        self.assertEqual(f"0x{events[0]['args']['name'].hex()}", f"{KEY}")
        self.assertEqual(f"0x{events[0]['args']['value'].hex()}", f"{NEW_VALUE}")
        self.assertEqual(f"{events[0]['args']['validity']}", f"{VALIDITY}")

        block_idx = self._eth_remove_attribute(contract, eth_kp_src, KP_SRC, KEY)
        self.assertRaises(ValueError, contract.functions.read_attribute(KP_SRC.public_key, KEY).call)

        event = contract.events.RemoveAttribte.create_filter(fromBlock=block_idx, toBlock=block_idx)
        events = event.get_all_entries()
        self.assertEqual(f"{events[0]['args']['did_account'].hex()}", f"{KP_SRC.public_key.hex()}")
        self.assertEqual(f"0x{events[0]['args']['name'].hex()}", f"{KEY}")

        print('Passssss test_did_bridge')
