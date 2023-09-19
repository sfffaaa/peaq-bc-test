import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, RELAYCHAIN_WS_URL
from tools.utils import transfer, TOKEN_NUM_BASE
from tools.payload import user_extrinsic_send
import time


@user_extrinsic_send
def transfer_currencies(substrate, kp_sign, kp_other, token_type, token_num, token_base=0):
    if not token_base:
        token_base = TOKEN_NUM_BASE

    return substrate.compose_call(
        call_module='Currencies',
        call_function='transfer',
        call_params={
            'dest': {
                'Id': kp_other.ss58_address,
            },
            'amount': token_num * token_base,
            'currency_id': {
                'Token': token_type,
            }
        })


@user_extrinsic_send
def send_from_xcm(substrate, kp_sign, paraid):
    return substrate.compose_call(
        call_module='XcmPallet',
        call_function='reserve_transfer_assets',
        call_params={
            'dest': {
                'V2': {
                    'parents': 0,
                    'interior': {
                        'X1': {
                            'Parachain': paraid,
                        }
                    },
                }
            },
            'beneficiary': {
                'V2': {
                    'parents': 0,
                    'interior': {
                        'X1': {
                            'AccountId32': {
                                'network': 'Any',
                                'id': kp_sign.public_key,
                            }
                        }
                    },
                }
            },
            'assets': {
                'V2': [[{
                    'id': {
                        'Concrete': {
                            'parents': 0,
                            'interior': 'Here'
                        }
                    },
                    'fun': {
                        'Fungible': 1000000000000000
                    }
                }]]
            },
            'fee_asset_item': 0,
        })


class TestExitentialDeposits(unittest.TestCase):
    def get_existential_deposit(self):
        result = self.substrate.get_constant(
            'Balances',
            'ExistentialDeposit',
        )
        return result.value

    def get_tokens_account(self, kp):
        result = self.substrate.query(
            'Tokens',
            'Accounts',
            params=[
                kp.ss58_address,
                {'Token': 'DOT'}
            ]
        )
        return result.value['free']

    def get_parachain_id(self, relay_substrate):
        result = relay_substrate.query(
            'Paras',
            'Parachains',
        )
        return result.value[0]

    def send_relaychain_token(self, kp):
        relay_substrate = SubstrateInterface(url=RELAYCHAIN_WS_URL, type_registry_preset='rococo')
        parachain_id = self.get_parachain_id(relay_substrate)
        receipt = send_from_xcm(relay_substrate, kp, parachain_id)
        return receipt

    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL,)
        self.alice = Keypair.create_from_uri('//Alice')
        self.kp = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())

    def test_local_token(self):
        token = self.get_existential_deposit()
        self.assertGreater(token, 2)
        token /= 2

        # Execute -> Send local token to another account but below the Exitential Deposits
        receipt = transfer(
            self.substrate,
            self.alice,
            self.kp.ss58_address,
            token,
            1
        )

        # Check: the error happens
        self.assertFalse(receipt.is_success)
        self.assertEqual(receipt.error_message['name'], 'ExistentialDeposit')

    def test_foreigner_token(self):
        token = self.get_existential_deposit()
        self.assertGreater(token, 2)
        token /= 2

        # Send foreigner tokens from the relay chain
        receipt = self.send_relaychain_token(self.alice)
        self.assertTrue(receipt.is_success)

        # Send the foreigner tokens to another account with the new address
        count = 0
        while not self.get_tokens_account(self.alice) and count < 10:
            time.sleep(12)
            count += 1

        # Check the error happens
        receipt = transfer_currencies(self.substrate, self.alice, self.kp, 'DOT', token, 1)
        self.assertFalse(receipt.is_success)
        self.assertEqual(receipt.error_message['name'], 'ExistentialDeposit')
