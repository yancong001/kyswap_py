import os
import math
import web3
import json
import functools
from web3 import Web3
from web3.eth import Contract  # noqa: F401
from web3.types import Address, ChecksumAddress
# from web3.contract import encodeABI
from typing import Union

AddressLike = Union[Address, ChecksumAddress]


def _load_abi(name: str) -> str:
    path = f"{os.path.dirname(os.path.abspath(__file__))}/"
    with open(os.path.abspath(path + f"{name}.abi")) as f:
        abi: str = json.load(f)
    return abi


@functools.lru_cache()
def _load_contract(w3: Web3, abi_name: str, address: AddressLike) -> Contract:
    address = Web3.toChecksumAddress(address)
    return w3.eth.contract(address=address, abi=_load_abi(abi_name))

def _load_contract_erc20(w3: Web3, address: AddressLike) -> Contract:
    return _load_contract(w3, "abi/erc20", address)

def _str_to_addr(s: Union[AddressLike, str]) -> Address:
    """Idempotent"""
    if isinstance(s, str):
        if s.startswith("0x"):
            return Address(bytes.fromhex(s[2:]))
        else:
            raise Exception(f"Couldn't convert string '{s}' to AddressLike")
    else:
        return s

def _addr_to_str(a: AddressLike) -> str:
    if isinstance(a, bytes):
        # Address or ChecksumAddress
        addr: str = Web3.toChecksumAddress("0x" + bytes(a).hex())
        return addr
    elif isinstance(a, str) and a.startswith("0x"):
        addr = Web3.toChecksumAddress(a)
        return addr

def price2tick(price, base_token_decimal=6,quote_token_decimal=18, spacing=60):
    # =========================================================================
    # spcing is different in different fees structures.
    # =========================================================================
    delta_decimal = 10 ** (quote_token_decimal - base_token_decimal)
    x192 = 2 ** 192 / (price / delta_decimal)
    x96 = math.sqrt(x192)
    exact_tick = round(math.log(x96 / 2 ** 96, math.sqrt(1.0001)))
    spaced_tick = exact_tick - exact_tick % spacing
    return spaced_tick

def tick2price(tick, base_token_decimal=6, quote_token_decimal=18):
    if tick < 0:
        tick = -tick
    delta_decimal = 10 ** (quote_token_decimal - base_token_decimal)
    sqrt_x96 = (math.sqrt(1.0001) ** tick) * (2 ** 96)
    price = (2 ** 192) / (sqrt_x96 ** 2) * int(delta_decimal)
    return price


"""
参考了 uniswap-v3-periphery 只能合约里面的 LiquidityAmounts.sol
https://github.com/Uniswap/uniswap-v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol
简化了部分计算，不考虑同时提供两个 amount 的情况，
只实现了根据 base_amount 和价格计算 quote_amount
"""

def _price_to_sqrtx96(price):
    return math.sqrt(price) * (2 ** 96)


def _get_liquidity_for_base_amount(low, high, quote_amount):
    low_x96 = _price_to_sqrtx96(low)
    high_x96 = _price_to_sqrtx96(high)

    if low_x96 > high_x96:
        low_x96, high_x96 = high_x96, low_x96

    return quote_amount * low_x96 * high_x96 / (2 ** 96) / (high_x96 - low_x96)


def _get_base_amount_for_liquidity(low, high, liquidity):
    low_x96 = _price_to_sqrtx96(low)
    high_x96 = _price_to_sqrtx96(high)

    if low_x96 > high_x96:
        low_x96, high_x96 = high_x96, low_x96

    return liquidity * (high_x96 - low_x96) / (2 ** 96)


def compute_base_amount_from_quote_amount(quote_amount, price, low, high):
    if price < low:
        return 0
    if price > high:
        raise Exception('price is high,out of range ')
    l = _get_liquidity_for_base_amount(price, high, quote_amount)
    base_amount = _get_base_amount_for_liquidity(low, price, l)
    return base_amount


# def _diff_test(quote_amount,base_amount,  price, low, high):
#    computed = compute_base_amount_from_quote_amount(quote_amount, price, low, high)
#    print("Expectec {}, got {:0.3f}".format(base_amount, computed))
"""
根据liquidity计算 amount，get position使用
参考了 uniswap-v3-periphery 只能合约里面的 LiquidityAmounts.sol
https://github.com/Uniswap/uniswap-v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol

简化了部分计算，不考虑同时提供两个 amount 的情况，
只实现了根据 base_amount 和价格计算 quote_amount
"""
import math

def price_to_sqrtx96(price):
    return math.sqrt(price) * (2 ** 96)


def get_liquidity_for_base_amount(low, high, base_amount):
    low_x96 = price_to_sqrtx96(low)
    high_x96 = price_to_sqrtx96(high)

    if low_x96 > high_x96:
        low_x96, high_x96 = high_x96, low_x96

    return base_amount * low_x96 * high_x96 / (2 ** 96) / (high_x96 - low_x96)


def get_base_amount_for_liquidity(low, high, liquidity):
    low_x96 = price_to_sqrtx96(low)
    high_x96 = price_to_sqrtx96(high)

    if low_x96 > high_x96:
        low_x96, high_x96 = high_x96, low_x96

    return liquidity * (high_x96 - low_x96) * (2 ** 96) / high_x96 / low_x96


def get_quote_amount_for_liquidity(low, high, liquidity):
    low_x96 = price_to_sqrtx96(low)
    high_x96 = price_to_sqrtx96(high)

    if low_x96 > high_x96:
        low_x96, high_x96 = high_x96, low_x96

    return liquidity * (high_x96 - low_x96) / (2 ** 96)


def get_amounts_for_liquidity(price, low, high, liquidity,base_token_decimal=6,quote_token_decimal=18):
    delta_decimal = 10 ** (quote_token_decimal - base_token_decimal)
    if low > high:
        low, high = high, low
    if price <= low:
        base_computed= get_base_amount_for_liquidity(low, high, liquidity) / delta_decimal
        return base_computed, 0
    elif price <= high:
        base_amount = get_base_amount_for_liquidity(price, high, liquidity) / delta_decimal
        quote_amount = get_quote_amount_for_liquidity(low, price, liquidity) / delta_decimal
        return base_amount, quote_amount
    else:
        quote_computed = get_quote_amount_for_liquidity(low, high, liquidity) / delta_decimal
        return 0, quote_computed


def compute_quote_amount_from_base_amount(base_amount, price, low, high):
    liquidity = get_liquidity_for_base_amount(price, high, base_amount)
    if price <= low:
        return get_base_amount_for_liquidity(low, high, liquidity)
    elif price <= high:
        return get_quote_amount_for_liquidity(low, price, liquidity)
    else:
        return get_quote_amount_for_liquidity(low, high, liquidity)