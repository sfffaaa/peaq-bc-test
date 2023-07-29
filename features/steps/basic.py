import sys
sys.path.append('./')

from behave import given, when, then
from substrateinterface import Keypair
from tools.utils import calculate_multi_sig, TOKEN_NUM_BASE
from tools.utils import transfer
import random
from tools.utils import show_account
from tools.utils import send_proposal, send_approval, get_as_multi_extrinsic_id
from tools.block_creation_utils import get_block_creation_times

THRESHOLD = 2
BLOCK_TRAVERSE = 20
BLOCK_CREATION_MS = 12000
BLOCK_TOLERATE_PERCENTAGE = 10


@given('Use the Alice keypair')
def get_alice_keypair(context):
    context._sender = Keypair.create_from_uri('//Alice')


@given('Use the Bob keypair')
def get_bob_keypair(context):
    context._receiver = Keypair.create_from_uri('//Bob')


@given('Create a multisig wallet from Alice and Bob')
def create_multisig_wallet(context):
    signators = [context._sender, context._receiver]
    context._multi_sig_addr = calculate_multi_sig(signators, THRESHOLD)


@given('Deposit random token to multisig wallet from Alice')
def deposit_random_multisit_wallet(context):
    context._num = random.randint(1, 10000)
    transfer(context._substrate, context._sender, context._multi_sig_addr, context._num)


@given('Store the bob balance')
def store_bob_balance(context):
    context._receiver_balance = show_account(
        context._substrate,
        context._multi_sig_addr,
        'before transfer')


@given('Send the transfer proposal to Bob from Alice')
def send_transfer_proposal(context):
    payload = context._substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': context._receiver.ss58_address,
            'value': context._num * TOKEN_NUM_BASE
        })

    receipt = send_proposal(
        context._substrate, context._sender, context._receiver, THRESHOLD, payload)
    timepoint = get_as_multi_extrinsic_id(receipt)

    context._proposal_info = {
        'timepoint': timepoint,
        'payload': payload,
    }


@when('Approve the transfer proposal by Bob')
def approve_transfer_proposal(context):
    send_approval(
        context._substrate,
        context._receiver, [context._sender],
        THRESHOLD,
        context._proposal_info['payload'],
        context._proposal_info['timepoint']
    )


@then('Check the token back to Bob')
def check_token_back_to_bob(context):
    post_multisig_token = show_account(
        context._substrate,
        context._multi_sig_addr, 'after transfer')
    assert(post_multisig_token + context._num * TOKEN_NUM_BASE == context._receiver_balance)


@when('Get all block creation time')
def get_block_creation_time(context):
    context._ave_time = get_block_creation_times(context._substrate, BLOCK_TRAVERSE)


@then('Check block create time')
def check_block_creation_time(context):
    ave_time = context._ave_time
    if abs(context._ave_time - BLOCK_CREATION_MS) / float(BLOCK_CREATION_MS) * 100. > BLOCK_TOLERATE_PERCENTAGE:
        print(f'The average block time {ave_time} is longer than the tolerate rate {BLOCK_TOLERATE_PERCENTAGE} * {BLOCK_CREATION_MS}')
        assert(f'Check the average block creation time {ave_time}')
    print(f'The block creation time {ave_time} (ms) is okay')
