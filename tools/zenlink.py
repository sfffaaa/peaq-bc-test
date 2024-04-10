from tools.utils import get_peaq_chain_id


PEAQ_PD_CHAIN_ID = get_peaq_chain_id()


def calc_deadline(substrate):
    return substrate.get_block_number(None) + 10


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
