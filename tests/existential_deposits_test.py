import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from peaq.extrinsic import transfer


class TestExitentialDeposits(unittest.TestCase):
    def get_existential_deposit(self):
        result = self.substrate.get_constant(
            'Balances',
            'ExistentialDeposit',
        )
        return result.value

    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL,)
        self.alice = Keypair.create_from_uri('//Alice')
        self.kp = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())

    def test_local_token(self):
        token = self.get_existential_deposit()
        self.assertGreater(token, 2)
        token /= 2

        # Execute -> Send local token to another account but below the Exitential Deposits
        receipt = transfer(
            self.substrate,
            self.alice,
            self.kp.ss58_address,
            token,
            1
        )

        # Check: the error happens
        self.assertFalse(receipt.is_success)
        self.assertEqual(receipt.error_message['name'], 'ExistentialDeposit')
