import sys
sys.path.append('./')

import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, RELAYCHAIN_WS_URL, BIFROST_WS_URL
from peaq.utils import get_account_balance
from peaq.utils import ExtrinsicBatch
from peaq.sudo_extrinsic import fund
from tools.utils import KP_GLOBAL_SUDO
from tools.asset import batch_create_asset, batch_set_metadata
import time
import pytest


XCM_VER = 'V3'  # So far not tested with V2!


def send_from_xcm(substrate, kp_sign, kp_dst, paraid, token):
    batch = ExtrinsicBatch(substrate, kp_sign)
    batch.compose_call(
        'XcmPallet',
        'reserve_transfer_assets',
        {
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
                                'id': kp_dst.public_key,
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
                        'Fungible': token
                    }
                }]]
            },
            'fee_asset_item': 0,
        }
    )
    return batch.execute()


def send_token_from_peaq(substrate, kp_sign, kp_dst, parachain_id, asset_id, token):
    batch = ExtrinsicBatch(substrate, kp_sign)
    batch.compose_call(
        'XTokens',
        'transfer',
        {
            'currency_id': str(asset_id),
            'amount': str(token),
            'dest': {XCM_VER: {
                'parents': '1',
                'interior': {'X2': [
                    {'Parachain': f'{parachain_id}'},
                    {'AccountId32': (None, kp_dst.public_key)}
                    ]}
                }},
            'dest_weight_limit': 'Unlimited',
        }
    )
    return batch.execute()


def send_token_from_peaq_to_relay(substrate, kp_sign, kp_dst, asset_id, token):
    batch = ExtrinsicBatch(substrate, kp_sign)
    batch.compose_call(
        'XTokens',
        'transfer',
        {
            'currency_id': str(asset_id),
            'amount': str(token),
            'dest': {XCM_VER: {
                'parents': '1',
                'interior': {'X1': {'AccountId32': (None, kp_dst.public_key)}}
                }},
            'dest_weight_limit': 'Unlimited',
        }
    )
    return batch.execute()


def send_token_from_biforst(substrate, kp_sign, kp_dst, parachain_id, token):
    batch = ExtrinsicBatch(substrate, kp_sign)
    batch.compose_call(
        'XTokens',
        'transfer',
        {
            'currency_id': {'Native': 'BNC'},
            'amount': str(token),
            'dest': {XCM_VER: {
                'parents': '1',
                'interior': {'X2': [
                    {'Parachain': f'{parachain_id}'},
                    {'AccountId32': (None, kp_dst.public_key)}
                    ]}
                }},
            'dest_weight_limit': 'Unlimited',
        }
    )
    return batch.execute()


class TextXCMTransfer(unittest.TestCase):
    def get_parachain_id(self, relay_substrate):
        result = relay_substrate.query(
            'Paras',
            'Parachains',
        )
        return result.value[0]

    def setUp(self):
        self.si_peaq = SubstrateInterface(url=WS_URL,)
        self.si_relay = SubstrateInterface(url=RELAYCHAIN_WS_URL, type_registry_preset='rococo')
        self.si_bifrost = SubstrateInterface(url=BIFROST_WS_URL)
        self.alice = Keypair.create_from_uri('//Alice')
        self.ferdie = Keypair.create_from_uri('//Ferdie')

    def setup_asset_if_not_exist(self, asset_id, metadata):
        asset = self.si_peaq.query("Assets", "Asset", [asset_id])
        if asset.value:
            return

        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch_create_asset(batch, KP_GLOBAL_SUDO.ss58_address, asset_id, 100)
        batch_set_metadata(batch, asset_id,
                           metadata['name'], metadata['symbol'], metadata['decimals'])
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f"Failed to create asset {asset_id}, {receipt.error_message}")

    def send_relaychain_token(self, kp_src, kp_dst, token):
        parachain_id = self.get_parachain_id(self.si_relay)
        receipt = send_from_xcm(self.si_relay, kp_src, kp_dst, parachain_id, token)
        return receipt

    def send_token_from_peaq(self, kp_src, kp_dst, asset_id, token):
        parachain_id = self.get_parachain_id(self.si_relay)
        receipt = send_token_from_peaq(self.si_peaq, kp_src, kp_dst, parachain_id, asset_id, token)
        return receipt

    def get_tokens_account(self, addr, asset_id):
        resp = self.si_peaq.query("Assets", "Account", [asset_id, addr])
        if not resp.value:
            return 0
        return resp.value['balance']

    @pytest.mark.skip(reason="Fail")
    def test_relay_tokens(self):
        self.setup_asset_if_not_exist(1, {
            'name': 'Relay Token',
            'symbol': 'DOT',
            'decimals': 12,
        })

        token = 100 * 10 ** 15
        kp_dst = self.ferdie
        # [TOOD] Need to change
        # kp_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_dst, 1000)

        # Send foreigner tokens from the relay chain
        receipt = self.send_relaychain_token(self.alice, kp_dst, token)
        self.assertTrue(receipt.is_success)

        asset_id = 1
        count = 0
        while not self.get_tokens_account(kp_dst.ss58_address, asset_id) and count < 10:
            time.sleep(12)
            count += 1

        # TODO Check: 20,000,000,000 fee??
        self.assertNotEqual(
            self.get_tokens_account(kp_dst.ss58_address, asset_id),
            0,
            f'Account {kp_dst.ss58_address} has no tokens'
        )
        got_token = self.get_tokens_account(kp_dst.ss58_address, asset_id)
        self.assertAlmostEqual(
            got_token / token,
            1, 5,
            f'Actual {got_token} and expected {token} tokens are largely different')

        # Send from peaq to relay chain
        prev_balance = get_account_balance(self.si_relay, self.ferdie.ss58_address)

        token = got_token - 10000
        receipt = send_token_from_peaq_to_relay(self.si_peaq, kp_dst, self.ferdie, 1, token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')
        count = 0
        while not get_account_balance(self.si_bifrost, self.ferdie.ss58_address) != prev_balance and count < 10:
            time.sleep(12)
            count += 1
        now_balance = get_account_balance(self.si_bifrost, self.ferdie.ss58_address)
        self.assertAlmostEqual(
            (now_balance - prev_balance) / token,
            1, 5,
            f'Actual {now_balance} and expected {prev_balance} tokens are largely different')

    @pytest.mark.skip(reason="NotCrossChainTransfer")
    def test_from_self_to_self(self):
        token = 23 * 10 ** 12
        kp_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = self.send_token_from_peaq(self.alice, kp_dst, 0, token)
        self.assertTrue(receipt.is_success)

        balance = get_account_balance(self.si_peaq, kp_dst.ss58_address)
        print(balance)
        self.assertNotEqual(balance, 0)

    @pytest.mark.skip(reason="Success")
    def test_from_bnc_to_self(self):
        self.setup_asset_if_not_exist(3, {
            'name': 'Bifrost Native Token',
            'symbol': 'BNC',
            'decimals': 12,
        })

        token = 100 * 10 ** 15
        # kp_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        # [TODO]
        kp_dst = self.ferdie
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_dst, 1000)
        self.assertTrue(receipt.is_success)
        parachain_id = self.get_parachain_id(self.si_relay)

        # Send foreigner tokens to peaq chain
        receipt = send_token_from_biforst(self.si_bifrost, self.alice, kp_dst, parachain_id, token)
        self.assertTrue(receipt.is_success, f"Failed to send token from bifrost to peaq chain: {receipt.error_message}")

        asset_id = 3
        count = 0
        while not self.get_tokens_account(kp_dst.ss58_address, asset_id) and count < 10:
            time.sleep(12)
            count += 1

        # TODO Check: 100,000,000,000 fee??
        got_token = self.get_tokens_account(kp_dst.ss58_address, asset_id)
        self.assertAlmostEqual(
            got_token / token,
            1, 5,
            f'Actual {got_token} and expected {token} tokens are largely different')

        # Send foreigner tokens from peaq chain
        prev_balance = get_account_balance(self.si_relay, self.ferdie.ss58_address)

        token = got_token - 10000
        receipt = send_token_from_peaq(self.si_peaq, kp_dst, self.ferdie, 3000, 3, token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')
        count = 0
        while not get_account_balance(self.si_bifrost, self.ferdie.ss58_address) != prev_balance and count < 10:
            time.sleep(12)
            count += 1
        now_balance = get_account_balance(self.si_bifrost, self.ferdie.ss58_address)
        self.assertAlmostEqual(
            (now_balance - prev_balance) / token,
            1, 5,
            f'Actual {now_balance} and expected {prev_balance} tokens are largely different')

    @pytest.mark.skip(reason="Fail...")
    def test_from_self_to_bnc(self):
        token = 23 * 10 ** 12
        kp_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = send_token_from_peaq(self.si_peaq, self.alice, kp_dst, 3000, 0, token)
        self.assertTrue(receipt.is_success)

        # asset_id = 0
        # count = 0
        # while not self.get_tokens_account(kp_dst.ss58_address, asset_id) and count < 10:
        #     time.sleep(12)
        #     count += 1

        # balance = self.get_tokens_account(kp_dst.ss58_address, asset_id)
        # print(balance)
        # self.assertNotEqual(balance, 0)
