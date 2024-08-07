#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import os, sys
import inspect
import random
import json
import subprocess

import pkg_resources

from mypylib.mypylib import MyPyClass, run_as_root, color_print
from mypyconsole.mypyconsole import MyPyConsole

from mytoninstaller.config import GetLiteServerConfig, get_ls_proxy_config
from mytoninstaller.node_args import get_node_args
from mytoninstaller.utils import GetInitBlock
from mytoncore.utils import dict2b64, str2bool, b642dict

from mytoninstaller.settings import (
	FirstNodeSettings,
	FirstMytoncoreSettings,
	EnableValidatorConsole,
	EnableLiteServer,
	EnableDhtServer,
	EnableJsonRpc,
	EnableTonHttpApi,
	DangerousRecoveryValidatorConfigFile,
	CreateSymlinks,
	enable_ls_proxy,
	enable_ton_storage,
	enable_ton_storage_provider,
	EnableMode
)
from mytoninstaller.config import (
	CreateLocalConfig,
	BackupVconfig,
	BackupMconfig,
)

from functools import partial


def Init(local, console):
	local.db.config.isStartOnlyOneProcess = False
	local.db.config.logLevel = "debug"
	local.db.config.isIgnorLogWarning = True # disable warning
	local.run()
	local.db.config.isIgnorLogWarning = False # enable warning


	# create variables
	user = os.environ.get("USER", "root")
	local.buffer.user = user
	local.buffer.vuser = "validator"
	local.buffer.cport = random.randint(2000, 65000)
	local.buffer.lport = random.randint(2000, 65000)

	# this funciton injects MyPyClass instance
	def inject_globals(func):
		args = []
		for arg_name in inspect.getfullargspec(func)[0]:
			if arg_name == 'local':
				args.append(local)
		return partial(func, *args)

	# Create user console
	console.name = "MyTonInstaller"
	console.color = console.RED
	console.AddItem("status", inject_globals(Status), "Print TON component status")
	console.AddItem("set_node_argument", inject_globals(set_node_argument), "Set node argument")
	console.AddItem("enable", inject_globals(Enable), "Enable some function")
	console.AddItem("update", inject_globals(Enable), "Update some function: 'JR' - jsonrpc.  Example: 'update JR'") 
	console.AddItem("plsc", inject_globals(PrintLiteServerConfig), "Print lite-server config")
	console.AddItem("clcf", inject_globals(CreateLocalConfigFile), "Create lite-server config file")
	console.AddItem("print_ls_proxy_config", inject_globals(print_ls_proxy_config), "Print ls-proxy config")
	console.AddItem("create_ls_proxy_config_file", inject_globals(create_ls_proxy_config_file), "Create ls-proxy config file")
	console.AddItem("drvcf", inject_globals(DRVCF), "Dangerous recovery validator config file")
	console.AddItem("setwebpass", inject_globals(SetWebPassword), "Set a password for the web admin interface")

	Refresh(local)
#end define


def Refresh(local):
	user = local.buffer.user
	local.buffer.mconfig_path = "/home/{user}/.local/share/mytoncore/mytoncore.db".format(user=user)
	if user == 'root':
		local.buffer.mconfig_path = "/usr/local/bin/mytoncore/mytoncore.db"
	#end if

	# create variables
	bin_dir = "/usr/bin/"
	src_dir = "/usr/src/"
	ton_work_dir = "/var/ton-work/"
	ton_bin_dir = bin_dir + "ton/"
	ton_src_dir = src_dir + "ton/"
	local.buffer.bin_dir = bin_dir
	local.buffer.src_dir = src_dir
	local.buffer.ton_work_dir = ton_work_dir
	local.buffer.ton_bin_dir = ton_bin_dir
	local.buffer.ton_src_dir = ton_src_dir
	ton_db_dir = ton_work_dir + "db/"
	keys_dir = ton_work_dir + "keys/"
	local.buffer.ton_db_dir = ton_db_dir
	local.buffer.keys_dir = keys_dir
	local.buffer.ton_log_path = ton_work_dir + "log"
	local.buffer.validator_app_path = ton_bin_dir + "validator-engine/validator-engine"
	local.buffer.global_config_path = ton_bin_dir + "global.config.json"
	local.buffer.vconfig_path = ton_db_dir + "config.json"
#end define


def Status(local, args):
	keys_dir = local.buffer.keys_dir
	server_key = keys_dir + "server"
	client_key = keys_dir + "client"
	liteserver_key = keys_dir + "liteserver"
	liteserver_pubkey = liteserver_key + ".pub"

	statuses = {
		'Full node status': os.path.isfile(local.buffer.vconfig_path),
		'Mytoncore status': os.path.isfile(local.buffer.mconfig_path),
		'V.console status': os.path.isfile(server_key) or os.path.isfile(client_key),
		'Liteserver status': os.path.isfile(liteserver_pubkey)
	}

	color_print("{cyan}===[ Services status ]==={endc}")
	for item in statuses.items():
		status = '{green}enabled{endc}' if item[1] else '{red}disabled{endc}'
		color_print(f"{item[0]}: {status}")

	node_args = get_node_args()
	color_print("{cyan}===[ Node arguments ]==={endc}")
	for key, value in node_args.items():
		print(f"{key}: {value}")
#end define


def set_node_argument(local, args):
	if len(args) < 1:
		color_print("{red}Bad args. Usage:{endc} set_node_argument <arg-name> [arg-value] [-d (to delete)]")
		return
	arg_name = args[0]
	args = [arg_name, args[1] if len(args) > 1 else ""]
	script_path = pkg_resources.resource_filename('mytoninstaller.scripts', 'set_node_argument.py')
	run_as_root(['python3', script_path] + args)
	color_print("set_node_argument - {green}OK{endc}")
#end define


def Enable(local, args):
	try:
		name = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} enable <mode-name>")
		print("'FN' - Full node")
		print("'VC' - Validator console")
		print("'LS' - Lite-Server")
		print("'DS' - DHT-Server")
		print("'JR' - jsonrpc")
		print("'THA' - ton-http-api")
		print("'LSP' - ls-proxy")
		print("'TSP' - ton-storage + ton-storage-provider")
		print("Example: 'enable FN'")
		return
	if name == "THA":
		CreateLocalConfigFile(local, args)
	args = ["python3", "-m", "mytoninstaller", "-u", local.buffer.user, "-e", f"enable{name}"]
	run_as_root(args)
#end define


def DRVCF(local, args):
	user = local.buffer["user"]
	args = ["python3", "-m", "mytoninstaller", "-u", local.buffer.user, "-e", "drvcf"]
	run_as_root(args)
#end define


def SetWebPassword(args):
	args = ["python3", "/usr/src/mtc-jsonrpc/mtc-jsonrpc.py", "-p"]
	subprocess.run(args)
#end define


def PrintLiteServerConfig(local, args):
	liteServerConfig = GetLiteServerConfig(local)
	text = json.dumps(liteServerConfig, indent=4)
	print(text)
#end define


def CreateLocalConfigFile(local, args):
	initBlock = GetInitBlock()
	initBlock_b64 = dict2b64(initBlock)
	user = local.buffer["user"]
	args = ["python3", "-m", "mytoninstaller", "-u", local.buffer.user, "-e", "clc", "-i", initBlock_b64]
	run_as_root(args)
#end define

def print_ls_proxy_config(local, args):
	ls_proxy_config = get_ls_proxy_config(local)
	text = json.dumps(ls_proxy_config, indent=4)
	print(text)
#end define

def create_ls_proxy_config_file(local, args):
	print("TODO")
#end define

def Event(local, name):
	if name == "enableFN":
		FirstNodeSettings(local)
	if name == "enableVC":
		EnableValidatorConsole(local)
	if name == "enableLS":
		EnableLiteServer(local)
	if name == "enableDS":
		EnableDhtServer(local)
	if name == "drvcf":
		DangerousRecoveryValidatorConfigFile(local)
	if name == "enableJR":
		EnableJsonRpc(local)
	if name == "enableTHA":
		EnableTonHttpApi(local)
	if name == "enableLSP":
		enable_ls_proxy(local)
	if name == "enableTSP":
		enable_ton_storage(local)
		enable_ton_storage_provider(local)
	if name == "clc":
		ix = sys.argv.index("-i")
		initBlock_b64 = sys.argv[ix+1]
		initBlock = b642dict(initBlock_b64)
		CreateLocalConfig(local, initBlock)
	local.exit()
#end define


def Command(local, args, console):
	cmd = args[0]
	args = args[1:]
	for item in console.menu_items:
		if cmd == item.cmd:
			console._try(item.func, args)
			print()
			local.exit()
	print(console.unknown_cmd)
	local.exit()
#end define


def General(local, console):
	if "-u" in sys.argv:
		ux = sys.argv.index("-u")
		user = sys.argv[ux+1]
		local.buffer.user = user
		Refresh(local)
	if "-c" in sys.argv:
		cx = sys.argv.index("-c")
		args = sys.argv[cx+1:]
		Command(local, args, console)
	if "-e" in sys.argv:
		ex = sys.argv.index("-e")
		name = sys.argv[ex+1]
		Event(local, name)
	if "-t" in sys.argv:
		mx = sys.argv.index("-t")
		telemetry = sys.argv[mx+1]
		local.buffer.telemetry = str2bool(telemetry)
	if "--dump" in sys.argv:
		mx = sys.argv.index("--dump")
		dump = sys.argv[mx+1]
		local.buffer.dump = str2bool(dump)
	if "-m" in sys.argv:
		mx = sys.argv.index("-m")
		mode = sys.argv[mx+1]
		local.buffer.mode = mode
	#end if

	FirstMytoncoreSettings(local)
	FirstNodeSettings(local)
	EnableValidatorConsole(local)
	EnableLiteServer(local)
	BackupVconfig(local)
	BackupMconfig(local)
	CreateSymlinks(local)
	EnableMode(local)
#end define


###
### Start of the program
###
def mytoninstaller():
	local = MyPyClass(__file__)
	console = MyPyConsole()

	Init(local, console)
	if len(sys.argv) > 1:
		General(local, console)
	else:
		console.Run()
	local.exit()
