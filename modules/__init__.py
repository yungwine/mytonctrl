import typing
from dataclasses import dataclass

from modules.module import MtcModule
from modules.pool import PoolModule
from modules.nominator_pool import NominatorPoolModule
from modules.single_pool import SingleNominatorModule
from modules.validator import ValidatorModule
from modules.controller import ControllerModule
from modules.liteserver import LiteserverModule


MODES = {
    'validator': ValidatorModule,
    'nominator-pool': NominatorPoolModule,
    'single-nominator': SingleNominatorModule,
    'liquid-staking': ControllerModule,
    'liteserver': LiteserverModule
}


def get_mode(mode_name: str) -> typing.Optional[MtcModule]:
    return MODES.get(mode_name)


@dataclass
class Setting:
    mode: typing.Optional[str]
    default_value: typing.Any
    description: str


SETTINGS = {
    'stake': Setting('validator', None, 'Stake amount'),
    'stakePercent': Setting('validator', 99, 'Stake percent if `stake` is null'),
    'isSlashing': Setting('validator', None, 'Create complaints to validators'),
    'validatorWalletName': Setting('validator', 'wallet_001', 'Validator\'s wallet name'),
    'maxFactor': Setting('validator', None, 'Param send to Elector. if null will be taken from 17 config param'),
    'participateBeforeEnd': Setting('validator', None, 'Amount of seconds before start of round to participate'),
    'liquid_pool_addr': Setting('liquid-staking', None, 'Liquid staking pool address'),
    'min_loan': Setting('liquid-staking', 41000, 'Min loan amount'),
    'max_loan': Setting('liquid-staking', 43000, 'Max loan amount'),
    'max_interest_percent': Setting('liquid-staking', 10, 'Max interest percent'),
    'duplicateSendfile': Setting(None, True, 'Duplicate external to public Liteservers'),
    'sendTelemetry': Setting(None, True, 'Send node telemetry'),
    'telemetryLiteUrl': Setting(None, 'https://telemetry.toncenter.com/report_status', 'Telemetry url'),
    'overlayTelemetryUrl': Setting(None, 'https://telemetry.toncenter.com/report_overlays', 'Overlay telemetry url'),
    'duplicateApi': Setting(None, 'sendTelemetry', 'Duplicate external to Toncenter'),
    'duplicateApiUrl': Setting(None, 'https://[testnet.]toncenter.com/api/v2/sendBoc', 'Toncenter api url for duplicate'),
    'checkAdnl': Setting(None, 'sendTelemetry', 'Check local udp port and adnl connection'),
    'liteclient_timeout': Setting(None, 3, 'Liteclient default timeout'),
    'console_timeout': Setting(None, 3, 'Validator console default timeout'),
    'fift_timeout': Setting(None, 3, 'Fift default timeout'),
    'useDefaultCustomOverlays': Setting(None, True, 'Participate in default custom overlays node eligible to'),
    'defaultCustomOverlaysUrl': Setting(None, 'https://ton-blockchain.github.io/fallback_custom_overlays.json', 'Default custom overlays config url'),
    'debug': Setting(None, False, 'Debug mtc console mode. Prints Traceback on errors'),
}


def get_setting(name: str) -> typing.Optional[Setting]:
    return SETTINGS.get(name)


def get_mode_settings(name: str):
    return {k: v for k, v in SETTINGS.items() if v.mode == name}

