import sys
sys.path.append('./')


from substrateinterface import SubstrateInterface, Keypair
from peaq.utils import ExtrinsicBatch
from peaq.sudo_extrinsic import funds
from tools.utils import PARACHAIN_WS_URL, KP_GLOBAL_SUDO
import requests


NUMBER = 10
WS_PORT_START = 10044
RPC_PORT_START = 20033


def setup_collator(ws_port, rpc_port, kp):
    substrate = SubstrateInterface(
        url=f'ws://127.0.0.1:{ws_port}',
    )
    aura_key = requests.post(
        f'http://127.0.0.1:{rpc_port}',
        headers={'Content-Type': 'application/json'},
        json={
            'id': 1,
            'jsonrpc': '2.0',
            'method': 'author_rotateKeys',
            'params': [],
        }
    ).json()['result']

    batch = ExtrinsicBatch(substrate, kp)
    batch.compose_call(
        'Session', 'set_keys',
        {
            'keys': {
                'aura': aura_key,
            },
            'proof': '0x00',
        })
    batch.compose_call(
        'ParachainStaking',
        'join_candidates',
        {
            'stake': 50000 * 10 ** 18,
        })
    receipt = batch.execute()
    print(f'receipt: {receipt}')


def fund_addrs(kps):
    substrate = SubstrateInterface(
        url=PARACHAIN_WS_URL,
    )
    receipt = funds(substrate, KP_GLOBAL_SUDO, [kp.ss58_address for kp in kps], 60000 * 10 ** 18, 0)
    print(f'funds receipt: {receipt}')


if __name__ == '__main__':
    entries = [(WS_PORT_START + i,
                RPC_PORT_START + i,
                Keypair.create_from_mnemonic(Keypair.generate_mnemonic())) for i in range(0, NUMBER)]
    fund_addrs([entry[2] for entry in entries])
    for ws_port, rpc_port, kp in entries:
        setup_collator(ws_port, rpc_port, kp)

    print('setup actions')
    substrate = SubstrateInterface(
        url=PARACHAIN_WS_URL,
    )
    batch = ExtrinsicBatch(substrate, KP_GLOBAL_SUDO)
    batch.compose_sudo_call(
        'ParachainStaking',
        'set_max_selected_candidates',
        {
            'new': 32
        })

    batch.execute_n_clear()
    batch.compose_sudo_call(
        'ParachainStaking',
        'force_new_round',
        {}
    )
    batch.execute()
    batch.execute()
