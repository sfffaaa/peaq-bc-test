import sys
sys.path.append('./')

from behave import given, when, then
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import calculate_multi_sig, TOKEN_NUM_BASE
from tools.utils import transfer
import random
from tools.two_address_substrate_with_extrinsic import show_account, send_proposal, send_approval

WS_URL = 'ws://127.0.0.1:9944'
THRESHOLD = 2


@given('Connect to peaq network')
def connect_to_peaq_network(context):
    context._substrate = SubstrateInterface(url=WS_URL,)


@given('Use the Alice keypair')
def get_alice_keypair(context):
    context._alice = Keypair.create_from_uri('//Alice')


@given('Use the Bob keypair')
def get_bob_keypair(context):
    context._bob = Keypair.create_from_uri('//Bob')


@given('Create a multisig wallet from Alice and Bob')
def create_multisig_wallet(context):
    signators = [context._alice, context._bob]
    context._multi_sig_addr = calculate_multi_sig(signators, THRESHOLD)


@given('Deposit random token to multisig wallet from Alice')
def deposit_random_multisit_wallet(context):
    context._num = random.randint(1, 10000)
    transfer(context._substrate, context._alice, context._multi_sig_addr, context._num)


@given('Store the bob balance')
def store_bob_balance(context):
    context._bob_balance = show_account(
        context._substrate,
        context._multi_sig_addr,
        'before transfer')


@given('Send the transfer proposal to Bob from Alice')
def send_transfer_proposal(context):
    payload = context._substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': context._bob.ss58_address,
            'value': context._num * TOKEN_NUM_BASE
        })

    timepoint = send_proposal(
        context._substrate, context._alice, context._bob, THRESHOLD, payload)

    context._proposal_info = {
        'timepoint': timepoint,
        'payload': payload,
    }


@when('Approve the transfer proposal by Bob')
def approve_transfer_proposal(context):
    send_approval(
        context._substrate,
        context._bob, [context._alice],
        THRESHOLD,
        context._proposal_info['payload'],
        context._proposal_info['timepoint']
    )


@then('Check the token back to Bob')
def check_token_back_to_bob(context):
    post_multisig_token = show_account(
        context._substrate,
        context._multi_sig_addr, 'after transfer')
    assert(post_multisig_token + context._num * TOKEN_NUM_BASE == context._bob_balance)
