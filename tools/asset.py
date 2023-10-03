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
