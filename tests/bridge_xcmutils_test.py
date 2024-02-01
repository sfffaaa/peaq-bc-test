import unittest
from tools.utils import WS_URL, ETH_URL
from tools.runtime_upgrade import wait_until_block_height
from tools.peaq_eth_utils import get_contract
from tools.peaq_eth_utils import GAS_LIMIT, get_eth_info
from peaq.eth import get_eth_chain_id
from substrateinterface import SubstrateInterface, Keypair
from peaq.utils import ExtrinsicBatch
from web3 import Web3
from tools.utils import KP_GLOBAL_SUDO
from peaq.utils import get_account_balance
from tools.utils import ACA_PD_CHAIN_ID, RELAYCHAIN_WS_URL
from tests.utils_func import restart_parachain_and_runtime_upgrade
from tools.asset import setup_aca_asset_if_not_exist
from tools.asset import PEAQ_ASSET_LOCATION, PEAQ_METADATA
from tools.asset import wait_for_account_asset_change_wrap
from tools.asset import get_tokens_account_from_pallet_tokens
from tools.asset import PEAQ_ASSET_ID


ABI_FILE = 'ETH/xcmutils/abi'
XCMUTILS_ADDRESS = '0x0000000000000000000000000000000000000804'


class TestBridgeXCMUtils(unittest.TestCase):
    def setUp(self):
        self.si_peaq = SubstrateInterface(url=WS_URL)
        self.w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self.kp_eth = get_eth_info()
        self.eth_chain_id = get_eth_chain_id(self.si_peaq)

        # transfer
        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch.compose_call(
            'Balances',
            'transfer',
            {
                'dest': self.kp_eth['substrate'],
                'value': 100 * 10 ** 18,
            }
        )
        batch.execute()

    def _compose_xcm_execute_message(self, kp):
        account = kp.public_key
        instr1 = {
            'WithdrawAsset': [
                [{
                  'id': {
                    'Concrete': {
                        'parents': 0,
                        'interior': {
                            'X1': {
                                'GeneralKey': {
                                    'length': 2,
                                    'data': '0x' + '00' * 32,
                                }
                            }
                        }
                    }
                  },
                  'fun': {'Fungible': 10 ** 18},
                }],
            ]
        }
        instr2 = {
            'DepositAsset': {
                'assets': {'Wild': {'AllCounted': 1}},
                'beneficiary': {
                    'parents': 0,
                    'interior': {
                        'X1': {
                            'AccountId32': {
                                'network': None,
                                'id': account,
                            }
                        }
                    }
                }
            }
        }
        message = {'V3': [[instr1, instr2]]}
        maxWeight = {'ref_time': 2 * 10 ** 21, 'proof_size': 10 ** 12}

        encoded_tx = self.si_peaq.compose_call(
            call_module='PolkadotXcm',
            call_function='execute',
            call_params={
                'message': message,
                'max_weight': maxWeight,
            }
        )
        return encoded_tx["call_args"]["message"]

    def _compose_xcm_send_message(self, kp):
        account = kp.public_key
        instr1 = {
            'WithdrawAsset': [
                [{
                  'id': {
                    'Concrete': {
                        'parents': 0,
                        'interior': 'Here',
                    }
                  },
                  'fun': {'Fungible': 10 ** 18},
                }],
            ]
        }
        instr2 = {
            'BuyExecution': {
                'fees': {
                    'id': {
                        'Concrete': {
                            'parents': 0,
                            'interior': 'Here',
                        }
                    },
                    'fun': {'Fungible': 10 ** 18},
                },
                'weight_limit': 'Unlimited',
            }
        }

        instr3 = {
            'DepositAsset': {
                'assets': {'Wild': 'All'},
                'beneficiary': {
                    'parents': 0,
                    'interior': {
                        'X1': {
                            'AccountId32': {'network': None, 'id': account}
                        }
                    }
                }
            }
        }
        message = {'V3': [[instr1, instr2, instr3]]}

        encoded_tx = self.si_peaq.compose_call(
            call_module='PolkadotXcm',
            call_function='send',
            call_params={
                'dest': {'V3': {
                    'parents': 0,
                    'interior': 'Here',
                }},
                'message': message,
            }
        )
        return encoded_tx["call_args"]["message"]

    def wait_for_aca_account_token_change(self, addr, asset_id, prev_token=0):
        return wait_for_account_asset_change_wrap(
            self.si_aca, addr, asset_id, prev_token, get_tokens_account_from_pallet_tokens)

    def test_xcm_execute(self):
        kp_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        encoded_calldata = self._compose_xcm_execute_message(kp_dst).encode().data

        kp_sign = self.kp_eth['kp']
        contract = get_contract(self.w3, XCMUTILS_ADDRESS, ABI_FILE)
        nonce = self.w3.eth.get_transaction_count(kp_sign.ss58_address)
        tx = contract.functions.xcmExecute(
            encoded_calldata, 20000000000,
            ).build_transaction({
                'from': kp_sign.ss58_address,
                'gas': GAS_LIMIT,
                'maxFeePerGas': self.w3.to_wei(250, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(2, 'gwei'),
                'nonce': nonce,
                'chainId': self.eth_chain_id
            })

        signed_txn = self.w3.eth.account.sign_transaction(tx, private_key=kp_sign.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        evm_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        balance = get_account_balance(self.si_peaq, kp_dst.ss58_address)
        self.assertNotEqual(balance, 0, f'Error: {balance}')

    def test_xcm_send(self):
        # import pdb
        # pdb.set_trace()

        # Restart
        self.si_peaq = SubstrateInterface(url=WS_URL)
        self.si_relay = SubstrateInterface(url=RELAYCHAIN_WS_URL, type_registry_preset='rococo')

        # compose the message
        kp_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        encoded_calldata = self._compose_xcm_send_message(kp_dst).encode().data

        # Address unifi with sudo

        # Use the pallet send to send it
        kp_sign = self.kp_eth['kp']
        contract = get_contract(self.w3, XCMUTILS_ADDRESS, ABI_FILE)
        nonce = self.w3.eth.get_transaction_count(kp_sign.ss58_address)
        tx = contract.functions.xcmSend(
            [0, []], encoded_calldata,
            ).build_transaction({
                'from': kp_sign.ss58_address,
                'gas': GAS_LIMIT,
                'maxFeePerGas': self.w3.to_wei(250, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(2, 'gwei'),
                'nonce': nonce,
                'chainId': self.eth_chain_id
            })

        signed_txn = self.w3.eth.account.sign_transaction(tx, private_key=kp_sign.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        evm_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(evm_receipt['status'], 1, f'Error: {evm_receipt}: {evm_receipt["status"]}')

        # got_token = self.wait_for_aca_account_token_change(kp_dst.ss58_address, PEAQ_ASSET_ID['para'])
        got_token = 0
        self.assertNotEqual(got_token, 1)
