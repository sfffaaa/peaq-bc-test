import unittest
import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from peaq.utils import ExtrinsicBatch


def did_add(batch, kp_src, name, value):
    batch.compose_call('PeaqDid', 'add_attribute', {
        'did_account': kp_src.ss58_address,
        'name': name,
        'value': value,
        'valid_for': None,
    })


def did_update(batch, kp_src, name, value):
    batch.compose_call(
        'PeaqDid',
        'update_attribute',
        {
            'did_account': kp_src.ss58_address,
            'name': name,
            'value': value,
            'valid_for': None,
        })


def did_remove(batch, kp_src, name):
    batch.compose_call(
        'PeaqDid',
        'remove_attribute',
        {
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

    def test_did_add(self):
        name = int(time.time())
        batch = ExtrinsicBatch(self.substrate, self.kp_src)

        key = f'0x{name}'
        value = '0x02'
        did_add(batch, self.kp_src, key, value)
        bl_hash = batch.execute_n_clear()
        self.assertTrue(bl_hash,
                        f'failed to add did: bl_hash={bl_hash}')

        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data['name'], key)
        self.assertEqual(data['value'], value)

    def test_did_update(self):
        name = int(time.time())
        key = f'0x{name}'
        value = '0x02'
        batch = ExtrinsicBatch(self.substrate, self.kp_src)

        did_add(batch, self.kp_src, key, value)
        value = '0x03'
        did_update(batch, self.kp_src, key, value)
        bl_hash = batch.execute_n_clear()
        self.assertTrue(bl_hash,
                        f'failed to update did: bl_hash={bl_hash}')

        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data['name'], key)
        self.assertEqual(data['value'], value)

    def test_did_remove(self):
        name = int(time.time())
        key = f'0x{name}'
        value = '0x02'
        batch = ExtrinsicBatch(self.substrate, self.kp_src)

        did_add(batch, self.kp_src, key, value)
        did_remove(batch, self.kp_src, key)
        bl_hash = batch.execute_n_clear()
        self.assertTrue(bl_hash,
                        f'failed to remove did: bl_hash={bl_hash}')

        data = self.did_rpc_read(self.substrate, self.kp_src, key)
        self.assertEqual(data, None)
