import os
import time


def restart_parachain_launch():
    os.system("bash -i -c 'r_parachain_launch_down; r_parachain_launch_up'")
    print('Restarting parachain-launch...')
    time.sleep(30)
