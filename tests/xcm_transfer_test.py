import sys
sys.path.append('./')

import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, RELAYCHAIN_WS_URL, BIFROST_WS_URL
from peaq.utils import get_account_balance
from peaq.utils import ExtrinsicBatch
from peaq.sudo_extrinsic import fund
from tools.utils import KP_GLOBAL_SUDO, BIFROST_PD_CHAIN_ID
from tools.asset import batch_create_asset, batch_set_metadata, setup_asset_if_not_exist
from tools.asset import batch_register_location, batch_set_units_per_second, setup_xc_register_if_not_exist
from tools.asset import UNITS_PER_SECOND
from tools.asset import BNC_TOKEN_LOCATION, BNC_METADATA, BNC_ASSET_ID
from tools.asset import RELAY_TOKEN_LOCATION, RELAY_METADATA, RELAY_ASSET_ID
import time
import pytest


TEST_TOKENS = 10 * 10 ** 15
INIT_TOKENS = 10 ** 18
KP_CHARLIE = Keypair.create_from_uri('//Charlie')

XCM_VER = 'V3'  # So far not tested with V2!


def send_from_relay(substrate, kp_sign, kp_dst, paraid, token):
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
            'currency_id': asset_id,
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
            'currency_id': asset_id,
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


class TestXCMTransfer(unittest.TestCase):
    def get_parachain_id(self, relay_substrate):
        result = relay_substrate.query(
            'Paras',
            'Parachains',
        )
        return result.value[0]

    def setUp(self):
        self.si_peaq = SubstrateInterface(url=WS_URL,)
        self.si_relay = SubstrateInterface(url=RELAYCHAIN_WS_URL, type_registry_preset='rococo')
        self.si_bitfrost = SubstrateInterface(url=BIFROST_WS_URL)
        self.alice = Keypair.create_from_uri('//Alice')

    def setup_asset_if_not_exist(self, asset_id, metadata):
        resp = self.si_peaq.query("Assets", "Asset", [asset_id])
        if resp.value:
            return

        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch_create_asset(batch, KP_GLOBAL_SUDO.ss58_address, asset_id, 100)
        batch_set_metadata(batch, asset_id,
                           metadata['name'], metadata['symbol'], metadata['decimals'])
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f"Failed to create asset {asset_id}, {receipt.error_message}")

    def setup_xc_register_if_not_exist(self, asset_id, location, units_per_second):
        resp = self.si_peaq.query("XcAssetConfig", "AssetIdToLocation", [asset_id])
        if resp.value:
            return
        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch_register_location(batch, asset_id, location)
        batch_set_units_per_second(batch, location, units_per_second)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f"Failed to register location {location}, {receipt.error_message}")

    def send_relaychain_token(self, kp_src, kp_dst, token):
        parachain_id = self.get_parachain_id(self.si_relay)
        receipt = send_from_relay(self.si_relay, kp_src, kp_dst, parachain_id, token)
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

    def wait_for_peaq_account_asset_change(self, addr, asset_id, prev_token):
        count = 0
        while self.get_tokens_account(addr, asset_id) == prev_token and count < 10:
            time.sleep(12)
            count += 1

    def wait_for_remote_account_change(self, substrate, kp_dst, prev_token):
        count = 0
        while not get_account_balance(substrate, kp_dst.ss58_address) != prev_token and count < 10:
            time.sleep(12)
            count += 1

    @pytest.mark.skip(reason="Success")
    def test_relay_tokens(self):
        asset_id = RELAY_ASSET_ID
        receipt = setup_asset_if_not_exist(self.si_peaq, KP_GLOBAL_SUDO, asset_id, RELAY_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO, asset_id,
            RELAY_TOKEN_LOCATION, UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')

        kp_remote_src = KP_CHARLIE
        kp_self_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_self_dst, INIT_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to fund account, {receipt.error_message}')

        # Send foreigner tokens from the relay chain
        receipt = self.send_relaychain_token(kp_remote_src, kp_self_dst, TEST_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to send tokens from relay chain, {receipt.error_message}')

        self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, asset_id, 0)

        now_token = self.get_tokens_account(kp_self_dst.ss58_address, asset_id)
        self.assertAlmostEqual(
            now_token / TEST_TOKENS,
            1, 5,
            f'Actual {now_token} and expected {TEST_TOKENS} tokens are largely different')

        # Send from peaq to relay chain
        prev_balance = get_account_balance(self.si_relay, kp_remote_src.ss58_address)

        token = now_token - 10000
        receipt = send_token_from_peaq_to_relay(
            self.si_peaq, kp_self_dst, kp_remote_src, asset_id, token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        self.wait_for_remote_account_change(self.si_relay, kp_remote_src, prev_balance)

        now_balance = get_account_balance(self.si_relay, kp_remote_src.ss58_address)
        self.assertAlmostEqual(
            (now_balance - prev_balance) / token,
            1, 5,
            f'Actual {now_balance} and expected {prev_balance} tokens are largely different')

    # @pytest.mark.skip(reason="Success")
    def test_from_bnc_to_self(self):
        asset_id = BNC_ASSET_ID
        receipt = setup_asset_if_not_exist(self.si_peaq, KP_GLOBAL_SUDO, asset_id, BNC_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO,
            asset_id, BNC_TOKEN_LOCATION, UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')

        kp_remote_src = KP_CHARLIE
        kp_self_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_self_dst, INIT_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to self: {receipt.error_message}')
        parachain_id = self.get_parachain_id(self.si_relay)

        # Send foreigner tokens to peaq chain
        receipt = send_token_from_biforst(self.si_bitfrost, kp_remote_src, kp_self_dst, parachain_id, TEST_TOKENS)
        self.assertTrue(receipt.is_success, f"Failed to send token from bifrost to peaq chain: {receipt.error_message}")

        self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, asset_id, 0)

        got_token = self.get_tokens_account(kp_self_dst.ss58_address, asset_id)
        self.assertAlmostEqual(
            got_token / TEST_TOKENS,
            1, 5,
            f'Actual {got_token} and expected {TEST_TOKENS} tokens are largely different')

        # Send foreigner tokens from peaq chain
        prev_balance = get_account_balance(self.si_bitfrost, kp_remote_src.ss58_address)

        token = got_token - 10000
        receipt = send_token_from_peaq(
            self.si_peaq, kp_self_dst,
            kp_remote_src, BIFROST_PD_CHAIN_ID, asset_id, token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')
        self.wait_for_remote_account_change(self.si_bitfrost, kp_remote_src, prev_balance)
        now_balance = get_account_balance(self.si_bitfrost, kp_remote_src.ss58_address)
        self.assertAlmostEqual(
            (now_balance - prev_balance) / token,
            1, 5,
            f'Actual {now_balance} and expected {prev_balance} tokens are largely different')

    # [TODO] Need to check on other...
    @pytest.mark.skip(reason="Fail...")
    def test_from_self_to_bnc(self):
        token = 23 * 10 ** 12
        kp_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = send_token_from_peaq(self.si_peaq, self.alice, kp_dst, BIFROST_PD_CHAIN_ID, 0, token)
        self.assertTrue(receipt.is_success)

        # asset_id = 0
        # count = 0
        # while not self.get_tokens_account(kp_dst.ss58_address, asset_id) and count < 10:
        #     time.sleep(12)
        #     count += 1

        # balance = self.get_tokens_account(kp_dst.ss58_address, asset_id)
        # print(balance)
        # self.assertNotEqual(balance, 0)
