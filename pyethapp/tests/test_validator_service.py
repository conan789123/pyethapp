from itertools import count
import pytest
import shutil
import tempfile
from devp2p.service import BaseService
from ethereum.config import default_config
from pyethapp.config import update_config_with_defaults, get_default_config
from ethereum.slogging import get_logger, configure_logging
from ethereum.hybrid_casper import chain as hybrid_casper_chain
from ethereum.tools import tester
from ethereum.tests.hybrid_casper.testing_lang import TestLangHybrid
from ethereum.utils import encode_hex
from pyethapp.app import EthApp
from pyethapp.eth_service import ChainService
from pyethapp.db_service import DBService
from pyethapp.accounts import Account, AccountsService
from pyethapp.validator_service import ValidatorService
from pyethapp.pow_service import PoWService

log = get_logger('tests.validator_service')
configure_logging('validator:debug')

class PeerManagerMock(BaseService):
    name = 'peermanager'

    def broadcast(*args, **kwargs):
        pass

@pytest.fixture()
def test_app(request, tmpdir):
    config = {
        'data_dir': str(tmpdir),
        'db': {'implementation': 'EphemDB'},
        'eth': {
            'block': {  # reduced difficulty, increased gas limit, allocations to test accounts
                'GENESIS_DIFFICULTY': 1,
                'BLOCK_DIFF_FACTOR': 2,  # greater than difficulty, thus difficulty is constant
                'GENESIS_GAS_LIMIT': 3141592,
                'GENESIS_INITIAL_ALLOC': {
                    encode_hex(tester.accounts[0]): {'balance': 10**24},
                },
                # Casper FFG stuff
                'EPOCH_LENGTH': 10,
                'WITHDRAWAL_DELAY': 100,
                'BASE_INTEREST_FACTOR': 0.02,
                'BASE_PENALTY_FACTOR': 0.002,
            }
        },
        # 'genesis_data': {},
        # 'jsonrpc': {'listen_port': 29873},
        'validate': [encode_hex(tester.accounts[0])],
    }

    services = [
        DBService,
        # AccountsService,
        ChainService,
        # PoWService,
        PeerManagerMock,
        ValidatorService,
        ]
    update_config_with_defaults(config, get_default_config([EthApp] + services))
    update_config_with_defaults(config, {'eth': {'block': default_config}})
    app = EthApp(config)

    # Add AccountsService first and initialize with coinbase account
    AccountsService.register_with_app(app)
    app.services.accounts.add_account(Account.new('', tester.keys[0]), store=False)

    for service in services:
        service.register_with_app(app)

    return app

def test_generate_valcode(test_app):
    test = TestLangHybrid(5, 25, 0.02, 0.002)
    test.parse('B B')

    # Create a smart chain object: this ties the chain used in the tester
    # to the validator chain.
    test.t.chain = hybrid_casper_chain.Chain(genesis=test.genesis, new_head_cb=test_app.services.validator.on_new_head)
    test_app.services.chain.chain = test.t.chain
    test.parse('B1')

    assert True
