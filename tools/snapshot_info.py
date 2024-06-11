from substrateinterface import SubstrateInterface
from peaq.utils import get_chain
import argparse


import pprint
pp = pprint.PrettyPrinter(indent=4)

ENDPOINTS = {
    'peaq-dev': 'wss://wsspc1-qa.agung.peaq.network',
    'krest': 'wss://wss-krest.peaq.network',
    'peaq': 'wss://mpfn1.peaq.network',
    'docker': 'wss://docker-test.peaq.network',
    'local-test': 'ws://localhost:10044',
}


STORAGE_SKIP_LIST = {
    'AddressUnification': 'all',
    'Assets': 'all',
    'AuraExt': 'all',
    'Authorship': 'all',
    'Balances': 'all',
    'Contracts': ['PristineCode', 'CodeStorage', 'OwnerInfoOf', 'ContractInfoOf', 'DeletionQueue'],
    'Council': ['ProposalCount', 'ProposalOf', 'Proposals', 'Voting'],
    'DmpQueue': ['CounterForOverweight', 'PageIndex', 'Pages'],
    'EVM': ['AccountCodes', 'AccountStorages', 'AccountCodesMetadata'],
    'Ethereum': 'all',
    'Multisig': 'all',
    # We should check out collators in the TopCandidates
    'ParachainStaking': [
        'CandidatePool', 'DelegatorState', 'LastDelegation', 'TopCandidates', 'TotalCollatorStake',
        'Unstaking'],
    'ParachainSystem': [
        'LastDmqMqcHead', 'LastRelayChainBlockNumber', 'RelayStateProof', 'RelevantMessagingState', 'ValidationData'],
    'PeaqStorage': 'all',
    'PeaqDid': 'all',
    'PeaqRbac': 'all',
    'RandomnessCollectiveFlip': 'all',
    'Session': 'all',
    'System': 'all',
    'Timestamp': 'all',
    'Treasury': 'all',
    'Vesting': 'all',
    'TransactionPayment': 'all',
}


def query_storage(substrate, module, storage_function):
    try:
        result = substrate.query(
            module=module,
            storage_function=storage_function,
        )
        print(f'Querying data: {module}::{storage_function}')
        return result.value
    except ValueError:
        pass

    print(f'Querying map: {module}::{storage_function}')
    result = substrate.query_map(
        module=module,
        storage_function=storage_function,
        max_results=1000,
        page_size=1000,
    )
    return {str(k.value): v.value for k, v in result.records}


def query_constant(substrate, module, storage_function):
    print(f'Querying constant: {module}::{storage_function}')
    result = substrate.get_constant(
        module,
        storage_function,
    )

    return result.value


def is_storage_ignore(module, storage_function):
    if module not in STORAGE_SKIP_LIST:
        return False
    if STORAGE_SKIP_LIST[module] == 'all':
        return True
    if storage_function in STORAGE_SKIP_LIST[module]:
        return True
    return False


def get_all_storage(substrate, metadata, out):
    for pallet in metadata.value[1]['V14']['pallets']:
        if not pallet['storage']:
            continue

        out[pallet['name']] = {}
        for entry in pallet['storage']['entries']:
            if is_storage_ignore(pallet['name'], entry['name']):
                out[pallet['name']][entry['name']] = 'ignored'
                continue
            data = query_storage(substrate, pallet['name'], entry['name'])
            out[pallet['name']][entry['name']] = data

    return out


def get_all_constants(substrate, metadata, out):
    for pallet in metadata.value[1]['V14']['pallets']:
        if not pallet['constants']:
            continue

        out[pallet['name']] = {}
        for entry in pallet['constants']:
            data = query_constant(substrate, pallet['name'], entry['name'])
            out[pallet['name']][entry['name']] = data

    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get storage and constants from a Substrate chain')
    parser.add_argument(
        '-r', '--runtime', type=str, required=True,
        help='Your runtime websocket endpoint. however,'
             'some keys will automatically convert it to the correct endpoint: e.g.'
             f'{pp.pformat(ENDPOINTS)}')
    parser.add_argument(
        '-s', '--storage', type=bool, default=False,
        help='The storage function to query'
    )
    parser.add_argument(
        '-f', '--folder', type=str, default='tools/snapshot',
        help='The output folder to write the data to'
    )

    args = parser.parse_args()
    runtime = args.runtime
    if args.runtime in ENDPOINTS:
        runtime = ENDPOINTS[args.runtime]

    substrate = SubstrateInterface(
        url=runtime,
    )
    metadata = substrate.get_metadata()
    out = {
        'chain': {
            'name': get_chain(substrate),
            'version': substrate.runtime_version,
        },
        'constants': {},
        'storage': {},
    }

    get_all_storage(substrate, metadata, out['storage'])
    get_all_constants(substrate, metadata, out['constants'])

    pp.pprint(out)
    if args.folder:
        filepath = f'{args.folder}/{args.runtime}.{substrate.runtime_version}'
        with open(filepath, 'w') as f:
            f.write(pp.pformat(out))
