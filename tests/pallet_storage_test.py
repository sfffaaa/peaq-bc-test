import time
from tools.utils import WS_URL
from tools.utils import get_balance_reserve_value
from substrateinterface import SubstrateInterface, Keypair
from peaq.utils import ExtrinsicBatch
from peaq.storage import storage_add_payload, storage_update_payload, storage_rpc_read

import unittest


def storage_remove_payload(batch, item_type):
    batch.compose_call(
        'PeaqStorage',
        'remove_item',
        {'item_type': item_type}
    )


class TestPalletStorage(unittest.TestCase):

    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)
        self._kp_src = Keypair.create_from_uri('//Alice')

    def test_storage(self):
        reserved_before = get_balance_reserve_value(self._substrate, self._kp_src.ss58_address, 'peaqstor')

        batch = ExtrinsicBatch(self._substrate, self._kp_src)
        item_type = f'0x{int(time.time())}'
        item = '0x032132'

        storage_add_payload(batch, item_type, item)

        receipt = batch.execute_n_clear()
        self.assertTrue(receipt.is_success, f'storage_add_item failed: {receipt}')
        self.assertEqual(
            storage_rpc_read(self._substrate, self._kp_src.ss58_address, item_type)['item'],
            item)
        reserved_after = get_balance_reserve_value(self._substrate, self._kp_src.ss58_address, 'peaqstor')
        self.assertGreater(reserved_after, reserved_before)

    def test_storage_update(self):
        batch = ExtrinsicBatch(self._substrate, self._kp_src)
        item_type = f'0x{int(time.time())}'
        item = '0x032132'

        storage_add_payload(batch, item_type, item)
        storage_update_payload(batch, item_type, '0x0123')
        receipt = batch.execute_n_clear()
        self.assertTrue(receipt.is_success, f'storage_update_item failed: {receipt}')
        self.assertEqual(
            storage_rpc_read(self._substrate, self._kp_src.ss58_address, item_type)['item'],
            '0x0123')

    def test_storage_remove(self):
        reserved_before = get_balance_reserve_value(self._substrate, self._kp_src.ss58_address, 'peaqstor')
        batch = ExtrinsicBatch(self._substrate, self._kp_src)
        item_type = f'0x{int(time.time())}'
        item = '0x032132'

        storage_add_payload(batch, item_type, item)
        storage_remove_payload(batch, item_type)
        receipt = batch.execute_n_clear()

        self.assertTrue(receipt.is_success, f'storage_remove_item failed: {receipt}')
        self.assertEqual(
            storage_rpc_read(self._substrate, self._kp_src.ss58_address, item_type),
            None)
        reserved_after = get_balance_reserve_value(self._substrate, self._kp_src.ss58_address, 'peaqstor')
        self.assertEqual(reserved_after, reserved_before)
