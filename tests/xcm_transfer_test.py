import sys
sys.path.append('./')

import unittest
from tests.utils_func import restart_parachain_and_runtime_upgrade
from tools.runtime_upgrade import wait_until_block_height
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, RELAYCHAIN_WS_URL, BIFROST_WS_URL, PARACHAIN_WS_URL
from peaq.utils import get_account_balance
from peaq.utils import ExtrinsicBatch
from peaq.sudo_extrinsic import fund
from tools.utils import KP_GLOBAL_SUDO, BIFROST_PD_CHAIN_ID, batch_fund
from tools.asset import setup_asset_if_not_exist
from tools.asset import batch_register_location, batch_set_units_per_second, setup_xc_register_if_not_exist
from tools.asset import setup_aca_asset_if_not_exist
from tools.asset import UNITS_PER_SECOND
from tools.asset import BNC_TOKEN_LOCATION, BNC_METADATA, BNC_ASSET_ID
from tools.asset import RELAY_TOKEN_LOCATION, RELAY_METADATA, RELAY_ASSET_ID
from tools.asset import PEAQ_TOKEN_LOCATION, PEAQ_METADATA, PEAQ_ASSET_ID  # , PEAQ_TOKEN_SELF_LOCATION
from tools.asset import PEAQ_CURRENCY_ID_ON_ACA, BNC_CURRENCY_ID_ON_ACA
from tools.utils import PEAQ_PD_CHAIN_ID
from tools.asset import batch_create_asset, batch_mint, batch_set_metadata
import time
# import pytest


TEST_TOKENS = 10 * 10 ** 15
INIT_TOKENS = 10 ** 18
# For avoid exhaust tokens
REMAIN_TOKENS = 10000
KP_CHARLIE = Keypair.create_from_uri('//Charlie')

XCM_VER = 'V3'  # So far not tested with V2!

SOVERIGN_ADDR = '5Eg2fntDDP4P8TjqRg3Jq89y5boE26JUMM3D7VU3bCAp76nc'
TEST_METADATA = {
    'name': 'WOW',
    'symbol': 'WOW',
    'decimals': 18,
}

TEST_ASSET_IDX = 5
TEST_ASSET_ID = {
    'peaq': {
        'Token': TEST_ASSET_IDX,
    },
    'para': {
        'ForeignAsset': 0,
    }
}

ASSET_TOKEN = {
    'peaq': {
        XCM_VER: {
            'parents': '0',
            'interior': {
                'X1': {
                    'GeneralKey': {
                        'length': 2,
                        'data': [0, TEST_ASSET_IDX] + [0] * 30,
                    }
                }
            }
        }
    },
    'para': {
        XCM_VER: {
            'parents': '1',
            'interior': {
                'X2': [{'Parachain': PEAQ_PD_CHAIN_ID}, {
                    'GeneralKey': {
                        'length': 2,
                        'data': [0, TEST_ASSET_IDX] + [0] * 30,
                    }
                }]
            }
        }
    }
}


def aca_fund(substrate, kp_sudo, kp_dst, new_free):
    batch = ExtrinsicBatch(substrate, kp_sudo)
    batch.compose_sudo_call(
        'Balances',
        'force_set_balance',
        {
            'who': kp_dst.ss58_address,
            'new_free': new_free,
        }
    )
    return batch.execute()


def send_token_from_relay_to_peaq(substrate, kp_sign, kp_dst, paraid, token):
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


def send_token_from_peaq_to_para(substrate, kp_sign, kp_dst, parachain_id, asset_id, token):
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


def send_token_from_para_to_peaq(substrate, kp_sign, kp_dst, parachain_id, currency_id, token):
    batch = ExtrinsicBatch(substrate, kp_sign)
    batch.compose_call(
        'XTokens',
        'transfer',
        {
            'currency_id': currency_id,
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
        restart_parachain_and_runtime_upgrade()
        wait_until_block_height(SubstrateInterface(url=PARACHAIN_WS_URL), 1)
        wait_until_block_height(SubstrateInterface(url=BIFROST_WS_URL), 1)

        self.si_peaq = SubstrateInterface(url=WS_URL,)
        self.si_relay = SubstrateInterface(url=RELAYCHAIN_WS_URL, type_registry_preset='rococo')
        self.si_aca = SubstrateInterface(url=BIFROST_WS_URL)
        self.alice = Keypair.create_from_uri('//Alice')

    def setup_xc_register_if_not_exist(self, asset_id, location, units_per_second):
        resp = self.si_peaq.query("XcAssetConfig", "AssetIdToLocation", [asset_id])
        if resp.value:
            return
        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch_register_location(batch, asset_id, location)
        batch_set_units_per_second(batch, location, units_per_second)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f"Failed to register location {location}, {receipt.error_message}")

    def send_relay_token_from_peaq_to_relay(self, kp_src, kp_dst, token):
        parachain_id = self.get_parachain_id(self.si_relay)
        receipt = send_token_from_relay_to_peaq(self.si_relay, kp_src, kp_dst, parachain_id, token)
        return receipt

    def get_tokens_account_from_pallet_assets(self, addr, asset_id):
        resp = self.si_peaq.query("Assets", "Account", [asset_id, addr])
        if not resp.value:
            return 0
        return resp.value['balance']

    def get_tokens_account_from_pallet_tokens(self, addr, asset_id):
        resp = self.si_aca.query("Tokens", "Accounts", [addr, asset_id])
        if not resp.value:
            return 0
        return resp.value['free']

    def wait_for_aca_account_token_change(self, addr, asset_id, prev_token=0):
        if not prev_token:
            prev_token = self.get_tokens_account_from_pallet_tokens(addr, asset_id)
        count = 0
        while self.get_tokens_account_from_pallet_tokens(addr, asset_id) == prev_token and count < 10:
            time.sleep(12)
            count += 1
        now_token = self.get_tokens_account_from_pallet_tokens(addr, asset_id)
        if now_token == prev_token:
            raise IOError(f"Account {addr} balance {prev_token} not changed on aca")
        return now_token

    def wait_for_peaq_account_asset_change(self, addr, asset_id, prev_token=0):
        if not prev_token:
            prev_token = self.get_tokens_account_from_pallet_assets(addr, asset_id)
        count = 0
        while self.get_tokens_account_from_pallet_assets(addr, asset_id) == prev_token and count < 10:
            time.sleep(12)
            count += 1
        now_token = self.get_tokens_account_from_pallet_assets(addr, asset_id)
        if now_token == prev_token:
            raise IOError(f"Account {addr} balance {prev_token} not changed on peaq")
        return now_token

    def wait_for_account_change(self, substrate, kp_dst, prev_token):
        count = 0
        while not get_account_balance(substrate, kp_dst.ss58_address) != prev_token and count < 10:
            time.sleep(12)
            count += 1
        now_token = get_account_balance(substrate, kp_dst.ss58_address)
        if now_token == prev_token:
            raise IOError(f"Account {kp_dst.ss58_address} balance {prev_token} not changed on {substrate.url}")
        return now_token

    # @pytest.mark.skip(reason="Success")
    def test_from_relay_to_peaq(self):
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
        receipt = self.send_relay_token_from_peaq_to_relay(kp_remote_src, kp_self_dst, TEST_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to send tokens from relay chain, {receipt.error_message}')

        now_token = self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, asset_id)
        self.assertGreater(
            now_token, 0,
            f'Actual {now_token} should > expected {TEST_TOKENS} tokens')

        # Send from peaq to relay chain
        prev_balance = get_account_balance(self.si_relay, kp_remote_src.ss58_address)

        token = now_token - REMAIN_TOKENS
        receipt = send_token_from_peaq_to_relay(
            self.si_peaq, kp_self_dst, kp_remote_src, asset_id, token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        now_balance = self.wait_for_account_change(self.si_relay, kp_remote_src, prev_balance)
        self.assertGreater(
            now_balance, prev_balance,
            f'Actual {now_balance} should > expected {prev_balance} tokens')

    # @pytest.mark.skip(reason="Success")
    # We don't need to test other token from aca to peaq because the flow is the same
    def test_native_from_aca_to_peaq(self):
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
        receipt = send_token_from_para_to_peaq(
            self.si_aca, kp_remote_src, kp_self_dst,
            parachain_id, BNC_CURRENCY_ID_ON_ACA, TEST_TOKENS)
        self.assertTrue(receipt.is_success, f"Failed to send token from bifrost to peaq chain: {receipt.error_message}")

        got_token = self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, asset_id)
        self.assertGreater(
            got_token, 0,
            f'Actual {got_token} should > expected {TEST_TOKENS}')

        # Send foreigner tokens from peaq chain
        prev_balance = get_account_balance(self.si_aca, kp_remote_src.ss58_address)

        token = got_token - REMAIN_TOKENS
        receipt = send_token_from_peaq_to_para(
            self.si_peaq, kp_self_dst,
            kp_remote_src, BIFROST_PD_CHAIN_ID, asset_id, token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')
        now_balance = self.wait_for_account_change(self.si_aca, kp_remote_src, prev_balance)
        self.assertGreater(
            now_balance, prev_balance,
            f'Actual {now_balance} should > expected {prev_balance}')

    # @pytest.mark.skip(reason="Success")
    def test_native_from_peaq_to_aca(self):
        receipt = setup_aca_asset_if_not_exist(
            self.si_aca, KP_GLOBAL_SUDO, PEAQ_TOKEN_LOCATION, PEAQ_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to register foreign asset: {receipt.error_message}')

        kp_para_src = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        kp_self_dst = kp_para_src
        receipt = aca_fund(self.si_aca, KP_GLOBAL_SUDO, kp_para_src, INIT_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to aca: {receipt.error_message}')
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_self_dst, INIT_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to peaq: {receipt.error_message}')

        receipt = send_token_from_peaq_to_para(
            self.si_peaq, self.alice, kp_para_src,
            BIFROST_PD_CHAIN_ID, PEAQ_ASSET_ID, TEST_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        # Extract...
        got_token = self.wait_for_aca_account_token_change(kp_para_src.ss58_address, {
            'ForeignAsset': 0,
        })
        self.assertNotEqual(got_token, 0)

        transfer_back_token = got_token - REMAIN_TOKENS
        prev_balance = get_account_balance(self.si_peaq, kp_self_dst.ss58_address)
        # Send it back to the peaq chain
        receipt = send_token_from_para_to_peaq(
            self.si_aca, kp_para_src, kp_self_dst,
            PEAQ_PD_CHAIN_ID, PEAQ_CURRENCY_ID_ON_ACA, transfer_back_token)
        self.assertTrue(receipt.is_success, f'Failed to send token from para to peaq: {receipt.error_message}')

        now_balance = self.wait_for_account_change(self.si_peaq, kp_self_dst, prev_balance)
        self.assertGreater(now_balance, prev_balance, f'Actual {now_balance} should > expected {prev_balance}')

    # @pytest.mark.skip(reason="Success")
    def test_asset_from_peaq_to_aca(self):
        # Create new asset id and register on peaq
        asset_id = TEST_ASSET_ID['peaq']
        kp_para_src = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        kp_self_dst = kp_para_src
        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch_fund(batch, kp_self_dst, INIT_TOKENS)
        batch_fund(batch, SOVERIGN_ADDR, INIT_TOKENS)
        batch_create_asset(batch, KP_GLOBAL_SUDO.ss58_address, asset_id)
        batch_set_metadata(
            batch, asset_id,
            TEST_METADATA['name'], TEST_METADATA['symbol'], TEST_METADATA['decimals'])
        batch_mint(batch, self.alice.ss58_address, asset_id, 10 * TEST_TOKENS)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Failed to create asset: {receipt.error_message}')
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO, asset_id,
            ASSET_TOKEN['peaq'], UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to register foreign asset: {receipt.error_message}')

        # register on aca
        receipt = setup_aca_asset_if_not_exist(
            self.si_aca, KP_GLOBAL_SUDO, ASSET_TOKEN['para'], TEST_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to register foreign asset: {receipt.error_message}')

        kp_self_dst = kp_para_src
        receipt = aca_fund(self.si_aca, KP_GLOBAL_SUDO, kp_para_src, INIT_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to aca: {receipt.error_message}')

        receipt = send_token_from_peaq_to_para(
            self.si_peaq, self.alice, kp_para_src,
            BIFROST_PD_CHAIN_ID, TEST_ASSET_ID['peaq'], TEST_TOKENS)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        # Extract...
        got_token = self.wait_for_aca_account_token_change(kp_para_src.ss58_address, TEST_ASSET_ID['para'])
        self.assertNotEqual(got_token, 0)

        transfer_back_token = got_token - REMAIN_TOKENS
        prev_balance = self.get_tokens_account_from_pallet_assets(kp_self_dst.ss58_address, TEST_ASSET_ID['peaq'])
        # Send it back to the peaq chain
        receipt = send_token_from_para_to_peaq(
            self.si_aca, kp_para_src, kp_self_dst,
            PEAQ_PD_CHAIN_ID, TEST_ASSET_ID['para'], transfer_back_token)
        self.assertTrue(receipt.is_success, f'Failed to send token from para to peaq: {receipt.error_message}')

        now_balance = self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, TEST_ASSET_ID['peaq'])
        self.assertGreater(now_balance, prev_balance, f'Actual {now_balance} should > expected {prev_balance}')
