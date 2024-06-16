from substrateinterface import SubstrateInterface
from tools.utils import KP_GLOBAL_SUDO, RELAYCHAIN_WS_URL
from peaq.utils import ExtrinsicBatch


def get_parachain_id(substrate):
    result = substrate.query(
        'Paras',
        'Parachains',
    )
    return result.value


def setup_hrmp_channel(url=RELAYCHAIN_WS_URL):
    relay_substrate = SubstrateInterface(url, type_registry_preset='rococo')
    result = relay_substrate.query(
        'Paras',
        'Parachains',
    )
    para_ids = result.value

    if not para_ids:
        print('No parachain registered')
        raise IOError('No parachain registered')

    if len(para_ids) > 2:
        raise IOError('More than 2 parachains registered')

    if len(para_ids) == 1:
        print('Only one parachain registered')
        return

    batch = ExtrinsicBatch(relay_substrate, KP_GLOBAL_SUDO)

    batch.compose_sudo_call(
        'ParasSudoWrapper',
        'sudo_establish_hrmp_channel',
        {
            'sender': para_ids[0],
            'recipient': para_ids[1],
            'max_capacity': 8,
            'max_message_size': 102400,
        }
    )

    batch.compose_sudo_call(
        'ParasSudoWrapper',
        'sudo_establish_hrmp_channel',
        {
            'sender': para_ids[1],
            'recipient': para_ids[0],
            'max_capacity': 8,
            'max_message_size': 102400,
        }
    )

    receipt = batch.execute()
    print(f'HRMP channel established, success: {receipt.is_success}')
