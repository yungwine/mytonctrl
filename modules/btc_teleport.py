import os
import subprocess

import pkg_resources

from modules.module import MtcModule
from mypylib.mypylib import run_as_root


class BtcTeleportModule(MtcModule):

    def __init__(self, ton, local, *args, **kwargs):
        super().__init__(ton, local, *args, **kwargs)
        self.workdir = os.path.abspath(self.ton.local.buffer.my_work_dir + '../btc_teleport')
        self.keystore_path = self.workdir + '/keystore'
        self.repo_name = 'ton-teleport-btc-oracle'
        self.src_dir = self.workdir + f'/{self.repo_name}'

    def create_env_file(self):
        env_path = self.src_dir + '/.env'
        if os.path.exists(env_path):
            return

        text = f"""
STANDALONE=0
TON_CENTER_V2_ENDPOINT=http://127.0.0.1:8801
COORDINATOR=EQDIEVARwkn6_4qNWeDlHwT40kzJBGIzKo4vcqRSvDUUS6bT
VALIDATOR_SERVER_ADDRESS={self.ton.validatorConsole.addr}
KEYSTORE_DIR={self.keystore_path}
SERVER_PUBLIC_KEY_PATH={self.ton.validatorConsole.pubKeyPath}
CLIENT_PRIVATE_KEY_PATH={self.ton.validatorConsole.privKeyPath}
VALIDATOR_ENGINE_CONSOLE_PATH={self.ton.validatorConsole.appPath}
"""
        with open(env_path, 'w') as f:
            f.write(text)

    @staticmethod
    def install_unzip():
        if subprocess.run('command -v unzip', shell=True).returncode != 0:
            run_as_root(['apt-get', 'install', 'unzip'])

    def add_daemon(self):
        bun_executable = subprocess.run('command -v bun', stdout=subprocess.PIPE, shell=True).stdout.decode().strip()
        cmd = f'''"import subprocess; import os; from mypylib.mypylib import add2systemd; add2systemd(name='btc_teleport', user=os.getlogin(), start='{bun_executable} start', workdir='{self.src_dir}'); subprocess.run(['systemctl', 'daemon-reload']); subprocess.run(['systemctl', 'restart', 'btc_teleport'])"'''
        run_as_root(['python3', '-c', cmd])

    def install(self):
        self.install_unzip()
        script_path = pkg_resources.resource_filename('mytonctrl', 'scripts/btc_teleport.sh')
        subprocess.run(["bash", script_path, "-s", self.workdir, "-r", self.repo_name])
        self.add_daemon()

    def init(self, reinstall=False):
        if os.path.exists(self.src_dir) and not reinstall:
            return
        os.makedirs(self.keystore_path, exist_ok=True)
        os.makedirs(self.workdir, exist_ok=True)
        self.install()
        self.create_env_file()

    def add_console_commands(self, console):
        pass
