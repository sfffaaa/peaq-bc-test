from peaq.utils import ExtrinsicBatch


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
