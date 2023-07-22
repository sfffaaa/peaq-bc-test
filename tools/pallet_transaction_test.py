import unittest
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL


class TestPalletTransaction(unittest.TestCase):
    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL)
        self.kp_src = Keypair.create_from_uri('//Alice')
        self.kp_dst = Keypair.create_from_uri('//Bob//stash')

    def service_request(self, substrate, kp_src, kp_dst, token_num):
        nonce = substrate.get_account_nonce(kp_src.ss58_address)
        call = substrate.compose_call(
            call_module='Transaction',
            call_function='service_requested',
            call_params={
                'provider': kp_dst.ss58_address,
                'token_deposited': token_num
            })

        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=kp_src,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        show_extrinsic(receipt, 'service_requested')

        self.assertTrue(receipt.is_success,
                        f'service_requested failed: {receipt.error_message} + ' +
                        f'{substrate.get_events(receipt.block_hash)}')

        return receipt, call

    def service_deliver(self, substrate, kp_src, kp_dst, receipt, call):
        # Do the request service
        info = receipt.get_extrinsic_identifier().split('-')
        timepoint = {'height': int(info[0]), 'index': int(info[1])}

        # Do the deleivery_server
        nonce = substrate.get_account_nonce(kp_src.ss58_address)
        call = substrate.compose_call(
            call_module='Transaction',
            call_function='service_delivered',
            call_params={
                'consumer': kp_dst.ss58_address,
                'refund_info': {
                    'token_num': 10,
                    'tx_hash': receipt.extrinsic_hash,
                    'time_point': timepoint,
                    'call_hash': f'0x{call.call_hash.hex()}',
                },
                'spent_info': {
                    'token_num': 20,
                    'tx_hash': receipt.extrinsic_hash,
                    'time_point': timepoint,
                    'call_hash': f'0x{call.call_hash.hex()}',
                }
            })

        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=kp_src,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        show_extrinsic(receipt, 'service_delivered')

        self.assertTrue(receipt.is_success,
                        f'service_delivered failed: {receipt.error_message} + ' +
                        f'{substrate.get_events(receipt.block_hash)}')

    def test_transaction(self):
        # fund(substrate, kp_src, 500)
        # transfer(substrate, kp_src, kp_dst.ss58_address, 50)
        receipt, call = self.service_request(self.substrate, self.kp_src, self.kp_dst, 50)
        self.service_deliver(self.substrate, self.kp_src, self.kp_dst, receipt, call)
