import sys
sys.path.append('./')
from substrateinterface import SubstrateInterface
from tools.utils import ExtrinsicBatch
from tools.utils import KP_GLOBAL_SUDO


URL = 'ws://localhost:10044'
COLLATOR = '5Gn1mqSNNXJ3KpFWFPGY5ZrXUTWV3ooqihaZjsBndDz9uYwM'


def get_collator(substrate):
    result = substrate.query(
           module='ParachainStaking',
           storage_function='TopCandidates',
           params=[]
    )

    return [entry['owner'] for entry in result]


if __name__ == '__main__':
    substrate = SubstrateInterface(
        url=URL,
    )
    collators = get_collator(substrate)
    collators = [collator for collator in collators if collator != COLLATOR]

    batch = ExtrinsicBatch(substrate, KP_GLOBAL_SUDO)
    for collator in collators:
        batch.compose_sudo_call(
            'ParachainStaking',
            'force_remove_candidate',
            {
                'collator': collator
            }
        )
    batch.compose_sudo_call(
        'ParachainStaking',
        'force_new_round',
        {}
    )
    bl_hash = batch.execute()
    print(f'Finish but need to wait... {bl_hash}')
