import unittest
from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.asset import batch_create_asset, get_valid_asset_id, batch_set_metadata, batch_mint
from tools.utils import WS_URL, ETH_URL
from peaq.utils import ExtrinsicBatch
from peaq.eth import calculate_evm_account
from tools.peaq_eth_utils import get_contract
from peaq.eth import get_eth_chain_id
from web3 import Web3


ABI_FILE = 'ETH/erc20/abi'
ERC20_ADDR_PREFIX = '0xffffffff00000000000000000000000000000000'
GAS_LIMIT = 4294967

TEST_METADATA = {
    'name': 'WOW',
    'symbol': 'WOW',
    'decimals': 18,
}


def calculate_asset_to_evm_address(asset_id):
    number = int(ERC20_ADDR_PREFIX, 16) + asset_id['Token']
    return Web3.to_checksum_address(hex(number))


def batch_transfer(batch, addr_dst, token_num):
    batch.compose_call(
        'Balances',
        'transfer',
        {
            'dest': addr_dst,
            'value': token_num
        }
    )


def get_eth_info():
    mnemonic = Keypair.generate_mnemonic()
    kp = Keypair.create_from_mnemonic(mnemonic, crypto_type=KeypairType.ECDSA)
    return {
        'kp': kp,
        'substrate': calculate_evm_account(kp.ss58_address),
        'eth': kp.ss58_address
    }


class erc20_asset_test(unittest.TestCase):
    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._kp_creator = Keypair.create_from_uri('//Alice')
        self._kp_admin = Keypair.create_from_uri('//Bob')
        self._eth_kp_src = get_eth_info()
        self._eth_kp_dst = get_eth_info()
        self._eth_chain_id = get_eth_chain_id(self._substrate)

    def evm_erc20_transfer(self, contract, eth_kp_src, eth_dst, token_num):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.transfer(eth_dst, token_num).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self._eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def test_metadata_asset(self):
        asset_id = get_valid_asset_id(self._substrate)
        batch = ExtrinsicBatch(self._substrate, self._kp_creator)
        batch_create_asset(batch, self._kp_creator.ss58_address, asset_id)
        batch_set_metadata(
            batch, asset_id,
            TEST_METADATA['name'], TEST_METADATA['symbol'], TEST_METADATA['decimals'])
        batch_mint(batch, self._kp_admin.ss58_address, asset_id, 10 ** 18)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Error: {receipt.error_message}')

        erc20_addr = calculate_asset_to_evm_address(asset_id)
        contract = get_contract(self._w3, erc20_addr, ABI_FILE)
        data = contract.functions.name().call()
        self.assertEqual(data, TEST_METADATA['name'], f'Error: {data} != {TEST_METADATA["name"]}')
        data = contract.functions.symbol().call()
        self.assertEqual(data, TEST_METADATA['symbol'], f'Error: {data} != {TEST_METADATA["symbol"]}')
        data = contract.functions.decimals().call()
        self.assertEqual(data, TEST_METADATA['decimals'], f'Error: {data} != {TEST_METADATA["decimals"]}')

    def test_transfer_asset(self):
        total_token_num = 100 * 10 ** 18
        erc_transfer_num = 10 ** 16
        asset_id = get_valid_asset_id(self._substrate)
        batch = ExtrinsicBatch(self._substrate, self._kp_creator)
        batch_transfer(batch, self._eth_kp_src['substrate'], total_token_num)
        batch_transfer(batch, self._eth_kp_dst['substrate'], total_token_num)
        batch_create_asset(batch, self._kp_creator.ss58_address, asset_id)
        batch_set_metadata(
            batch, asset_id,
            TEST_METADATA['name'], TEST_METADATA['symbol'], TEST_METADATA['decimals'])
        batch_mint(batch, self._eth_kp_src['substrate'], asset_id, total_token_num)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Error: {receipt.error_message}')
        balance = self._w3.eth.get_balance(self._eth_kp_src['eth'])
        self.assertNotEqual(balance, 0, f'Error: {balance} != {0}')

        erc20_addr = calculate_asset_to_evm_address(asset_id)
        contract = get_contract(self._w3, erc20_addr, ABI_FILE)

        # Check minted to eth address
        evm_src_balance = contract.functions.balanceOf(self._eth_kp_src['eth']).call()
        self.assertEqual(evm_src_balance, total_token_num, f'Error: {evm_src_balance} != {10 ** 18}')

        # Execute transfer
        evm_receipt = self.evm_erc20_transfer(
            contract,
            self._eth_kp_src['kp'],
            self._eth_kp_dst['eth'],
            erc_transfer_num)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        # Check balance after transfer
        evm_src_balance = contract.functions.balanceOf(self._eth_kp_src['eth']).call()
        self.assertEqual(
            evm_src_balance, total_token_num - erc_transfer_num,
            f'Error: {evm_src_balance} != {total_token_num - erc_transfer_num}')
        evm_dst_balance = contract.functions.balanceOf(self._eth_kp_dst['eth']).call()
        self.assertEqual(
            evm_dst_balance, erc_transfer_num,
            f'Error: {evm_dst_balance} != {erc_transfer_num}')
