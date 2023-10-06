from peaq.utils import ExtrinsicBatch
from tools.utils import BIFROST_PD_CHAIN_ID


XCM_VER = 'V3'  # So far not tested with V2!

UNITS_PER_SECOND = 5 * 10 ** 5
BNC_TOKEN_LOCATION = {
    XCM_VER: {
        'parents': '1',
        'interior': {'X2': [
            {'Parachain': BIFROST_PD_CHAIN_ID},
            {'GeneralKey': {
                'length': 2,
                'data': [0, 1] + [0] * 30,
            }}
        ]}
    }
}
BNC_METADATA = {
    'name': 'Bifrost Native Token',
    'symbol': 'BNC',
    'decimals': 12,
}
BNC_ASSET_ID = {
    'Token': '3',
}


RELAY_TOKEN_LOCATION = {
    XCM_VER: {
        'parents': '1',
        'interior': 'Here'
    }
}
RELAY_ASSET_ID = {
    'Token': '1',
}
RELAY_METADATA = {
    'name': 'Relay Token',
    'symbol': 'DOT',
    'decimals': 12,
}


def batch_register_location(batch, asset_id, location):
    batch.compose_sudo_call(
        'XcAssetConfig',
        'register_asset_location',
        {
            'asset_location': location,
            'asset_id': asset_id
        }
    )


def batch_set_units_per_second(batch, location, units_per_second):
    batch.compose_sudo_call(
        'XcAssetConfig',
        'set_asset_units_per_second',
        {
            'asset_location': location,
            'units_per_second': units_per_second
        }
    )


def batch_create_asset(batch, addr_admin, asset_id, min_balance=100):
    batch.compose_call(
        'Assets',
        'create',
        {
            'id': asset_id,
            'admin': addr_admin,
            'min_balance': min_balance,
        }
    )


def batch_set_metadata(batch, asset_id, name, symbol, decimals):
    batch.compose_call(
        'Assets',
        'set_metadata',
        {
            'id': asset_id,
            'name': name,
            'symbol': symbol,
            'decimals': decimals,
        }
    )


def setup_asset_if_not_exist(si_peaq, kp_sudo, asset_id, metadata, min_balance=100):
    resp = si_peaq.query("Assets", "Asset", [asset_id])
    if resp.value:
        return {
            'is_success': True,
        }

    batch = ExtrinsicBatch(si_peaq, kp_sudo)
    batch_create_asset(batch, kp_sudo.ss58_address, asset_id, min_balance)
    batch_set_metadata(batch, asset_id,
                       metadata['name'], metadata['symbol'], metadata['decimals'])
    return batch.execute()


def setup_xc_register_if_not_exist(si_peaq, KP_GLOBAL_SUDO, asset_id, location, units_per_second):
    resp = si_peaq.query("XcAssetConfig", "AssetIdToLocation", [asset_id])
    if resp.value:
        return {
            'is_success': True,
        }
    batch = ExtrinsicBatch(si_peaq, KP_GLOBAL_SUDO)
    batch_register_location(batch, asset_id, location)
    batch_set_units_per_second(batch, location, units_per_second)
    return batch.execute()
