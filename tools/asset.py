from peaq.utils import ExtrinsicBatch
from tools.utils import BIFROST_PD_CHAIN_ID, PEAQ_PD_CHAIN_ID
import copy


XCM_VER = 'V3'  # So far not tested with V2!

ACA_ASSET_ID = {
    'peaq': {
        'Token': '3',
    },
    'para': {
        'Token': 'ACA',
    }
}
ACA_ASSET_LOCATION = {
    'peaq': {
        XCM_VER: {
            'parents': '1',
            'interior': {'X2': [
                {'Parachain': BIFROST_PD_CHAIN_ID},
                {'GeneralKey': {
                    'length': 2,
                    'data': [0, 0] + [0] * 30,
                }}
            ]}
        }
    },
    'para': None
}

UNITS_PER_SECOND = 5 * 10 ** 5
ACA_METADATA = {
    'name': 'ACA',
    'symbol': 'ACA',
    'decimals': 12,
}


RELAY_ASSET_LOCATION = {
    'peaq': {
        XCM_VER: {
            'parents': '1',
            'interior': 'Here'
        }
    },
    'para': None,
}
RELAY_ASSET_ID = {
    'peaq': {
        'Token': '1',
    },
    'para': None,
}
RELAY_METADATA = {
    'name': 'Relay Token',
    'symbol': 'DOT',
    'decimals': 12,
}

PEAQ_ASSET_ID = {
    'peaq': 'SelfReserve',
    'para': {
        'ForeignAsset': '0',
    }
}
PEAQ_ASSET_LOCATION = {
    'peaq': {
        XCM_VER: {
            'parents': '0',
            'interior': {
                'X1': {
                    'GeneralKey': {
                        'length': 2,
                        'data': [0, 0] + [0] * 30,
                    }
                }
            }
        }
    },
    'para': {
        XCM_VER: {
            'parents': '1',
            'interior': {'X2': [
                {'Parachain': PEAQ_PD_CHAIN_ID},
                {'GeneralKey': {
                    'length': 2,
                    'data': [0, 0] + [0] * 30,
                }}
            ]}
        }
    },
}
PEAQ_METADATA = {
    'name': 'Peaq Token',
    'symbol': 'AGUNG',
    'decimals': 18,
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


def batch_mint(batch, addr_src, asset_id, token_amount):
    batch.compose_call(
        'Assets',
        'mint',
        {
            'id': asset_id,
            'beneficiary': addr_src,
            'amount': token_amount,
        }
    )


class AlwaysTrueReceipt():
    def __init__(self, *args, **kwargs):
        pass

    def is_success(self):
        return True

    def error_message(self):
        return ''


def setup_aca_asset_if_not_exist(si_aca, kp_sudo, location, metadata, min_balance=100):
    resp = si_aca.query('AssetRegistry', 'LocationToCurrencyIds', [location['V3']])
    if resp.value:
        return AlwaysTrueReceipt()

    new_metadata = copy.deepcopy(metadata)
    new_metadata['minimal_balance'] = min_balance
    batch = ExtrinsicBatch(si_aca, kp_sudo)
    batch.compose_sudo_call(
        'AssetRegistry',
        'register_foreign_asset',
        {
            'location': location,
            'metadata': new_metadata,
        }
    )
    return batch.execute()


def setup_asset_if_not_exist(si_peaq, kp_sudo, asset_id, metadata, min_balance=100):
    resp = si_peaq.query("Assets", "Asset", [asset_id])
    if resp.value:
        return AlwaysTrueReceipt()

    batch = ExtrinsicBatch(si_peaq, kp_sudo)
    batch_create_asset(batch, kp_sudo.ss58_address, asset_id, min_balance)
    batch_set_metadata(batch, asset_id,
                       metadata['name'], metadata['symbol'], metadata['decimals'])
    return batch.execute()


def setup_xc_register_if_not_exist(si_peaq, KP_GLOBAL_SUDO, asset_id, location, units_per_second):
    resp = si_peaq.query("XcAssetConfig", "AssetIdToLocation", [asset_id])
    if resp.value:
        return AlwaysTrueReceipt()
    batch = ExtrinsicBatch(si_peaq, KP_GLOBAL_SUDO)
    batch_register_location(batch, asset_id, location)
    batch_set_units_per_second(batch, location, units_per_second)
    return batch.execute()


def get_valid_asset_id(conn):
    for i in range(1, 100):
        asset = conn.query("Assets", "Asset", [{'Token': i}])
        if asset.value:
            continue
        else:
            return {'Token': i}
