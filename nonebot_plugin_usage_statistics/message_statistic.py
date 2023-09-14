from datetime import datetime
from typing import Optional, Dict, Any

from nonebot import Bot, on_command, get_driver
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.message import event_preprocessor
from pydantic import BaseModel

from .datastore import PrefKey, get_pref, inc_pref, set_pref
from .serializer import serialize_datetime, deserialize_datetime
from .utils import get_cls_fullname

EVENT_MESSAGE = {
    "OneBot V11": "nonebot.adapters.onebot.v11.event.MessageEvent",
    "OneBot V12": "nonebot.adapters.onebot.v12.event.MessageEvent",
    "QQ Guild": "nonebot.adapters.qqguild.event.MessageEvent",
    "Kaiheila": "nonebot.adapters.kaiheila.event.MessageEvent",
    "Console": "nonebot.adapters.console.event.MessageEvent",
    "Telegram": "nonebot.adapters.telegram.event.MessageEvent"
}

API_SEND_MESSAGE = {
    "OneBot V11": ["send_msg", "send_group_msg", "send_private_msg"],
    "OneBot V12": ["send_message"],
    "QQ Guild": ["post_messages", "post_dms_messages"],
    "Kaiheila": ["message_create", "directMessage_create"],
    "Console": ["send_msg"],
    "Telegram": ["send_message", "send_photo", "send_audio", "send_document",
                 "send_video", "send_animation", "send_voice", "send_video_note",
                 "send_media_group", "send_location", "send_venue", "send_contact",
                 "send_poll", "send_dice", "send_chat_action"]
}

K_MSG_RECV_FROM_INSTALLED = PrefKey("msg_recv_from_installed", int)
K_MSG_RECV_LAST_TIME = PrefKey("msg_recv_last_time", datetime,
                               serializer=serialize_datetime, deserializer=deserialize_datetime)
K_MSG_RECV_FROM_STARTUP = PrefKey("msg_recv_from_startup", int)
K_MSG_RECV_TODAY = PrefKey("msg_recv_today", int)
K_MSG_SENT_SUCC_FROM_INSTALLED = PrefKey("msg_sent_succ_from_installed", int)
K_MSG_SENT_SUCC_LAST_TIME = PrefKey("msg_sent_succ_last_time", datetime,
                                    serializer=serialize_datetime, deserializer=deserialize_datetime)
K_MSG_SENT_SUCC_FROM_STARTUP = PrefKey("msg_sent_succ_from_startup", int)
K_MSG_SENT_SUCC_TODAY = PrefKey("msg_sent_succ_today", int)
K_MSG_SENT_FAIL_FROM_INSTALLED = PrefKey("msg_sent_fail_from_installed", int)
K_MSG_SENT_FAIL_LAST_TIME = PrefKey("msg_sent_fail_last_time", datetime,
                                    serializer=serialize_datetime, deserializer=deserialize_datetime)
K_MSG_SENT_FAIL_FROM_STARTUP = PrefKey("msg_sent_fail_from_startup", int)
K_MSG_SENT_FAIL_TODAY = PrefKey("msg_sent_fail_today", int)


async def _handle_inc(k_from_installed: PrefKey[int],
                      k_last_time: PrefKey[datetime],
                      k_from_startup: PrefKey[int],
                      k_today: PrefKey[int]):
    await inc_pref(k_from_installed)
    await inc_pref(k_from_startup)

    async with k_last_time.lock:
        async with k_today.lock:
            now = datetime.now()
            if now.date() != (await get_pref(k_last_time)).date():
                await set_pref(k_today, 1)
            else:
                await inc_pref(k_today, with_lock=False)
            await set_pref(k_last_time, now)


@get_driver().on_startup
async def _clear_startup():
    await set_pref(K_MSG_RECV_FROM_STARTUP, 0)
    await set_pref(K_MSG_SENT_SUCC_FROM_STARTUP, 0)
    await set_pref(K_MSG_SENT_FAIL_FROM_STARTUP, 0)


@event_preprocessor
async def _count_msg_recv(bot: Bot, event: Event):
    if bot.type not in EVENT_MESSAGE:
        return

    for cls in event.__class__.mro():
        if get_cls_fullname(cls) == EVENT_MESSAGE[bot.type]:
            await _handle_inc(k_from_installed=K_MSG_RECV_FROM_INSTALLED,
                              k_from_startup=K_MSG_RECV_FROM_STARTUP,
                              k_today=K_MSG_RECV_TODAY,
                              k_last_time=K_MSG_RECV_LAST_TIME)

            return


@Bot.on_called_api
async def _count_msg_sent(
        bot: Bot, exception: Optional[Exception], api: str, data: Dict[str, Any], result: Any
):
    if api not in API_SEND_MESSAGE.get(bot.type, []):
        return

    if not exception:
        await _handle_inc(k_from_installed=K_MSG_SENT_SUCC_FROM_INSTALLED,
                          k_from_startup=K_MSG_SENT_SUCC_FROM_STARTUP,
                          k_today=K_MSG_SENT_SUCC_TODAY,
                          k_last_time=K_MSG_SENT_SUCC_LAST_TIME)
    else:
        await _handle_inc(k_from_installed=K_MSG_SENT_FAIL_FROM_INSTALLED,
                          k_from_startup=K_MSG_SENT_FAIL_FROM_STARTUP,
                          k_today=K_MSG_SENT_FAIL_TODAY,
                          k_last_time=K_MSG_SENT_FAIL_LAST_TIME)


class MessageStatistic(BaseModel):
    msg_recv_from_installed: int
    msg_recv_from_startup: int
    msg_recv_today: int

    msg_sent_succ_from_installed: int
    msg_sent_succ_from_startup: int
    msg_sent_succ_today: int

    msg_sent_fail_from_installed: int
    msg_sent_fail_from_startup: int
    msg_sent_fail_today: int


async def get_message_statistic() -> MessageStatistic:
    return MessageStatistic(
        msg_recv_from_installed=await get_pref(K_MSG_RECV_FROM_INSTALLED) or 0,
        msg_recv_from_startup=await get_pref(K_MSG_RECV_FROM_STARTUP) or 0,
        msg_recv_today=await get_pref(K_MSG_RECV_TODAY) or 0,

        msg_sent_succ_from_installed=await get_pref(K_MSG_SENT_SUCC_FROM_INSTALLED) or 0,
        msg_sent_succ_from_startup=await get_pref(K_MSG_SENT_SUCC_FROM_STARTUP) or 0,
        msg_sent_succ_today=await get_pref(K_MSG_SENT_SUCC_TODAY) or 0,

        msg_sent_fail_from_installed=await get_pref(K_MSG_SENT_FAIL_FROM_INSTALLED) or 0,
        msg_sent_fail_from_startup=await get_pref(K_MSG_SENT_FAIL_FROM_STARTUP) or 0,
        msg_sent_fail_today=await get_pref(K_MSG_SENT_FAIL_TODAY) or 0,
    )


@on_command("消息统计").handle()
async def _handle_message_statistic(matcher: Matcher):
    stat = await get_message_statistic()
    await matcher.send(
        "今日：\n" +
        f"- 接收消息：{stat.msg_recv_today}\n" +
        f"- 发送消息：{stat.msg_sent_succ_today}\n" +
        f"- 发送消息失败：{stat.msg_sent_fail_today}\n" +
        "自NoneBot启动至今：\n" +
        f"- 接收消息：{stat.msg_recv_from_startup}\n" +
        f"- 发送消息：{stat.msg_sent_succ_from_startup}\n" +
        f"- 发送消息失败：{stat.msg_sent_fail_from_startup}\n" +
        "自NoneBot安装至今：\n" +
        f"- 接收消息：{stat.msg_recv_from_installed}\n" +
        f"- 发送消息：{stat.msg_sent_succ_from_installed}\n" +
        f"- 发送消息失败：{stat.msg_sent_fail_from_installed}\n"
    )


__all__ = ("MessageStatistic", "get_message_statistic")
