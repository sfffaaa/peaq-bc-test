import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, TOKEN_NUM_BASE
from tools.utils import fund, get_account_balance


class TestFund(unittest.TestCase):
    def test_fund(self):
        substrate = SubstrateInterface(url=WS_URL)
        kp_dst = Keypair.create_from_uri('//Bob')
        receipt = fund(substrate, kp_dst, 500)
        self.assertTrue(receipt.is_success, f'fund failed: {receipt.error_message}')
        self.assertEqual(get_account_balance(substrate, kp_dst.ss58_address), 500 * TOKEN_NUM_BASE)
