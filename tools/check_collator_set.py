import sys
sys.path.append('./')
from substrateinterface import SubstrateInterface

URL = "wss://wss-krest.peaq.network"

ADDR = '5H3YNvfVXfbz6rYbQ3FHbH1K1KQDmaHe2J8ka8TfYxoUaKnF'


def check_collator_in_set(substrate, addr):
    result = substrate.query(
           module='ParachainStaking',
           storage_function='TopCandidates',
           params=[]
    )

    index = 1000000
    for i, entry in enumerate(result):
        if addr in entry['owner']:
            index = i
            break

    if index == 1000000:
        print(f"I didn't find {addr} in the top candidates.")
        return False

    print(f"Index of {addr} is {index}")
    return True


def check_in_session_validator(substrate, addr):
    result = substrate.query(
           module='Session',
           storage_function='Validators',
           params=[]
    )

    if addr in result:
        print(f"{addr} is in the session validator set.")
        return True
    else:
        print(f"{addr} is not in the session validator set.")
        return False


def check_in_session_next_key(substrate, addr):
    result = substrate.query(
           module='Session',
           storage_function='NextKeys',
           params=[addr]
    )

    if result:
        print(f"{addr} is in the session next key set.")
        return result['aura']

    return None


def check_in_autorities(substrate, addr):
    result = substrate.query(
           module='AuraExt',
           storage_function='Authorities',
           params=[]
    )

    if addr in result:
        print(f"{addr} is in the authorities set.")
        return True
    else:
        print(f"{addr} is not in the authorities set.")
        return False


if __name__ == '__main__':
    substrate = SubstrateInterface(
        url=URL,
    )
    if not check_collator_in_set(substrate, ADDR):
        sys.exit(1)

    if not check_in_session_validator(substrate, ADDR):
        sys.exit(1)

    session_key = check_in_session_next_key(substrate, ADDR)
    if session_key is None:
        print("I didn't find the session key.")
        sys.exit(1)

    if not check_in_autorities(substrate, session_key):
        print("I did't found the session key in the authorities.")
        sys.exit(1)

    print('\n\n')
    print("Everything is fine, please ask user to check the session belongs to the user's node:")
    print(f"Session key: {session_key}")
    print(f'1. Polkadot.js RPC.author.hasSessionKeys(["{session_key}"])')
    print(f'''2. Use below command to check:
curl -H "Content-Type: application/json" -d '{{"id":1, "jsonrpc":"2.0", "method": "author_hasSessionKeys", "params":["{session_key}"]}}' http://localhost:9933''')  # noqa: E501
