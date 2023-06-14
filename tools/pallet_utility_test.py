from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL, TOKEN_NUM_BASE
from tools.utils import show_account

# The purpose of this code is to test pallet_utility functionality

# deinfe a conneciton with a peaq-network node
substrate = SubstrateInterface(
        url=WS_URL
    )

# source account
kp_src = Keypair.create_from_uri('//Alice')
# destination account
kp_dst = Keypair.create_from_uri('//Charlie')
# An arbitrary amount to be transfered from source to destination
amount_to_be_transfered = 1

# a valid funds transfer transaction from src to dest with batch
# after transaction, dest will be credited twice as amount_to_be_transfered


def all_valid_extrinsics_bath():
    print('---Start of test: all_valid_extrinsics_bath()---')
    print()

    # check account balances before transactions
    bal_src_before = show_account(substrate,
                                  kp_src.ss58_address, "src bal before trans")
    bal_dst_before = show_account(substrate,
                                  kp_dst.ss58_address, "Dest bal before trans")
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    # a valid  transaciton
    payload_first = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered * TOKEN_NUM_BASE
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

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    # check account balances after transaciton
    bal_src_after = show_account(substrate,
                                 kp_src.ss58_address, "Src bal after trans")
    bal_dst_after = show_account(substrate,
                                 kp_dst.ss58_address, "Dest bal after trans")

    show_extrinsic(receipt, 'batch')
    # since same amount has been transfered two times
    assert (bal_dst_before+(amount_to_be_transfered * TOKEN_NUM_BASE) * 2
            == bal_dst_after)

    print('---End   of test: all_valid_extrinsics_bath()---')
    print()


def all_valid_extrinsics_bath_all():
    print('---Start of test: all_valid_extrinsics_bath_all()---')
    print()

    # check account balances before transactions
    bal_src_before = show_account(substrate,
                                  kp_src.ss58_address, "src bal before trans")
    bal_dst_before = show_account(substrate,
                                  kp_dst.ss58_address, "Dest bal before trans")
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    # a valid  transaciton
    payload_first = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered * TOKEN_NUM_BASE
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

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    # check account balances after transaciton
    bal_src_after = show_account(substrate,
                                 kp_src.ss58_address, "Src bal after trans")
    bal_dst_after = show_account(substrate,
                                 kp_dst.ss58_address, "Dest bal after trans")

    show_extrinsic(receipt, 'batch')
    # since same amount has been transfered two times
    assert (bal_dst_before+(amount_to_be_transfered * TOKEN_NUM_BASE) * 2
            == bal_dst_after)

    print('---End   of test: all_valid_extrinsics_bath_all()---')
    print()


def atleast_one_invalid_extrinsic_bath():
    print('---Start of test: atleast_one_invalid_extrinsic_bath()---')
    print()

    # check account balances before transactions
    bal_src_before = show_account(substrate,
                                  kp_src.ss58_address, "src bal before trans")
    bal_dst_before = show_account(substrate,
                                  kp_dst.ss58_address, "Dest bal before trans")
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    # a valid  transaciton
    payload_first = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered * TOKEN_NUM_BASE
        })

    # Second invalid transaciton
    payload_second = substrate.compose_call(
        call_module='Balances',
        call_function='force_transfer',
        call_params={
            'source': kp_src.ss58_address,
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered * TOKEN_NUM_BASE
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
    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    # check account balances after transaciton
    bal_src_after = show_account(substrate,
                                 kp_src.ss58_address, "Src bal after trans")
    bal_dst_after = show_account(substrate,
                                 kp_dst.ss58_address, "Dest bal after trans")

    show_extrinsic(receipt, 'batch')
    # since amount has been transfered only once
    assert (bal_dst_before+(amount_to_be_transfered * TOKEN_NUM_BASE)
            == bal_dst_after)

    print('---End   of test: atleast_one_invalid_extrinsics_bath()---')
    print()


def atleast_one_invalid_extrinsic_bath_all():
    print('---Start of test: atleast_one_invalid_extrinsics_bath_all()---')
    print()

    # check account balances before transactions
    bal_src_before = show_account(substrate,
                                  kp_src.ss58_address, "src bal before trans")
    bal_dst_before = show_account(substrate,
                                  kp_dst.ss58_address, "Dest bal before trans")
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    # a valid  transaciton
    payload_first = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered * TOKEN_NUM_BASE
        })

    # Second invalid transaciton
    payload_second = substrate.compose_call(
        call_module='Balances',
        call_function='force_transfer',
        call_params={
            'source': kp_src.ss58_address,
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered * TOKEN_NUM_BASE
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
    bal_src_after = show_account(substrate,
                                 kp_src.ss58_address, "Src bal after trans")
    bal_dst_after = show_account(substrate,
                                 kp_dst.ss58_address, "Dest bal after trans")

    show_extrinsic(receipt, 'batch')
    # since due to an invalid transation, all transactions will be reverted
    assert (bal_dst_before == bal_dst_after)

    print('---End of test: atleast_one_invalid_extrinsics_bath_all()---')
    print()


def pallet_utility_test():
    all_valid_extrinsics_bath()
    all_valid_extrinsics_bath_all()
    atleast_one_invalid_extrinsic_bath()
    atleast_one_invalid_extrinsic_bath_all()
