import time
from tools.utils import WS_URL
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import ExtrinsicBatch

import unittest
# from tools.pallet_assets_test import pallet_assets_test


def utf8_to_ascii(utf8str):
    return [int(utf8str[i:i+2], 16) for i in range(0, len(utf8str), 2)]


def storage_rpc_read(substrate, kp_src, item_type):
    data = substrate.rpc_request('peaqstorage_readAttribute', [
                                 kp_src.ss58_address, item_type])
    return data["result"]["item"]


class TestPalletStorage(unittest.TestCase):

    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)

    def test_storage(self):
        kp_src = Keypair.create_from_uri('//Alice')
        batch = ExtrinsicBatch(self._substrate, kp_src)
        item_type = f'0x{int(time.time())}'
        item = '0x032132'

        batch.compose_call(
            'PeaqStorage',
            'add_item',
            {
                'item_type': item_type,
                'item': item,
            })

        bl_hash = batch.execute_n_clear()
        self.assertTrue(bl_hash, f'storage_add_item failed: {bl_hash}')
        self.assertEqual(storage_rpc_read(self._substrate, kp_src, item_type), item)

    def test_storage_update(self):
        kp_src = Keypair.create_from_uri('//Alice')
        batch = ExtrinsicBatch(self._substrate, kp_src)
        item_type = f'0x{int(time.time())}'
        item = '0x032132'

        batch.compose_call(
            'PeaqStorage',
            'add_item',
            {
                'item_type': item_type,
                'item': item,
            })

        batch.compose_call(
            'PeaqStorage',
            'get_item',
            {
                'item_type': item_type,
            })

        batch.compose_call(
            'PeaqStorage',
            'update_item',
            {
                'item_type': item_type,
                'item': '0x0123',
            })
        bl_hash = batch.execute_n_clear()
        self.assertTrue(bl_hash, f'storage_update_item failed: {bl_hash}')
