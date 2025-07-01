# nama file: bot.py (MODIFIED v2)

import time
import random
import requests
import json
import concurrent.futures
from web3 import Web3
from web3.exceptions import TransactionNotFound
from eth_account import Account
from eth_account.messages import encode_defunct
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from datetime import datetime, timedelta
from rich.live import Live
from rich.text import Text

# --- KONFIGURASI ---
class Config:
    PRIVATE_KEY_FILE = "privatekey.txt"
    RPC_URL = "https://testnet.dplabs-internal.com/"
    # SESUAIKAN JUMLAH THREADS (PEKERJA SIMULTAN)
    MAX_THREADS = 3 # Direkomendasikan 3-5 untuk menghindari error RPC

    class Zenith:
        SWAP_ENABLED = True
        LIQUIDITY_ENABLED = True
        ROUTER_ADDRESS = "0x1a4de519154ae51200b0ad7c90f7fac75547888a"
        POSITION_MANAGER_ADDRESS = "0xf8a1d4ff0f9b9af7ce58e1fc1833688f3bfd6115"
        WPHRS_ADDRESS = "0x76aaada469d23216be5f7c596fa25f282ff9b364"
        TARGET_TOKEN_ADDRESS = "0xd4071393f8716661958f766df660033b3d35fd29"
        FEE_TIER = 3000
        SWAP_AMOUNT_PHRS = (0.001, 0.002)
        LIQUIDITY_AMOUNT_PHRS = (0.001, 0.0015)
        TICK_SPACING = 60

    class FaroSwap:
        ENABLED = True
        ROUTER_ADDRESS = "0x3541423f25A1Ca5C98fdBCf478405d3f0aaD1164"
        USDT_ADDRESS = "0xD4071393f8716661958F766DF660033b3d35fD29"
        AMOUNT_TO_SWAP = (0.001, 0.0015)

    class Timers:
        DELAY_BETWEEN_ACTIONS = (15, 30)
        DELAY_FOR_NEXT_RUN_HOURS = 24

    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Referer": "https://testnet.pharosnetwork.xyz/"
    }
# --- AKHIR KONFIGURASI ---

console = Console()

# --- Fungsi API Pharos (Login, Info, Check-in, Faucet) ---

def perform_login(account):
    """Mencoba login dan mengembalikan JWT token jika berhasil."""
    login_url = "https://api.pharosnetwork.xyz/user/login"
    message_to_sign = encode_defunct(text="pharos")
    signed_message = account.sign_message(message_to_sign)
    params = {
        "address": account.address,
        "signature": signed_message.signature.hex(),
        "wallet": "OKX Wallet",
        "invite_code": "S6NGMzXSCDBxhnwo"
    }
    headers = Config.BASE_HEADERS.copy()
    try:
        response = requests.post(login_url, params=params, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("jwt")
    except requests.exceptions.RequestException:
        pass
    console.print(f"({account.address[:6]}) [bold red]❌ Gagal Login. Melewati akun ini.[/bold red]")
    return None

def get_user_info(address, jwt_token):
    """Mengambil dan menampilkan balance poin pengguna."""
    info_url = f"https://api.pharosnetwork.xyz/api/user/info?address={address}"
    headers = Config.BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {jwt_token}"
    try:
        response = requests.get(info_url, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                points = data.get("data", {}).get("points", 0)
                console.print(f"[    | Balance    : [bold cyan]{points} PTS[/bold cyan]")
                return
    except requests.exceptions.RequestException:
        pass
    console.print("[    | Balance    : [bold red]Gagal mengambil data[/bold red]")


def perform_daily_signin(address, jwt_token):
    """Melakukan check-in harian dan menampilkan statusnya."""
    signin_url = f"https://api.pharosnetwork.xyz/sign/in?address={address}"
    headers = Config.BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {jwt_token}"
    try:
        response = requests.post(signin_url, headers=headers, timeout=20)
        data = response.json()
        msg = data.get("msg", "").lower()
        if "already" in msg:
            console.print("[    | Check-In   : [bold yellow]Already Claimed[/bold yellow]")
        elif data.get("code") == 0:
            console.print("[    | Check-In   : [bold green]Claimed Successfully[/bold green]")
        else:
            console.print(f"[    | Check-In   : [bold red]Claim Failed: {msg}[/bold red]")
    except requests.exceptions.RequestException:
        console.print("[    | Check-In   : [bold red]Gagal terhubung ke server[/bold red]")

def claim_faucet(address, jwt_token):
    """Mengklaim faucet dan menampilkan statusnya."""
    faucet_url = f"https://api.pharosnetwork.xyz/api/faucet/claim?address={address}"
    headers = Config.BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {jwt_token}"
    try:
        response = requests.post(faucet_url, headers=headers, timeout=20)
        data = response.json()
        msg = data.get("msg", "").lower()

        if "claimed" in msg or "wait" in msg:
            try:
                # Mencoba ekstrak waktu dari pesan "you have claimed ... available at: 2025-06-24 02:27:44"
                available_at_str = msg.split("available at: ")[1]
                available_dt = datetime.strptime(available_at_str, "%Y-%m-%d %H:%M:%S")
                # Konversi ke format yang diinginkan (dd/mm/yy HH:MM:SS)
                formatted_time = available_dt.strftime("%m/%d/%y %H:%M:%S")
                text = Text("Already Claimed", style="yellow")
                text.append(f" - Available at: {formatted_time} WIB", style="default")
                console.print(f"[    | Faucet     : ", text)
            except (IndexError, ValueError):
                console.print("[    | Faucet     : [bold yellow]Already Claimed[/bold yellow]")

        elif data.get("code") == 0:
            console.print("[    | Faucet     : [bold green]Claimed Successfully[/bold green]")
        else:
             console.print(f"[    | Faucet     : [bold red]Claim Failed: {msg}[/bold red]")
    except requests.exceptions.RequestException:
        console.print("[    | Faucet     : [bold red]Gagal terhubung ke server[/bold red]")


# --- Fungsi Web3 & Helper (tidak banyak berubah) ---
# ... (Semua fungsi lain seperti `wait_for_transaction`, `approve_token`, `perform_swap`, `add_liquidity`, dll tetap ada di sini) ...
ERC20_ABI = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"success","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
ZENITH_V3_POOL_ABI = json.loads('[{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"}]')

def get_gas_price(w3): return w3.eth.gas_price
def get_nonce(w3, address): return w3.eth.get_transaction_count(address)
def load_json_file(file_path):
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[bold red]❌ Gagal memuat file {file_path}: {e}[/bold red]")
        return None

def wait_for_transaction(w3, tx_hash, action_name, address):
    console.print(f"[yellow]   ({address[:6]}) ⏳ Menunggu transaksi '{action_name}'... ({tx_hash.hex()})[/yellow]")
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        if receipt['status'] == 1:
            console.print(f"[bold green]   ({address[:6]}) ✅ Transaksi '{action_name}' Berhasil![/bold green]")
            return receipt
        else:
            console.print(f"[bold red]   ({address[:6]}) ❌ Transaksi '{action_name}' Gagal (Reverted).[/bold red]")
            return None
    except Exception as e:
        console.print(f"[bold red]   ({address[:6]}) ❌ Error saat menunggu transaksi '{action_name}': {e}[/bold red]")
        return None

def approve_token(account, w3, token_address, spender_address, amount):
    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
    try:
        allowance = token_contract.functions.allowance(account.address, spender_address).call()
        if allowance >= amount:
            console.print(f"[green]      ({account.address[:6]}) ✅ Approval sudah cukup untuk {token_address[:8]}...[/green]")
            return True
        tx = token_contract.functions.approve(spender_address, amount).build_transaction({
            'from': account.address, 'gas': 100000, 'gasPrice': get_gas_price(w3), 'nonce': get_nonce(w3, account.address)
        })
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        wait_for_transaction(w3, tx_hash, "Approve", account.address)
        return True
    except Exception as e:
        console.print(f"[bold red]      ({account.address[:6]}) ❌ Gagal melakukan approval: {e}[/bold red]")
        return False

def get_current_tick(w3, pool_address):
    pool_contract = w3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=ZENITH_V3_POOL_ABI)
    slot0 = pool_contract.functions.slot0().call()
    return slot0[1]

def perform_swap(account, w3, dex_abi, router_address, token_in, token_out, amount_in_wei, is_native=False):
    console.print(f"[cyan]   ({account.address[:6]}) 🔄 Melakukan swap {Web3.from_wei(amount_in_wei, 'ether'):.6f} token...[/cyan]")
    router_contract = w3.eth.contract(address=Web3.to_checksum_address(router_address), abi=dex_abi)
    params = {'tokenIn': Web3.to_checksum_address(token_in), 'tokenOut': Web3.to_checksum_address(token_out), 'fee': Config.Zenith.FEE_TIER, 'recipient': account.address, 'deadline': int(time.time()) + 20 * 60, 'amountIn': amount_in_wei, 'amountOutMinimum': 0, 'sqrtPriceLimitX96': 0}
    try:
        tx_params = {'from': account.address, 'gas': 500000, 'nonce': get_nonce(w3, account.address), 'gasPrice': get_gas_price(w3)}
        if is_native: tx_params['value'] = amount_in_wei
        tx = router_contract.functions.exactInputSingle(params).build_transaction(tx_params)
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return wait_for_transaction(w3, tx_hash, "Swap", account.address) is not None
    except Exception as e:
        console.print(f"[bold red]   ({account.address[:6]}) ❌ Error saat swap: {e}[/bold red]")
        return False

def add_liquidity(account, w3, dex_abi, manager_address, token0, token1, amount0, amount1):
    console.print(f"[cyan]   ({account.address[:6]}) 💧 Menambah likuiditas...[/cyan]")
    manager_contract = w3.eth.contract(address=Web3.to_checksum_address(manager_address), abi=dex_abi)
    if token0.lower() > token1.lower():
        token0, token1, amount0, amount1 = token1, token0, amount1, amount0
    factory_address = manager_contract.functions.factory().call()
    factory_abi = '[{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"}],"name":"getPool","outputs":[{"internalType":"address","name":"pool","type":"address"}],"stateMutability":"view","type":"function"}]'
    factory_contract = w3.eth.contract(address=factory_address, abi=factory_abi)
    pool_address = factory_contract.functions.getPool(Web3.to_checksum_address(token0), Web3.to_checksum_address(token1), Config.Zenith.FEE_TIER).call()
    if pool_address == '0x0000000000000000000000000000000000000000':
        console.print(f"[bold red]   ({account.address[:6]}) ❌ Pool tidak ditemukan![/bold red]")
        return False
    current_tick = get_current_tick(w3, pool_address)
    tick_lower = (current_tick // Config.Zenith.TICK_SPACING) * Config.Zenith.TICK_SPACING
    tick_upper = tick_lower + Config.Zenith.TICK_SPACING
    mint_params = {'token0': Web3.to_checksum_address(token0), 'token1': Web3.to_checksum_address(token1), 'fee': Config.Zenith.FEE_TIER, 'tickLower': tick_lower, 'tickUpper': tick_upper, 'amount0Desired': amount0, 'amount1Desired': amount1, 'amount0Min': 0, 'amount1Min': 0, 'recipient': account.address, 'deadline': int(time.time()) + 20 * 60}
    try:
        console.print(f"      ({account.address[:6]}) Menyiapkan approval untuk likuiditas...")
        approve_token(account, w3, token0, manager_address, amount0)
        time.sleep(random.uniform(3, 5))
        approve_token(account, w3, token1, manager_address, amount1)
        time.sleep(random.uniform(*Config.Timers.DELAY_BETWEEN_ACTIONS))
        tx = manager_contract.functions.mint(mint_params).build_transaction({'from': account.address, 'gas': 800000, 'nonce': get_nonce(w3, account.address), 'gasPrice': get_gas_price(w3)})
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return wait_for_transaction(w3, tx_hash, "Add Liquidity (Mint)", account.address) is not None
    except Exception as e:
        console.print(f"[bold red]   ({account.address[:6]}) ❌ Gagal menambah likuiditas: {e}[/bold red]")
        return False

def get_token_balance(w3, token_address, owner_address):
    try:
        token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        return token_contract.functions.balanceOf(owner_address).call()
    except Exception: return 0

# --- Fungsi Utama ---

def process_account(private_key, index, total, w3, dex_abi):
    """Alur kerja utama untuk setiap akun."""
    try:
        account = Account.from_key(private_key)
        console.print(Rule(f"[bold]Memproses Akun {index}/{total} | {account.address}[/bold]"))
    except Exception:
        console.print(f"[bold red]❌ Private key [Akun {index}] tidak valid.[/bold red]")
        return

    # 1. Login dan klaim harian
    jwt_token = perform_login(account)
    if not jwt_token:
        return # Jika login gagal, hentikan proses untuk akun ini

    get_user_info(account.address, jwt_token)
    perform_daily_signin(account.address, jwt_token)
    claim_faucet(account.address, jwt_token)
    time.sleep(2) # Jeda singkat setelah klaim

    # 2. Aksi di Zenith DEX
    if Config.Zenith.SWAP_ENABLED or Config.Zenith.LIQUIDITY_ENABLED:
        console.print(Rule(f"[bold magenta]💲 ZENITH DEX[/bold magenta]", style="magenta"))
        if Config.Zenith.SWAP_ENABLED:
            amount_to_swap = w3.to_wei(random.uniform(*Config.Zenith.SWAP_AMOUNT_PHRS), 'ether')
            perform_swap(account, w3, dex_abi, Config.Zenith.ROUTER_ADDRESS, Config.Zenith.WPHRS_ADDRESS, Config.Zenith.TARGET_TOKEN_ADDRESS, amount_to_swap, is_native=True)
            time.sleep(random.uniform(*Config.Timers.DELAY_BETWEEN_ACTIONS))
        if Config.Zenith.LIQUIDITY_ENABLED:
            amount_phrs_for_lp = w3.to_wei(random.uniform(*Config.Zenith.LIQUIDITY_AMOUNT_PHRS), 'ether')
            console.print(f"      ({account.address[:6]}) Menukar PHRS untuk persiapan likuiditas...")
            if perform_swap(account, w3, dex_abi, Config.Zenith.ROUTER_ADDRESS, Config.Zenith.WPHRS_ADDRESS, Config.Zenith.TARGET_TOKEN_ADDRESS, amount_phrs_for_lp, is_native=True):
                time.sleep(random.uniform(*Config.Timers.DELAY_BETWEEN_ACTIONS))
                amount_target_token_wei = get_token_balance(w3, Config.Zenith.TARGET_TOKEN_ADDRESS, account.address)
                if amount_target_token_wei > 0:
                    add_liquidity(account, w3, dex_abi, Config.Zenith.POSITION_MANAGER_ADDRESS, Config.Zenith.WPHRS_ADDRESS, Config.Zenith.TARGET_TOKEN_ADDRESS, amount_phrs_for_lp, amount_target_token_wei)
                else: console.print(f"[yellow]      ({account.address[:6]}) ⚠️ Saldo token tidak cukup untuk LP.[/yellow]")
            else: console.print(f"[yellow]      ({account.address[:6]}) ⚠️ Swap untuk LP gagal, melewati.[/yellow]")
            time.sleep(random.uniform(*Config.Timers.DELAY_BETWEEN_ACTIONS))

    # 3. Aksi di FaroSwap DEX
    if Config.FaroSwap.ENABLED:
        console.print(Rule(f"[bold blue]🌊 FAROSWAP DEX[/bold blue]", style="blue"))
        amount_to_swap_faro = w3.to_wei(random.uniform(*Config.FaroSwap.AMOUNT_TO_SWAP), 'ether')
        perform_swap(account, w3, dex_abi, Config.FaroSwap.ROUTER_ADDRESS, Config.Zenith.WPHRS_ADDRESS, Config.FaroSwap.USDT_ADDRESS, amount_to_swap_faro, is_native=True)
        time.sleep(random.uniform(*Config.Timers.DELAY_BETWEEN_ACTIONS))

def main():
    console.print(Rule("[bold magenta]🚀 Bot Pharos (v2: Info & Claims) - Modified by AI 🚀[/bold magenta]"))
    try:
        with open(Config.PRIVATE_KEY_FILE, 'r') as f:
            private_keys = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        console.print(f"[bold red]❌ File '{Config.PRIVATE_KEY_FILE}' tidak ditemukan![/bold red]")
        return
    dex_abi = load_json_file('abi.json')
    if not private_keys or not dex_abi:
        console.print("[bold red]Bot berhenti. Pastikan 'privatekey.txt' dan 'abi.json' ada dan valid.[/bold red]")
        return
    w3 = Web3(Web3.HTTPProvider(Config.RPC_URL))
    if not w3.is_connected():
        console.print(f"[bold red]❌ Gagal koneksi ke RPC: {Config.RPC_URL}[/bold red]")
        return
    console.print(f"[green]✅ Terhubung ke RPC. Chain ID: {w3.eth.chain_id}[/green]")
    console.print(f"[blue]✅ Berhasil memuat {len(private_keys)} private key.[/blue]")
    while True:
        with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_THREADS) as executor:
            [executor.submit(process_account, pk, i + 1, len(private_keys), w3, dex_abi) for i, pk in enumerate(private_keys)]
        
        console.print(Rule(f"[bold green]✅ Semua akun selesai. Siklus berikutnya dalam {Config.Timers.DELAY_FOR_NEXT_RUN_HOURS} jam.[/bold green]"))
        duration_seconds = Config.Timers.DELAY_FOR_NEXT_RUN_HOURS * 3600
        end_time = datetime.now() + timedelta(seconds=duration_seconds)
        with Live(console=console, refresh_per_second=1) as live:
            while datetime.now() < end_time:
                remaining = end_time - datetime.now()
                live.update(Panel(f"Siklus berikutnya dalam: [bold cyan]{str(remaining).split('.')[0]}[/bold cyan]", title="[bold green]💤 Waktu Jeda[/bold green]"))
                time.sleep(1)

if __name__ == "__main__":
    main()