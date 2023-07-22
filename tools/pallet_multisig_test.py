import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import TOKEN_NUM_BASE, calculate_multi_sig, show_extrinsic, WS_URL
from tools.utils import transfer, show_account
import random


class PalletMultiSig(unittest.TestCase):

    def send_proposal(self, substrate, kp_src, kp_dst, threshold, payload, timepoint=None):
        nonce = substrate.get_account_nonce(kp_src.ss58_address)

        as_multi_call = substrate.compose_call(
            call_module='MultiSig',
            call_function='as_multi',
            call_params={
                'threshold': threshold,
                'other_signatories': [kp_dst.ss58_address],
                'maybe_timepoint': timepoint,
                'call': payload.value,
                'max_weight': {'ref_time': 1000000000, 'proof_size': 1000000},
            })

        extrinsic = substrate.create_signed_extrinsic(
            call=as_multi_call,
            keypair=kp_src,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        show_extrinsic(receipt, 'as_multi')
        self.assertTrue(receipt.is_success,
                        f'as_multi failed: {receipt.error_message} + ' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        info = receipt.get_extrinsic_identifier().split('-')
        return {'height': int(info[0]), 'index': int(info[1])}

    def send_approval(self, substrate, kp_src, kps, threshold, payload, timepoint):
        nonce = self.substrate.get_account_nonce(kp_src.ss58_address)

        as_multi_call = substrate.compose_call(
            call_module='MultiSig',
            call_function='approve_as_multi',
            call_params={
                'threshold': threshold,
                'other_signatories': [kp.ss58_address for kp in kps],
                'maybe_timepoint': timepoint,
                'call_hash': f'0x{payload.call_hash.hex()}',
                'max_weight': {'ref_time': 1000000000, 'proof_size': 1000000},
            })

        extrinsic = substrate.create_signed_extrinsic(
            call=as_multi_call,
            keypair=kp_src,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        show_extrinsic(receipt, 'approve_as_multi')
        self.assertTrue(receipt.is_success,
                        f'approve_as_multi failed: {receipt.error_message} + ' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

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
        transfer(self.substrate, self.kp_src, multi_sig_addr, num)

        payload = self.substrate.compose_call(
            call_module='Balances',
            call_function='transfer',
            call_params={
                'dest': self.kp_src.ss58_address,
                'value': num * TOKEN_NUM_BASE
            })

        # Send proposal
        pre_multisig_token = show_account(self.substrate, multi_sig_addr, 'before transfer')

        timepoint = self.send_proposal(self.substrate, self.kp_src, self.kp_dst, threshold, payload)
        self.send_approval(self.substrate, self.kp_dst, [self.kp_src],
                           threshold, payload, timepoint)
        self.send_proposal(self.substrate, self.kp_src, self.kp_dst, threshold, payload, timepoint)

        post_multisig_token = show_account(self.substrate, multi_sig_addr, 'after transfer')
        print(f'pre_multisig_token: {pre_multisig_token}, post_multisig_token: {post_multisig_token}')
        print(f'num: {num}, num * TOKEN_NUM_BASE: {num * TOKEN_NUM_BASE}')
        self.assertEqual(post_multisig_token + num * TOKEN_NUM_BASE, pre_multisig_token)
