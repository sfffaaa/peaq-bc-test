# peaq-bc-test

- [Introduction](#introduction)
- [Preparation](#preparation)
- [Limitation](#limitation)

# Introduction

This project is used for the integration test on the peaq's parachain/standalone chain. Therefore, several fundemental functionilities testings are included.

# Preparation

1. Install the related library. If you want you can use the virtualenv to install your libraries.
```
python3 -m venv ~/venv.test
source ~/venv.test/bin/activate
pip3 install -r requirements.txt
```
Note: if you encounter below errors, you can use another way to solve it.
```
  ERROR: Command errored out with exit status 1:
   command: /home/jaypan/venv.test/bin/python3 -u -c 'import sys, setuptools, tokenize; sys.argv[0] = '"'"'/tmp/pip-install-6gjnxc
vd/parsimonious/setup.py'"'"'; __file__='"'"'/tmp/pip-install-6gjnxcvd/parsimonious/setup.py'"'"';f=getattr(tokenize, '"'"'open'"'
"', open)(__file__);code=f.read().replace('"'"'\r\n'"'"', '"'"'\n'"'"');f.close();exec(compile(code, __file__, '"'"'exec'"'"'))' b
dist_wheel -d /tmp/pip-wheel-dolzicpn
       cwd: /tmp/pip-install-6gjnxcvd/parsimonious/
  Complete output (6 lines):
  usage: setup.py [global_opts] cmd1 [cmd1_opts] [cmd2 [cmd2_opts] ...]
     or: setup.py --help [cmd1 cmd2 ...]                                                                                               or: setup.py --help-commands                                                                                                      or: setup.py cmd --help                                                                                                                                                                                                                                          error: invalid command 'bdist_wheel'
  ----------------------------------------
  ERROR: Failed building wheel for parsimonious
```

Please install the wheel and reinstall the dependency library again. [Ref](https://stackoverflow.com/questions/34819221/why-is-python-setup-py-saying-invalid-command-bdist-wheel-on-travis-ci)
```
pip3 install wheel
pip3 install -r requirements.txt
```
2. If you want, please run the peaq parchain/standalone on your local machine. You can follow the [parachain-launch](https://github.com/peaqnetwork/parachain-launch) to launch the parachain.
3. Change the related URL in the `tools/utils.py`
3.1. Please change the WS URL for the targeted parchain/standalone chain. For example:
```
WS_URL =  'ws://127.0.0.1:9947'
```
3.2. Please change the RPC URL for your targeted parchain/standalone chain
```
ETH_URL = 'http://127.0.0.1:9936'
```
3.3. Please change the Ethereum chain ID for your targeted parachain/standalone chain
```
ETH_CHAIN_ID = PEAQ_DEV_CHAIN_ID
```
4. Run the integration test
```
python3 test.py
```

Note: if you encounter the below error, please follow below way to solve it.

```
Traceback (most recent call last):
  File "test.py", line 18, in <module>
    evm_rpc_test()
  File "/home/jaypan/Work/peaq/peaq-bc-test/tools/two_address_evm_contract_with_rpc.py", line 158, in evm_rpc_test
    call_eth_transfer_a_lot(conn, kp_src, eth_src, kp_eth_src.ss58_address.lower())
  File "/home/jaypan/Work/peaq/peaq-bc-test/tools/two_address_evm_contract_with_rpc.py", line 32, in call_eth_transfer_a_lot
    call = substrate.compose_call(
  File "/home/jaypan/venv.test/lib/python3.8/site-packages/substrateinterface/base.py", line 1566, in compose_call
    call.encode({
  File "/home/jaypan/venv.test/lib/python3.8/site-packages/scalecodec/base.py", line 709, in encode
    self.data = self.process_encode(self.value_serialized)
  File "/home/jaypan/venv.test/lib/python3.8/site-packages/scalecodec/types.py", line 1439, in process_encode
    data += arg_obj.encode(param_value)
  File "/home/jaypan/venv.test/lib/python3.8/site-packages/scalecodec/base.py", line 709, in encode
    self.data = self.process_encode(self.value_serialized)
  File "/home/jaypan/venv.test/lib/python3.8/site-packages/scalecodec/types.py", line 551, in process_encode
    data += element_obj.encode(value[idx])
  File "/home/jaypan/venv.test/lib/python3.8/site-packages/scalecodec/base.py", line 709, in encode
    self.data = self.process_encode(self.value_serialized)
  File "/home/jaypan/venv.test/lib/python3.8/site-packages/scalecodec/types.py", line 1644, in process_encode
    raise ValueError('Given value is not a list')
ValueError: Given value is not a list
```
Solution: Apply this [commit](https://github.com/sfffaaa/py-scale-codec/commit/7da7fbe6c8c0a18fb7b825c12ff37edd206df4b8) to your py-scale-codec python library (/home/jaypan/venv.test/lib/python3.8/site-packages/scalecodec/types.py).

# Limitation
1. In peaq network, the standalone chain and parachain don't have the the same features and parameters, therefore, some tests may not pass, for example, block creation time test and DID RPC test.
2. This project requires the dependent libraries whose version is higher than 0.9.29 because the weight structure.
3. In current implmentation, the related account (Alice/Bob/Alice//stash/Bob//stash) should have enough tokens otherwise, the test cases fail. It means, we cannot run the integration test for Agung/Krest network in the production stage direcly.
4. Not sure why, but this project can only test the peaq related chain. If we run for the rococo chain, some runtime errors happen.
5. In the future, we should refine this integration tests.
