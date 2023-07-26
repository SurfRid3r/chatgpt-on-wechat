# -*- coding: utf-8 -*-#

from bridge.context import ContextType
from channel.chat_message import ChatMessage
from common.log import logger
from channel.wechat_wxhelper.utils.api import WXAPIBot


class WXHelperMessage(ChatMessage):
    def __init__(self, wxapibot: WXAPIBot, msg: dict, is_group=False):
        super().__init__(msg)

        self.msg_id = msg.get("msgId")
        self.create_time = msg.get("timestamp")
        self.is_group = is_group
        # 0表示自己接收了消息 1表示自己发送的消息
        self.isSendMsg = msg.get("isSendMsg")

        # 直接是bot自己的wxid
        self.other_user_id = self.from_user_id = msg.get("fromGroup")
        self.to_user_id = wxapibot.bot_info["user_info"]["wxid"]
        m_type = msg.get("type")
        self.actual_user_id = msg.get("fromUser")
        # 发送者是群id
        if is_group:
            chatroomid = self.from_user_id
            # 获取群聊名称=>group_name_white_list
            self.group_name_white_list = wxapibot.get_ninckname(chatroomid)
        else:
            chatroomid = None

        # 获取群聊中对应用户的nickname
        self.actual_user_nickname = wxapibot.get_ninckname(wxid=self.actual_user_id, chatroomid=self.from_user_id)
        self.other_user_nickname = self.from_user_nickname = wxapibot.get_ninckname(wxid=self.from_user_id, chatroomid=chatroomid)
        self.to_user_nickname = wxapibot.get_ninckname(wxid=self.to_user_id, chatroomid=chatroomid)

        if is_group and f"@{self.to_user_nickname}\u2005" in msg.get("content", ""):
            self.is_at = True

        if m_type == 1:
            self.ctype = ContextType.TEXT
            self.content = msg.get("content")
        elif m_type == 3:
            # TODO 图片处理
            self.ctype = ContextType.IMAGE
            raise NotImplementedError(f"Unknow message Type: {self.ctype}")
        elif m_type == 34:
            # TODO 语音处理
            self.ctype = ContextType.VOICE
            raise NotImplementedError(f"Unknow message Type: {self.ctype}")
        else:
            raise NotImplementedError(f"Unknow message Type: {self.ctype}")
