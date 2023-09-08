from web3.net import (
	AsyncNet,
	Net,
)
from web3.eth import AsyncEth, Eth
from web3.geth import (
	Geth,
	GethAdmin,
	GethMiner,
	GethPersonal,
	GethTxPool,
)
from web3.parity import (
	Parity,
	ParityPersonal,
)
from web3.version import (
	Version,
)
from web3.testing import (
	Testing,
)
from web3.manager import (
	RequestManager as DefaultRequestManager,
)
from web3.middleware import (
	abi_middleware,
	attrdict_middleware,
	buffered_gas_estimate_middleware,
	gas_price_strategy_middleware,
	name_to_address_middleware,
	pythonic_middleware,
	request_parameter_normalizer,
	validation_middleware,
	async_buffered_gas_estimate_middleware
)

web3_module = {
	"eth": (AsyncEth,),
	"net": (AsyncNet,),
	"version": (Version,),
	"parity": (Parity, {
		"personal": (ParityPersonal,),
	}),
	"geth": (Geth, {
		"admin": (GethAdmin,),
		"miner": (GethMiner,),
		"personal": (GethPersonal,),
		"txpool": (GethTxPool,),
	}),
	"testing": (Testing,),
}


def _async_request_manager_middlewares(web3):
	async_request_manager_middlewares = [
		(request_parameter_normalizer, 'request_param_normalizer'),  # Delete
		(gas_price_strategy_middleware, 'gas_price_strategy'),  # Add Async
		(name_to_address_middleware(web3), 'name_to_address'),  # Add Async
		(attrdict_middleware, 'attrdict'),  # Delete
		(pythonic_middleware, 'pythonic'),  # Delete
		(validation_middleware, 'validation'),  # Add async
		(abi_middleware, 'abi'),  # Delete
		(async_buffered_gas_estimate_middleware, 'gas_estimate'),
	]
	return async_request_manager_middlewares


async_request_manager_middlewares = [
	(async_buffered_gas_estimate_middleware, 'gas_estimate'),
]

class Async_ETH(Eth):
	is_async = True

_only_send_raw_transaction_web3_module = {
	"eth": (Async_ETH,),
	"net": (Net,),
	"version": (Version,),
	"parity": (Parity, {
		"personal": (ParityPersonal,),
	}),
	"geth": (Geth, {
		"admin": (GethAdmin,),
		"miner": (GethMiner,),
		"personal": (GethPersonal,),
		"txpool": (GethTxPool,),
	}),
	"testing": (Testing,),
}
