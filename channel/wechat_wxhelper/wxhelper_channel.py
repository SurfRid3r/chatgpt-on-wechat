# -*- coding: utf-8 -*-
from bridge.context import *
from bridge.reply import *
from channel.chat_channel import ChatChannel
from common.log import logger
from common.singleton import singleton
from config import conf
from channel.wechat_wxhelper.utils.api import WXAPIBot
from channel.wechat_wxhelper.wxhelper_message import WXHelperMessage

# from channel.wechat.wechat_message import *

# # wxhelper的配置
# "wxhelper_wxaddr": "http://127.0.0.1:19088/", # 注入微信后API的地址,
# "wxhelper_hookmsg_host": "127.0.0.1", # 注入微信后监听消息的地址
# "wxhelper_hookmsg_port": "8000",  # 注入微信后监听消息的端口


@singleton
class WXHelperChannel(ChatChannel):
    NOT_SUPPORT_REPLYTYPE = [ReplyType.VOICE, ReplyType.IMAGE, ReplyType.IMAGE_URL]

    def __init__(self):
        super().__init__()
        # wxhelper的API监听地址
        self.wx_addr = conf().get("wxhelper_wxaddr", "http://127.0.0.1:19088/")
        self.wxapibot = WXAPIBot(self.wx_addr)

        # message hook地址
        self.hook_host = conf().get("wxhelper_hookmsg_host", "127.0.0.1")
        self.hook_port = int(conf().get("wxhelper_hookmsg_port", 8000))

    def startup(self):
        # TODO :1.后续添加自动注入并启动微信
        # TODO :2.定时任务
        # 启动listener监听hook msg端口，并且注册处理函数
        from channel.wechat_wxhelper.wxhelper_msgserver import WXBotTCPHandler, WXBotTCPServer

        self.hookmsg_server = WXBotTCPServer((self.hook_host, self.hook_port), WXBotTCPHandler)
        # 注册处理函数
        self.hookmsg_server.register_callback(self.handle_msg)
        # 调用API设置hook messsage server地址
        self.wxapibot.hook_msg(enablehttp="0", hook_ip=self.hook_host, hook_port=self.hook_port)
        # 启动服务器
        self.hookmsg_server.run()

    def handle_msg(self, msg: dict):
        group_id = msg.get("fromGroup")
        user_wxid = msg.get("fromUser")
        # 私聊
        if group_id == user_wxid:
            self.handle_single(msg)
        # 群里
        elif "@chatroom" in group_id:
            self.handle_group(msg)
        # 其余暂不处理
        return {"message": "success"}

    def handle_single(self, msg: dict):
        """
        处理个人私聊信息
        """
        user_white_list = conf().get("wxhelper_user_white_list", [])
        user_wxid = msg.get("fromUser")
        m_type = int(msg.get("type"))
        # 白名单过滤
        if user_wxid not in user_white_list:
            return
        try:
            wxhelper_cmsg = WXHelperMessage(self.wxapibot, msg, is_group=False)
        except NotImplementedError as e:
            logger.debug("[WXHelper] " + str(e))
            return "success"
        # context = channel._compose_context(
        #     wechatcom_msg.ctype,
        #     wechatcom_msg.content,
        #     isgroup=False,
        #     msg=wechatcom_msg,
        # )

    def handle_group(self, msg: dict):
        """
        处理群聊信息
        """
        try:
            wxhelper_cmsg = WXHelperMessage(self.wxapibot, msg, is_group=False)
        except NotImplementedError as e:
            logger.debug("[WXHelper] " + str(e))
            return "success"

    def send(self):
        pass
