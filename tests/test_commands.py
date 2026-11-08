from types import SimpleNamespace

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.exception import FinishedException
import pytest


@pytest.fixture
def members():
    return {"10000": "admin", "20000": "admin", "30000": "member"}


@pytest.fixture
def bot(mocker, members):
    async def get_member_info(*, group_id, user_id):
        return {"role": members[str(user_id)]}

    return SimpleNamespace(
        self_id="10000",
        config=SimpleNamespace(superusers=set()),
        get_group_member_info=mocker.AsyncMock(side_effect=get_member_info),
        set_group_ban=mocker.AsyncMock(),
        set_group_kick=mocker.AsyncMock(),
    )


@pytest.fixture
def event():
    return SimpleNamespace(group_id=12345, user_id=20000)


@pytest.fixture
def matcher(mocker):
    return SimpleNamespace(finish=mocker.AsyncMock(side_effect=FinishedException))


def command_arg(text=""):
    return Message(MessageSegment.at(30000)) + Message(text)


@pytest.mark.asyncio
@pytest.mark.parametrize(("text", "seconds"), [("", 60), ("5", 300), ("5M", 300), ("5d", 432000)])
async def test_mute_sends_requested_duration(bot, event, matcher, text, seconds):
    import group_helper as plugin

    await plugin.mute_matcher.handlers[0].call(matcher, bot, event, command_arg(text))

    bot.set_group_ban.assert_awaited_once_with(
        group_id=12345, user_id=30000, duration=seconds,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["0", "-5", "abc"])
async def test_invalid_duration_never_calls_moderation_api(bot, event, matcher, text):
    import group_helper as plugin

    with pytest.raises(FinishedException):
        await plugin.mute_matcher.handlers[0].call(matcher, bot, event, command_arg(text))

    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(("actor_role", "target_role"), [("admin", "admin"), ("admin", "owner"), ("member", "member")])
async def test_unauthorized_actor_cannot_mute_target(bot, members, event, matcher, actor_role, target_role):
    import group_helper as plugin

    members["20000"] = actor_role
    members["30000"] = target_role

    with pytest.raises(FinishedException):
        await plugin.mute_matcher.handlers[0].call(matcher, bot, event, command_arg("5"))

    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_bot_without_admin_role_cannot_execute_commands(bot, members, event, matcher):
    import group_helper as plugin

    members["10000"] = "member"

    with pytest.raises(FinishedException):
        await plugin.unmute_matcher.handlers[0].call(matcher, bot, event, command_arg())

    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_superuser_privilege_still_requires_bot_admin(bot, members, event, matcher):
    import group_helper as plugin

    bot.config.superusers.add("20000")
    members["10000"] = "member"

    with pytest.raises(FinishedException):
        await plugin.unmute_matcher.handlers[0].call(matcher, bot, event, command_arg())

    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_unmute_uses_zero_duration(bot, event, matcher):
    import group_helper as plugin

    await plugin.unmute_matcher.handlers[0].call(matcher, bot, event, command_arg())

    bot.set_group_ban.assert_awaited_once_with(group_id=12345, user_id=30000, duration=0)


@pytest.mark.asyncio
async def test_kick_waits_for_confirmation(bot, event, matcher):
    import group_helper as plugin

    state = {}
    await plugin.kick_matcher.handlers[0].call(matcher, bot, event, state, command_arg())
    bot.set_group_kick.assert_not_awaited()

    await plugin.kick_matcher.handlers[1].call(matcher, bot, event, state, "确定是")

    bot.set_group_kick.assert_awaited_once_with(
        group_id=12345, user_id=30000, reject_add_request=False,
    )


@pytest.mark.asyncio
async def test_kick_rechecks_permissions_after_confirmation(bot, members, event, matcher):
    import group_helper as plugin

    state = {}
    await plugin.kick_matcher.handlers[0].call(matcher, bot, event, state, command_arg())
    members["30000"] = "admin"

    with pytest.raises(FinishedException):
        await plugin.kick_matcher.handlers[1].call(matcher, bot, event, state, "确定")

    bot.set_group_kick.assert_not_awaited()


@pytest.mark.asyncio
async def test_kick_cancellation_never_calls_api(bot, event, matcher):
    import group_helper as plugin

    with pytest.raises(FinishedException):
        await plugin.kick_matcher.handlers[1].call(matcher, bot, event, {"target_id": 30000}, "取消")

    bot.set_group_kick.assert_not_awaited()
