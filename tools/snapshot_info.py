from substrateinterface import SubstrateInterface
from peaq.utils import get_chain
import argparse


import pprint
pp = pprint.PrettyPrinter(indent=4)


def query_storage(substrate, module, storage_function):
    result = substrate.query(
        module=module,
        storage_function=storage_function,
        params=[],
    )
    return result.value


def query_constant(substrate, module, storage_function):
    result = substrate.get_constant(
        module,
        storage_function,
    )

    return result.value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get storage and constants from a Substrate chain')
    parser.add_argument('-r', '--runtime', type=str, required=True, help='Your runtime websocket endpoint')

    args = parser.parse_args()

    substrate = SubstrateInterface(
        url=args.runtime,
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

    for pallet in metadata.value[1]['V14']['pallets']:
        if not pallet['storage']:
            continue

        out['storage'][pallet['name']] = {}
        # if pallet['name'] != 'ParachainStaking':
        #     continue
        for entry in pallet['storage']['entries']:
            data = query_storage(substrate, pallet['name'], entry['name'])
            out['storage'][pallet['name']][entry['name']] = data

    for pallet in metadata.value[1]['V14']['pallets']:
        if not pallet['constants']:
            continue

        out['constants'][pallet['name']] = {}
        # if pallet['name'] != 'ParachainStaking':
        #     continue
        for entry in pallet['constants']:
            data = query_constant(substrate, pallet['name'], entry['name'])
            out['constants'][pallet['name']][entry['name']] = data

    pp.pprint(out)
