import unittest
from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import WS_URL, ETH_URL
from tools.utils import KP_GLOBAL_SUDO
from tools.asset import batch_create_asset, batch_mint, get_valid_asset_id
from tools.asset import get_asset_balance
from peaq.sudo_extrinsic import fund, funds
from tools.peaq_eth_utils import get_eth_balance
from peaq.eth import get_eth_chain_id
from peaq.utils import ExtrinsicBatch
from peaq.utils import get_block_hash
# import eth_account
from eth_account import Account as ETHAccount
from eth_account.messages import encode_structured_data
from tools.peaq_eth_utils import calculate_asset_to_evm_address
from tools.peaq_eth_utils import GAS_LIMIT, get_contract
from web3 import Web3
import pytest

ABI_FILE = 'ETH/erc20/abi'
FUND_NUMBER = 3 * 10 ** 18


def claim_account(substrate, kp_sub, kp_eth, eth_signature):
    batch = ExtrinsicBatch(substrate, kp_sub)
    batch_claim_account(batch, kp_eth, eth_signature)
    return batch.execute()


def batch_claim_account(batch, kp_eth, eth_signature):
    batch.compose_call(
        'EVMAccounts',
        'claim_account',
        {
            'eth_address': kp_eth.ss58_address,
            'eth_signature': eth_signature,
        }
    )


def gen_eth_signature(substrate, kp_sub, kp_eth, chain_id):
    block_hash_zero = get_block_hash(substrate, 0)
    message = {
        'types': {
            'EIP712Domain': [
                {'type': 'string', 'name': 'name'},
                {'type': 'string', 'name': 'version'},
                {'type': 'uint256', 'name': 'chainId'},
                {'type': 'bytes32', 'name': 'salt'},
            ],
            'Transaction': [
                {'type': 'bytes', 'name': 'substrateAddress'},
            ]
        },
        'primaryType': 'Transaction',
        'domain': {
            'name': 'Peaq EVM claim',
            'version': '1',
            'chainId': chain_id,
            # Block hash zero
            'salt': bytes.fromhex(block_hash_zero[2:]),
        },
        'message': {
            'substrateAddress': kp_sub.public_key,
        }
    }
    signature = ETHAccount.sign_message(encode_structured_data(message), kp_eth.private_key)

    return signature.signature.hex()


def evm_erc20_trasfer(asset_id, kp_eth_src, kp_eth_dst, amount, eth_chain_id):
    erc20_addr = calculate_asset_to_evm_address(asset_id)
    w3 = Web3(Web3.HTTPProvider(ETH_URL))
    contract = get_contract(w3, erc20_addr, ABI_FILE)
    nonce = w3.eth.get_transaction_count(kp_eth_src.ss58_address)
    tx = contract.functions.transfer(kp_eth_dst.ss58_address, amount).build_transaction({
        'from': kp_eth_src.ss58_address,
        'gas': GAS_LIMIT,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': nonce,
        'chainId': eth_chain_id})

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=kp_eth_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_receipt


class TestPalletEvmAccounts(unittest.TestCase):
    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)
        self._eth_chain_id = get_eth_chain_id(self._substrate)

    @pytest.mark.skip(reason="Success")
    def test_claim_account_native(self):
        kp_sub = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        kp_eth = Keypair.create_from_mnemonic(Keypair.generate_mnemonic(), crypto_type=KeypairType.ECDSA)
        receipt = fund(self._substrate, KP_GLOBAL_SUDO, kp_sub, FUND_NUMBER)
        self.assertTrue(receipt.is_success, f'Failed to fund {kp_sub.ss58_address}, {receipt.error_message}')

        signature = gen_eth_signature(self._substrate, kp_sub, kp_eth, self._eth_chain_id)

        # Execute
        receipt = claim_account(self._substrate, kp_sub, kp_eth, signature)
        self.assertTrue(receipt.is_success, f'Failed to claim account {kp_sub.ss58_address}, {receipt.error_message}')

        # Check
        now_value = get_eth_balance(self._substrate, kp_eth.ss58_address)
        self.assertNotEqual(now_value, 0, f'The balance is the same, {now_value} == 0')

    def test_claim_account_erc20(self):
        # Create two sub wallet
        # Create two eth wallet
        # Link two wallets
        # Mint one asset to sub wallet
        # Transfer erc20 from one eth to another eth
        # Check the sub wallet have the asset
        transfer_number = 7 * 10 ** 16
        kp_sub_src, kp_sub_dst = [
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic()),
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        ]
        kp_eth_src, kp_eth_dst = [
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic(), crypto_type=KeypairType.ECDSA),
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic(), crypto_type=KeypairType.ECDSA)
        ]
        receipt = funds(
            self._substrate, KP_GLOBAL_SUDO,
            [kp_sub_src.ss58_address, kp_sub_dst.ss58_address],
            FUND_NUMBER)
        self.assertTrue(receipt.is_success, f'Failed to fund {receipt.error_message}')

        for kp_sub, kp_eth in [[kp_sub_src, kp_eth_src], [kp_sub_dst, kp_eth_dst]]:
            signature = gen_eth_signature(
                self._substrate, kp_sub, kp_eth, self._eth_chain_id)
            receipt = claim_account(self._substrate, kp_sub, kp_eth, signature)
            self.assertTrue(
                receipt.is_success,
                f'Failed to claim account {kp_sub.ss58_address}, {receipt.error_message}')

        # Setup and mint erc20 tokens
        asset_id = get_valid_asset_id(self._substrate)
        batch = ExtrinsicBatch(self._substrate, KP_GLOBAL_SUDO)
        batch_create_asset(batch, KP_GLOBAL_SUDO.ss58_address, asset_id)
        batch_mint(batch, kp_sub_src.ss58_address, asset_id, FUND_NUMBER)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Failed to mint {receipt.error_message}')

        # Transfer erc20 tokens
        evm_receipt = evm_erc20_trasfer(
            asset_id, kp_eth_src, kp_eth_dst,
            transfer_number, self._eth_chain_id)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        # Check
        balance = get_asset_balance(self._substrate, kp_sub_src.ss58_address, asset_id)['balance']
        self.assertEqual(
            balance, FUND_NUMBER - transfer_number,
            f'Balance is not correct, {balance} != {FUND_NUMBER - transfer_number}')
        balance = get_asset_balance(self._substrate, kp_sub_dst.ss58_address, asset_id)['balance']
        self.assertEqual(
            balance, transfer_number,
            f'Balance is not correct, {balance} != {transfer_number}')

    @pytest.mark.skip(reason="Not implemented")
    def test_claim_default_account(self):
        pass
