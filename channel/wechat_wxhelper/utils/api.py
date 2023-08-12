import requests
import json
from urllib.parse import urljoin
from common.log import logger


class WXHelperError(Exception):
    def __init__(self, message, api_type):
        self.message = "WeChatError: " + str(message)
        self.api_type = api_type


class WXHelperReqError(Exception):
    def __init__(self, api_type, payloads="", repsonse=""):
        self.message = f"API request fail, API type:{api_type}, Payload: {payloads}, Repsonse: {repsonse}"
        logger.error("[WXHelperReqError]" + self.message)


class WXAPIBot:
    def __init__(self, wx_addr):
        # dll注入的监听地址
        self.wx_addr = wx_addr
        # 保存的bot用户信息
        self.bot_info = LazyDict(self)

    def api_request(
        self,
        api_type,
        headers={"Content-Type": "application/json"},
        payloads={},
        max_retries=3,
        timeout=10,
    ):
        url = urljoin(self.wx_addr, f"/api/?type={str(api_type)}")
        retries = 0
        response = {"code": 0, "result": "Fail"}
        while retries < max_retries:
            try:
                req = requests.request("POST", url, headers=headers, data=payloads, timeout=timeout)
                response = req.json()
                break
            except requests.Timeout:
                logger.error(f"[WXAPIBot]API request timeout, API type:{api_type}, Retrying...")
                retries += 1
            except Exception as e:
                logger.error(f"[WXAPIBot]API request fail, API type:{api_type}, Error Info: {e}")
                raise e
        return response

    def check_login(self):
        """
        type=0.检查是否登录
        :return:
            True:登录成功
            False:登录失败
        """
        logger.debug("[WXAPIBot]Checking login status.")
        api_type = "0"
        reponse = self.api_request(api_type)
        if reponse.get("code", 0):
            return True
        raise WXHelperReqError(api_type, repsonse=json.dumps(reponse))

    def get_user_info(self):
        """
        获取登录用户信息
        {"code":1,"data":{"account":"xx","headImage":"https://wx.qlogo.cn/mmhead/ver_1xx","city":"xx","country":"CN","currentDataPath":"C:\\xx\\wxid_xxxxx","dataSavePath":"C:\\xx","mobie":"13812345678","name":"xx","province":"xx","signature":"xx","wxid":"xx","dbKey":"aaa2222"},"result":"OK"}
        wxid
        :return:
        """
        logger.debug("[WXAPIBot]Getting user info.")
        api_type = "1"
        reponse = self.api_request(api_type, headers={})
        if reponse.get("code", 0):
            # self.bot_info["user_info"] = reponse.get("data")
            return reponse.get("data")
        raise WXHelperReqError(api_type="1", repsonse=json.dumps(reponse))

    def send_text_msg(self, msg, wxid="filehelper"):
        """
        向指定用户发送消息文本
        msg: 文本信息
        wxid: 目标用户wxid
        :return:
            response:发送成功 {"code":345686720,"result":"OK"}
            None:发送失败
        """
        logger.debug("[WXAPIBot]Sending text msg.")
        api_type = "2"
        payloads = json.dumps({"wxid": wxid, "msg": msg})
        # 发送文本
        response = self.api_request(api_type, payloads=payloads)
        if response.get("code", 0):
            return response
        else:
            logger.warning(f"[WXAPIBot]Sending text msg fail, Payload: {payloads}, Repsonse: {json.dumps(response)}")
            return None

    def send_msg_at(self, msg, chat_room_id, wxids=["notify@all"]):
        """
        3.向指定聊天群发送at用户文本
        msg: 文本信息
        chat_room_id: 群id
        wxids: at指定的用户数组,默认at所有人
        """
        logger.debug(f"[WXAPIBot]Sending msg at. chatroom:{chat_room_id}, msg:{msg}, at_users:{str(wxids)}.")
        payloads = json.dumps({"wxids": ",".join(wxids), "msg": msg, "chatRoomId": chat_room_id})
        # 发送文本
        response = self.api_request(api_type="3", payloads=payloads)
        if response.get("code", 0):
            return response
        else:
            logger.warning(f"[WXAPIBot]Sending msg at fail, Payload: {payloads}, Repsonse: {json.dumps(response)}")
            return None
    
    def send_img(self, filepath, wxid="filehelper"):
        """
        5.发送图片
        filePath: 图片路径
        wxid: 接收人wxid
        :return:
            reponse:发送成功
            None:发送失败
        """
        logger.debug(f"[WXAPIBot]Sending image: {filepath} .")
        api_type = "5"
        payloads = json.dumps({"wxid": wxid, "imagePath": filepath})
        response = self.api_request(api_type, payloads=payloads)
        if response.get("code", 0):
            return response
        else:
            logger.warning(f"[WXAPIBot]Sending image fail, Payload: {payloads}, Repsonse: {json.dumps(response)}")
            return None

    def send_file_msg(self, filepath, wxid="filehelper"):
        """
        6.向指定用户发送文件
        filePath: 文件路径
        wxid: 接收人wxid
        :return:
            reponse:发送成功
            None:发送失败
        """
        logger.debug(f"[WXAPIBot]Sending file: {filepath} .")
        api_type = "6"
        payloads = json.dumps({"wxid": wxid, "filePath": filepath})
        response = self.api_request(api_type, payloads=payloads)
        if response.get("code", 0):
            return response
        else:
            logger.warning(f"[WXAPIBot]Sending file fail, Payload: {payloads}, Repsonse: {json.dumps(response)}")
            return None

    def hook_msg(
        self,
        enablehttp="1",
        hook_ip="127.0.0.1",
        hook_port="19099",
        hook_url="http://127.0.0.1/19099",
        timeout="10",
        max_retrirs=2,
    ):
        """
        9.hook消息,发送到指定服务器
        enablehttp: 1:发送HTTP请求 0:TCP请求
        hook_ip和hook_port: 如果设置TCP请求,则使用hook_ip和hook_port即 tcp://ip:port
        hook_url: 如果设置HTTP请求,则使用hook_url即
        """
        server_addr = f"tcp://{hook_ip}:{hook_port}"
        if int(enablehttp):
            server_addr = hook_url
        logger.debug(f"[WXAPIBot]Hooking msg, server: {server_addr}.")
        api_type = "9"
        payloads = json.dumps(
            {
                "port": hook_port,
                "ip": hook_ip,
                "enableHttp": enablehttp,
                "url": hook_url,
                "timeout": timeout,
            }
        )
        response = self.api_request(api_type, payloads=payloads)
        # code:1 hook成功
        # code:2 已经存在hook
        # code:3 hook失败
        while max_retrirs:
            if response.get("code", 0) == 1:
                return True
            elif response.get("code", 0) == 2:
                logger.debug(f"[WXAPIBot]Wechat had alerady benn hooked, try to unhook. retrirs:{max_retrirs}...")
                # 取消hook后重新hook
                self.unhook_msg()
                response = self.api_request(api_type, payloads=payloads)
                logger.debug(f"[WXAPIBot]Hooking msg after unhooking, server: {server_addr}.")
                max_retrirs -= 1
            else:
                raise WXHelperReqError(api_type, payloads=payloads, repsonse=json.dumps(response))
        raise WXHelperError(f"Fail to hook,max_retrirs: {max_retrirs}", api_type)

    def unhook_msg(self):
        """
        10.取消hook消息
        """
        logger.debug("[WXAPIBot]UnHooking msg.")
        api_type = "10"
        response = self.api_request(api_type, headers={})
        # code:1 unhook成功
        # code:2 不存在hook
        if response.get("code", 0) == 1:
            return True
        elif response.get("code", 0) == 2:
            logger.debug("[WXAPIBot]Wechat hasn't been hooked.")
        raise WXHelperReqError(api_type, repsonse=json.dumps(response))

    def fetch_chat_room_members(self, chatroomid):
        """
        25.获取指定群的所有群成员及管理员
        :return: members {"admin":"wxid_123","chatRoomId":"485359@chatroom","members":["wxid_7ebbaek22","Gwxid_2x7akw12","Gwxid_v68hxn22"]}
        """
        logger.debug(f"[WXAPIBot]Fetching chat room: {chatroomid} memebers.")
        api_type = "25"
        payloads = json.dumps(
            {
                "chatRoomId": chatroomid,
            }
        )
        response = self.api_request(api_type, payloads=payloads)
        if response.get("code", 0):
            chatroom_info = response.get("data")
            chatroom_info["members"] = chatroom_info["members"].split("^")
            return chatroom_info
        raise WXHelperReqError(api_type, repsonse=json.dumps(response))

    def get_member_nickname(self, chatroomid, wxid):
        """
        26.获取群成员昵称
        :return: nickname str
        """
        logger.debug(f"[WXAPIBot]Fetching chatroom member nickname, chat room: {chatroomid} memebers: {wxid}.")
        api_type = "26"
        payloads = json.dumps({"chatRoomId": chatroomid, "memberId": wxid})
        response = self.api_request(api_type, payloads=payloads)
        if response.get("code", 0):
            return response.get("nickname")
        raise WXHelperReqError(api_type, repsonse=json.dumps(response))

    def get_db_handlers(self):
        """
        32.获取sqlite3的操作句柄
        :return:
            data:获取成功
        """
        logger.debug("[WXAPIBot]Getting db handlers.")
        api_type = "32"
        response = self.api_request(api_type, headers={})
        if response.get("result", "Fail") == "OK":
            # self.bot_info["db_handles"] = response.get("data")
            return response.get("data")
        raise WXHelperReqError(api_type, repsonse=json.dumps(response))

    def query_db_by_sql(self, table_name, sql):
        """
        34.通过sql查询语句
        :return:
            data:sql语句查询的结果为list
            None:查询失败
        """
        logger.debug(f"[WXAPIBot]Querying db by sql: {sql} .")
        api_type = "34"
        if table_name not in sql:
            raise WXHelperError(f"Check querying db sql, Table: {table_name}, SQL: {sql} .", api_type)
        payloads = json.dumps(
            {
                "dbHandle": self.get_dbhandler_by_name(table_name),
                "sql": sql,
            }
        )
        response = self.api_request(api_type, payloads=payloads)
        if response.get("code", 0):
            return response.get("data")
        else:
            logger.warning(f"[WXAPIBot]Querying db by sql Fail. SQL: {sql}, reponse:{json.dumps(response)}")
            return None

    def get_contact_list(self):
        """
        46.获取微信好友列表，聊天群列表，微信公众号列表
        {"code":1,"data":[{"customAccount":"custom","delFlag":0,"type":8388611,"userName":"昵称","verifyFlag":0,"wxid":"wxid_123pcqm22"}]}
        :return:
            data:获取成功
        """
        logger.debug("[WXAPIBot]Getting contact list.")
        api_type = "46"
        response = self.api_request(api_type, headers={})
        if response.get("code", 0):
            return response.get("data")
        raise WXHelperReqError(api_type, repsonse=json.dumps(response))

    def query_nickname(self, wxid):
        """
        55.查询联系人或群名称
        输入wxid或group_id获取nickname
        :return: str
        """
        logger.debug("[WXAPIBot]Querying nickname.")
        api_type = "55"
        payloads = json.dumps(
            {
                "id": wxid,
            }
        )
        response = self.api_request(api_type, payloads=payloads)
        if response.get("code", 0):
            return response.get("name")
        raise WXHelperReqError(api_type, repsonse=json.dumps(response))

    def get_ninckname(self, wxid, chatroomid=None):
        """
        通过wxid获取nickname,如果传入了group_id则获取在群聊中的nickname
        :return: nickname
        """
        if chatroomid:
            nickname = self.get_member_nickname(chatroomid=chatroomid, wxid=wxid)
        else:
            nickname = self.query_nickname(wxid)
        return nickname

    def get_dbhandler_by_name(self, table_name):
        """
        通过table_name获取数据库handler
        :return: db_handler
        """
        for db_info in self.bot_info["db_handles"]:
            db_handler = db_info["handle"]
            for table in db_info["tables"]:
                if table_name == table["name"]:
                    return db_handler
        raise WXHelperError(f"Can't find table_name in db_handles, Table: {table_name}.", api_type="-1")


class LazyDict:
    def __init__(self, wx_bot):
        self.dict = {}
        self.wx_bot = wx_bot

    def __getitem__(self, key):
        if key not in self.dict:
            if key == "user_info":
                self.dict[key] = self.wx_bot.get_user_info()
            elif key == "contact_list":
                self.dict[key] = self.wx_bot.get_contact_list()
            elif key == "db_handles":
                self.dict[key] = self.wx_bot.get_db_handlers()
        return self.dict[key]
