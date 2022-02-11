import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, SCALE_CODEC
from tools.utils import transfer, calculate_evm_account, calculate_evm_addr
# from scalecodec.base import RuntimeConfiguration
# from scalecodec.base import ScaleBytes

import pprint
pp = pprint.PrettyPrinter(indent=4)

ERC_TOKEN_TRANSFER = 34


# For the ERC 20 token
# https://github.com/paritytech/frontier/blob/master/template/examples/contract-erc20/truffle/contracts/MyToken.json#L259
def create_constract(substrate, kp_src, eth_src):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    call = substrate.compose_call(
        call_module='EVM',
        call_function='create',
        call_params={
            'source': eth_src,
            'init': '0x608060405234801561001057600080fd5b50610041337fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff61004660201b60201c565b610291565b600073ffffffffffffffffffffffffffffffffffffffff168273ffffffffffffffffffffffffffffffffffffffff1614156100e9576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601f8152602001807f45524332303a206d696e7420746f20746865207a65726f20616464726573730081525060200191505060405180910390fd5b6101028160025461020960201b610c7c1790919060201c565b60028190555061015d816000808573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205461020960201b610c7c1790919060201c565b6000808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055508173ffffffffffffffffffffffffffffffffffffffff16600073ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef836040518082815260200191505060405180910390a35050565b600080828401905083811015610287576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601b8152602001807f536166654d6174683a206164646974696f6e206f766572666c6f77000000000081525060200191505060405180910390fd5b8091505092915050565b610e3a806102a06000396000f3fe608060405234801561001057600080fd5b50600436106100885760003560e01c806370a082311161005b57806370a08231146101fd578063a457c2d714610255578063a9059cbb146102bb578063dd62ed3e1461032157610088565b8063095ea7b31461008d57806318160ddd146100f357806323b872dd146101115780633950935114610197575b600080fd5b6100d9600480360360408110156100a357600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff16906020019092919080359060200190929190505050610399565b604051808215151515815260200191505060405180910390f35b6100fb6103b7565b6040518082815260200191505060405180910390f35b61017d6004803603606081101561012757600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190803573ffffffffffffffffffffffffffffffffffffffff169060200190929190803590602001909291905050506103c1565b604051808215151515815260200191505060405180910390f35b6101e3600480360360408110156101ad57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff1690602001909291908035906020019092919050505061049a565b604051808215151515815260200191505060405180910390f35b61023f6004803603602081101561021357600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff16906020019092919050505061054d565b6040518082815260200191505060405180910390f35b6102a16004803603604081101561026b57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff16906020019092919080359060200190929190505050610595565b604051808215151515815260200191505060405180910390f35b610307600480360360408110156102d157600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff16906020019092919080359060200190929190505050610662565b604051808215151515815260200191505060405180910390f35b6103836004803603604081101561033757600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190803573ffffffffffffffffffffffffffffffffffffffff169060200190929190505050610680565b6040518082815260200191505060405180910390f35b60006103ad6103a6610707565b848461070f565b6001905092915050565b6000600254905090565b60006103ce848484610906565b61048f846103da610707565b61048a85604051806060016040528060288152602001610d7060289139600160008b73ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000610440610707565b73ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054610bbc9092919063ffffffff16565b61070f565b600190509392505050565b60006105436104a7610707565b8461053e85600160006104b8610707565b73ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008973ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054610c7c90919063ffffffff16565b61070f565b6001905092915050565b60008060008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020549050919050565b60006106586105a2610707565b8461065385604051806060016040528060258152602001610de160259139600160006105cc610707565b73ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008a73ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054610bbc9092919063ffffffff16565b61070f565b6001905092915050565b600061067661066f610707565b8484610906565b6001905092915050565b6000600160008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054905092915050565b600033905090565b600073ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff161415610795576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401808060200182810382526024815260200180610dbd6024913960400191505060405180910390fd5b600073ffffffffffffffffffffffffffffffffffffffff168273ffffffffffffffffffffffffffffffffffffffff16141561081b576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401808060200182810382526022815260200180610d286022913960400191505060405180910390fd5b80600160008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055508173ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925836040518082815260200191505060405180910390a3505050565b600073ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff16141561098c576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401808060200182810382526025815260200180610d986025913960400191505060405180910390fd5b600073ffffffffffffffffffffffffffffffffffffffff168273ffffffffffffffffffffffffffffffffffffffff161415610a12576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401808060200182810382526023815260200180610d056023913960400191505060405180910390fd5b610a7d81604051806060016040528060268152602001610d4a602691396000808773ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054610bbc9092919063ffffffff16565b6000808573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002081905550610b10816000808573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054610c7c90919063ffffffff16565b6000808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055508173ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef836040518082815260200191505060405180910390a3505050565b6000838311158290610c69576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004018080602001828103825283818151815260200191508051906020019080838360005b83811015610c2e578082015181840152602081019050610c13565b50505050905090810190601f168015610c5b5780820380516001836020036101000a031916815260200191505b509250505060405180910390fd5b5060008385039050809150509392505050565b600080828401905083811015610cfa576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040180806020018281038252601b8152602001807f536166654d6174683a206164646974696f6e206f766572666c6f77000000000081525060200191505060405180910390fd5b809150509291505056fe45524332303a207472616e7366657220746f20746865207a65726f206164647265737345524332303a20617070726f766520746f20746865207a65726f206164647265737345524332303a207472616e7366657220616d6f756e7420657863656564732062616c616e636545524332303a207472616e7366657220616d6f756e74206578636565647320616c6c6f77616e636545524332303a207472616e736665722066726f6d20746865207a65726f206164647265737345524332303a20617070726f76652066726f6d20746865207a65726f206164647265737345524332303a2064656372656173656420616c6c6f77616e63652062656c6f77207a65726fa265627a7a72315820c7a5ffabf642bda14700b2de42f8c57b36621af020441df825de45fd2b3e1c5c64736f6c63430005100032',
            'value': '0x0000000000000000000000000000000000000000000000000000000000000000',
            'gas_limit': 4294967294,
            'max_fee_per_gas': "0xfffffff000000000000000000000000000000000000000000000000000000000",
            'max_priority_fee_per_gas': None,
            'nonce': None,
            'access_list': []
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'evm_create')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError
    else:
        created_event = [_ for _ in substrate.get_events(receipt.block_hash)
                         if _['event'].value['event_id'] == 'Created'][0]
        return created_event.value['attributes']


def call_eth_transfer(substrate, kp_src, eth_src, eth_dst):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    call = substrate.compose_call(
        call_module='EVM',
        call_function='call',
        call_params={
            'source': eth_src,
            'target': eth_dst,
            'input': '0x',
            'value': '0xffff000000000000000000000000000000000000000000000000000000000000',
            'gas_limit': 4294967294,
            'max_fee_per_gas': "0xffffffff00000000000000000000000000000000000000000000000000000000",
            'max_priority_fee_per_gas': None,
            'nonce': None,
            'access_list': []
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'evm_call')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


def transfer_erc_token(substrate, kp_src, eth_src, eth_dst, contract_addr):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    call = substrate.compose_call(
        call_module='EVM',
        call_function='call',
        call_params={
            'target': contract_addr,
            'source': eth_src,
            'input': f'0xa9059cbb000000000000000000000000{eth_dst.lower()[2:]}00000000000000000000000000000000000000000000000000000000000000{hex(ERC_TOKEN_TRANSFER)[2:]}',
            'value': '0x0000000000000000000000000000000000000000000000000000000000000000',
            'gas_limit': 4294967295,
            'max_fee_per_gas': "0xfffffff000000000000000000000000000000000000000000000000000000000",
            'max_priority_fee_per_gas': None,
            'nonce': None,
            'access_list': []
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'call')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError
    #  else:
        #  created_event = [_ for _ in substrate.get_events(receipt.block_hash)
        #                   if _['event'].value['event_id'] == 'Created'][0]
        #  return created_event.value['attributes']


def evm_extrinsic_test():
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url="ws://127.0.0.1:9944", type_registry=SCALE_CODEC) as conn:
            # print('Check the get balance')
            kp_src = Keypair.create_from_uri('//Alice')
            eth_src = calculate_evm_addr(kp_src.ss58_address)

            # Transfer token to 0xd43593c715fdd31c61141abd04a99fd6822c8558
            token_num = 10000 * pow(10, 15)
            transfer(conn, kp_src, calculate_evm_account(eth_src), token_num)

            eth_balance = int(conn.rpc_request("eth_getBalance", [eth_src]).get('result'), 16)
            print(f'src ETH balance: {eth_balance}')
            assert(0 != eth_balance)

            print('Check the transfer eth token')
            eth_dst = '0x8eaf04151687736326c9fea17e25fc5287613693'
            eth_before_balance = int(conn.rpc_request("eth_getBalance", [eth_dst]).get('result'), 16)
            print(f'dst ETH balance: {eth_before_balance}')

            call_eth_transfer(conn, kp_src, eth_src, eth_dst)

            eth_after_balance = int(conn.rpc_request("eth_getBalance", [eth_dst]).get('result'), 16)
            print(f'dst ETH balance: {eth_after_balance}')
            # assert(eth_after_balance == eth_before_balance + 65535)

            # # [TODO]... Check the precompile ???
            # # contract_addr = "0x0000000000000000000000000000000000000002"
            # # eth_code = conn.query("EVM", "AccountCodes", [contract_addr])
            # # print(eth_code)
            # # print(contract_addr)
            # # raise IOError

            contract_addr = create_constract(conn, kp_src, eth_src)
            eth_code = conn.query("EVM", "AccountCodes", [contract_addr])
            assert(contract_addr)
            assert(eth_code)
            print(f'ETH code: {eth_code[:30]}')
            print(f'Contract addr: {contract_addr}')

            # # slot_addr = '0xd0ff6628d37f0e034a8f3f7b2b8fbe3f46f06adc578f2b220b99861487f7a638'
            slot_addr = '0x045c0350b9cf0df39c4b40400c965118df2dca5ce0fbcf0de4aafc099aea4a14'
            prev_src_erc20 = int(conn.query("EVM", "AccountStorages", [contract_addr, slot_addr])[2:], 16)
            print(f'Alice\'s before ERC20 token: {prev_src_erc20}')

            transfer_erc_token(conn, kp_src, eth_src, eth_dst, contract_addr)

            after_src_erc20 = int(conn.query("EVM", "AccountStorages", [contract_addr, slot_addr])[2:], 16)
            print(f'Alice\'s after ERC20 token: {after_src_erc20}')
            assert(after_src_erc20 + ERC_TOKEN_TRANSFER == prev_src_erc20)

            slot_addr = '0xe15f03c03b19c474c700f0ded08fa4d431a189d91588b86c3ef774970f504892'
            after_dst_erc20 = int(conn.query("EVM", "AccountStorages", [contract_addr, slot_addr])[2:], 16)
            print(f'Bob\'s after ERC20 token: {after_dst_erc20}')
            assert(after_dst_erc20 == ERC_TOKEN_TRANSFER)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    evm_extrinsic_test()
