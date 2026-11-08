"""Use real NoneBot with metadata stubs instead of loading a production host."""

from enum import Enum
import sys
from types import ModuleType, SimpleNamespace

import nonebot
from nonebot.adapters.onebot.v11 import Adapter
from pydantic import BaseModel
import pytest


@pytest.fixture(scope="session", autouse=True)
def init_plugin():
    nonebot.init(driver="~fastapi", command_start={""}, superusers={"10000"})
    nonebot.get_driver().register_adapter(Adapter)

    names = [
        "zhenxun", "zhenxun.configs", "zhenxun.configs.config",
        "zhenxun.configs.utils", "zhenxun.utils", "zhenxun.utils.enum",
    ]
    previous = {name: sys.modules.get(name) for name in names}
    for name in names:
        module = ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module

    class PluginType(str, Enum):
        NORMAL = "NORMAL"

    class Command(BaseModel):
        command: str
        description: str

    class PluginExtraData(BaseModel):
        author: str
        version: str
        menu_type: str
        plugin_type: PluginType
        commands: list[Command]

    sys.modules["zhenxun.configs.config"].BotConfig = SimpleNamespace(self_nickname="真寻")
    sys.modules["zhenxun.configs.utils"].Command = Command
    sys.modules["zhenxun.configs.utils"].PluginExtraData = PluginExtraData
    sys.modules["zhenxun.utils.enum"].PluginType = PluginType

    plugin = nonebot.load_plugin("group_helper")
    assert plugin is not None, "Plugin failed to load"
    yield plugin

    for name, module in previous.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
