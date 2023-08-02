import time
from tools.utils import WS_URL
from substrateinterface import SubstrateInterface, Keypair
from tools.payload import user_extrinsic_send

import unittest
# from tools.pallet_assets_test import pallet_assets_test


def utf8_to_ascii(utf8str):
    return [int(utf8str[i:i+2], 16) for i in range(0, len(utf8str), 2)]


def storage_rpc_read(substrate, kp_src, item_type):
    data = substrate.rpc_request('peaqstorage_readAttribute', [
                                 kp_src.ss58_address, item_type])
    return data["result"]["item"]


@user_extrinsic_send
def storage_add_item(substrate, kp_src, item_type, item):
    return substrate.compose_call(
        call_module='PeaqStorage',
        call_function='add_item',
        call_params={
            'item_type': item_type,
            'item': item,
        })


@user_extrinsic_send
def storage_batch_transaction_ok(substrate, kp_src, item_type, item):
    payload_first = substrate.compose_call(
        call_module='PeaqStorage',
        call_function='add_item',
        call_params={
            'item_type': item_type,
            'item': item,
        })

    payload_second = substrate.compose_call(
        call_module='PeaqStorage',
        call_function='get_item',
        call_params={
            'item_type': item_type,
        })

    payload_third = substrate.compose_call(
        call_module='PeaqStorage',
        call_function='update_item',
        call_params={
            'item_type': item_type,
            'item': '0x0123',
        })

    # Wrape payload into a utility batch cal
    return substrate.compose_call(
        call_module='Utility',
        call_function='batch_all',
        call_params={
            'calls': [payload_first.value,
                      payload_second.value, payload_third.value],
        })


class TestPalletStorage(unittest.TestCase):

    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)

    def test_storage(self):
        kp_src = Keypair.create_from_uri('//Alice')
        item_type = f'0x{int(time.time())}'
        item = '0x032132'

        receipt = storage_add_item(self._substrate, kp_src, item_type, item)
        self.assertTrue(receipt.is_success, f'storage_add_item failed: {receipt.error_message}')
        self.assertEqual(storage_rpc_read(self._substrate, kp_src, item_type), item)

        item_type = f'0x{int(time.time()) + 1}'
        item = '0x032133'
        receipt = storage_batch_transaction_ok(self._substrate, kp_src, item_type, item)
        self.assertTrue(receipt.is_success, f'storage_batch_transaction_ok failed: {receipt.error_message}')
