import sys
import traceback

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import RELAYCHAIN_WS_URL, PARACHAIN_WS_URL, ExtrinsicBatch, get_account_balance
from tools.utils import show_test, show_title, show_subtitle, wait_for_event
# from tools.utils import wait_for_n_blocks
from tools.currency import peaq, mpeaq, dot, bnc


# Technical constants
PEAQ_PARACHAIN_ID = 2000
BIFROST_PARACHAIN_ID = 3000
XCM_VER = 'V3'  # So far not tested with V2!
XCM_RTA_TO = 45  # timeout for xcm-rta
DOT_IDX = 576  # u8 value for DOT-token (CurrencyId/TokenSymbol)
BNC_IDX = 641  # u8 value for BNC-token (CurrencyId/TokenSymbol)
BIFROST_WS_URL = 'ws://127.0.0.1:10047'
# Test parameter configurations
BENEFICIARY = '//Dave'
DOT_LIQUIDITY = dot(20)
AMNT_DOT = dot(5)
BNC_LIQUIDITY = bnc(20)
AMNT_BNC = bnc(5)


def relay_amount_w_fees(x):
    return x + dot(2.5)


def bifrost_amount_w_fees(x):
    return x + bnc(1)


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


def compose_xtokens_transfer(batch, kp_beneficiary, amount):
    params = {
            'currency_id': { 'Native': 'BNC' },
            'amount': str(amount),
            'dest': { XCM_VER: {
                'parents': '1',
                'interior': { 'X2': [
                    {'Parachain': f'{PEAQ_PARACHAIN_ID}'},
                    {'AccountId32': (None, kp_beneficiary.public_key)}
                    ]}
                }},
            'dest_weight_limit': 'Unlimited',
        }
    batch.compose_call('XTokens', 'transfer', params)


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
    deadline = calc_deadline(batch.substrate)
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


def compose_bootstrap_create_call(batch, tok_idx):
    asset0, asset1 = compose_zdex_lppair_params(tok_idx)
    target0 = str(BNC_LIQUIDITY)
    target1 = str(BNC_LIQUIDITY)
    capacity0 = str(BNC_LIQUIDITY*100)  # no clue on this
    capacity1 = str(BNC_LIQUIDITY*100)  # no clue on this
    end = batch.substrate.get_block_number(None) + 2
    params = {
        'asset_0': asset0,
        'asset_1': asset1,
        'target_supply_0': target0,
        'target_supply_1': target1,
        'capacity_supply_0': capacity0,
        'capacity_supply_1': capacity1,
        'end': end,
        'rewards': [asset0],
        'limits': [],
    }
    batch.compose_sudo_call('ZenlinkProtocol', 'bootstrap_create', params)


def compose_bootstrap_contribute_call(batch, tok_idx, amount0, amount1):
    asset0, asset1 = compose_zdex_lppair_params(tok_idx)
    deadline = calc_deadline(batch.substrate)
    params = {
        'asset_0': asset0,
        'asset_1': asset1,
        'amount_0_contribute': str(amount0),
        'amount_1_contribute': str(amount1),
        'deadline': deadline,
    }
    batch.compose_call('ZenlinkProtocol', 'bootstrap_contribute', params)


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


def wait_n_check_token_deposit(substrate, kp_beneficiary, token):
    attributes = {
        'currency_id': {'Token': token},
        'who': kp_beneficiary.ss58_address
    }
    wait_n_check_event(substrate, 'Tokens', 'Deposited', attributes)


def wait_n_check_swap_event(substrate, min_tokens):
    event = wait_for_event(substrate, 'ZenlinkProtocol', 'AssetSwap', timeout=XCM_RTA_TO)
    assert not event is None
    assert event['attributes'][3][1] > min_tokens


def wait_check_bootstrap_created(substrate):
    event = wait_for_event(substrate, 'ZenlinkProtocol', '')


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
    
    data = si_peaq.rpc_request(
        'zenlinkProtocol_calculateRemoveLiquidity',
        [asset0, asset1, 10]
    )
    print(data['result'])

    show_test('zenlink_dex_rpc_test', True)


def currency_transfer_test(si_relay, si_peaq, si_bifrost):
    """
    This test is about transfering foreign currencies from relaychain
    and another parachain to our local parachain.
    """
    show_subtitle('currency_transfer_test')

    kp_beneficiary = Keypair.create_from_uri(BENEFICIARY)
    kp_peaq_sudo = Keypair.create_from_uri('//Alice')
    kp_sender = Keypair.create_from_uri('//Bob')  # Bob exists everywhere

    bat_relay = ExtrinsicBatch(si_relay, kp_sender)
    bat_bifrost = ExtrinsicBatch(si_bifrost, kp_sender)
    bat_peaq = ExtrinsicBatch(si_peaq, kp_sender)

    # Currently we cannot pay in foreign currencies, so we have to make
    # sure, that our recipient has enough tokens on his account...
    balance = state_system_account(si_peaq, kp_beneficiary)
    if balance < mpeaq(200):
        compose_balances_transfer(bat_peaq, kp_beneficiary, peaq(1))
        bat_peaq.execute_n_clear()
        balance = balance + peaq(1)
    assert state_system_account(si_peaq, kp_beneficiary) == balance

    # 1.) Transfer tokens from relaychain to peaq-parachain
    # Tokens to the sudo, to test if he can add liquidity
    compose_xcm_rta_relay2para(bat_relay, kp_peaq_sudo,
                               relay_amount_w_fees(DOT_LIQUIDITY))
    # Tokens to the user, to test if he can swap them
    compose_xcm_rta_relay2para(bat_relay, kp_beneficiary,
                               relay_amount_w_fees(AMNT_DOT))
    bat_relay.execute_n_clear()
    wait_n_check_token_deposit(si_peaq, kp_beneficiary, 'DOT')

    # 2.) Transfer tokens from bifrost-parachain to peaq-parachain
    # Tokens to the sudo, to test if he can add liquidity
    compose_xtokens_transfer(bat_bifrost, kp_peaq_sudo,
                             bifrost_amount_w_fees(BNC_LIQUIDITY))
    # Tokens to the user, to test if he can swap them
    compose_xtokens_transfer(bat_bifrost, kp_beneficiary,
                             bifrost_amount_w_fees(AMNT_BNC))
    bat_bifrost.execute_n_clear()
    wait_n_check_token_deposit(si_peaq, kp_beneficiary, 'BNC')

    show_test('currency_transfer_test', True)


def create_pair_n_swap_test(si_peaq):
    """
    This test is about creating directly a liquidity-pair with the
    Zenlink-DEX-Protocol and using its swap-function (no bootstrap).
    """
    show_subtitle('create_pair_n_swap_test')

    kp_beneficiary = Keypair.create_from_uri(BENEFICIARY)
    kp_para_sudo = Keypair.create_from_uri('//Alice')
    
    bat_para_sudo = ExtrinsicBatch(si_peaq, kp_para_sudo)
    bat_para_bene = ExtrinsicBatch(si_peaq, kp_beneficiary)

    # Check that DOT tokens for liquidity have been transfered succesfully
    dot_liquidity = state_tokens_accounts(si_peaq, kp_para_sudo, 'DOT')
    assert dot_liquidity > DOT_LIQUIDITY
    # Check that beneficiary has DOT and PEAQ tokens available
    dot_balance = state_tokens_accounts(si_peaq, kp_beneficiary, 'DOT')
    assert dot_balance > AMNT_DOT
    peaq_balance = get_account_balance(si_peaq, kp_beneficiary.ss58_address)
    assert peaq_balance > mpeaq(100)

    # 1.) Create a liquidity pair and add liquidity on pallet Zenlink-Protocol
    compose_zdex_create_lppair(bat_para_sudo, DOT_IDX)
    compose_zdex_add_liquidity(bat_para_sudo, DOT_IDX, dot_liquidity)
    bat_para_sudo.execute_n_clear()

    # Check that liquidity pool is filled with DOT-tokens
    lpstatus = state_znlnkprot_lppair_status(si_peaq, DOT_IDX)
    assert lpstatus['total_supply'] >= DOT_LIQUIDITY
    
    # 2.) Swap liquidity pair on Zenlink-DEX
    compose_zdex_swap_lppair(bat_para_bene, kp_beneficiary, DOT_IDX, dot_balance)
    bat_para_bene.execute_n_clear()
    wait_n_check_swap_event(si_peaq, int(AMNT_DOT*0.4))
    
    show_test('create_pair_n_swap_test', True)


def bootstrap_pair_n_swap_test(si_peaq):
    """
    This test as about the Zenlink-DEX-Protocol bootstrap functionality.
    """
    show_subtitle('bootstrap_pair_n_swap_test')

    kp_sudo = Keypair.create_from_uri('//Alice')
    kp_user = Keypair.create_from_uri('//Bob')

    bat_peaq_sudo = ExtrinsicBatch(si_peaq, kp_sudo)
    bat_peaq_user = ExtrinsicBatch(si_peaq, kp_user)

    # 1.) Create bootstrap-liquidity-pair and contribute to
    compose_bootstrap_create_call(bat_peaq_sudo, BNC_IDX)
    compose_bootstrap_contribute_call(bat_peaq_sudo, BNC_IDX, 5*pow(10, 22), 0)
    bat_peaq_sudo.execute_n_clear()

    # Check that pool has been created when goal is reached

    # 2.) User swaps tokens by using the created pool

    show_test('bootstrap_pair_n_swap_test', True)


def zenlink_dex_test():
    show_title('Zenlink-DEX-Protocol Test')
    try:
        with SubstrateInterface(url=RELAYCHAIN_WS_URL) as si_relay:
            with SubstrateInterface(url=PARACHAIN_WS_URL) as si_peaq:
                with SubstrateInterface(url=BIFROST_WS_URL) as si_bifrost:
                    # Order of tests is important (they're structured)
                    currency_transfer_test(si_relay, si_peaq, si_bifrost)
                    # create_pair_n_swap_test(si_peaq)
                    # bootstrap_pair_n_swap_test(si_peaq)
                    # zenlink_dex_rpc_test(si_peaq)

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

