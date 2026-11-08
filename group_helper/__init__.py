import re

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule
from nonebot.typing import T_State

from zhenxun.configs.config import BotConfig
from zhenxun.configs.utils import Command, PluginExtraData
from zhenxun.utils.enum import PluginType

CONFIRM_WORDS = {"是", "好", "确定", "确定是"}
DEFAULT_MUTE_DURATION = 60
DURATION_PATTERN = re.compile(r"^(\d+)([mMdD]?)$")


__plugin_meta__ = PluginMetadata(
    name="群聊管理",
    description="群聊禁言、解除禁言和踢出成员",
    homepage="https://github.com/lumenmai",
    usage="""
    mute @用户       : 禁言 1 分钟
    mute @用户 5     : 禁言 5 分钟
    mute @用户 5m    : 禁言 5 分钟
    mute @用户 5d    : 禁言 5 天
    unmute @用户     : 解除禁言
    kick @用户       : 踢出群聊，需要二次确认
    """.strip(),
    supported_adapters={"~onebot.v11"},
    extra=PluginExtraData(
        author="lumen",
        version="0.1.0",
        menu_type="功能",
        plugin_type=PluginType.NORMAL,
        commands=[
            Command(command="mute @用户 [时间]", description="禁言群成员"),
            Command(command="unmute @用户", description="解除群成员禁言"),
            Command(command="kick @用户", description="踢出群成员"),
        ],
    ).dict(),
)


def _is_group_message(event) -> bool:
    return isinstance(event, GroupMessageEvent)


mute_matcher = on_command(
    "mute",
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    rule=Rule(_is_group_message),
    priority=5,
    block=True,
)
unmute_matcher = on_command(
    "unmute",
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    rule=Rule(_is_group_message),
    priority=5,
    block=True,
)
kick_matcher = on_command(
    "kick",
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    rule=Rule(_is_group_message),
    priority=5,
    block=True,
)


def _extract_at_user(message: Message) -> int | None:
    for segment in message:
        if segment.type != "at":
            continue
        user_id = str(segment.data.get("qq", ""))
        if user_id.isdigit():
            return int(user_id)
    return None


def _parse_duration(message: Message) -> int | None:
    text = message.extract_plain_text().strip()
    if not text:
        return DEFAULT_MUTE_DURATION

    match = DURATION_PATTERN.match(text)
    if not match:
        return None

    value = int(match.group(1))
    if value <= 0:
        return None

    unit = match.group(2).lower()
    if unit == "d":
        return value * 24 * 60 * 60
    return value * 60


async def _is_bot_group_admin(bot: Bot, group_id: int) -> bool:
    try:
        member_info = await bot.get_group_member_info(
            group_id=group_id,
            user_id=int(bot.self_id),
        )
    except Exception:
        return False
    return member_info.get("role") in {"admin", "owner"}


async def _can_manage_target(
    bot: Bot,
    event: GroupMessageEvent,
    target_id: int,
) -> tuple[bool, bool]:
    """返回 (是否允许操作, 是否需要回复做不到)。"""
    if str(event.user_id) in bot.config.superusers:
        return True, False

    try:
        operator_info = await bot.get_group_member_info(
            group_id=event.group_id,
            user_id=event.user_id,
        )
        target_info = await bot.get_group_member_info(
            group_id=event.group_id,
            user_id=target_id,
        )
    except Exception:
        return False, False

    operator_role = operator_info.get("role")
    target_role = target_info.get("role")

    if operator_role == "owner":
        return True, False
    if operator_role == "admin":
        if target_role in {"admin", "owner"}:
            return False, True
        return True, False
    return False, False


async def _check_preconditions(
    matcher: Matcher,
    bot: Bot,
    event: GroupMessageEvent,
    target_id: int | None,
) -> bool:
    if target_id is None:
        await matcher.finish("请使用 @ 指定目标用户")

    if not await _is_bot_group_admin(bot, event.group_id):
        await matcher.finish()

    can_manage, should_reply = await _can_manage_target(bot, event, target_id)
    if should_reply:
        await matcher.finish(f"{BotConfig.self_nickname}做不到喵")
    if not can_manage:
        await matcher.finish()
    return True


@mute_matcher.handle()
async def _(
    matcher: Matcher,
    bot: Bot,
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
):
    target_id = _extract_at_user(arg)
    duration = _parse_duration(arg)
    if duration is None:
        await matcher.finish("用法：mute @用户 5 / 5m / 5d")

    await _check_preconditions(matcher, bot, event, target_id)

    try:
        await bot.set_group_ban(
            group_id=event.group_id,
            user_id=target_id,
            duration=duration,
        )
    except Exception:
        await matcher.finish()


@unmute_matcher.handle()
async def _(
    matcher: Matcher,
    bot: Bot,
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
):
    target_id = _extract_at_user(arg)
    await _check_preconditions(matcher, bot, event, target_id)

    try:
        await bot.set_group_ban(
            group_id=event.group_id,
            user_id=target_id,
            duration=0,
        )
    except Exception:
        await matcher.finish()


@kick_matcher.handle()
async def _(
    matcher: Matcher,
    bot: Bot,
    event: GroupMessageEvent,
    state: T_State,
    arg: Message = CommandArg(),
):
    target_id = _extract_at_user(arg)
    await _check_preconditions(matcher, bot, event, target_id)
    state["target_id"] = target_id


@kick_matcher.got(
    "confirm",
    prompt="确定是否踢出？\n确定请回复[是|好|确定]",
)
async def _(
    matcher: Matcher,
    bot: Bot,
    event: GroupMessageEvent,
    state: T_State,
    confirm: str = ArgPlainText("confirm"),
):
    if confirm.strip() not in CONFIRM_WORDS:
        await matcher.finish("已取消操作...")

    target_id = state.get("target_id")
    await _check_preconditions(matcher, bot, event, target_id)

    try:
        await bot.set_group_kick(
            group_id=event.group_id,
            user_id=target_id,
            reject_add_request=False,
        )
    except Exception:
        await matcher.finish()
