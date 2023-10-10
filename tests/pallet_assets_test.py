import unittest
import sys
sys.path.append('./')
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from tools.asset import batch_create_asset, batch_set_metadata, batch_mint, get_valid_asset_id
from peaq.utils import ExtrinsicBatch


def get_asset_balance(conn, addr, asset_id):
    return conn.query("Assets", "Account", [asset_id, addr])


def set_metadata(conn, kp_admin, asset_id, name, symbol, decimals):
    batch = ExtrinsicBatch(conn, kp_admin)
    batch_set_metadata(batch, asset_id, name, symbol, decimals)
    return batch.execute()


def create_asset(conn, kp_creator, kp_admin, asset_id, min_balance=100):
    batch = ExtrinsicBatch(conn, kp_creator)
    batch_create_asset(batch, kp_admin.ss58_address, asset_id, min_balance)
    return batch.execute()


def freeze_asset(conn, kp_admin, asset_id):
    batch = ExtrinsicBatch(conn, kp_admin)
    batch_freeze_asset(batch, asset_id)
    return batch.execute()


def batch_freeze_asset(batch, asset_id):
    batch.compose_call(
        'Assets',
        'freeze_asset',
        {
            'id': asset_id,
        }
    )


def thaw_asset(conn, kp_admin, asset_id):
    batch = ExtrinsicBatch(conn, kp_admin)
    batch_thaw_asset(batch, asset_id)
    return batch.execute()


def batch_thaw_asset(batch, asset_id):
    batch.compose_call(
        'Assets',
        'thaw_asset',
        {
            'id': asset_id,
        }
    )


def mint(conn, kp_admin, addr_src, asset_id, token_amount):
    batch = ExtrinsicBatch(conn, kp_admin)
    batch_mint(batch, addr_src, asset_id, token_amount)
    return batch.execute()


def burn(conn, kp_admin, addr_src, asset_id, token_amount):
    batch = ExtrinsicBatch(conn, kp_admin)
    batch_burn(batch, addr_src, asset_id, token_amount)
    return batch.execute()


def batch_burn(batch, addr_src, asset_id, token_amount):
    batch.compose_call(
        'Assets',
        'burn',
        {
            'id': asset_id,
            'who': addr_src,
            'amount': token_amount,
        }
    )


def transfer(conn, kp_src, kp_dst, asset_id, token_amount):
    batch = ExtrinsicBatch(conn, kp_src)
    batch_transfer(batch, kp_dst.ss58_address, asset_id, token_amount)
    return batch.execute()


def batch_transfer(batch, addr_dst, asset_id, token_amount):
    batch.compose_call(
        'Assets',
        'transfer',
        {
            'id': asset_id,
            'target': addr_dst,
            'amount': token_amount,
        }
    )


def freeze(conn, kp_admin, kp_src, asset_id):
    batch = ExtrinsicBatch(conn, kp_admin)
    batch_freeze(batch, kp_src, asset_id)
    return batch.execute()


def batch_freeze(batch, kp_src, asset_id):
    batch.compose_call(
        'Assets',
        'freeze',
        {
            'id': asset_id,
            'who': kp_src.ss58_address,
        }
    )


def thaw(conn, kp_admin, kp_src, asset_id):
    batch = ExtrinsicBatch(conn, kp_admin)
    batch_thaw(batch, kp_src, asset_id)
    return batch.execute()


def batch_thaw(batch, kp_src, asset_id):
    batch.compose_call(
        'Assets',
        'thaw',
        {
            'id': asset_id,
            'who': kp_src.ss58_address,
        }
    )


# Only for partial testing
class pallet_assets_test(unittest.TestCase):
    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)
        self._kp_creator = Keypair.create_from_uri('//Alice')
        self._kp_admin = Keypair.create_from_uri('//Bob')

    def test_create_asset(self):
        asset_id = get_valid_asset_id(self._substrate)
        receipt = create_asset(self._substrate, self._kp_creator, self._kp_admin, asset_id)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')

    def test_set_metadata_asset(self):
        asset_id = get_valid_asset_id(self._substrate)
        batch = ExtrinsicBatch(self._substrate, self._kp_creator)
        batch_create_asset(batch, self._kp_admin.ss58_address, asset_id)
        # Execute
        batch_set_metadata(batch, asset_id, 'WOW', 'WOW', 18)
        receipt = batch.execute()

        # Check
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')

        # Test
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        asset = self._substrate.query("Assets", "Metadata", [asset_id]).value
        self.assertEqual(asset['symbol'], 'WOW')
        self.assertEqual(asset['name'], 'WOW')
        self.assertEqual(asset['decimals'], 18)

    def test_mint_burn(self):
        conn = self._substrate
        kp_admin = self._kp_admin
        asset_id = get_valid_asset_id(conn)
        batch = ExtrinsicBatch(conn, self._kp_creator)
        receipt = create_asset(conn, self._kp_creator, kp_admin, asset_id)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        kp_src = Keypair.create_from_uri('//Alice//stash')

        # Execute
        batch = ExtrinsicBatch(conn, kp_admin)
        mint_number = 10000
        burn_number = 5000
        batch_mint(batch, kp_src.ss58_address, asset_id, mint_number)
        batch_burn(batch, kp_src.ss58_address, asset_id, burn_number)
        receipt = batch.execute()

        # Check
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertEqual(
            get_asset_balance(conn, kp_src.ss58_address, asset_id).value['balance'],
            0 + mint_number - burn_number,
            f'Balance is not correct: {get_asset_balance(conn, kp_src.ss58_address, asset_id).value["balance"]}')

    def test_transfer(self):
        conn = self._substrate
        kp_admin = self._kp_admin
        asset_id = get_valid_asset_id(conn)
        batch = ExtrinsicBatch(conn, self._kp_creator)
        receipt = create_asset(conn, self._kp_creator, kp_admin, asset_id)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        kp_dst = Keypair.create_from_uri('//Alice//stash')

        # Execute
        batch = ExtrinsicBatch(conn, kp_admin)
        mint_number = 10000
        batch_mint(batch, kp_admin.ss58_address, asset_id, mint_number)
        transfer_number = 5000
        batch_transfer(batch, kp_dst.ss58_address, asset_id, transfer_number)
        receipt = batch.execute()

        # Check
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertEqual(
            get_asset_balance(conn, kp_admin.ss58_address, asset_id).value['balance'],
            0 + mint_number - transfer_number,
            f'Balance is not correct: {get_asset_balance(conn, kp_dst.ss58_address, asset_id).value["balance"]}')

        self.assertEqual(
            get_asset_balance(conn, kp_dst.ss58_address, asset_id).value['balance'],
            0 + transfer_number,
            f'Balance is not correct: {get_asset_balance(conn, kp_dst.ss58_address, asset_id).value["balance"]}')

    def test_freeze_thaw_asset(self):
        conn = self._substrate
        asset_id = get_valid_asset_id(conn)
        batch = ExtrinsicBatch(conn, self._kp_creator)
        batch_create_asset(batch, self._kp_creator.ss58_address, asset_id)
        batch_freeze_asset(batch, asset_id)
        batch_thaw_asset(batch, asset_id)
        receipt = batch.execute()

        # Check
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertEqual(
            conn.query("Assets", "Asset", [asset_id]).value['status'],
            'Live',
            f'Asset id: {asset_id}: Asset is not thawed: {conn.query("Assets", "Asset", [asset_id])}')

    def test_all(self):
        conn = self._substrate
        asset_id = get_valid_asset_id(conn)

        kp_creator = Keypair.create_from_uri('//Alice')
        kp_admin = Keypair.create_from_uri('//Bob')
        # Done
        receipt = create_asset(conn, kp_creator, kp_admin, asset_id)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')

        kp_src = Keypair.create_from_uri('//Alice//stash')
        mint_number = 10000
        # Done
        receipt = mint(conn, kp_admin, kp_src.ss58_address, asset_id, mint_number)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertEqual(
            get_asset_balance(conn, kp_src.ss58_address, asset_id).value['balance'],
            0 + mint_number,
            f'Balance is not correct: {get_asset_balance(conn, kp_src.ss58_address, asset_id).value["balance"]}')

        burn_number = 5000
        # Done
        receipt = burn(conn, kp_admin, kp_src.ss58_address, asset_id, burn_number)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertEqual(
            get_asset_balance(conn, kp_src.ss58_address, asset_id).value['balance'],
            0 + mint_number - burn_number,
            f'Balance is not correct: {get_asset_balance(conn, kp_src.ss58_address, asset_id).value["balance"]}')

        transfer_number = 500
        kp_dst = Keypair.create_from_uri('//Bob//stash')
        # Done
        receipt = transfer(conn, kp_src, kp_dst, asset_id, transfer_number)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertEqual(
            get_asset_balance(conn, kp_src.ss58_address, asset_id).value['balance'],
            0 + mint_number - burn_number - transfer_number,
            f'Balance is not correct: {get_asset_balance(conn, kp_src.ss58_address, asset_id).value["balance"]}')
        self.assertEqual(
            get_asset_balance(conn, kp_dst.ss58_address, asset_id).value['balance'],
            0 + transfer_number,
            f'Balance is not correct: {get_asset_balance(conn, kp_dst.ss58_address, asset_id).value["balance"]}')

        # Done
        receipt = freeze_asset(conn, kp_admin, asset_id)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertEqual(
            conn.query("Assets", "Asset", [asset_id]).value['status'],
            'Frozen',
            f'Asset id: {asset_id}: Asset is not frozen: {conn.query("Assets", "Asset", [asset_id])}')

        # Done
        receipt = thaw_asset(conn, kp_admin, asset_id)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertEqual(
            conn.query("Assets", "Asset", [asset_id]).value['status'],
            'Live',
            f'Asset id: {asset_id}: Asset is not thawed: {conn.query("Assets", "Asset", [asset_id])}')

        receipt = freeze(conn, kp_admin, kp_src, asset_id)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertTrue(
            get_asset_balance(conn, kp_src.ss58_address, asset_id).value['is_frozen'],
            f'Asset id: {asset_id}: Account is not frozen: {get_asset_balance(conn, kp_src.ss58_address, asset_id)}')
        receipt = thaw(conn, kp_admin, kp_src, asset_id)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')
        self.assertFalse(
            get_asset_balance(conn, kp_src.ss58_address, asset_id).value['is_frozen'],
            f'Asset id: {asset_id}: Account is not thawed: {get_asset_balance(conn, kp_src.ss58_address, asset_id)}')
