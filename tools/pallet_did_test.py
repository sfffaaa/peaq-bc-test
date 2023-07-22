import unittest
import sys
sys.path.append('./')
import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL


class TestPalletDid(unittest.TestCase):
    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL)
        self.kp_src = Keypair.create_from_uri('//Alice')

    def did_add(self, substrate, kp_src, name, value):
        nonce = substrate.get_account_nonce(kp_src.ss58_address)
        call = substrate.compose_call(
            call_module='PeaqDid',
            call_function='add_attribute',
            call_params={
                'did_account': kp_src.ss58_address,
                'name': name,
                'value': value,
                'valid_for': None,
            })

        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=kp_src,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        show_extrinsic(receipt, 'did_add')

        self.assertTrue(receipt.is_success,
                        f'Add did failed: {receipt.error_message} + ' +
                        f'{substrate.get_events(receipt.block_hash)}')

    def did_update(self, substrate, kp_src, name, value):
        nonce = substrate.get_account_nonce(kp_src.ss58_address)
        call = substrate.compose_call(
            call_module='PeaqDid',
            call_function='update_attribute',
            call_params={
                'did_account': kp_src.ss58_address,
                'name': name,
                'value': value,
                'valid_for': None,
            })

        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=kp_src,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        show_extrinsic(receipt, 'did_update')

        self.assertTrue(receipt.is_success,
                        f'Add did failed: {receipt.error_message} + ' +
                        f'{substrate.get_events(receipt.block_hash)}')

    def did_remove(self, substrate, kp_src, name):
        nonce = substrate.get_account_nonce(kp_src.ss58_address)
        call = substrate.compose_call(
            call_module='PeaqDid',
            call_function='remove_attribute',
            call_params={
                'did_account': kp_src.ss58_address,
                'name': name,
            })

        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=kp_src,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        show_extrinsic(receipt, 'did_remove')

        self.assertTrue(receipt.is_success,
                        f'Add did failed: {receipt.error_message} + ' +
                        f'{substrate.get_events(receipt.block_hash)}')

    def did_rpc_read(self, substrate, kp_src, name):
        data = substrate.rpc_request('peaqdid_readAttribute', [kp_src.ss58_address, name])
        return data['result']

    def test_did_actions(self):
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        name = int(time.time())

        key = f'0x{name}'
        value = '0x02'
        self.did_add(self.substrate, self.kp_src, key, value)
        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data['name'], key)
        self.assertEqual(data['value'], value)

        value = '0x03'
        self.did_update(self.substrate, self.kp_src, key, value)
        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data['name'], key)
        self.assertEqual(data['value'], value)

        self.did_remove(self.substrate, self.kp_src, key)
        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data, None)
