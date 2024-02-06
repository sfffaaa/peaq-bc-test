import unittest
from substrateinterface import SubstrateInterface
from tools.asset import get_valid_asset_id
from tools.utils import WS_URL, ETH_URL
from peaq.utils import ExtrinsicBatch
from tools.peaq_eth_utils import get_contract
from tools.peaq_eth_utils import get_eth_chain_id
from tools.peaq_eth_utils import calculate_asset_to_evm_address
from tools.peaq_eth_utils import GAS_LIMIT, get_eth_info
from tools.utils import KP_GLOBAL_SUDO
from web3 import Web3


ABI_FILE = 'ETH/asset-factory/abi'
ASSET_FACTORY_ADDR = '0x0000000000000000000000000000000000000806'

TEST_METADATA = {
    'name': 'WOW',
    'symbol': 'WOW',
    'decimals': 18,
}


def batch_transfer(batch, addr_dst, token_num):
    batch.compose_call(
        'Balances',
        'transfer',
        {
            'dest': addr_dst,
            'value': token_num
        }
    )


class bridge_asset_factory_test(unittest.TestCase):
    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._kp_creator = get_eth_info()
        self._kp_admin = get_eth_info()
        self._eth_chain_id = get_eth_chain_id(self._substrate)

    def _fund_users(self):
        # Fund users
        batch = ExtrinsicBatch(self._substrate, KP_GLOBAL_SUDO)
        batch.compose_call(
            'Balances',
            'transfer',
            {
                'dest': self._kp_creator['substrate'],
                'value': 100 * 10 ** 18,
            }
        )
        batch.compose_call(
            'Balances',
            'transfer',
            {
                'dest': self._kp_admin['substrate'],
                'value': 100 * 10 ** 18,
            }
        )
        batch.execute()

    def evm_asset_create(self, contract, eth_kp_src, asset_id, eth_admin, min_balance):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.create(asset_id['Token'], eth_admin.ss58_address, min_balance).build_transaction({
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

    def evm_asset_set_metadata(self, contract, eth_kp_src, asset_id, name, symbol, decimal):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.setMetadata(
            asset_id['Token'],
            f'0x{name.encode().hex()}',
            f'0x{symbol.encode().hex()}',
            decimal
        ).build_transaction({
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

    def evm_asset_set_min_balance(self, contract, eth_kp_src, asset_id, min_balance):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.setMinBalance(asset_id['Token'], min_balance).build_transaction({
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

    def evm_asset_set_team(self, contract, eth_kp_src, asset_id, teams):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.setTeam(
            asset_id['Token'],
            teams[0]['kp'].ss58_address,
            teams[1]['kp'].ss58_address,
            teams[2]['kp'].ss58_address
        ).build_transaction({
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

    def evm_asset_transfer_ownership(self, contract, eth_kp_src, asset_id, eth_owner):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.transferOwnership(
            asset_id['Token'],
            eth_owner.ss58_address
        ).build_transaction({
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

    def evm_asset_start_destroy(self, contract, eth_kp_src, asset_id):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.startDestroy(
            asset_id['Token'],
        ).build_transaction({
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

    def evm_asset_finish_destroy(self, contract, eth_kp_src, asset_id):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.finishDestroy(
            asset_id['Token'],
        ).build_transaction({
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

    def test_bridge_asset_create(self):
        self._fund_users()

        asset_id = get_valid_asset_id(self._substrate)

        contract = get_contract(self._w3, ASSET_FACTORY_ADDR, ABI_FILE)

        # TODO Change to the batch func
        evm_receipt = self.evm_asset_create(
            contract, self._kp_creator['kp'], asset_id, self._kp_admin['kp'], 555)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        asset = self._substrate.query("Assets", "Asset", [asset_id]).value
        self.assertEqual(asset['owner'], self._kp_creator['substrate'])
        self.assertEqual(asset['admin'], self._kp_admin['substrate'])
        self.assertEqual(asset['min_balance'], 555)

    def test_brdige_addr_convert(self):
        asset_id = get_valid_asset_id(self._substrate)

        contract = get_contract(self._w3, ASSET_FACTORY_ADDR, ABI_FILE)
        erc20_addr = contract.functions.convertAssetIdToAddress(asset_id['Token']).call()
        self.assertEqual(erc20_addr, calculate_asset_to_evm_address(asset_id))

    def test_bridge_asset_set_metadata(self):
        self._fund_users()

        asset_id = get_valid_asset_id(self._substrate)

        contract = get_contract(self._w3, ASSET_FACTORY_ADDR, ABI_FILE)

        evm_receipt = self.evm_asset_create(
            contract, self._kp_creator['kp'], asset_id, self._kp_admin['kp'], 555)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        evm_receipt = self.evm_asset_set_metadata(
            contract, self._kp_creator['kp'], asset_id, 'Moon', 'Moon', 18)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        asset = self._substrate.query("Assets", "Metadata", [asset_id]).value
        self.assertEqual(asset['name'], 'Moon')
        self.assertEqual(asset['symbol'], 'Moon')
        self.assertEqual(asset['decimals'], 18)

    def test_bridge_asset_set_min_balance(self):
        self._fund_users()

        asset_id = get_valid_asset_id(self._substrate)

        contract = get_contract(self._w3, ASSET_FACTORY_ADDR, ABI_FILE)

        evm_receipt = self.evm_asset_create(
            contract, self._kp_creator['kp'], asset_id, self._kp_admin['kp'], 555)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        evm_receipt = self.evm_asset_set_min_balance(
            contract, self._kp_creator['kp'], asset_id, 10101)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        asset = self._substrate.query("Assets", "Asset", [asset_id]).value
        self.assertEqual(asset['min_balance'], 10101)

    def test_bridge_asset_set_team(self):
        self._fund_users()

        asset_id = get_valid_asset_id(self._substrate)

        contract = get_contract(self._w3, ASSET_FACTORY_ADDR, ABI_FILE)
        teams = [get_eth_info() for _ in range(3)]

        evm_receipt = self.evm_asset_create(
            contract, self._kp_creator['kp'], asset_id, self._kp_admin['kp'], 555)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        evm_receipt = self.evm_asset_set_team(
            contract, self._kp_creator['kp'], asset_id, teams)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        asset = self._substrate.query("Assets", "Asset", [asset_id]).value
        self.assertEqual(asset['issuer'], teams[0]['substrate'])
        self.assertEqual(asset['admin'], teams[1]['substrate'])
        self.assertEqual(asset['freezer'], teams[2]['substrate'])

    def test_bridge_asset_transfer_ownership(self):
        self._fund_users()

        asset_id = get_valid_asset_id(self._substrate)

        contract = get_contract(self._w3, ASSET_FACTORY_ADDR, ABI_FILE)

        evm_receipt = self.evm_asset_create(
            contract, self._kp_creator['kp'], asset_id, self._kp_admin['kp'], 555)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        evm_receipt = self.evm_asset_transfer_ownership(
            contract, self._kp_creator['kp'], asset_id, self._kp_admin['kp'])
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        asset = self._substrate.query("Assets", "Asset", [asset_id]).value
        self.assertEqual(asset['owner'], self._kp_admin['substrate'])

    def test_bridge_asset_destroy(self):
        self._fund_users()

        asset_id = get_valid_asset_id(self._substrate)

        contract = get_contract(self._w3, ASSET_FACTORY_ADDR, ABI_FILE)

        evm_receipt = self.evm_asset_create(
            contract, self._kp_creator['kp'], asset_id, self._kp_admin['kp'], 555)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        evm_receipt = self.evm_asset_start_destroy(
            contract, self._kp_creator['kp'], asset_id)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        asset = self._substrate.query("Assets", "Asset", [asset_id]).value
        self.assertEqual(asset['status'], 'Destroying')

        evm_receipt = self.evm_asset_finish_destroy(
            contract, self._kp_creator['kp'], asset_id)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        asset = self._substrate.query("Assets", "Asset", [asset_id]).value
        self.assertEqual(asset, None)
