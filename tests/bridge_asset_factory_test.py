import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.asset import batch_create_asset, get_valid_asset_id, batch_set_metadata, batch_mint
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

    def test_bridge_asset_create(self):
        self._fund_users()

        asset_id = get_valid_asset_id(self._substrate)

        # erc20_addr = calculate_asset_to_evm_address(asset_id)
        contract = get_contract(self._w3, ASSET_FACTORY_ADDR, ABI_FILE)

        evm_receipt = self.evm_asset_create(
            contract, self._kp_creator['kp'], asset_id, self._kp_admin['kp'], 555)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        asset = self._substrate.query("Assets", "Asset", [asset_id]).value
        self.assertEqual(asset['owner'], self._kp_creator['substrate'])
        self.assertEqual(asset['admin'], self._kp_admin['substrate'])
        self.assertEqual(asset['min_balance'], 555)
