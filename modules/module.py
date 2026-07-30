from abc import ABC, abstractmethod

from mypylib.mypylib import MyPyClass

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mytoncore import MyTonCore


class MtcModule(ABC):

    description = ''  # module text description
    default_value = True  # is module enabled by default

    def __init__(self, ton, local, *args, **kwargs):
        from mytoncore.mytoncore import MyTonCore
        self.ton: MyTonCore = ton
        self.local: MyPyClass = local

    @abstractmethod
    def add_console_commands(self, console):  ...

    @classmethod
    def check_enable(cls, ton: "MyTonCore"):
        return

    def check_disable(self):
        return
