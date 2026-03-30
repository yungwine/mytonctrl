import datetime
import os
import time
import json
import subprocess

from mypylib import MyPyClass
from mytoncore.mytoncore import MyTonCore
from mypylib.mypylib import (
    get_timestamp,
    thr_sleep,
)
from mytoncore.stats_collector import StatsCollector
from mytoncore.telemetry import build_telemetry_payload, build_overlay_telemetry_payload


def Init(local: MyPyClass):
    local.run()


def Offers(_, ton: MyTonCore):
    save_offers = ton.GetSaveOffers()
    if save_offers:
        ton.offers_gc(save_offers)
    else:
        return
    offers = ton.GetOffers()
    for offer in offers:
        offer_hash = offer.get("hash")
        if offer_hash in save_offers:
            offer_pseudohash = offer.get("pseudohash")
            save_offer = save_offers.get(offer_hash)
            if isinstance(save_offer, list):  # new version of save offers {"hash": ["pseudohash", param_id]}
                save_offer_pseudohash = save_offer[0]
            else:  # old version of save offers {"hash": "pseudohash"}
                save_offer_pseudohash = save_offer
            if offer_pseudohash == save_offer_pseudohash and offer_pseudohash is not None:
                ton.VoteOffer(offer)


def Complaints(_, ton: MyTonCore):
    validator_index = ton.GetValidatorIndex()
    if validator_index < 0:
        return
    if time.time() < 1776643200:
        return

    # Voting for complaints
    config32 = ton.GetConfig32()
    election_id = config32.get("startWorkTime")
    complaints = ton.GetComplaints(election_id)  # get complaints from Elector
    if not complaints:
        return
    valid_complaints = ton.get_valid_complaints(complaints, election_id)
    for c in valid_complaints.values():
        complaint_hash = c.get("hash")
        ton.VoteComplaint(election_id, complaint_hash)


def Slashing(local: MyPyClass, ton: MyTonCore):
    is_slashing = local.db.get("isSlashing")
    is_validator = ton.using_validator()
    if is_slashing is not True or not is_validator:
        return

    # Creating complaints
    slash_time = local.buffer.slash_time
    config32 = ton.GetConfig32()
    start = config32.get("startWorkTime")
    end = config32.get("endWorkTime")
    config15 = ton.GetConfig15()
    ts = get_timestamp()
    if not(end < ts < end + config15['stakeHeldFor']):  # check that currently is freeze time
        return
    local.add_log("slash_time {}, start {}, end {}".format(slash_time, start, end), "debug")
    if slash_time != start:
        end -= 60
        ton.CheckValidators(start, end)
        local.buffer.slash_time = start
# end define


def save_past_events(local: MyPyClass, ton: MyTonCore):
    local.try_function(ton.GetElectionEntries)
    local.try_function(ton.GetComplaints)
    local.try_function(ton.GetValidatorsList, args=[True])  # cache past vl


def ScanLiteServers(local: MyPyClass, ton: MyTonCore):
    file_path = ton.liteClient.configPath
    if file_path is None:
        raise RuntimeError("liteClient.configPath is None")
    with open(file_path, 'rt') as f:
        text = f.read()
    data = json.loads(text)

    result = list()
    liteservers = data.get("liteservers")
    for index in range(len(liteservers)):
        try:
            ton.liteClient.Run("last", index=index)
            result.append(index)
        except Exception:
            pass

    local.db["liteServers"] = result


def check_initial_sync(_, ton: MyTonCore):
    if not ton.in_initial_sync():
        return
    validator_status = ton.GetValidatorStatus()
    if validator_status.initial_sync:
        return
    if validator_status.out_of_sync < 20:
        ton.set_initial_sync_off()
        return


def gc_import(local: MyPyClass, ton: MyTonCore):
    if not ton.local.db.get('importGc', False):
        return
    local.add_log("GC import is running", "debug")
    import_path = '/var/ton-work/db/import'
    files = os.listdir(import_path)
    if not files:
        local.add_log("No files left to import", "debug")
        ton.local.db['importGc'] = False
        ton.local.save()
        return
    try:
        status = ton.GetValidatorStatus()
        node_seqno = int(status.shardclientmasterchainseqno)
    except Exception as e:
        local.add_log(f"Failed to get shardclientmasterchainseqno: {e}", "warning")
        return
    to_delete = []
    to_delete_dirs = []
    for root, dirs, files in os.walk(import_path):
        if root != import_path and not dirs and not files:
            to_delete_dirs.append(root)
        for file in files:
            file_seqno = int(file.split('.')[1])
            if node_seqno > file_seqno + 101:
                to_delete.append(os.path.join(root, file))
    for file_path in to_delete:
        try:
            os.remove(file_path)
        except Exception as e:
            local.add_log(f"Failed to remove file {file_path}: {e}", "error")
    for dir_path in to_delete_dirs:
        try:
            os.rmdir(dir_path)
        except Exception as e:
            local.add_log(f"Failed to remove dir {dir_path}: {e}", "error")
    local.add_log(f"Removed {len(to_delete)} import files and {len(to_delete_dirs)} import dirs up to {node_seqno} seqno", "debug")


def backup_mytoncore_logs(local: MyPyClass, ton: MyTonCore):
    logs_path = os.path.join(ton.tempDir, 'old_logs')
    os.makedirs(logs_path, exist_ok=True)
    for file in os.listdir(logs_path):
        file_path = os.path.join(logs_path, file)
        if time.time() - os.path.getmtime(file_path) < 3600:  # check that last file was created not less than an hour ago
            return
    now = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    log_backup_tmp_path = os.path.join(logs_path, 'mytoncore_log_' + now + '.log')
    subprocess.run(["cp", local.log_file_name, log_backup_tmp_path])
    ton.clear_dir(logs_path)


def check_mytoncore_db(local: MyPyClass, ton: MyTonCore):
    try:
        local.read_db(local.db_path)
        backup_path = local.db_path + ".backup"
        if not os.path.isfile(backup_path) or time.time() - os.path.getmtime(backup_path) > 3600*6:
            ton.create_self_db_backup()
        return
    except Exception as e:
        print(f'Failed to read mytoncore db: {e}')
        local.add_log(f"Failed to read mytoncore db: {e}", "error")
    ton.CheckConfigFile(None, None)  # get mytoncore db from backup


def General(local: MyPyClass):
    local.add_log("start General function", "debug")
    ton = MyTonCore(local)
    # scanner = Dict()
    # scanner.Run()

    # Start threads
    stats_collector = StatsCollector(local, ton)
    local.start_cycle(stats_collector.save_statistics, sec=10, args=())
    local.start_cycle(build_telemetry_payload, sec=60, args=(local, ton, ))
    local.start_cycle(build_overlay_telemetry_payload, sec=7200, args=(local, ton, ))
    local.start_cycle(backup_mytoncore_logs, sec=3600*4, args=(local, ton, ))
    local.start_cycle(check_mytoncore_db, sec=600, args=(local, ton, ))

    if local.db.get("onlyNode"):  # mytoncore service works only for telemetry
        thr_sleep()
        return

    from modules.validator import ValidatorModule
    local.start_cycle(ValidatorModule(ton, local).run_elections, sec=600, args=())
    local.start_cycle(Offers, sec=600, args=(local, ton, ))
    local.start_cycle(save_past_events, sec=300, args=(local, ton, ))

    t = 1800
    if ton.GetNetworkName() != 'mainnet':
        t = 300
    local.start_cycle(Complaints, sec=t, args=(local, ton, ))
    local.start_cycle(Slashing, sec=t, args=(local, ton, ))

    local.start_cycle(ScanLiteServers, sec=60, args=(local, ton,))

    local.start_cycle(stats_collector.save_node_statistics, sec=60, args=())

    from modules.custom_overlays import CustomOverlayModule
    local.start_cycle(CustomOverlayModule(ton, local).custom_overlays, sec=60, args=())

    from modules.alert_bot import AlertBotModule
    local.start_cycle(AlertBotModule(ton, local).check_status, sec=60, args=())

    from modules.prometheus import PrometheusModule
    local.start_cycle(PrometheusModule(ton, local).push_metrics, sec=30, args=())

    if ton.in_initial_sync():
        local.start_cycle(check_initial_sync, sec=120, args=(local, ton))

    local.start_cycle(gc_import, sec=600, args=(local, ton))

    thr_sleep()
