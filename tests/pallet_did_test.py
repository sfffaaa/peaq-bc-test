import unittest
import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from tools.payload import user_extrinsic_send


@user_extrinsic_send
def did_add(substrate, kp_src, name, value):
    return substrate.compose_call(
        call_module='PeaqDid',
        call_function='add_attribute',
        call_params={
            'did_account': kp_src.ss58_address,
            'name': name,
            'value': value,
            'valid_for': None,
        })


@user_extrinsic_send
def did_update(substrate, kp_src, name, value):
    return substrate.compose_call(
        call_module='PeaqDid',
        call_function='update_attribute',
        call_params={
            'did_account': kp_src.ss58_address,
            'name': name,
            'value': value,
            'valid_for': None,
        })


@user_extrinsic_send
def did_remove(substrate, kp_src, name):
    return substrate.compose_call(
        call_module='PeaqDid',
        call_function='remove_attribute',
        call_params={
            'did_account': kp_src.ss58_address,
            'name': name,
        })


class TestPalletDid(unittest.TestCase):
    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL)
        self.kp_src = Keypair.create_from_uri('//Alice')

    def did_rpc_read(self, substrate, kp_src, name):
        data = substrate.rpc_request('peaqdid_readAttribute', [kp_src.ss58_address, name])
        return data['result']

    def test_did_actions(self):
        name = int(time.time())

        key = f'0x{name}'
        value = '0x02'
        receipt = did_add(self.substrate, self.kp_src, key, value)
        self.assertTrue(receipt.is_success,
                        f'Add did failed: {receipt.error_message} + ' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data['name'], key)
        self.assertEqual(data['value'], value)

        value = '0x03'
        receipt = did_update(self.substrate, self.kp_src, key, value)
        self.assertTrue(receipt.is_success,
                        f'Add did failed: {receipt.error_message} + ' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data['name'], key)
        self.assertEqual(data['value'], value)

        receipt = did_remove(self.substrate, self.kp_src, key)
        self.assertTrue(receipt.is_success,
                        f'Add did failed: {receipt.error_message} + ' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data, None)
