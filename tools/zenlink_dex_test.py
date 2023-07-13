import sys
import traceback

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import RELAYCHAIN_WS_URL, PARACHAIN_WS_URL, ExtrinsicBatch
from tools.utils import show_test, show_title, wait_for_event
# from tools.utils import wait_for_n_blocks
from tools.currency import peaq, mpeaq, dot


PEAQ_PARACHAIN_ID = 2000
BIFROST_PARACHAIN_ID = 3000
XCM_VER = 'V3'  # So far not tested with V2!
XCM_RTA_TO = 45  # timeout for xcm-rta
DOT_IDX = 576  # u8 value for DOT-token (CurrencyId/TokenSymbol)
BIFROST_WS_URL = 'ws://127.0.0.1:10047'

def relay_amount_w_fees(x):
    return x + dot(2.5)


def compose_zdex_lppair_params(tok_idx, w_str=True):
    if w_str:
        chain_id = str(PEAQ_PARACHAIN_ID)
        zero = '0'
        two = '2'
        asset_idx = str(tok_idx)
    else:
        chain_id = PEAQ_PARACHAIN_ID
        zero = 0
        two = 2
        asset_idx = tok_idx
    asset0 = {
            'chain_id': chain_id,
            'asset_type': zero,
            'asset_index': zero,
        }
    asset1 = {
            'chain_id': chain_id,
            'asset_type': two,
            'asset_index': asset_idx,
        }
    return asset0, asset1


def calc_deadline(substrate):
    return substrate.get_block_number(None) + 10


def compose_balances_transfer(batch, kp_beneficiary, amount):
    params = {
            'dest': kp_beneficiary.ss58_address,
            'value': str(amount),
        }
    batch.compose_call('Balances', 'transfer', params)


# Composes a XCM Reserve-Transfer-Asset call to transfer DOT-tokens
# from relaychain to parachain
def compose_xcm_rta_relay2para(batch, kp_beneficiary, amount):
    dest = { XCM_VER: {
            'parents': '0',
            'interior': { 'X1': { 'Parachain': f'{PEAQ_PARACHAIN_ID}' }}
        }}
    beneficiary = { XCM_VER: {
            'parents': '0',
            'interior': { 'X1': { 'AccountId32': (None, kp_beneficiary.public_key) }}
        }}
    assets = { XCM_VER: [[{
            'id': { 'Concrete': { 'parents': '0', 'interior': 'Here' }},
            'fun': { 'Fungible': f'{amount}' }
            }]]}
    params = {
            'dest': dest,
            'beneficiary': beneficiary,
            'assets': assets,
            'fee_asset_item': '0'
        }
    batch.compose_call('XcmPallet', 'reserve_transfer_assets', params)


def compose_zdex_create_lppair(batch, tok_idx):
    asset0, asset1 = compose_zdex_lppair_params(tok_idx)
    params = {
            'asset_0': asset0,
            'asset_1': asset1,
        }
    batch.compose_sudo_call('ZenlinkProtocol', 'create_pair', params)


def compose_zdex_add_liquidity(batch, tok_idx, liquidity):
    asset0, asset1 = compose_zdex_lppair_params(tok_idx)
    deadline = calc_deadline(batch.substrate)
    params = {
            'asset_0': asset0,
            'asset_1': asset1,
            'amount_0_desired': str(liquidity),
            'amount_1_desired': str(liquidity),
            'amount_0_min': '0',
            'amount_1_min': '0',
            'deadline': str(deadline),
        }
    batch.compose_call('ZenlinkProtocol', 'add_liquidity', params)


def compose_zdex_swap_lppair(batch, kp_beneficiary, tok_idx, amount):
    asset0, asset1 = compose_zdex_lppair_params(tok_idx)
    deadline = calc_deadline(batch.substrate)
    params = {
            'amount_in': str(amount),
            'amount_out_min': '0',
            'path': [asset1, asset0],
            'recipient': kp_beneficiary.ss58_address,
            'deadline': deadline,
        }
    batch.compose_call('ZenlinkProtocol', 'swap_exact_assets_for_assets', params)


def compose_zdex_remove_liquidity(batch, kp_beneficiary, tok_idx, amount):
    asset0, asset1 = compose_zdex_lppair_params(tok_idx)
    deadline = calc_deadline(si_peaq)
    params = {
            'asset_0': asset0,
            'asset_1': asset1,
            'liquidity': str(amount),
            'amount_0_min': '0',
            'amount_1_min': '1',
            'recipient': kp_beneficiary.ss58_address,
            'deadline': deadline,
        }
    batch.compose_call('ZenlinkProtocol', 'remove_liquidity', params)


def state_system_account(si_peaq, kp_user):
    query = si_peaq.query('System', 'Account', [kp_user.ss58_address])
    return int(query['data']['free'].value)


def state_tokens_accounts(si_peaq, kp_user, token):
    params = [kp_user.ss58_address, {'Token': token}]
    query = si_peaq.query('Tokens', 'Accounts', params)
    return int(query['free'].value)


def state_znlnkprot_lppair_assetidx(si_peaq, tok_idx):
    asset0, asset1 = compose_zdex_lppair_params(tok_idx)
    query = si_peaq.query('ZenlinkProtocol', 'LiquidityPairs', [[asset0, asset1]])
    if query.value is None:
        return 0
    else:
        return int(query['asset_index'].value)


def state_znlnkprot_lppair_status(si_peaq, tok_idx):
    asset0, asset1 = compose_zdex_lppair_params(tok_idx)
    query = si_peaq.query('ZenlinkProtocol', 'PairStatuses', [[asset0, asset1]])
    if isinstance(query.value, dict):
        return query.value['Trading']
    else:
        return query.value


def wait_n_check_event(substrate, module, event, attributes=None):
    event = wait_for_event(substrate, module, event,
                           attributes=attributes,
                           timeout=XCM_RTA_TO)
    assert not event is None


def wait_n_check_rta_event(substrate, kp_beneficiary):
    attributes = {
        'currency_id': {'Token': 'DOT'},
        'who': kp_beneficiary.ss58_address
    }
    wait_n_check_event(substrate, 'Tokens', 'Deposited', attributes)


def wait_n_check_swap_event(substrate, min_tokens):
    event = wait_for_event(substrate, 'ZenlinkProtocol', 'AssetSwap', timeout=XCM_RTA_TO)
    assert not event is None
    assert event['attributes'][3][1] > min_tokens


def relaychain2parachain_test(si_relay, si_peaq):
    """
    This test is about transfering tokens from the relaychain to our parachain
    and to swap the transfered tokens in our local token by using the
    Zenlink-DEX-Protocol and its regular swap-function (not bootstrap).
    """
    kp_sender = Keypair.create_from_uri('//Alice')
    kp_beneficiary = Keypair.create_from_uri('//Dave')
    kp_para_sudo = Keypair.create_from_uri('//Alice')
    amnt_liquidity = dot(20)
    amnt_peaq = peaq(1)
    amnt_dot = dot(1)
    
    bat_relay_sudo = ExtrinsicBatch(si_relay, kp_sender)
    bat_para_sudo = ExtrinsicBatch(si_peaq, kp_para_sudo)
    bat_para_bene = ExtrinsicBatch(si_peaq, kp_beneficiary)

    # In advance: Create a liquidity pair with pallet Zenlink-Protocol
    if not state_znlnkprot_lppair_assetidx(si_peaq, DOT_IDX):
        compose_zdex_create_lppair(bat_para_sudo, DOT_IDX)

    # Beneficiary needs local tokens on his account to be able to add, swap and remove liquidity
    balance = state_system_account(si_peaq, kp_beneficiary)
    if balance < mpeaq(200):
        compose_balances_transfer(bat_para_sudo, kp_beneficiary, amnt_peaq)
        balance = balance + amnt_peaq

    bat_para_sudo.execute_n_clear()
    assert state_system_account(si_peaq, kp_beneficiary) == balance

    # In advance: Add liquidity to token pair on Zenlink-DEX
    lpstatus = state_znlnkprot_lppair_status(si_peaq, DOT_IDX)
    addliquidity = not lpstatus['total_supply'] >= amnt_liquidity
    if addliquidity:
        request = relay_amount_w_fees(amnt_liquidity)
        compose_xcm_rta_relay2para(bat_relay_sudo, kp_para_sudo, request)

    # Transfer tokens from relaychain to parachain
    request = relay_amount_w_fees(amnt_dot)
    compose_xcm_rta_relay2para(bat_relay_sudo, kp_beneficiary, request)
    bat_relay_sudo.execute_n_clear()
    wait_n_check_rta_event(si_peaq, kp_beneficiary)
    if addliquidity:
        # event = wait_for_event(si_peaq, 'Tokens', 'Deposited', timeout=XCM_RTA_TO
        #                        attributes={'currency_id': {'Token': 'DOT'}, })
        # assert not event is None
        # dot_balance = state_tokens_accounts(si_peaq, kp_para_sudo, 'DOT')
        # assert dot_balance > amnt_liquidity
        compose_zdex_add_liquidity(bat_para_sudo, DOT_IDX, amnt_liquidity)
        bat_para_sudo.execute_n_clear()
    # Check that liquidity pool is filled with DOT-tokens
    lpstatus = state_znlnkprot_lppair_status(si_peaq, DOT_IDX)
    assert lpstatus['total_supply'] >= amnt_liquidity
    
    # assert not wait_for_event(si_peaq, 'Tokens', 'Deposited', XCM_RTA_TO) is None
    # wait_for_n_blocks(si_peaq, 2)
    dot_balance = state_tokens_accounts(si_peaq, kp_beneficiary, 'DOT')
    assert dot_balance >= amnt_dot

    # Swap liquidity pair on Zenlink-DEX
    compose_zdex_swap_lppair(bat_para_bene, kp_beneficiary, DOT_IDX, amnt_dot)
    bat_para_bene.execute_n_clear()
    wait_n_check_swap_event(si_peaq, 0)
    
    show_test('relaychain2parachain_test', True)


def zenlink_dex_rpc_test(si_peaq):
    """
    This test is checking some of the RPC functions of the
    Zenlink-DEX-Protocol pallet.
    """
    asset0, asset1 = compose_zdex_lppair_params(DOT_IDX, False)
    data = si_peaq.rpc_request(
        'zenlinkProtocol_getPairByAssetId',
        [asset0, asset1]
    )
    assert not data['result'] is None

    kp_beneficiary = Keypair.create_from_uri('//Dave')
    data = si_peaq.rpc_request(
        'zenlinkProtocol_getBalance',
        [asset0, kp_beneficiary.ss58_address]
    )
    assert int(data['result'][2:], 16) > 0

    show_test('zenlink_dex_rpc_test', True)


def parachain2parachain_test(si_peaq, si_bifrost):
    """
    This test is about parachain-to-parachain-transfer using the
    Zenlink-DEX-Protocol. TODO
    """
    pass


def zenlink_dex_test():
    show_title('Zenlink-DEX-Protocol Test')
    try:
        with SubstrateInterface(url=RELAYCHAIN_WS_URL) as si_relay:
            with SubstrateInterface(url=PARACHAIN_WS_URL) as si_peaq:
                with SubstrateInterface(url=BIFROST_WS_URL) as si_bifrost:
                    relaychain2parachain_test(si_relay, si_peaq)
                    zenlink_dex_rpc_test(si_peaq)
                    parachain2parachain_test(si_peaq, si_bifrost)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, \
            try running 'start_local_substrate_node.sh' first")
        sys.exit()

    except AssertionError:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        print(tb_info)
        _, line, func = tb_info[1]
        show_test(func, False, line)
        # print(f'🔥 Test/{func} in line {line}, Failed')

