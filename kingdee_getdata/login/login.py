import json
import time
import hashlib
import requests


class K3CloudLogin:
    def __init__(self, base_url, db_id, user_name, app_id, app_secret, lcid=2052):
        """
        初始化登录对象

        :param base_url: 金蝶 K3Cloud API 的基础 URL
        :param db_id: 数据库 ID
        :param user_name: 用户名
        :param app_id: 应用 ID
        :param app_secret: 应用秘钥
        :param lcid: 本地化语言 ID，默认为 2052 (简体中文)
        """
        self.base_url = base_url if base_url.endswith('/') else base_url + '/'
        self.db_id = db_id
        self.user_name = user_name
        self.app_id = app_id
        self.app_secret = app_secret
        self.lcid = lcid
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json;charset=UTF-8"})
        self.context = None

    def get_sha256_sign(self, arr):
        """
        对数组进行 SHA256 签名

        :param arr: 需要签名的数组
        :return: 返回签名后的字符串
        """
        if not arr:
            return ""
        arr.sort()
        text = "".join(arr)
        sha256 = hashlib.sha256()
        sha256.update(text.encode('utf-8'))
        return sha256.hexdigest().lower()

    def login(self):
        """
        执行登录操作，获取会话
        """
        timestamp = int(time.time())
        sign_arr = [self.db_id, self.user_name, self.app_id, self.app_secret, str(timestamp)]
        sign = self.get_sha256_sign(sign_arr)

        payload = {
            "acctID": self.db_id,
            "username": self.user_name,
            "appId": self.app_id,
            "sign": sign,
            "timestamp": timestamp,
            "lcid": self.lcid
        }

        login_url = self.base_url + "Kingdee.BOS.WebApi.ServicesStub.AuthService.LoginBySign.common.kdsvc"
        try:
            response = self.session.post(login_url, data=json.dumps(payload))

            if response.status_code == 200:
                login_result = response.json()
                result_type = login_result.get("LoginResultType")
                if result_type == 1:
                    self.context = login_result.get("Context")
                    print("登录成功！")
                    return True
                else:
                    print(f"登录失败，错误信息: {login_result.get('Message')}")
                    return False
            else:
                print(f"HTTP 请求失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"登录异常: {e}")
            return False

    def is_logged_in(self):
        """
        判断是否已经登录
        """
        return self.context is not None

    def reset_session(self):
        """
        重置会话
        """
        self.context = None


def execute_login_and_query():
    """
    执行登录和查询的函数
    """
    # 配置信息
    HOST_URL = "http://erp.julan.com.cn:8081/k3cloud/"
    DB_ID = "6644c38845eb69"
    USER_NAME = "王旭阳"
    APP_ID = "334609_073DxbsH6Opb498K3+2BQdVt5qWa5pnI"
    APP_SECRET = "a3ef9df734964a4cb76a63b645c632a3"

    # 1. 初始化登录类
    client = K3CloudLogin(HOST_URL, DB_ID, USER_NAME, APP_ID, APP_SECRET)

    # 2. 执行登录
    if client.login():
        print("登录成功！")
    else:
        print("登录失败。")



