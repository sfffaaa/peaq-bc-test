import sys
sys.path.append('./')
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL


def get_valid_asset_id(conn):
    for i in range(0, 100):
        asset = conn.query("Assets", "Asset", [i])
        if asset.value:
            continue
        else:
            return i


def get_asset_balance(conn, addr, asset_id):
    return conn.query("Assets", "Account", [asset_id, addr])


def set_metadata(conn, kp_admin, asset_id, name, symbol, decimals):
    nonce = conn.get_account_nonce(kp_admin.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='set_metadata',
        call_params={
            'id': asset_id,
            'name': name,
            'symbol': symbol,
            'decimals': decimals,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_admin,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_set_metadata')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def create_asset(conn, kp_sudo, kp_admin, asset_id):
    nonce = conn.get_account_nonce(kp_sudo.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='create',
        call_params={
            'id': asset_id,
            'admin': kp_admin.ss58_address,
            'min_balance': 100,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_create')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def freeze_asset(conn, kp_sudo, asset_id):
    nonce = conn.get_account_nonce(kp_sudo.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='freeze_asset',
        call_params={
            'id': asset_id,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_freeze_asset')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def thaw_asset(conn, kp_sudo, asset_id):
    nonce = conn.get_account_nonce(kp_sudo.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='thaw_asset',
        call_params={
            'id': asset_id,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_thaw_asset')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def mint(conn, kp_sudo, addr_src, asset_id, token_amount):
    nonce = conn.get_account_nonce(kp_sudo.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='mint',
        call_params={
            'id': asset_id,
            'beneficiary': addr_src,
            'amount': token_amount,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_mint')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def burn(conn, kp_sudo, addr_src, asset_id, token_amount):
    nonce = conn.get_account_nonce(kp_sudo.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='burn',
        call_params={
            'id': asset_id,
            'who': addr_src,
            'amount': token_amount,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_burn')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def transfer(conn, kp_src, kp_dst, asset_id, token_amount):
    nonce = conn.get_account_nonce(kp_src.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='transfer',
        call_params={
            'id': asset_id,
            'target': kp_dst.ss58_address,
            'amount': token_amount,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_transfer')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def destroy(conn, kp_sudo, asset_id):
    asset = conn.query("Assets", "Asset", [asset_id])

    nonce = conn.get_account_nonce(kp_sudo.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='destroy',
        call_params={
            'id': asset_id,
            'witness': {
                'accounts': str(asset['accounts']),
                'sufficients': str(asset['sufficients']),
                'approvals': str(asset['approvals']),
            },
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_destroy')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def freeze(conn, kp_sudo, kp_src, asset_id):
    nonce = conn.get_account_nonce(kp_sudo.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='freeze',
        call_params={
            'id': asset_id,
            'who': kp_src.ss58_address,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_freeze')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def thaw(conn, kp_sudo, kp_src, asset_id):
    nonce = conn.get_account_nonce(kp_sudo.ss58_address)
    call = conn.compose_call(
        call_module='Assets',
        call_function='thaw',
        call_params={
            'id': asset_id,
            'who': kp_src.ss58_address,
        })

    extrinsic = conn.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
        nonce=nonce
    )

    receipt = conn.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'asset_thaw')

    if not receipt.is_success:
        print(conn.get_events(receipt.block_hash))
        raise IOError


def pallet_assets_test():
    print('---- pallet_assets_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as conn:
            asset_id = get_valid_asset_id(conn)

            kp_sudo = Keypair.create_from_uri('//Alice')
            kp_admin = Keypair.create_from_uri('//Bob')
            create_asset(conn, kp_sudo, kp_admin, asset_id)

            kp_src = Keypair.create_from_uri('//Alice//stash')
            balance_src = get_asset_balance(conn, kp_src.ss58_address, asset_id)['balance'].value
            mint_number = 10000
            mint(conn, kp_admin, kp_src.ss58_address, asset_id, mint_number)
            assert(get_asset_balance(
                   conn, kp_src.ss58_address, asset_id)['balance'].value == balance_src + mint_number)

            burn_number = 5000
            burn(conn, kp_admin, kp_src.ss58_address, asset_id, burn_number)
            assert(get_asset_balance(
                   conn, kp_src.ss58_address, asset_id)['balance'].value == balance_src + mint_number - burn_number)

            transfer_number = 500
            kp_dst = Keypair.create_from_uri('//Bob//stash')
            balance_dst = get_asset_balance(conn, kp_dst.ss58_address, asset_id)['balance'].value
            transfer(conn, kp_src, kp_dst, asset_id, transfer_number)
            assert(get_asset_balance(
                   conn, kp_dst.ss58_address, asset_id)['balance'].value == balance_dst + transfer_number)

            freeze_asset(conn, kp_admin, asset_id)
            assert(conn.query("Assets", "Asset", [asset_id]).value['is_frozen'])
            thaw_asset(conn, kp_admin, asset_id)
            assert(not conn.query("Assets", "Asset", [asset_id]).value['is_frozen'])

            freeze(conn, kp_admin, kp_src, asset_id)
            assert(get_asset_balance(conn, kp_src.ss58_address, asset_id).value['is_frozen'])
            thaw(conn, kp_admin, kp_src, asset_id)
            assert(not get_asset_balance(conn, kp_src.ss58_address, asset_id).value['is_frozen'])

            destroy(conn, kp_sudo, asset_id)
            assert(asset_id == get_valid_asset_id(conn))

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    pallet_assets_test()
