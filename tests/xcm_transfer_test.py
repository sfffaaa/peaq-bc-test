import sys
sys.path.append('./')

import unittest
from tests.utils_func import restart_parachain_and_runtime_upgrade
from tools.runtime_upgrade import wait_until_block_height
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, RELAYCHAIN_WS_URL, ACA_WS_URL, PARACHAIN_WS_URL
from peaq.utils import get_account_balance
from peaq.utils import ExtrinsicBatch
from peaq.sudo_extrinsic import fund
from tools.utils import KP_GLOBAL_SUDO, ACA_PD_CHAIN_ID, batch_fund
from tools.asset import setup_asset_if_not_exist
from tools.asset import batch_register_location, batch_set_units_per_second, setup_xc_register_if_not_exist
from tools.asset import setup_aca_asset_if_not_exist
from tools.asset import UNITS_PER_SECOND
from tools.asset import ACA_ASSET_LOCATION, ACA_METADATA, PEAQ_ASSET_LOCATION
from tools.asset import RELAY_ASSET_LOCATION, RELAY_METADATA, RELAY_ASSET_ID
from tools.asset import PEAQ_METADATA, PEAQ_ASSET_ID
from tools.asset import ACA_ASSET_ID
from tools.utils import get_peaq_chain_id
from tools.asset import batch_create_asset, batch_mint, batch_set_metadata, batch_force_create_asset
from tools.asset import convert_enum_to_asset_id
from tools.zenlink import compose_zdex_create_lppair, compose_zdex_add_liquidity
from tools.asset import wait_for_account_asset_change_wrap
from tools.asset import get_balance_account_from_pallet_balance
from tools.asset import get_tokens_account_from_pallet_assets
from tools.asset import get_tokens_account_from_pallet_tokens

from tools.xcm_setup import setup_hrmp_channel
import pytest


PEAQ_PD_CHAIN_ID = get_peaq_chain_id()

TEST_TOKEN_NUM = 100 * 10 ** 18
INIT_TOKEN_NUM = 1000 * 10 ** 18
# For avoid exhaust tokens
REMAIN_TOKEN_NUM = 10000
KP_CHARLIE = Keypair.create_from_uri('//Charlie')

XCM_VER = 'V3'  # So far not tested with V2!

# From 3000
SOVERIGN_ADDR = '5Eg2fntDDP4P8TjqRg3Jq89y5boE26JUMM3D7VU3bCAp76nc'
TEST_ASSET_METADATA = {
    'name': 'WOW',
    'symbol': 'WOW',
    'decimals': 18,
}

TEST_ASSET_IDX = 5
TEST_ASSET_ID = {
    'peaq': TEST_ASSET_IDX,
    'para': {
        'ForeignAsset': 0,
    }
}

TEST_ASSET_TOKEN = {
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

TEST_LP_ASSET_ID = {
    'peaq': convert_enum_to_asset_id({'LPToken': [0, 1]}),
    'para': {
        'ForeignAsset': 0,
    }
}

TEST_LP_ASSET_TOKEN = {
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
    def get_parachain_id(self, peaq_substrate):
        result = peaq_substrate.query(
            'ParachainInfo',
            'ParachainId',
        )
        return result.value

    def setUp(self):
        restart_parachain_and_runtime_upgrade()
        wait_until_block_height(SubstrateInterface(url=PARACHAIN_WS_URL), 1)
        wait_until_block_height(SubstrateInterface(url=ACA_WS_URL), 1)
        setup_hrmp_channel(RELAYCHAIN_WS_URL)

        self.si_peaq = SubstrateInterface(url=WS_URL,)
        self.si_relay = SubstrateInterface(url=RELAYCHAIN_WS_URL, type_registry_preset='rococo')
        self.si_aca = SubstrateInterface(url=ACA_WS_URL)
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

    def send_relay_token_from_relay_to_peaq(self, kp_src, kp_dst, token):
        parachain_id = self.get_parachain_id(self.si_peaq)
        receipt = send_token_from_relay_to_peaq(self.si_relay, kp_src, kp_dst, parachain_id, token)
        return receipt

    def wait_for_aca_account_token_change(self, addr, asset_id, prev_token=0):
        return wait_for_account_asset_change_wrap(
            self.si_aca, addr, asset_id, prev_token, get_tokens_account_from_pallet_tokens)

    def wait_for_peaq_account_asset_change(self, addr, asset_id, prev_token=0):
        return wait_for_account_asset_change_wrap(
            self.si_peaq, addr, asset_id, prev_token, get_tokens_account_from_pallet_assets)

    def wait_for_account_change(self, substrate, kp_dst, prev_token):
        return wait_for_account_asset_change_wrap(
            self.si_peaq, kp_dst.ss58_address, None, prev_token, get_balance_account_from_pallet_balance)

    @pytest.mark.xcm
    def test_from_relay_to_peaq(self):
        receipt = setup_asset_if_not_exist(self.si_peaq, KP_GLOBAL_SUDO, RELAY_ASSET_ID['peaq'], RELAY_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO,
            RELAY_ASSET_ID['peaq'], RELAY_ASSET_LOCATION['peaq'], UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')

        kp_remote_src = KP_CHARLIE
        kp_self_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_self_dst, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund account, {receipt.error_message}')
        receipt = fund(self.si_relay, KP_GLOBAL_SUDO, kp_remote_src, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund account, {receipt.error_message}')

        # Send foreigner tokens from the relay chain
        receipt = self.send_relay_token_from_relay_to_peaq(kp_remote_src, kp_self_dst, TEST_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to send tokens from relay chain, {receipt.error_message}')

        now_token = self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, RELAY_ASSET_ID['peaq'])
        self.assertGreater(
            now_token, 0,
            f'Actual {now_token} should > expected {TEST_TOKEN_NUM} tokens')

        # Send from peaq to relay chain
        prev_balance = get_account_balance(self.si_relay, kp_remote_src.ss58_address)

        token = now_token - REMAIN_TOKEN_NUM
        receipt = send_token_from_peaq_to_relay(
            self.si_peaq, kp_self_dst, kp_remote_src, RELAY_ASSET_ID['peaq'], token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        now_balance = self.wait_for_account_change(self.si_relay, kp_remote_src, prev_balance)
        self.assertGreater(
            now_balance, prev_balance,
            f'Actual {now_balance} should > expected {prev_balance} tokens')

    # No fund dst account before receive the relay chain's token
    @pytest.mark.xcm
    def test_from_relay_to_peaq_with_sufficient(self):
        receipt = setup_asset_if_not_exist(self.si_peaq, KP_GLOBAL_SUDO, RELAY_ASSET_ID['peaq'], RELAY_METADATA, 100, True)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO,
            RELAY_ASSET_ID['peaq'], RELAY_ASSET_LOCATION['peaq'], UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')

        kp_remote_src = KP_CHARLIE
        kp_self_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = fund(self.si_relay, KP_GLOBAL_SUDO, kp_remote_src, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund account, {receipt.error_message}')

        # Send foreigner tokens from the relay chain
        receipt = self.send_relay_token_from_relay_to_peaq(kp_remote_src, kp_self_dst, TEST_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to send tokens from relay chain, {receipt.error_message}')

        now_token = self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, RELAY_ASSET_ID['peaq'])
        self.assertGreater(
            now_token, 0,
            f'Actual {now_token} should > expected {TEST_TOKEN_NUM} tokens')

        # Send from peaq to relay chain
        prev_balance = get_account_balance(self.si_relay, kp_remote_src.ss58_address)

        # For paying fee
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_self_dst, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund account, {receipt.error_message}')
        token = now_token - REMAIN_TOKEN_NUM
        receipt = send_token_from_peaq_to_relay(
            self.si_peaq, kp_self_dst, kp_remote_src, RELAY_ASSET_ID['peaq'], token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        now_balance = self.wait_for_account_change(self.si_relay, kp_remote_src, prev_balance)
        self.assertGreater(
            now_balance, prev_balance,
            f'Actual {now_balance} should > expected {prev_balance} tokens')

    # We don't need to test other token from aca to peaq because the flow is the same
    @pytest.mark.xcm
    def test_native_from_aca_to_peaq(self):
        asset_id = ACA_ASSET_ID['peaq']
        receipt = setup_asset_if_not_exist(self.si_peaq, KP_GLOBAL_SUDO, asset_id, ACA_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO,
            asset_id, ACA_ASSET_LOCATION['peaq'], UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')

        kp_remote_src = KP_CHARLIE
        receipt = aca_fund(self.si_aca, KP_GLOBAL_SUDO, kp_remote_src, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to aca: {receipt.error_message}')
        kp_self_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_self_dst, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to self: {receipt.error_message}')
        parachain_id = self.get_parachain_id(self.si_peaq)

        # Send foreigner tokens to peaq chain
        receipt = send_token_from_para_to_peaq(
            self.si_aca, kp_remote_src, kp_self_dst,
            parachain_id, ACA_ASSET_ID['para'], TEST_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f"Failed to send token from bifrost to peaq chain: {receipt.error_message}")

        got_token = self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, asset_id)
        self.assertGreater(
            got_token, 0,
            f'Actual {got_token} should > expected {TEST_TOKEN_NUM}')

        # Send foreigner tokens from peaq chain
        prev_balance = get_account_balance(self.si_aca, kp_remote_src.ss58_address)

        token = got_token - REMAIN_TOKEN_NUM
        receipt = send_token_from_peaq_to_para(
            self.si_peaq, kp_self_dst,
            kp_remote_src, ACA_PD_CHAIN_ID, asset_id, token)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')
        now_balance = self.wait_for_account_change(self.si_aca, kp_remote_src, prev_balance)
        self.assertGreater(
            now_balance, prev_balance,
            f'Actual {now_balance} should > expected {prev_balance}')

    @pytest.mark.xcm
    def test_native_from_peaq_to_aca(self):
        receipt = setup_aca_asset_if_not_exist(
            self.si_aca, KP_GLOBAL_SUDO, PEAQ_ASSET_LOCATION['para'], PEAQ_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to register foreign asset: {receipt.error_message}')

        kp_para_src = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        kp_self_dst = kp_para_src
        receipt = aca_fund(self.si_aca, KP_GLOBAL_SUDO, kp_para_src, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to aca: {receipt.error_message}')
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_self_dst, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to peaq: {receipt.error_message}')

        receipt = send_token_from_peaq_to_para(
            self.si_peaq, self.alice, kp_para_src,
            ACA_PD_CHAIN_ID, PEAQ_ASSET_ID['peaq'], TEST_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        # Extract...
        got_token = self.wait_for_aca_account_token_change(kp_para_src.ss58_address, PEAQ_ASSET_ID['para'])
        self.assertNotEqual(got_token, 0)

        transfer_back_token = got_token - REMAIN_TOKEN_NUM
        prev_balance = get_account_balance(self.si_peaq, kp_self_dst.ss58_address)
        # Send it back to the peaq chain
        receipt = send_token_from_para_to_peaq(
            self.si_aca, kp_para_src, kp_self_dst,
            PEAQ_PD_CHAIN_ID, PEAQ_ASSET_ID['para'], transfer_back_token)
        self.assertTrue(receipt.is_success, f'Failed to send token from para to peaq: {receipt.error_message}')

        now_balance = self.wait_for_account_change(self.si_peaq, kp_self_dst, prev_balance)
        self.assertGreater(now_balance, prev_balance, f'Actual {now_balance} should > expected {prev_balance}')

    @pytest.mark.xcm
    def test_asset_from_peaq_to_aca_with_sufficient(self):
        # Create new asset id and register on peaq
        asset_id = TEST_ASSET_ID['peaq']
        kp_para_src = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        self._set_up_peaq_asset_on_peaq(asset_id, kp_para_src, True)

        # register on aca
        receipt = setup_aca_asset_if_not_exist(
            self.si_aca, KP_GLOBAL_SUDO, TEST_ASSET_TOKEN['para'], TEST_ASSET_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to register foreign asset: {receipt.error_message}')

        kp_self_dst = kp_para_src
        receipt = aca_fund(self.si_aca, KP_GLOBAL_SUDO, kp_para_src, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to aca: {receipt.error_message}')

        self._check_peaq_asset_from_peaq_to_aca_and_back(kp_para_src, kp_self_dst)

    def _set_up_peaq_asset_on_peaq(self, asset_id, kp_para_src, is_sufficent=False):
        kp_self_dst = kp_para_src
        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch_fund(batch, kp_self_dst, INIT_TOKEN_NUM)
        if is_sufficent:
            batch_force_create_asset(batch, KP_GLOBAL_SUDO.ss58_address, asset_id)
        else:
            batch_create_asset(batch, KP_GLOBAL_SUDO.ss58_address, asset_id)
        batch_set_metadata(
            batch, asset_id,
            TEST_ASSET_METADATA['name'], TEST_ASSET_METADATA['symbol'], TEST_ASSET_METADATA['decimals'])
        batch_mint(batch, self.alice.ss58_address, asset_id, 10 * TEST_TOKEN_NUM)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Failed to create asset: {receipt.error_message}')
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO, asset_id,
            TEST_ASSET_TOKEN['peaq'], UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to register foreign asset: {receipt.error_message}')

    def _check_peaq_asset_from_peaq_to_aca_and_back(self, kp_para_src, kp_self_dst):
        receipt = send_token_from_peaq_to_para(
            self.si_peaq, self.alice, kp_para_src,
            ACA_PD_CHAIN_ID, TEST_ASSET_ID['peaq'], TEST_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        # Extract...
        got_token = self.wait_for_aca_account_token_change(kp_para_src.ss58_address, TEST_ASSET_ID['para'])
        self.assertNotEqual(got_token, 0)

        transfer_back_token = got_token - REMAIN_TOKEN_NUM
        prev_balance = get_tokens_account_from_pallet_assets(
            self.si_peaq, kp_self_dst.ss58_address, TEST_ASSET_ID['peaq'])
        # Send it back to the peaq chain
        receipt = send_token_from_para_to_peaq(
            self.si_aca, kp_para_src, kp_self_dst,
            PEAQ_PD_CHAIN_ID, TEST_ASSET_ID['para'], transfer_back_token)
        self.assertTrue(receipt.is_success, f'Failed to send token from para to peaq: {receipt.error_message}')

        now_balance = self.wait_for_peaq_account_asset_change(kp_self_dst.ss58_address, TEST_ASSET_ID['peaq'])
        self.assertGreater(now_balance, prev_balance, f'Actual {now_balance} should > expected {prev_balance}')

    @pytest.mark.xcm
    def test_asset_from_peaq_to_aca(self):
        # From Alice transfer to kp_para_src (other chain) and move to the kp_self_dst
        # Create new asset id and register on peaq
        asset_id = TEST_ASSET_ID['peaq']
        kp_para_src = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        self._set_up_peaq_asset_on_peaq(asset_id, kp_para_src, False)

        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch_fund(batch, SOVERIGN_ADDR, INIT_TOKEN_NUM)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Failed to create asset: {receipt.error_message}')

        # register on aca
        receipt = setup_aca_asset_if_not_exist(
            self.si_aca, KP_GLOBAL_SUDO, TEST_ASSET_TOKEN['para'], TEST_ASSET_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to register foreign asset: {receipt.error_message}')

        kp_self_dst = kp_para_src
        receipt = aca_fund(self.si_aca, KP_GLOBAL_SUDO, kp_para_src, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to aca: {receipt.error_message}')

        self._check_peaq_asset_from_peaq_to_aca_and_back(kp_para_src, kp_self_dst)

    # Note, lp asset should create by zenlink protocol
    @pytest.mark.xcm
    def test_lp_asset_from_peaq_to_aca(self):
        # Setup
        kp_peaq = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        kp_aca = kp_peaq
        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        batch_fund(batch, kp_peaq, INIT_TOKEN_NUM)
        batch_fund(batch, SOVERIGN_ADDR, INIT_TOKEN_NUM)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Failed to create asset: {receipt.error_message}')

        receipt = aca_fund(self.si_aca, KP_GLOBAL_SUDO, kp_aca, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to aca: {receipt.error_message}')

        # Register dot tokens
        receipt = setup_asset_if_not_exist(self.si_peaq, KP_GLOBAL_SUDO, RELAY_ASSET_ID['peaq'], RELAY_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO,
            RELAY_ASSET_ID['peaq'], RELAY_ASSET_LOCATION['peaq'], UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')

        receipt = fund(self.si_relay, KP_GLOBAL_SUDO, KP_GLOBAL_SUDO, INIT_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to fund tokens to peaq: {receipt.error_message}')

        # Transfer dot
        receipt = self.send_relay_token_from_relay_to_peaq(KP_GLOBAL_SUDO, kp_peaq, TEST_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to send tokens from relay chain, {receipt.error_message}')

        now_token = self.wait_for_peaq_account_asset_change(kp_peaq.ss58_address, RELAY_ASSET_ID['peaq'])
        self.assertGreater(
            now_token, 0,
            f'Actual {now_token} should > expected {TEST_TOKEN_NUM} tokens')

        # Create lp asset
        liquity_token_num = int(TEST_TOKEN_NUM / 2)

        batch = ExtrinsicBatch(self.si_peaq, KP_GLOBAL_SUDO)
        compose_zdex_create_lppair(batch, 1)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Failed to create lp asset: {receipt.error_message}')

        batch = ExtrinsicBatch(self.si_peaq, kp_peaq)
        compose_zdex_add_liquidity(batch, 1, liquity_token_num, liquity_token_num)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Failed to add liquidity: {receipt.error_message}')

        # Register LP asset on PEAQ
        receipt = setup_xc_register_if_not_exist(
            self.si_peaq, KP_GLOBAL_SUDO,
            TEST_LP_ASSET_ID['peaq'], TEST_LP_ASSET_TOKEN['peaq'], UNITS_PER_SECOND)
        self.assertTrue(receipt.is_success, f'Failed to setup asset, {receipt.error_message}')

        # Register LP asset on ACA
        receipt = setup_aca_asset_if_not_exist(
            self.si_aca, KP_GLOBAL_SUDO, TEST_LP_ASSET_TOKEN['para'], TEST_ASSET_METADATA)
        self.assertTrue(receipt.is_success, f'Failed to register foreign asset: {receipt.error_message}')

        # Transfe it to the ACA
        transfer_token_num = int(liquity_token_num / 2)
        receipt = send_token_from_peaq_to_para(
            self.si_peaq, kp_peaq, kp_aca,
            ACA_PD_CHAIN_ID, TEST_LP_ASSET_ID['peaq'], transfer_token_num)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')
        got_token = self.wait_for_aca_account_token_change(kp_aca.ss58_address, TEST_LP_ASSET_ID['para'])
        self.assertNotEqual(got_token, 0)

        # Transfer it back to peaq
        transfer_back_token = got_token - REMAIN_TOKEN_NUM
        prev_balance = get_tokens_account_from_pallet_assets(
            self.si_peaq, kp_peaq.ss58_address, TEST_LP_ASSET_ID['peaq'])
        # Send it back to the peaq chain
        receipt = send_token_from_para_to_peaq(
            self.si_aca, kp_aca, kp_peaq,
            PEAQ_PD_CHAIN_ID, TEST_LP_ASSET_ID['para'], transfer_back_token)
        self.assertTrue(receipt.is_success, f'Failed to send token from para to peaq: {receipt.error_message}')

        # TODO Need to change because it's in the LPAsset, but not Asset
        now_balance = self.wait_for_peaq_account_asset_change(
            kp_peaq.ss58_address, TEST_LP_ASSET_ID['peaq'], prev_balance)
        self.assertGreater(now_balance, prev_balance, f'Actual {now_balance} should > expected {prev_balance}')

    def test_sibling_parachain_delivery_fee(self):
        # Setup
        kp_para_src = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        kp_para_dst = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        initial_balance = 1000 * 10 ** 18

        # Fund source account
        receipt = fund(self.si_peaq, KP_GLOBAL_SUDO, kp_para_src, initial_balance)
        self.assertTrue(receipt.is_success, f'Failed to fund account, {receipt.error_message}')

        # Get initial balance
        initial_balance = get_account_balance(self.si_peaq, kp_para_src.ss58_address)

        # Send tokens from one parachain to another
        receipt = send_token_from_peaq_to_para(
            self.si_peaq, kp_para_src, kp_para_dst,
            ACA_PD_CHAIN_ID, PEAQ_ASSET_ID['peaq'], TEST_TOKEN_NUM)
        self.assertTrue(receipt.is_success, f'Failed to send token from peaq to relay chain: {receipt.error_message}')

        # Get final balance
        final_balance = get_account_balance(self.si_peaq, kp_para_src.ss58_address)

        # Calculate the delivery fee
        delivery_fee = initial_balance - final_balance - TEST_TOKEN_NUM

        # Assert that the delivery fee is within the expected range
        self.assertGreaterEqual(delivery_fee, 0)
        self.assertLessEqual(delivery_fee, 200000000000)
