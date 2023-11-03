import sys
import traceback
import unittest
import pytest

sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import RELAYCHAIN_WS_URL, PARACHAIN_WS_URL, BIFROST_WS_URL, KP_GLOBAL_SUDO, URI_GLOBAL_SUDO
from tools.utils import show_test, show_title, show_subtitle, wait_for_event, get_account_balance
from tools.utils import PEAQ_PD_CHAIN_ID
from tools.utils import ExtrinsicBatch, into_keypair
from tools.currency import peaq, dot, bnc
from tests.utils_func import restart_parachain_and_runtime_upgrade
from tools.runtime_upgrade import wait_until_block_height
from tests import utils_func as TestUtils


# Technical constants
XCM_VER = 'V3'  # So far not tested with V2!
XCM_RTA_TO = 45  # timeout for xcm-rta
DOT_IDX = 64  # u8 value for DOT-token (CurrencyId/TokenSymbol)
BNC_IDX = 129  # u8 value for BNC-token (CurrencyId/TokenSymbol)
# Test parameter configurations
TOK_LIQUIDITY = 50  # generic amount of tokens
TOK_SWAP = 1  # generic amount of tokens


def relay_amount_w_fees(x):
    return x + dot(2.5)


def bifrost_amount_w_fees(x):
    return x + bnc(1)


def compose_zdex_lppair_params(tok_idx, w_str=True):
    if w_str:
        chain_id = str(PEAQ_PD_CHAIN_ID)
        zero = '0'
        two = '2'
        asset_idx = str(tok_idx)
    else:
        chain_id = PEAQ_PD_CHAIN_ID
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


def compose_balances_setbalance(batch, who, amount):
    kp_who = into_keypair(who)
    params = {
        'who': kp_who.ss58_address,
        'new_free': str(amount),
        'new_reserved': '0',
    }
    batch.compose_sudo_call('Balances', 'force_set_balance', params)


# Composes a XCM Reserve-Transfer-Asset call to transfer DOT-tokens
# from relaychain to parachain
def compose_xcm_rta_relay2para(batch, kp_beneficiary, amount):
    dest = {XCM_VER: {
        'parents': '0',
        'interior': {'X1': {'Parachain': f'{PEAQ_PD_CHAIN_ID}'}}
    }}
    beneficiary = {XCM_VER: {
        'parents': '0',
        'interior': {'X1': {'AccountId32': (None, kp_beneficiary.public_key)}}
    }}
    assets = {XCM_VER: [[{
        'id': {'Concrete': {'parents': '0', 'interior': 'Here'}},
        'fun': {'Fungible': f'{amount}'}
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
        'currency_id': {'Native': 'BNC'},
        'amount': str(amount),
        'dest': {XCM_VER: {
            'parents': '1',
            'interior': {'X2': [
                {'Parachain': f'{PEAQ_PD_CHAIN_ID}'},
                {'AccountId32': (None, kp_beneficiary.public_key)}
                ]}
            }},
        'dest_weight_limit': 'Unlimited',
    }
    batch.compose_call('XTokens', 'transfer', params)


def compose_zdex_create_lppair(batch, tok_idx):
    asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
    params = {
        'asset_0': asset_0,
        'asset_1': asset_1,
    }
    batch.compose_sudo_call('ZenlinkProtocol', 'create_pair', params)


def compose_zdex_add_liquidity(batch, tok_idx, liquidity0, liquidity1):
    asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
    deadline = calc_deadline(batch.substrate)
    params = {
        'asset_0': asset_0,
        'asset_1': asset_1,
        'amount_0_desired': str(liquidity0),
        'amount_1_desired': str(liquidity1),
        'amount_0_min': '0',
        'amount_1_min': '0',
        'deadline': str(deadline),
    }
    batch.compose_call('ZenlinkProtocol', 'add_liquidity', params)


def compose_zdex_swap_exact_for(batch, tok_idx, amount_in0=None, amount_in1=None):
    if amount_in1 is None and amount_in0 is not None:
        asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
        amount = amount_in0
    elif amount_in0 is None and amount_in1 is not None:
        asset_1, asset_0 = compose_zdex_lppair_params(tok_idx)
        amount = amount_in1
    else:
        raise AttributeError
    deadline = calc_deadline(batch.substrate)
    params = {
        'amount_in': str(amount),
        'amount_out_min': '0',
        'path': [asset_0, asset_1],
        'recipient': batch.keypair.ss58_address,
        'deadline': deadline,
    }
    batch.compose_call('ZenlinkProtocol', 'swap_exact_assets_for_assets', params)


def compose_zdex_swap_for_exact(batch, tok_idx, amount_out0=None, amount_out1=None,
                                amnt_in_max=100e18):
    if amount_out0 is None and amount_out1 is not None:
        asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
        amount = amount_out1
    elif amount_out1 is None and amount_out0 is not None:
        asset_1, asset_0 = compose_zdex_lppair_params(tok_idx)
        amount = amount_out0
    else:
        raise AttributeError
    deadline = calc_deadline(batch.substrate)
    params = {
        'amount_out': str(amount),
        'amount_in_max': str(amnt_in_max),
        'path': [asset_0, asset_1],
        'recipient': batch.keypair.ss58_address,
        'deadline': deadline,
    }
    batch.compose_call('ZenlinkProtocol', 'swap_assets_for_exact_assets', params)


def compose_zdex_remove_liquidity(batch, tok_idx, amount):
    asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
    deadline = calc_deadline(batch.substrate)
    params = {
        'asset_0': asset_0,
        'asset_1': asset_1,
        'liquidity': str(amount),
        'amount_0_min': '1',
        'amount_1_min': '1',
        'recipient': batch.keypair.ss58_address,
        'deadline': deadline,
    }
    batch.compose_call('ZenlinkProtocol', 'remove_liquidity', params)


def compose_bootstrap_create_call(batch, tok_idx, target0, target1, limit0, limit1):
    asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
    target_0 = str(target0)
    target_1 = str(target1)
    capacity_0 = str(target0*100)
    capacity_1 = str(target1*100)
    end = batch.substrate.get_block_number(None) + 500
    params = {
        'asset_0': asset_0,
        'asset_1': asset_1,
        'target_supply_0': target_0,
        'target_supply_1': target_1,
        'capacity_supply_0': capacity_0,
        'capacity_supply_1': capacity_1,
        'end': end,
        'rewards': [asset_0],
        'limits': [(asset_0, limit0), (asset_1, limit1)],
    }
    batch.compose_sudo_call('ZenlinkProtocol', 'bootstrap_create', params)


def compose_bootstrap_contribute_call(batch, tok_idx, amount0, amount1):
    assert amount0 == 0 or amount1 == 0
    asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
    deadline = calc_deadline(batch.substrate)
    params = {
        'asset_0': asset_0,
        'asset_1': asset_1,
        'amount_0_contribute': str(amount0),
        'amount_1_contribute': str(amount1),
        'deadline': deadline,
    }
    batch.compose_call('ZenlinkProtocol', 'bootstrap_contribute', params)


def compose_bootstrap_end_call(batch, tok_idx):
    asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
    params = {
        'asset_0': asset_0,
        'asset_1': asset_1,
    }
    batch.compose_call('ZenlinkProtocol', 'bootstrap_end', params)


def compose_call_bootstrap_update_end(batch, tok_idx):
    si = batch.substrate
    asset_0, asset_1 = compose_zdex_lppair_params(tok_idx)
    lpstatus = state_znlnkprot_lppair_status(si, tok_idx)
    target_0 = lpstatus['target_supply'][0]
    target_1 = lpstatus['target_supply'][1]
    capacity_0 = lpstatus['capacity_supply'][0]
    capacity_1 = lpstatus['capacity_supply'][1]
    query = si.query('ZenlinkProtocol', 'BootstrapLimits', [[asset_0, asset_1]])
    limit_0 = str(query[0][1])
    limit_1 = str(query[1][1])
    params = {
        'asset_0': asset_0,
        'asset_1': asset_1,
        'target_supply_0': target_0,
        'target_supply_1': target_1,
        'capacity_supply_0': capacity_0,
        'capacity_supply_1': capacity_1,
        'end': str(si.get_block_number(None)),
        'rewards': [asset_0],
        'limits': [(asset_0, limit_0), (asset_1, limit_1)],
    }
    batch.compose_sudo_call('ZenlinkProtocol', 'bootstrap_update', params)


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
        if 'Trading' in query.value.keys():
            return query.value['Trading']
        elif 'Bootstrap' in query.value.keys():
            return query.value['Bootstrap']
        else:
            raise KeyError
    else:
        return query.value


def wait_n_check_event(substrate, module, event, attributes=None):
    event = wait_for_event(substrate, module, event,
                           attributes=attributes,
                           timeout=XCM_RTA_TO)
    assert event is not None


def wait_n_check_token_deposit(substrate, kp_beneficiary, token):
    attributes = {
        'currency_id': {'Token': token},
        'who': kp_beneficiary.ss58_address
    }
    wait_n_check_event(substrate, 'Tokens', 'Deposited', attributes)


def wait_n_check_swap_event(substrate, min_tokens):
    event = wait_for_event(substrate, 'ZenlinkProtocol', 'AssetSwap', timeout=XCM_RTA_TO)
    assert event is not None
    assert event['attributes'][3][1] > min_tokens


def relay2para_transfer(si_relay, si_peaq, sender, tos, amnts):
    """
    This is a commong test-setup function to provide liquidity transactions from
    relaychain to parachain. Specify the sender as uri (e.g. '//Alice') and one
    or multiple recipients as array (e.g. ['//Dave', '//Eve'].
    """
    assert len(tos) == len(amnts)

    kp_recipi = list()
    for to in tos:
        kp_recipi.append(into_keypair(to))

    bt_sender = ExtrinsicBatch(si_relay, sender)
    for i, recipi in enumerate(kp_recipi):
        compose_xcm_rta_relay2para(bt_sender, recipi, amnts[i])
    bt_sender.execute()
    wait_n_check_token_deposit(si_peaq, kp_recipi[-1], 'DOT')


def bifrost2para_transfer(si_bifrost, si_peaq, sender, tos, amnts):
    """
    This is a commong test-setup function to provide liquidity transactions from
    parachain to parachain. Specify the sender as uri (e.g. '//Alice') and one
    or multiple recipients as array (e.g. ['//Dave', '//Eve'].
    """
    assert len(tos) == len(amnts)

    kp_recipi = list()
    for to in tos:
        kp_recipi.append(Keypair.create_from_uri(to))

    bt_sender = ExtrinsicBatch(si_bifrost, sender)
    for i, recipi in enumerate(kp_recipi):
        compose_xtokens_transfer(bt_sender, recipi, amnts[i])
    bt_sender.execute_n_clear()
    wait_n_check_token_deposit(si_peaq, kp_recipi[-1], 'BNC')


def create_pair_n_swap_test(si_relay, si_peaq):
    """
    This test is about creating directly a liquidity-pair with the
    Zenlink-DEX-Protocol and using its swap-function (no bootstrap).
    This test also tests some of Zenlink-Protocol RPC methods.
    """
    show_subtitle('create_pair_n_swap_test')

    user1 = '//Dave'
    user2 = '//Bob'

    kp_para_sudo = into_keypair(KP_GLOBAL_SUDO)
    kp_beneficiary = into_keypair(user1)
    kp_para_bob = into_keypair(user2)

    bt_para_sudo = ExtrinsicBatch(si_peaq, kp_para_sudo)
    bt_para_bob = ExtrinsicBatch(si_peaq, kp_para_bob)
    bt_para_bene = ExtrinsicBatch(si_peaq, kp_beneficiary)

    # Transfer tokens from relaychain to parachain
    amount = relay_amount_w_fees(dot(TOK_LIQUIDITY))
    relay2para_transfer(si_relay, si_peaq, '//Alice', ['//Alice', '//Dave'], [amount, amount])

    # Check that DOT tokens for liquidity have been transfered succesfully
    dot_liquidity = state_tokens_accounts(si_peaq, kp_para_sudo, 'DOT')
    assert dot_liquidity >= dot(TOK_LIQUIDITY)
    # Check that beneficiary has DOT and PEAQ tokens available
    dot_balance = state_tokens_accounts(si_peaq, kp_beneficiary, 'DOT')
    assert dot_balance > dot(TOK_SWAP)

    # 1.) Create a liquidity pair and add liquidity on pallet Zenlink-Protocol
    compose_zdex_create_lppair(bt_para_sudo, DOT_IDX)
    # Check different amounts of liquidity!!!
    compose_zdex_add_liquidity(bt_para_sudo, DOT_IDX, dot_liquidity, dot_liquidity)
    # Reset user1's account to very low amount, to test payment in local currency
    compose_balances_setbalance(bt_para_sudo, user1, 1000)
    bt_para_sudo.execute_n_clear()

    # Check that liquidity pool is filled with DOT-tokens
    lpstatus = state_znlnkprot_lppair_status(si_peaq, DOT_IDX)
    assert lpstatus['total_supply'] >= dot(TOK_LIQUIDITY)

    # Check that RPC functionality is working on this created lp-pair.
    asset0, asset1 = compose_zdex_lppair_params(DOT_IDX, False)
    bl_hsh = substrate.get_block_hash(None)
    data = si_peaq.rpc_request(
        'zenlinkProtocol_getPairByAssetId',
        [asset0, asset1, bl_hsh])
    assert not data['result'] is None

    # 2.) Swap liquidity pair on Zenlink-DEX
    compose_zdex_swap_exact_for(bt_para_bene, DOT_IDX, amount_in1=dot(TOK_SWAP))
    bt_para_bene.execute_n_clear()
    wait_n_check_swap_event(si_peaq, dot(TOK_SWAP))

    compose_zdex_swap_exact_for(bt_para_bob, DOT_IDX, amount_in0=peaq(TOK_SWAP))
    bt_para_bob.execute_n_clear()
    wait_n_check_swap_event(si_peaq, dot(TOK_SWAP))

    # 3.) Remove some liquidity
    compose_zdex_remove_liquidity(bt_para_sudo, DOT_IDX, int(dot_liquidity / 4))
    bt_para_sudo.execute_n_clear()

    show_test('create_pair_n_swap_test', True)


def bootstrap_pair_n_swap_test(si_bifrost, si_peaq):
    """
    This test as about the Zenlink-DEX-Protocol bootstrap functionality.
    """
    show_subtitle('bootstrap_pair_n_swap_test')

    tok_limit = 5
    assert TOK_LIQUIDITY / 2 > tok_limit

    cont = '//Bob'
    user = '//Dave'

    kp_sudo = into_keypair(KP_GLOBAL_SUDO)
    kp_cont = into_keypair(cont)
    kp_user = into_keypair(user)

    bt_peaq_sudo = ExtrinsicBatch(si_peaq, kp_sudo)
    bt_peaq_cont = ExtrinsicBatch(si_peaq, kp_cont)
    bt_peaq_user = ExtrinsicBatch(si_peaq, kp_user)

    # Transfer tokens from relaychain to parachain
    amount = bifrost_amount_w_fees(bnc(TOK_LIQUIDITY)) // 2
    bifrost2para_transfer(
        si_bifrost, si_peaq, URI_GLOBAL_SUDO,
        [URI_GLOBAL_SUDO, cont, user], [amount, amount, bifrost_amount_w_fees(bnc(TOK_SWAP))])

    # 1.) Create bootstrap-liquidity-pair & start contributing
    compose_bootstrap_create_call(bt_peaq_sudo, BNC_IDX,
                                  peaq(TOK_LIQUIDITY), bnc(TOK_LIQUIDITY),
                                  peaq(tok_limit), bnc(tok_limit))
    compose_bootstrap_contribute_call(bt_peaq_sudo, BNC_IDX,
                                      peaq(TOK_LIQUIDITY/2), 0)
    compose_bootstrap_contribute_call(bt_peaq_sudo, BNC_IDX,
                                      0, bnc(TOK_LIQUIDITY/2))
    bt_peaq_sudo.execute_n_clear()

    # Check that bootstrap-liquidity-pair has been created
    lpstatus = state_znlnkprot_lppair_status(si_peaq, BNC_IDX)
    assert lpstatus['target_supply'][0] == peaq(TOK_LIQUIDITY)
    assert lpstatus['target_supply'][1] == bnc(TOK_LIQUIDITY)
    assert lpstatus['capacity_supply'][0] == peaq(TOK_LIQUIDITY) * 100
    assert lpstatus['capacity_supply'][1] == bnc(TOK_LIQUIDITY) * 100
    assert lpstatus['accumulated_supply'][0] == peaq(TOK_LIQUIDITY/2)
    assert lpstatus['accumulated_supply'][1] == bnc(TOK_LIQUIDITY/2)

    # 2.) Contribute to bootstrap-liquidity-pair until goal is reached
    compose_bootstrap_contribute_call(bt_peaq_cont, BNC_IDX,
                                      peaq(TOK_LIQUIDITY/2), 0)
    compose_bootstrap_contribute_call(bt_peaq_cont, BNC_IDX,
                                      0, bnc(TOK_LIQUIDITY/2))
    bt_peaq_cont.execute_n_clear()

    # Check that bootstrap-liquidity-pair has been created
    lpstatus = state_znlnkprot_lppair_status(si_peaq, BNC_IDX)
    assert lpstatus['accumulated_supply'][0] == peaq(TOK_LIQUIDITY)
    assert lpstatus['accumulated_supply'][1] == bnc(TOK_LIQUIDITY)

    # 3.) Pool should be filled up (both targets are reached). now end bootstrap
    compose_call_bootstrap_update_end(bt_peaq_sudo, BNC_IDX)
    compose_bootstrap_end_call(bt_peaq_sudo, BNC_IDX)
    bt_peaq_sudo.execute_n_clear()
    wait_for_event(si_peaq, 'ZenlinkProtocol', 'BootstrapEnd')

    # 4.) User swaps tokens by using the created pool
    balance = get_account_balance(si_peaq, kp_user.ss58_address)
    compose_zdex_swap_exact_for(bt_peaq_user, BNC_IDX, amount_in1=bnc(TOK_SWAP))
    bt_peaq_user.execute_n_clear()
    wait_n_check_swap_event(si_peaq, 1)

    # Check that pool has been fully created after goal was reached
    lpstatus = state_znlnkprot_lppair_status(si_peaq, BNC_IDX)
    assert 'total_supply' in lpstatus.keys()  # means it is a true liquidity-pair
    assert lpstatus['total_supply'] > 0

    # Check tokens have been swaped and transfered to user's account
    new_balance = get_account_balance(si_peaq, kp_user.ss58_address)
    assert new_balance > balance

    show_test('bootstrap_pair_n_swap_test', True)


def zenlink_empty_lp_swap_test(si_relay, si_peaq):
    """
    Maryna encountered an issue while testing Zenlink, where one users swaps all available tokens
    of one currency, and then another user tries again to swap the same tokens. Kept this test
    situation to keep track of Zenlink's response on that.
    """
    show_subtitle('zenlink_empty_lp_swap_test')

    usr1 = '//Eve'
    usr2 = '//Dave'

    bt_sudo = ExtrinsicBatch(si_peaq, KP_GLOBAL_SUDO)
    bt_usr1 = ExtrinsicBatch(si_peaq, usr1)
    bt_usr2 = ExtrinsicBatch(si_peaq, usr2)

    # Setup until step 6.
    relay2para_transfer(si_relay, si_peaq, '//Alice', [usr1], [dot(5000)])
    compose_zdex_create_lppair(bt_sudo, DOT_IDX)
    compose_balances_setbalance(bt_sudo, usr1, peaq(30))
    compose_balances_setbalance(bt_sudo, usr2, peaq(20))
    bt_sudo.execute_n_clear()

    # 7.
    compose_zdex_add_liquidity(bt_usr1, DOT_IDX, 1000, 1000)
    bt_usr1.execute_n_clear()

    # 8.
    compose_zdex_swap_exact_for(bt_usr2, DOT_IDX, amount_in0=peaq(1))
    bt_usr2.execute_n_clear()

    # 9.
    dot_balance = state_tokens_accounts(si_peaq, bt_usr2.keypair, 'DOT')
    assert dot_balance > 0

    # 10. #error
    compose_zdex_swap_for_exact(bt_usr2, DOT_IDX, amount_out1=1000, amnt_in_max=1000000000000)
    bt_usr2.execute_n_clear()


class TestZenlinkDex(unittest.TestCase):
    def setUp(self):
        restart_parachain_and_runtime_upgrade()
        wait_until_block_height(SubstrateInterface(url=PARACHAIN_WS_URL), 1)
        wait_until_block_height(SubstrateInterface(url=BIFROST_WS_URL), 1)
        show_title('Zenlink-DEX-Protocol Test')
        self.si_relay = SubstrateInterface(url=RELAYCHAIN_WS_URL)
        self.si_peaq = SubstrateInterface(url=PARACHAIN_WS_URL)
        self.si_bifrost = SubstrateInterface(url=BIFROST_WS_URL)

    @pytest.mark.skipif(TestUtils.is_not_dev_chain() is True, reason='Skip for runtime upgrade test')
    def test_zenlink_dex(self):
        try:
            create_pair_n_swap_test(self.si_relay, self.si_peaq)

        except AssertionError:
            ex_type, ex_val, ex_tb = sys.exc_info()
            tb = traceback.TracebackException(ex_type, ex_val, ex_tb)
            show_test(tb.stack[-1].name, False, tb.stack[-1].lineno)

    @pytest.mark.skipif(TestUtils.is_not_dev_chain() is True, reason='Skip for runtime upgrade test')
    def bootstrap_pair_n_swap_test(self):
        try:
            bootstrap_pair_n_swap_test(self.si_bifrost, self.si_peaq)

        except AssertionError:
            ex_type, ex_val, ex_tb = sys.exc_info()
            tb = traceback.TracebackException(ex_type, ex_val, ex_tb)
            show_test(tb.stack[-1].name, False, tb.stack[-1].lineno)

    # @pytest.mark.skipif(TestUtils.is_not_dev_chain() is True, reason='Skip for runtime upgrade test')
    # def zenlink_empty_lp_swap_test(self):
    #     try:
    #         zenlink_empty_lp_swap_test(self.si_relay, self.si_peaq)

    #     except AssertionError:
    #         ex_type, ex_val, ex_tb = sys.exc_info()
    #         tb = traceback.TracebackException(ex_type, ex_val, ex_tb)
    #         show_test(tb.stack[-1].name, False, tb.stack[-1].lineno)
