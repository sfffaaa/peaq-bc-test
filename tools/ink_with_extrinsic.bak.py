import sys

from substrateinterface import SubstrateInterface, Keypair
from substrateinterface.contracts import ContractCode
from utils import TOKEN_NUM_BASE, show_extrinsic, WS_URL


def transfer(substrate, kp_src, kp_dst_addr, token_num):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    call = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst_addr,
            'value': token_num * TOKEN_NUM_BASE
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'transfer')
    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


def did_add(substrate, kp_src, name, value):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    call = substrate.compose_call(
        call_module='PeaqDid',
        call_function='add_attribute',
        call_params={
            'did_account': kp_src.ss58_address,
            'name': name,
            'value': value,
            'valid_for': None,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'did_add')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


def ink_test():
    print('---- pallet_did_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL, type_registry_preset='canvas') as substrate:
            kp_src = Keypair.create_from_uri('//Alice')

            code = ContractCode.create_from_contract_files(
                metadata_file='INK/metadata.json',
                wasm_file='INK/flipper.wasm',
                substrate=substrate
            )

            contract = code.deploy(
                keypair=kp_src,
                endowment=10 ** 15,
                gas_limit=1000000000000,
                constructor="new",
                args={'init_value': True},
                upload_code=True
            )
            print(f'✅ Deployed @ {contract.contract_address}')

            result = contract.read(kp_src, 'get')
            print('Current value of "get":', result.contract_result_data)

            gas_predit_result = contract.read(kp_src, 'flip')

            print('Result of dry-run: ', gas_predit_result.contract_result_data)
            print('Gas estimate: ', gas_predit_result.gas_consumed)

            # Do the actual transfer
            print('Executing contract call...')
            contract_receipt = contract.exec(kp_src, 'flip', args={},
                                             gas_limit=gas_predit_result.gas_consumed)

            print(f'Events triggered in contract: {contract_receipt.contract_events}')
            result = contract.read(kp_src, 'get')
            print('Current value of "get":', result.contract_result_data)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    ink_test()
