import time
from tools.utils import WS_URL
from substrateinterface import SubstrateInterface, Keypair
from peaq.utils import ExtrinsicBatch
from peaq.storage import storage_add_payload, storage_update_payload, storage_rpc_read

import unittest
# from tools.pallet_assets_test import pallet_assets_test


class TestPalletStorage(unittest.TestCase):

    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)

    def test_storage(self):
        kp_src = Keypair.create_from_uri('//Alice')
        batch = ExtrinsicBatch(self._substrate, kp_src)
        item_type = f'0x{int(time.time())}'
        item = '0x032132'

        storage_add_payload(batch, item_type, item)

        receipt = batch.execute_n_clear()
        self.assertTrue(receipt.is_success, f'storage_add_item failed: {receipt}')
        self.assertEqual(
            storage_rpc_read(self._substrate, kp_src.ss58_address, item_type)['item'],
            item)

    def test_storage_update(self):
        kp_src = Keypair.create_from_uri('//Alice')
        batch = ExtrinsicBatch(self._substrate, kp_src)
        item_type = f'0x{int(time.time())}'
        item = '0x032132'

        storage_add_payload(batch, item_type, item)
        storage_update_payload(batch, item_type, '0x0123')
        receipt = batch.execute_n_clear()
        self.assertTrue(receipt.is_success, f'storage_update_item failed: {receipt}')
        self.assertEqual(
            storage_rpc_read(self._substrate, kp_src.ss58_address, item_type)['item'],
            '0x0123')
