import warnings
# Ignore warnings about config keys changing in V2 from the python_on_whales
warnings.filterwarnings("ignore", "Valid config keys have changed in V2")

import sys
sys.path.append('.')

import time
from python_on_whales import docker, DockerClient
from substrateinterface import SubstrateInterface
from tools.utils import WS_URL, show_extrinsic
from tools.runtime_upgrade import send_ugprade_call, wait_relay_upgrade_block
from websocket import WebSocketConnectionClosedException


RUNTIME_PATH = "peaq_dev_runtime.compact.compressed.wasm.0.0.9"


def do_runtime_upgrade():
    print(f'Upgrading runtime to {RUNTIME_PATH}')
    substrate = SubstrateInterface(url=WS_URL)
    receipt = send_ugprade_call(substrate, RUNTIME_PATH)
    show_extrinsic(receipt, 'upgrade?')
    wait_relay_upgrade_block()
    time.sleep(60)
    print('Runtime upgraded')


def _restart_parachain_launch():
    projects = docker.compose.ls()
    project = [p for p in projects if 'parachain-launch' in str(p.config_files[0])]
    if len(project) == 0 or len(project) > 1:
        return IOError(f'Found {len(project)} parachain-launch projects, {project}')

    compose_file = str(project[0].config_files[0])
    my_docker = DockerClient(compose_files=[compose_file])

    my_docker.compose.down(volumes=True)
    my_docker.compose.up(detach=True, build=True)
    count_down = 0
    wait_time = 60
    while count_down < wait_time:
        try:
            SubstrateInterface(
                url=WS_URL,
            )
            return
        except (ConnectionResetError, WebSocketConnectionClosedException) as e:
            print(f'Cannot connect to {WS_URL}, {e}')
            count_down += 5
            time.sleep(5)
            continue
        except Exception:
            raise IOError(f'Cannot connect to {WS_URL}')
    raise IOError(f'Cannot connect to {WS_URL} after {wait_time} seconds')


def restart_parachain_launch():
    _restart_parachain_launch()
    # do_runtime_upgrade()


if __name__ == '__main__':
    restart_parachain_launch()
    do_runtime_upgrade()
    print('Sleeping for 60 seconds')
    time.sleep(60)
