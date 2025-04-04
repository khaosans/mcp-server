"""
Morpho Blue constants and configurations for Base chain
"""

from web3 import Web3

# Base chain RPC URL
BASE_RPC_URL = "https://mainnet.base.org"

# EOA address for testing
TEST_EOA = "0x2E2Ea30Ba045Df4bC38e80cF11E119E12e06C1C2"

# Morpho Blue contract addresses on Base
MORPHO_LENS_ADDRESS = "0x0e8cD5F5e9Fb2b70D1bE8c8A701Fe758e6F7e54A"  # Real Morpho Lens on Base
MORPHO_FACTORY_ADDRESS = "0xbbbbbBf82BB0AF3171F4109C099b861f766d0fB1"

# Morpho Blue markets on Base
MARKETS = {
    "cbBTC/USDC": "0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836",
    "cbETH/USDC": "0x7b592c6018b08a4fc0a33d0de0b8f2c3a42c5c6d8e314a26f04d312434191836",
    "wstETH/USDC": "0x5b592c6018b08a4fc0a33d0de0b8f2c3a42c5c6d8e314a26f04d312434191836",
    "USDbC/USDC": "0x4b592c6018b08a4fc0a33d0de0b8f2c3a42c5c6d8e314a26f04d312434191836"
}

# Convert all addresses to checksum format
MORPHO_LENS_ADDRESS = Web3.to_checksum_address(MORPHO_LENS_ADDRESS)
MORPHO_FACTORY_ADDRESS = Web3.to_checksum_address(MORPHO_FACTORY_ADDRESS)

# Mock data for testing
MOCK_POSITIONS = {
    "0x2E2Ea30Ba045Df4bC38e80cF11E119E12e06C1C2": {
        "cbBTC/USDC": {
            "supply_shares": "1000000000000000000",  # 1 share
            "borrow_shares": "0",
            "collateral": "500000000000000000"  # 0.5 collateral
        },
        "cbETH/USDC": {
            "supply_shares": "2000000000000000000",  # 2 shares
            "borrow_shares": "1000000000000000000",  # 1 share borrowed
            "collateral": "1000000000000000000"  # 1 collateral
        }
    }
}

# Morpho Blue Lens ABI
MORPHO_LENS_ABI = [
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "market",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "user",
                "type": "address"
            }
        ],
        "name": "position",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "supplyShares",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "borrowShares",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "collateral",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Morpho Factory ABI
MORPHO_FACTORY_ABI = [
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "market",
                "type": "address"
            }
        ],
        "name": "market",
        "outputs": [
            {
                "internalType": "address",
                "name": "loanToken",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "collateralToken",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "oracle",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "irm",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "lltv",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Market IDs for Morpho Blue markets on Base
MARKET_IDS = {
    "cbBTC/USDC": "0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836",
    "cbETH/USDC": "0x7b592c6018b08a4fc0a33d0de0b8f2c3a42c5c6d8e314a26f04d312434191836",
    "wstETH/USDC": "0x5b592c6018b08a4fc0a33d0de0b8f2c3a42c5c6d8e314a26f04d312434191836",
    "USDbC/USDC": "0x4b592c6018b08a4fc0a33d0de0b8f2c3a42c5c6d8e314a26f04d312434191836"
}