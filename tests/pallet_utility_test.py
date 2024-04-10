from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, TOKEN_NUM_BASE
from peaq.utils import show_extrinsic
from tools.utils import show_account
import unittest

# An arbitrary amount to be transfered from source to destination
AMOUNT_TO_BE_TRANSFERED = 1

# a valid funds transfer transaction from src to dest with batch
# after transaction, dest will be credited twice as AMOUNT_TO_BE_TRANSFERED


class TestPalletUtility(unittest.TestCase):

    # source account
    kp_src = Keypair.create_from_uri('//Alice')
    # destination account
    kp_dst = Keypair.create_from_uri('//Eve')

    def setUp(self):
        # deinfe a conneciton with a peaq-network node
        self.substrate = SubstrateInterface(
                url=WS_URL
            )

    def test_all_valid_extrinsics_bath(self):
        substrate = self.substrate
        kp_src = self.kp_src
        kp_dst = self.kp_dst

        # check account balances before transactions
        show_account(substrate, kp_src.ss58_address, "src bal before trans")
        bal_dst_before = show_account(substrate,
                                      kp_dst.ss58_address, "Dest bal before trans")
        nonce = substrate.get_account_nonce(kp_src.ss58_address)

        # a valid  transaciton
        payload_first = substrate.compose_call(
            call_module='Balances',
            call_function='transfer',
            call_params={
                'dest': kp_dst.ss58_address,
                'value': AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE
            })

        # above valid transaciton repeated twice to compose a bath of transaction
        batch = substrate.compose_call(
            call_module='Utility',
            call_function='batch',
            call_params={
                'calls': [payload_first.value, payload_first.value],
            })

        extrinsic = substrate.create_signed_extrinsic(call=batch,
                                                      keypair=kp_src,
                                                      era={'period': 64},
                                                      nonce=nonce)

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        self.assertTrue(receipt.is_success,
                        f'Batch extrinsic failed: {receipt.error_message} + ' +
                        f'{substrate.get_events(receipt.block_hash)}')

        # check account balances after transaciton
        show_account(substrate, kp_src.ss58_address, "Src bal after trans")
        bal_dst_after = show_account(substrate,
                                     kp_dst.ss58_address, "Dest bal after trans")

        show_extrinsic(receipt, 'batch')
        # since same amount has been transfered two times
        self.assertEqual(bal_dst_before + (AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE) * 2,
                         bal_dst_after)

    def test_all_valid_extrinsics_bath_all(self):
        substrate = self.substrate
        kp_src = self.kp_src
        kp_dst = self.kp_dst

        # check account balances before transactions
        show_account(substrate, kp_src.ss58_address, "src bal before trans")
        bal_dst_before = show_account(substrate,
                                      kp_dst.ss58_address, "Dest bal before trans")
        nonce = substrate.get_account_nonce(kp_src.ss58_address)

        # a valid  transaciton
        payload_first = substrate.compose_call(
            call_module='Balances',
            call_function='transfer',
            call_params={
                'dest': kp_dst.ss58_address,
                'value': AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE
            })

        # above valid transaciton repeated twice to compose a bath_all of trans
        batch = substrate.compose_call(
            call_module='Utility',
            call_function='batch_all',
            call_params={
                'calls': [payload_first.value, payload_first.value],
            })

        extrinsic = substrate.create_signed_extrinsic(call=batch,
                                                      keypair=kp_src,
                                                      era={'period': 64},
                                                      nonce=nonce)

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        self.assertTrue(receipt.is_success,
                        f'Batch extrinsic failed: {receipt.error_message} + ' +
                        f'{substrate.get_events(receipt.block_hash)}')

        # check account balances after transaciton
        show_account(substrate, kp_src.ss58_address, "Src bal after trans")
        bal_dst_after = show_account(substrate,
                                     kp_dst.ss58_address, "Dest bal after trans")

        show_extrinsic(receipt, 'batch')
        # since same amount has been transfered two times
        self.assertEqual(bal_dst_before + (AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE) * 2, bal_dst_after)

    def test_atleast_one_invalid_extrinsic_bath(self):
        substrate = self.substrate
        kp_src = self.kp_src
        kp_dst = self.kp_dst

        # check account balances before transactions
        show_account(substrate, kp_src.ss58_address, "src bal before trans")
        bal_dst_before = show_account(substrate,
                                      kp_dst.ss58_address, "Dest bal before trans")
        nonce = substrate.get_account_nonce(kp_src.ss58_address)

        # a valid  transaciton
        payload_first = substrate.compose_call(
            call_module='Balances',
            call_function='transfer',
            call_params={
                'dest': kp_dst.ss58_address,
                'value': AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE
            })

        # Second invalid transaciton
        payload_second = substrate.compose_call(
            call_module='Balances',
            call_function='force_transfer',
            call_params={
                'source': kp_src.ss58_address,
                'dest': kp_dst.ss58_address,
                'value': AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE
            })

        # batch of valid and atleast one iinvalid transactionss
        batch = substrate.compose_call(
            call_module='Utility',
            call_function='batch',
            call_params={
                'calls': [payload_first.value, payload_second.value],
            })

        extrinsic = substrate.create_signed_extrinsic(call=batch,
                                                      keypair=kp_src,
                                                      era={'period': 64},
                                                      nonce=nonce)

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        self.assertTrue(receipt.is_success,
                        f'Batch extrinsic failed: {receipt.error_message} + ' +
                        f'{substrate.get_events(receipt.block_hash)}')

        # check account balances after transaciton
        show_account(substrate, kp_src.ss58_address, "Src bal after trans")
        bal_dst_after = show_account(substrate,
                                     kp_dst.ss58_address, "Dest bal after trans")

        show_extrinsic(receipt, 'batch')
        # since amount has been transfered only once
        self.assertEqual(bal_dst_before + (AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE), bal_dst_after)

    def test_atleast_one_invalid_extrinsic_bath_all(self):
        substrate = self.substrate
        kp_src = self.kp_src
        kp_dst = self.kp_dst

        # check account balances before transactions
        show_account(substrate, kp_src.ss58_address, "src bal before trans")
        bal_dst_before = show_account(substrate,
                                      kp_dst.ss58_address, "Dest bal before trans")
        nonce = substrate.get_account_nonce(kp_src.ss58_address)

        # a valid  transaciton
        payload_first = substrate.compose_call(
            call_module='Balances',
            call_function='transfer',
            call_params={
                'dest': kp_dst.ss58_address,
                'value': AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE
            })

        # Second invalid transaciton
        payload_second = substrate.compose_call(
            call_module='Balances',
            call_function='force_transfer',
            call_params={
                'source': kp_src.ss58_address,
                'dest': kp_dst.ss58_address,
                'value': AMOUNT_TO_BE_TRANSFERED * TOKEN_NUM_BASE
            })

        # batch of valid and atleast one iinvalid transactionss
        batch = substrate.compose_call(
            call_module='Utility',
            call_function='batch_all',
            call_params={
                'calls': [payload_first.value, payload_second.value],
            })

        extrinsic = substrate.create_signed_extrinsic(call=batch,
                                                      keypair=kp_src,
                                                      era={'period': 64},
                                                      nonce=nonce)

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        # check account balances after transaciton
        show_account(substrate, kp_src.ss58_address, "Src bal after trans")
        bal_dst_after = show_account(substrate,
                                     kp_dst.ss58_address, "Dest bal after trans")

        show_extrinsic(receipt, 'batch')
        # since due to an invalid transation, all transactions will be reverted
        self.assertEqual(bal_dst_before, bal_dst_after)
