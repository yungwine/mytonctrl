import base64
import os

from modules.module import MtcModule
from mypylib.mypylib import color_print, print_table
from mytonctrl.console_cmd import (check_usage_no_args, check_usage_one_arg, check_usage_two_args,
    add_command, check_usage_args_len, check_usage_args_min_len, check_usage_args_min_max_len, check_usage_args_lens
)


class WalletModule(MtcModule):

    description = ''
    default_value = False

    def create_new_wallet(self, args):
        if not check_usage_args_lens("nw", args, [0, 2, 3, 4]):
            return
        version = "v1"
        if len(args) == 0:
            walletName = self.ton.GenerateWalletName()
            workchain = 0
        else:
            workchain = int(args[0])
            walletName = args[1]
        if len(args) > 2:
            version = args[2]
        if len(args) == 4:
            subwallet = int(args[3])
        else:
            subwallet = 698983191 + workchain  # 0x29A9A317 + workchain
        wallet = self.ton.CreateWallet(walletName, workchain, version, subwallet=subwallet)
        table = list()
        table += [["Name", "Workchain", "Address"]]
        table += [[wallet.name, wallet.workchain, wallet.addrB64_init]]
        print_table(table)

    def _wallets_check(self):
        self.local.add_log("start WalletsCheck function", "debug")
        wallets = self.get_wallets()
        for wallet in wallets:
            if os.path.isfile(wallet.bocFilePath):
                account = self.ton.GetAccount(wallet.addrB64)
                if account.balance > 0:
                    self.ton.SendFile(wallet.bocFilePath, wallet)

    def activate_wallet(self, args):
        if not check_usage_args_min_max_len("aw", args, min_len=0, max_len=1):
            return
        wallet_name = args[0] if len(args) == 1 else "all"
        if wallet_name == "all":
            self._wallets_check()
        else:
            wallet = self.ton.GetLocalWallet(wallet_name)
            self.ton.ActivateWallet(wallet)
        color_print("ActivateWallet - {green}OK{endc}")

    def get_wallets(self):
        self.local.add_log("start GetWallets function", "debug")
        wallets = list()
        wallets_name_list = self.ton.GetWalletsNameList()
        for walletName in wallets_name_list:
            wallet = self.ton.GetLocalWallet(walletName)
            wallets.append(wallet)
        return wallets

    def print_wallets_list(self, args):
        if not check_usage_no_args("wl", args):
            return
        table = list()
        table += [["Name", "Status", "Balance", "Ver", "Wch", "Address"]]
        data = self.get_wallets()
        if data is None or len(data) == 0:
            print("No data")
            return
        for wallet in data:
            account = self.ton.GetAccount(wallet.addrB64)
            if account.status != "active":
                wallet.addrB64 = wallet.addrB64_init
            table += [[wallet.name, account.status, account.balance, wallet.version, wallet.workchain, wallet.addrB64]]
        print_table(table)

    def do_import_wallet(self, addr_b64, key):
        addr_bytes = self.ton.addr_b64_to_bytes(addr_b64)
        pk_bytes = base64.b64decode(key)
        wallet_name = self.ton.GenerateWalletName()
        wallet_path = self.ton.walletsDir + wallet_name
        with open(wallet_path + ".addr", 'wb') as file:
            file.write(addr_bytes)
        with open(wallet_path + ".pk", 'wb') as file:
            file.write(pk_bytes)
        return wallet_name

    def import_wallet(self, args):
        if not check_usage_two_args("iw", args):
            return
        addr, key = args[0], args[1]
        name = self.do_import_wallet(addr, key)
        print("Wallet name:", name)

    def set_wallet_version(self, args):
        if not check_usage_two_args("swv", args):
            return
        addr, version = args[0], args[1]
        self.ton.SetWalletVersion(addr, version)
        color_print("SetWalletVersion - {green}OK{endc}")

    def do_export_wallet(self, wallet_name):
        wallet = self.ton.GetLocalWallet(wallet_name)
        with open(wallet.privFilePath, 'rb') as file:
            data = file.read()
        key = base64.b64encode(data).decode("utf-8")
        return wallet.addrB64, key

    def export_wallet(self, args):
        if not check_usage_one_arg("ew", args):
            return
        name = args[0]
        addr, key = self.do_export_wallet(name)
        print("Wallet name:", name)
        print("Address:", addr)
        print("Secret key:", key)

    def delete_wallet(self, args):
        if not check_usage_one_arg("dw", args):
            return
        wallet_name = args[0]
        if input("Are you sure you want to delete this wallet (yes/no): ") != "yes":
            print("Cancel wallet deletion")
            return
        wallet = self.ton.GetLocalWallet(wallet_name)
        wallet.Delete()
        color_print("DeleteWallet - {green}OK{endc}")

    def move_coins(self, args):
        if not check_usage_args_min_len("mg", args, 3):
            return
        wallet_name, destination, amount = args[0], args[1], args[2]
        flags = args[3:]
        wallet = self.ton.GetLocalWallet(wallet_name)
        destination = self.ton.get_destination_addr(destination)
        self.ton.MoveCoins(wallet, destination, amount, flags=flags)
        color_print("MoveCoins - {green}OK{endc}")

    def do_move_coins_through_proxy(self, wallet, dest, coins):
        self.local.add_log("start MoveCoinsThroughProxy function", "debug")
        wallet1 = self.ton.CreateWallet("proxy_wallet1", 0)
        wallet2 = self.ton.CreateWallet("proxy_wallet2", 0)
        self.ton.MoveCoins(wallet, wallet1.addrB64_init, coins)
        self.ton.ActivateWallet(wallet1)
        self.ton.MoveCoins(wallet1, wallet2.addrB64_init, "alld")
        self.ton.ActivateWallet(wallet2)
        self.ton.MoveCoins(wallet2, dest, "alld", flags=["-n"])
        wallet1.Delete()
        wallet2.Delete()

    def move_coins_through_proxy(self, args):
        if not check_usage_args_len("mgtp", args, 3):
            return
        wallet_name, destination, amount = args[0], args[1], args[2]
        wallet = self.ton.GetLocalWallet(wallet_name)
        destination = self.ton.get_destination_addr(destination)
        self.do_move_coins_through_proxy(wallet, destination, amount)
        color_print("MoveCoinsThroughProxy - {green}OK{endc}")

    def add_console_commands(self, console):
        add_command(self.local, console, "nw", self.create_new_wallet)
        add_command(self.local, console, "aw", self.activate_wallet)
        add_command(self.local, console, "wl", self.print_wallets_list)
        add_command(self.local, console, "iw", self.import_wallet)
        add_command(self.local, console, "swv", self.set_wallet_version)
        add_command(self.local, console, "ew", self.export_wallet)
        add_command(self.local, console, "dw", self.delete_wallet)
        add_command(self.local, console, "mg", self.move_coins)
        add_command(self.local, console, "mgtp", self.move_coins_through_proxy)
