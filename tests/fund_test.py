import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from peaq.sudo_extrinsic import fund
from peaq.utils import get_account_balance
from tools.utils import KP_GLOBAL_SUDO

TOKEN_NUM_BASE = pow(10, 18)


class TestFund(unittest.TestCase):
    def test_fund(self):
        substrate = SubstrateInterface(url=WS_URL)
        kp_dst = Keypair.create_from_uri('//Bob')
        receipt = fund(substrate, KP_GLOBAL_SUDO, kp_dst, 500 * TOKEN_NUM_BASE)
        self.assertTrue(receipt.is_success, f'fund failed: {receipt.error_message}')
        self.assertEqual(get_account_balance(substrate, kp_dst.ss58_address), 500 * TOKEN_NUM_BASE)
