# peaq-bc-test

- [Introduction](#introduction)
- [Preparation](#preparation)
- [Limitation](#limitation)
- [QA](#QA)

# Introduction

This project is used for the integration test on the peaq's parachain/standalone chain. Therefore, several fundamental functionalities tests are included.

# Preparation

1. Install the related library. If you want, you can use the virtual environment to install your libraries.

```
python3 -m venv ~/venv.test
source ~/venv.test/bin/activate
pip3 install -r requirements.txt
```
2. Please run the peaq parachain/standalone on your local machine if you want. You can follow the [parachain-launch](https://github.com/peaqnetwork/parachain-launch) to launch the parachain.
3. Change the related URL in the tools/utils.py.

3.1. Please change the WS URL for the targeted parachain/standalone chain. For example:
```
WS_URL =  'ws://127.0.0.1:9947'
```
3.2. Please change the RPC URL for your targeted parachain/standalone chain.
```
ETH_URL = 'http://127.0.0.1:9936'
```
4. Run the integration test
```
python3 test.py
```

# Limitation
1. In the peaq network, the standalone chain and parachain have different features and parameters; therefore, some tests may not pass, for example, the block creation time test and DID RPC test.
2. This project requires the dependent libraries whose version is higher than 0.9.29 because of the weight structure.
3. In the current implementation, the related account (Alice/Bob/Alice//stash/Bob//stash) should have enough tokens; otherwise, the test cases will fail. It means we can only directly run the integration test for Agung/Krest network in the local environment after we change the genesis settings, but not in the production environment.
4. This project can only test the peaq related chain. If we run for the rococo chain, some runtime errors happen.
5. In the future, we should refine these integration tests.

# QA
1. If you enounter the issue when installing the dependant library
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

Solution: Please install the wheel and reinstall the dependency library again. [Ref](https://stackoverflow.com/questions/34819221/why-is-python-setup-py-saying-invalid-command-bdist-wheel-on-travis-ci)
```
pip3 install wheel
pip3 install -r requirements.txt
```
