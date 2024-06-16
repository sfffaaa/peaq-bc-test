import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from tools.utils import show_account, send_approval, send_proposal, get_as_multi_extrinsic_id
from peaq.extrinsic import transfer
from peaq.utils import calculate_multi_sig
import random

TOKEN_NUM_BASE = 10 ** 18


class PalletMultisig(unittest.TestCase):

    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL,)
        self.kp_src = Keypair.create_from_uri('//Alice')
        self.kp_dst = Keypair.create_from_uri('//Bob//stash')

    def test_multisig(self):
        threshold = 2
        signators = [self.kp_src, self.kp_dst]
        multi_sig_addr = calculate_multi_sig(signators, threshold)

        num = random.randint(1, 10000)
        # Deposit to wallet addr
        transfer(self.substrate, self.kp_src, multi_sig_addr, num * TOKEN_NUM_BASE, 1)

        payload = self.substrate.compose_call(
            call_module='Balances',
            call_function='transfer',
            call_params={
                'dest': self.kp_src.ss58_address,
                'value': num * TOKEN_NUM_BASE
            })

        # Send proposal
        pre_multisig_token = show_account(self.substrate, multi_sig_addr, 'before transfer')

        receipt = send_proposal(self.substrate, self.kp_src, self.kp_dst, threshold, payload)
        self.assertTrue(receipt.is_success,
                        f'as_multi failed: {receipt.error_message} + ' +
                        f'{self.substrate.get_events(receipt.block_hash)}')
        timepoint = get_as_multi_extrinsic_id(receipt)

        receipt = send_approval(self.substrate, self.kp_dst, [self.kp_src],
                                threshold, payload, timepoint)
        self.assertTrue(receipt.is_success,
                        f'approve_as_multi failed: {receipt.error_message} + ' +
                        f'{self.substrate.get_events(receipt.block_hash)}')
        receipt = send_proposal(self.substrate, self.kp_src, self.kp_dst, threshold, payload, timepoint)
        self.assertTrue(receipt.is_success,
                        f'as_multi failed: {receipt.error_message} + ' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        post_multisig_token = show_account(self.substrate, multi_sig_addr, 'after transfer')
        print(f'pre_multisig_token: {pre_multisig_token}, post_multisig_token: {post_multisig_token}')
        print(f'num: {num}, num * TOKEN_NUM_BASE: {num * TOKEN_NUM_BASE}')
        self.assertEqual(post_multisig_token + num * TOKEN_NUM_BASE, pre_multisig_token)
