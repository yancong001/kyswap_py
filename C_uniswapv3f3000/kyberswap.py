# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from web3 import Web3, HTTPProvider
from web3.contract import ContractFunction
from typing import Optional, NamedTuple
from web3.types import (
    TxParams,
    Wei,
    Nonce,
    HexBytes,
)
import json
import os
from utils import _str_to_addr, _addr_to_str, tick2price
from constant import MARKET_INFO_DICT


class KyberswapPositionParam(NamedTuple):
    token_id: int
    symbol: str
    israw: bool


class KyberswapRemovePositionParam(NamedTuple):
    token_id: int
    reduce_percent: int
    burn: bool

class KyberswapNewLiquidityParam(NamedTuple):
    symbol: str
    # lowerPrice: float
    # upperPrice: float
    tickLower: float
    tickUpper: float
    base_amountDesired: float
    quote_amountDesired: float
    base_amountMin: float
    quote_amountMin: float


FeeTier = 3000

class Kyberswapv3f3000ApiTrade():
    UNI_V3_ROUTER_ADDRESS = _str_to_addr("0xF9c2b5746c946EF883ab2660BbbB1f10A5bdeAb4")
    UNI_V3_FACTORY_ADDRESS = _str_to_addr("0xC7a590291e07B9fe9E64b86c58fD8fC764308C4A")
    UNIS_V3_NFT_MANAGER_ADDRESS = _str_to_addr("0x2b1c7b41f6a8f2b2bc45c3233a5d5fb3cd6dc9a8")

    def __init__(self,
                 pub_key,
                 secret_key: str,
                 loop=None,
                 uniswapv3_rpc_url=None
                 ):
        self.provider = uniswapv3_rpc_url
        self.market_info_map = MARKET_INFO_DICT['uniswapv3']
        self.V3_Factory_ABI = json.load(
            open(os.path.abspath(f"{os.path.dirname(os.path.abspath(__file__))}/abi/" + "UniswapV3Factory.json")))[
            "abi"]
        self.V3_NFT_Manager_ABI = json.load(
            open(os.path.abspath(
                f"{os.path.dirname(os.path.abspath(__file__))}/abi/" + "NonfungiblePositionManager.json")))
        self.V3_ROUTER_ABI = json.load(
            open(os.path.abspath(
                f"{os.path.dirname(os.path.abspath(__file__))}/abi/" + "SwapRouter.json")))[
            "abi"]
        self.V3_POOL_ABI = json.load(
            open(os.path.abspath(
                f"{os.path.dirname(os.path.abspath(__file__))}/abi/" + "UniswapV3Pool.json")))[
            "abi"]

        self.address = Web3.toChecksumAddress(pub_key)
        self.wallet_private_key = secret_key
        self.sync_w3 = Web3(
            Web3.HTTPProvider(self.provider),
        )
        self.w3 = Web3(HTTPProvider(self.provider))
        self.last_nonce: Nonce = self.sync_w3.eth.get_transaction_count(self.address)
        self.router_address = self.UNI_V3_ROUTER_ADDRESS
        self.v3_factory = self.sync_w3.eth.contract(address=self.UNI_V3_FACTORY_ADDRESS, abi=self.V3_Factory_ABI)
        self.v3_nft_manager = self.sync_w3.eth.contract(address=self.UNIS_V3_NFT_MANAGER_ADDRESS,
                                                        abi=self.V3_NFT_Manager_ABI)
        self.max_approval_hex = f"0x{64 * 'f'}"
        self.max_approval_int = int(self.max_approval_hex, 16)
        self.max_128_int = int(f"0x{32 * 'f'}", 16)

    # # 同步等返回结果，可先不返回结果，返回txhash
    # def approve_uniswap_spender(self, coin: str):
    #     """
    #     Approves Uniswap contract as a spender for a token.
    #     """
    #     # coin = param.coin
    #     token_addr = self.market_info_map.get(coin)['id']
    #     max_approval = self.max_approval_int
    #     contract_addr = self.UNIS_V3_NFT_MANAGER_ADDRESS
    #     function = _load_contract_erc20(self.sync_w3, token_addr).functions.approve(
    #         contract_addr, max_approval
    #     )
    #     tx = self._build_and_send_tx(function)
    #     ret = {
    #         'txn_hash': tx.hex(),
    #         'coin': coin,
    #         'approval': max_approval,
    #     }
    #     return ret
    #
    # def query_allowance(self, coin: str):
    #     # coin = param.coin
    #     token_addr = self.market_info_map.get(coin)['id']
    #     contract_addr = self.UNIS_V3_NFT_MANAGER_ADDRESS
    #     txn_params = _load_contract_erc20(self.sync_w3, token_addr)._prepare_transaction(
    #         fn_name='allowance',
    #         fn_args=(self.address, contract_addr),
    #         transaction={'from': self.address, 'to': token_addr}
    #     )
    #     call_result = self.w3.eth.call(txn_params)
    #     result = self.w3.codec.decode_single('uint256', call_result)
    #     return result

    def query_get_position(self, param: KyberswapPositionParam):
        symbol, token_id, israw = param.symbol, param.token_id, param.israw
        base_coin = symbol.split('_')[0].upper()
        quote_coin = symbol.split('_')[1].upper()

        base_token_decimal = self.market_info_map.get(base_coin)['decimals']
        quote_token_decimal = self.market_info_map.get(quote_coin)['decimals']
        address = self.market_info_map.get(symbol)['id']
        symbol_pool_address = Web3.toChecksumAddress(address)
        print(111)
        position_info = self._query_get_lp_position(token_id)
        try:
            poolId = position_info[0][2]
            # feetier = position_info[4]
            tickLower = position_info[0][3]
            tickUpper = position_info[0][4]
            liquidity = position_info[0][5]
            rTokenOwed = position_info[0][6]
            feeGrowthInsideLast = position_info[0][7]

            token0 = position_info[1][0]
            fee = position_info[1][1]
            token1 = position_info[1][2]
            print(tickUpper, base_token_decimal, quote_token_decimal)
            lowerPrice = tick2price(tickUpper, base_token_decimal, quote_token_decimal)
            upperPrice = tick2price(tickLower, base_token_decimal, quote_token_decimal)
            # quote_computed, base_computed = get_amounts_for_liquidity(quote_token_price, lowerPrice, upperPrice, liquidity)
            # if not israw:
            #     base_token_fee_amout, quote_token_fee_amount, _base_coin, _quote_coin = self._query_get_collect_fee(
            #         param)
            #     base_computed = base_computed + base_token_fee_amout
            #     quote_computed = quote_computed + quote_token_fee_amount
            result = {
                'poolId': poolId,
                'base_coin': base_coin,
                'quote_coin': quote_coin,
                # 'base_amount': base_computed,
                # 'quote_amount': quote_computed,
                'lowerPrice': lowerPrice,
                'upperPrice': upperPrice,
                'liquidity': liquidity,
                'rTokenOwed': rTokenOwed,
                'token0': token0,
                'fee': fee,
                'token1': token1,
                'feeGrowthInsideLast': feeGrowthInsideLast,
                'symbol_pool_address': symbol_pool_address
            }
            print(result)
            return result
        except Exception as e:
            print(e)
            print(position_info)
            return position_info

    def _query_get_lp_position(self, token_id):
        positions_info = self.v3_nft_manager.functions.positions(token_id).call()
        print(positions_info)
        return positions_info

    # def sync_query_get_lp_position(self, token_id):
    #     # txn_params = self.v3_nft_manager._prepare_transaction(fn_name='positions',
    #     #                                                       fn_args=(token_id,),
    #     #                                                       transaction={'from': self.address,
    #     #                                                                    'to': self.UNIS_V3_NFT_MANAGER_ADDRESS})
    #     # call_result = self.w3.eth.call(txn_params)
    #     # positions_info = self.w3.codec.decode_single(
    #     #     '(uint96,address,address,address,uint24,int24,int24,uint128,uint256,uint256,uint128,uint128)', call_result)
    #     print(token_id)
    #     positions_info = self.v3_nft_manager.functions.positions(1835).call()
    #     print(positions_info)
    #     return positions_info
    #
    # def _query_get_pool_address(self, symbol, fee_tier=FeeTier):
    #     base_coin = symbol.split('_')[0].upper()
    #     quote_coin = symbol.split('_')[1].upper()
    #     base_token_addr = self.market_info_map.get(base_coin)['id']
    #     quote_token_addr = self.market_info_map.get(quote_coin)['id']
    #     txn_params = self.v3_factory._prepare_transaction(fn_name='getPool',
    #                                                       fn_args=(base_token_addr, quote_token_addr, fee_tier),
    #                                                       transaction={'from': self.address,
    #                                                                    'to': self.UNI_V3_FACTORY_ADDRESS})
    #     call_result = self.w3.eth.call(txn_params)
    #     pool_address = self.w3.codec.decode_single('address', call_result)
    #     return pool_address


    # slippageTolerance not used,
    def add_position(self, param: KyberswapNewLiquidityParam):
        symbol = param.symbol
        quote_amountDesired = param.quote_amountDesired
        # lowerPrice = param.lowerPrice
        # upperPrice = param.upperPrice
        tickLower = param.tickLower
        tickUpper = param.tickUpper
        base_amountDesired = param.base_amountDesired
        base_amountMin = param.base_amountMin
        quote_amountMin = param.quote_amountMin

        deadline = int(time.time() + 10 ** 3)
        fee = self.market_info_map.get(symbol)['feeTier']
        base_coin = symbol.split('_')[0].upper()
        quote_coin = symbol.split('_')[1].upper()
        address = self.market_info_map.get(symbol)['id']
        # symbol_pool_address = Web3.toChecksumAddress(address)
        recipient = self.address
        base_token_addr = Web3.toChecksumAddress(self.market_info_map.get(base_coin)['id'])

        quote_token_addr = Web3.toChecksumAddress(self.market_info_map.get(quote_coin)['id'])
        base_token_decimal = self.market_info_map.get(base_coin)['decimals']
        quote_token_decimal = self.market_info_map.get(quote_coin)['decimals']
        # tickLower = price2tick(upperPrice, base_token_decimal=base_token_decimal,
        #                        quote_token_decimal=quote_token_decimal)
        # tickUpper = price2tick(lowerPrice, base_token_decimal=base_token_decimal,
        #                        quote_token_decimal=quote_token_decimal)
        # if not base_amountDesired:
        #     base_amountDesired = compute_base_amount_from_quote_amount(quote_amountDesired, price=quote_token_price,
        #                                                                low=lowerPrice,
        #                                                                high=upperPrice)
        base_amountDesired = int(base_amountDesired * 10 ** base_token_decimal)
        quote_amountDesired = int(quote_amountDesired * 10 ** quote_token_decimal)
        ticksPrevious = [tickLower, tickUpper]
        args = ((base_token_addr, quote_token_addr, fee, tickLower, tickUpper, ticksPrevious, base_amountDesired,
                 quote_amountDesired,
                 base_amountMin, quote_amountMin, recipient, deadline),)
        print(args)
        hex_str = self.v3_nft_manager.encodeABI("mint", args=args)
        refund_hex_str = self.v3_nft_manager.encodeABI("refundEth")
        result = self.v3_nft_manager.functions.multicall([hex_str, refund_hex_str])
        if Web3.toChecksumAddress(base_token_addr) == Web3.toChecksumAddress(self.market_info_map['ETH']['id']):
            value = base_amountDesired
        elif Web3.toChecksumAddress(quote_token_addr) == Web3.toChecksumAddress(self.market_info_map['ETH']['id']):
            value = quote_amountDesired
        else:
            value = 0
        current_nonce = self.w3.eth.get_transaction_count(self.address)
        tx_patams = {
            "from": _addr_to_str(self.address),
            "value": value,
            # "gas": Wei(880000),
            # "gasPrice": self.w3.toWei(12,"gwei"), gasPrice不填默认使用全网平均价
            "nonce": max(self.last_nonce, current_nonce)
        }
        tx = self._build_and_send_tx(result, tx_patams)
        increase_result = {
            'txn_hash': tx.hex(),
            'ori_base_amount': base_amountDesired / 10 ** base_token_decimal,
            'ori_quote_amount': quote_amountDesired / 10 ** quote_token_decimal,
            'tickLower': tickLower,
            'tickUpper': tickUpper,
            'ticksPrevious': [tickLower, tickUpper],
            # 'lowerPrice': lowerPrice,
            # 'upperPrice': upperPrice,
        }
        return increase_result

    def remove_position(self, param: KyberswapRemovePositionParam):
        token_id, reduce_percent, burn = param.token_id, param.reduce_percent, param.burn
        multicall_list = []
        position_info = self._query_get_lp_position(token_id)
        # [0, '0x0000000000000000000000000000000000000000', '0x07865c6E87B9F70255377e024ace6630C1Eaa37F', '0xc778417E063141139Fce010982780140Aa0cD5Ab', 3000, 197880, 198600, 447150632383970, 0, 0, 0, 0]
        liquidity = int(position_info[0][5] * reduce_percent * 0.01)
        base_token = Web3.toChecksumAddress(position_info[1][0])
        quote_token = Web3.toChecksumAddress(position_info[1][2])
        base_amountMin = 0
        quote_amountMin = 0
        collect_base_amountMax = self.max_128_int
        collect_quote_amountMax = self.max_128_int
        deadline = int(time.time() + 10 ** 3)
        decrease_params = ((token_id, liquidity, base_amountMin, quote_amountMin, deadline),)
        dec_hex_str = self.v3_nft_manager.encodeABI("removeLiquidity", args=decrease_params)
        multicall_list.append(dec_hex_str)

        if base_token == Web3.toChecksumAddress(self.market_info_map['ETH']['id']):
            unwrapWeth_params = (0, self.address)
            unwrap_hex_str = self.v3_nft_manager.encodeABI("unwrapWeth", args=unwrapWeth_params)
            multicall_list.append(unwrap_hex_str)
        elif quote_token == Web3.toChecksumAddress(self.market_info_map['ETH']['id']):
            unwrapWeth_params = (0, self.address)
            unwrap_hex_str = self.v3_nft_manager.encodeABI("unwrapWeth", args=unwrapWeth_params)
            multicall_list.append(unwrap_hex_str)
        else:
            pass
        if burn:
            burn_hex_str = self.v3_nft_manager.encodeABI("burn", args=(token_id,))
            multicall_list.append(burn_hex_str)
        result = self.v3_nft_manager.functions.multicall(multicall_list)
        current_nonce = self.w3.eth.get_transaction_count(self.address)

        tx_patams = {
            "from": _addr_to_str(self.address),
            "value": 0,
            "gas": Wei(22500),
            # "gasPrice": self.w3.toWei(88,"gwei"), #gasPrice不填默认使用全网平均价
            "nonce": max(self.last_nonce, current_nonce)
        }
        tx = self._build_and_send_tx(result, tx_patams)
        print(tx)
        remove_result = {
            'txn_hash': tx.hex(),
            'token_id': token_id,
            'remove_liquidity': liquidity,
        }
        return remove_result

    def _get_tx_params(self, value: Wei = Wei(0), gas: Wei = Wei(25000)) -> TxParams:
        """Get generic transaction parameters."""
        current_nonce = self.w3.eth.get_transaction_count(self.address)

        return {
            "from": _addr_to_str(self.address),
            "value": value,
            "gas": gas,
            # "gasPrice": self.w3.toWei(12,"gwei"),
            "nonce": max(self.last_nonce, current_nonce)
        }

    def _build_and_send_tx(
            self, function: ContractFunction, tx_params: Optional[TxParams] = None
    ) -> HexBytes:
        """Build and send a transaction."""
        if not tx_params:
            tx_params = self._get_tx_params()
        transaction = function.buildTransaction(tx_params)
        # transaction['gas'] = self.sync_w3.eth.estimateGas(transaction)
        signed_txn = self.sync_w3.eth.account.sign_transaction(
            transaction, private_key=self.wallet_private_key
        )
        # TODO: This needs to get more complicated if we want to support replacing a transaction
        # FIXME: This does not play nice if transactions are sent from other places using the same wallet.
        try:
            return self.sync_w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        finally:
            self.last_nonce = Nonce(tx_params["nonce"] + 1)


if __name__ == '__main__':
    RPC_URL = 'https://mainnet.infura.io/v3/2e9062cf4c124537a722b068f2f40a0a'
    PUB_KEY = ""
    SECRET_KEY = ""

    uni_cli = Kyberswapv3f3000ApiTrade(
        pub_key=PUB_KEY,
        secret_key=SECRET_KEY,
        uniswapv3_rpc_url=RPC_URL
    )
    result2 = uni_cli.query_get_position(KyberswapPositionParam(token_id=75, symbol='ETH_USDT', israw=False))
    # result2 = uni_cli.remove_position(KyberswapRemovePositionParam(token_id=75, reduce_percent=100, burn=False))
    # result2 = uni_cli.add_position(KyberswapNewLiquidityParam(
    #     symbol="ETH_USDT",
    #     tickLower=276323,
    #     tickUpper=276343,
    #     base_amountDesired=0,
    #     quote_amountDesired=0,
    #     base_amountMin=0,
    #     quote_amountMin=0,
    # ))
    print(result2)

    ## (0, '0x0000000000000000000000000000000000000000', '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', 3000, 200520, 201060, 0, 64697891706152575323693699827833, 33865331492154463223057000400683994853434, 0, 0)
    ## (0, '0x0000000000000000000000000000000000000000', '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', 3000, 200520, 201060, 0, 64697891706152575323693699827833, 33865331492154463223057000400683994853434, 0, 0)
    # [(0, '0x0000000000000000000000000000000000000000', 17, 276332, 276338, 0, 0, 315643686027589165627), ('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 8, '0xC285B7E09A4584D027E5BC36571785B515898246')]
# [(0, '0x0000000000000000000000000000000000000000', 17, 276323, 276343, 0, 0, 2055808673850439898745), ('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 8, '0xC285B7E09A4584D027E5BC36571785B515898246')]
# [(0, '0x0000000000000000000000000000000000000000', 1, -208380, -200460, 0, 0, 17858837545992315384617258), ('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 300, '0xdAC17F958D2ee523a2206206994597C13D831ec7')]
# {'poolId': 17, 'base_coin': 'ETH', 'quote_coin': 'USDT', 'lowerPrice': 0.0, 'upperPrice': 0.0, 'liquidity': 0, 'rTokenOwed': 0, 'token0': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 'fee': 8, 'token1': '0xC285B7E09A4584D027E5BC36571785B515898246', 'feeGrowthInsideLast': 2055808673850439898745, 'symbol_pool_address': '0xF138462C76568CDFD77C6EB831E973D6963F2006'}
