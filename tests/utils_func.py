import os

from tools.utils import WS_URL, get_chain
from tools.restart import restart_parachain_launch
from tools.runtime_upgrade import do_runtime_upgrade
from substrateinterface import SubstrateInterface


def is_runtime_upgrade_test():
    return os.environ.get('RUNTIME_UPGRADE_PATH') is not None


def get_runtime_upgrade_path():
    return os.environ.get('RUNTIME_UPGRADE_PATH')


def restart_parachain_and_runtime_upgrade():
    restart_parachain_launch()
    if is_runtime_upgrade_test():
        path = get_runtime_upgrade_path()
        do_runtime_upgrade(path)


def is_not_dev_chain():
    ws = SubstrateInterface(url=WS_URL)
    chain_name = get_chain(ws)
    print(f'chain_name: {chain_name}')
    return chain_name not in ['peaq-dev', 'peaq-dev-fork']
