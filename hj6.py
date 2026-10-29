
import asyncio
import base64
import gzip
import json
import logging
import os
import re
import secrets
import smtplib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from typing import Dict

import aiohttp

# ========== 可修改配置 ==========
# 【配置开始】
USER_EMAIL = "banjiu1625@163.com"
USER_PS = "画加订单，请在两分钟内打开画加→我的→橱窗购买  进行支付"

SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465
EMAIL_USER = ""
EMAIL_PASSWORD = ""

REQUEST_INTERVAL = 0.005
RANDOM_MODE_CHECK_INTERVAL = 10
TIMING_MODE_CHECK_INTERVAL = 60
MIN_WAIT_THRESHOLD = 30
PRECISION_OFFSET = 0
MAX_REQUESTS = 200
CONNECTOR_LIMIT = 200
CONNECTOR_LIMIT_PER_HOST = 100
KEEPALIVE_TIMEOUT = 60
PREWARM_BEFORE_SECONDS = 2

DEBUG_MODE = True

# 换 sid 请求头（按抓包）
LOGIN_CLIENT_VERSION = "a3.15.1"
LOGIN_USER_AGENT = "okhttp/5.3.2"
LOGIN_TIMEZONE = "Asia/Hong_Kong"

# 设备指纹默认值（生成设备ID时用）
DEFAULT_RESOLUTION = "1272*2659"
DEFAULT_CARRIER = "中国电信"
DEFAULT_NETWORK = "UNKNOWN"

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "huajia_config.json")
# 【配置结束】

DEVICE_ID = ""
USER_COOKIE = ""
logger = None


# ============================================================
# 日志
# ============================================================
def setup_logging(goods_id):
    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"huajia_order_{goods_id}_{timestamp}.log")
    logging.basicConfig(
        level=logging.INFO if DEBUG_MODE else logging.WARNING,
        format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def log_debug(msg):
    if DEBUG_MODE and logger:
        logger.info(msg)


def log_info(msg):
    if logger:
        logger.warning(msg)
    else:
        print(msg)


# ============================================================
# 纯 Python AES-128（FIPS-197）
# ============================================================
_SBOX = bytes([
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
])
_INV_SBOX = bytearray(256)
for _i in range(256):
    _INV_SBOX[_SBOX[_i]] = _i
_INV_SBOX = bytes(_INV_SBOX)

_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]


def _xtime(a):
    a <<= 1
    if a & 0x100:
        a ^= 0x11b
    return a & 0xff


def _gmul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        b >>= 1
        a = _xtime(a)
    return r


_GMUL_2  = bytes(_xtime(x) for x in range(256))
_GMUL_3  = bytes(_xtime(x) ^ x for x in range(256))
_GMUL_9  = bytes(_gmul(x, 9)  for x in range(256))
_GMUL_11 = bytes(_gmul(x, 11) for x in range(256))
_GMUL_13 = bytes(_gmul(x, 13) for x in range(256))
_GMUL_14 = bytes(_gmul(x, 14) for x in range(256))


class _AES128:
    def __init__(self, key: bytes):
        if len(key) != 16:
            raise ValueError("AES-128 key 必须是 16 字节")
        self._rks = self._expand_key(key)

    @staticmethod
    def _expand_key(key: bytes):
        w = [list(key[i:i + 4]) for i in range(0, 16, 4)]
        for i in range(4, 44):
            t = list(w[i - 1])
            if i % 4 == 0:
                t = t[1:] + t[:1]
                t = [_SBOX[x] for x in t]
                t[0] ^= _RCON[i // 4 - 1]
            w.append([w[i - 4][j] ^ t[j] for j in range(4)])
        return [bytes(sum(w[r * 4:(r + 1) * 4], [])) for r in range(11)]

    @staticmethod
    def _add_rk(state, rk):
        return bytes(a ^ b for a, b in zip(state, rk))

    @staticmethod
    def _sub(state):
        return bytes(_SBOX[b] for b in state)

    @staticmethod
    def _inv_sub(state):
        return bytes(_INV_SBOX[b] for b in state)

    @staticmethod
    def _shift(state):
        s = state
        return bytes([
            s[0],  s[5],  s[10], s[15],
            s[4],  s[9],  s[14], s[3],
            s[8],  s[13], s[2],  s[7],
            s[12], s[1],  s[6],  s[11],
        ])

    @staticmethod
    def _inv_shift(state):
        s = state
        return bytes([
            s[0],  s[13], s[10], s[7],
            s[4],  s[1],  s[14], s[11],
            s[8],  s[5],  s[2],  s[15],
            s[12], s[9],  s[6],  s[3],
        ])

    @staticmethod
    def _mix(state):
        out = [0] * 16
        for c in range(4):
            a0, a1, a2, a3 = state[c * 4:c * 4 + 4]
            out[c * 4 + 0] = _GMUL_2[a0] ^ _GMUL_3[a1] ^ a2 ^ a3
            out[c * 4 + 1] = a0 ^ _GMUL_2[a1] ^ _GMUL_3[a2] ^ a3
            out[c * 4 + 2] = a0 ^ a1 ^ _GMUL_2[a2] ^ _GMUL_3[a3]
            out[c * 4 + 3] = _GMUL_3[a0] ^ a1 ^ a2 ^ _GMUL_2[a3]
        return bytes(out)

    @staticmethod
    def _inv_mix(state):
        out = [0] * 16
        for c in range(4):
            a0, a1, a2, a3 = state[c * 4:c * 4 + 4]
            out[c * 4 + 0] = _GMUL_14[a0] ^ _GMUL_11[a1] ^ _GMUL_13[a2] ^ _GMUL_9[a3]
            out[c * 4 + 1] = _GMUL_9[a0]  ^ _GMUL_14[a1] ^ _GMUL_11[a2] ^ _GMUL_13[a3]
            out[c * 4 + 2] = _GMUL_13[a0] ^ _GMUL_9[a1]  ^ _GMUL_14[a2] ^ _GMUL_11[a3]
            out[c * 4 + 3] = _GMUL_11[a0] ^ _GMUL_13[a1] ^ _GMUL_9[a2]  ^ _GMUL_14[a3]
        return bytes(out)

    def encrypt_block(self, blk: bytes) -> bytes:
        s = self._add_rk(blk, self._rks[0])
        for r in range(1, 10):
            s = self._sub(s)
            s = self._shift(s)
            s = self._mix(s)
            s = self._add_rk(s, self._rks[r])
        s = self._sub(s)
        s = self._shift(s)
        s = self._add_rk(s, self._rks[10])
        return s

    def decrypt_block(self, blk: bytes) -> bytes:
        s = self._add_rk(blk, self._rks[10])
        for r in range(9, 0, -1):
            s = self._inv_shift(s)
            s = self._inv_sub(s)
            s = self._add_rk(s, self._rks[r])
            s = self._inv_mix(s)
        s = self._inv_shift(s)
        s = self._inv_sub(s)
        s = self._add_rk(s, self._rks[0])
        return s


# 请求 params 和响应 msg 共用同一把密钥（抓包确认）
_AES_KEY = bytes.fromhex("48ec81b2854d2bf643836a1bec8a9ce7")
_AES_CIPHER = _AES128(_AES_KEY)


def _aes_ecb_encrypt_raw(data: bytes) -> bytes:
    return b"".join(
        _AES_CIPHER.encrypt_block(data[i:i + 16])
        for i in range(0, len(data), 16)
    )


def _aes_ecb_decrypt_raw(data: bytes) -> bytes:
    return b"".join(
        _AES_CIPHER.decrypt_block(data[i:i + 16])
        for i in range(0, len(data), 16)
    )


def _pkcs7_strip(raw: bytes) -> bytes:
    if raw:
        pad = raw[-1]
        if 1 <= pad <= 16:
            raw = raw[:-pad]
    return raw


def _aes_encrypt_hex(text: str) -> str:
    data = text.encode("utf-8")
    pad = 16 - len(data) % 16
    data += bytes([pad]) * pad
    return _aes_ecb_encrypt_raw(data).hex()


def _aes_decrypt_hex(text: str) -> str:
    return _pkcs7_strip(_aes_ecb_decrypt_raw(bytes.fromhex(text))).decode("utf-8", "replace")


def _decode_msg_blob(msg) -> bytes:
    if msg is None:
        raise ValueError("msg 为 None")
    s = str(msg).strip()
    if not s:
        raise ValueError("msg 为空字符串")
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    try:
        return bytes.fromhex(s)
    except ValueError:
        pass
    try:
        return base64.b64decode(s, validate=True)
    except Exception:
        pass
    compact = re.sub(r"\s+", "", s)
    if compact != s:
        try:
            return bytes.fromhex(compact)
        except ValueError:
            pass
    raise ValueError(f"msg 既不是 hex 也不是 base64（长度 {len(s)}，前 80 字符：{s[:80]!r}）")


def _decrypt_msg(msg) -> str:
    raw = _decode_msg_blob(msg)
    if len(raw) % 16 != 0:
        raise ValueError(f"msg 长度 {len(raw)} 不是 16 的倍数")
    return _pkcs7_strip(_aes_ecb_decrypt_raw(raw)).decode("utf-8", "replace")


def self_test_aes() -> bool:
    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    pt = bytes.fromhex("00112233445566778899aabbccddeeff")
    want = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    c = _AES128(key)
    ct = c.encrypt_block(pt)
    if ct != want:
        raise AssertionError(f"AES encrypt 失败: {ct.hex()} != {want.hex()}")
    if c.decrypt_block(ct) != pt:
        raise AssertionError("AES decrypt 失败")

    sample = "rtid=abc&mobile=13800138000&password=test"
    h = _aes_encrypt_hex(sample)
    if len(h) % 32 != 0:
        raise AssertionError("请求加密输出不是 16 字节对齐")

    raw = sample.encode("utf-8")
    pad = 16 - len(raw) % 16
    raw += bytes([pad]) * pad
    ct2 = b"".join(
        _AES_CIPHER.encrypt_block(raw[i:i + 16])
        for i in range(0, len(raw), 16)
    )
    if _decrypt_msg(ct2.hex()) != sample:
        raise AssertionError("响应解密 roundtrip(hex) 失败")
    if _decrypt_msg(base64.b64encode(ct2).decode()) != sample:
        raise AssertionError("响应解密 roundtrip(base64) 失败")
    if _is_plain_ok("ok") is not True:
        raise AssertionError('"ok" 识别失败')
    return True


# ============================================================
# 登录协议（按抓包对齐）
# ============================================================
# URS id / 换 sid 的 app_id 是同一个值
_URS_APP_ID = (
    "903BFC7A4AC32A2AF85D29438B2EE184"
    "7CDEC8371C99D0CAC45A3268F61317F0"
    "B6F0E44087D61EFC06BE92279CD6EEC6"
)
# mConfig 每次会话会变，抓包里是 @c9a9149；服务端通常不严格校验
_URS_MCONFIG = "com.netease.loginapi.i@c9a9149"

_URL_LOGIN1 = "https://sdk.reg.163.com/interfaces/yd/login1.do"
_URL_LOGIN2 = "https://sdk.reg.163.com/interfaces/yd/login2.do"
_URL_PWD_LOGIN = "https://sdk.reg.163.com/interfaces/yd/pwdlogin.do"
_URL_APP_LOGIN = "https://huajia.163.com/napp/account/login/app"

_URS_HEADERS = {
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "yd-version": "2.4.9.4",
    "yd-version-code": "21041401",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 16; PLC110 Build/BP2A.250605.015)",
    "Host": "sdk.reg.163.com",
    "Accept-Encoding": "gzip",
}

_CHINA = "86"
_LOGIN_REASONS = {
    "415": "登录过于频繁，请稍后再试",
    "427": "客户端版本参数无效",
    "401": "上游不接受该号码格式（检查区号与号码）",
}


def _wire_mobile(mobile: str) -> str:
    text = str(mobile or "").strip()
    if "-" in text:
        head, _, tail = text.partition("-")
        head_digits = re.sub(r"\D", "", head)
        local = re.sub(r"\D", "", tail)
        if head_digits and 1 <= len(head_digits) <= 3:
            return local if head_digits == _CHINA else f"{head_digits}-{local}"
    digits = re.sub(r"\D", "", text)
    if text.startswith("+") and digits.startswith(_CHINA) and len(digits) - len(_CHINA) >= 10:
        return digits[len(_CHINA):]
    return digits


def _post_form(url: str, data: dict, headers: dict, cookies=None):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    if cookies:
        clean = []
        for item in cookies:
            head = item.split(";", 1)[0].strip()
            if head and "=" in head:
                clean.append(head)
        if clean:
            req.add_header("Cookie", "; ".join(clean))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", "replace"), (resp.headers.get_all("Set-Cookie") or [])
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        if exc.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace"), (exc.headers.get_all("Set-Cookie") or [])


def _json_or_empty(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        return {}


def _cookie_value(set_cookies, name: str) -> str:
    for item in set_cookies or []:
        head = item.split(";", 1)[0]
        if head.strip().startswith(name + "="):
            return head.split("=", 1)[1].strip()
    return ""


def _device_fields(uid_short: str, uid_long: str) -> str:
    
    return (
        f"uniqueID={uid_short}&uniqueID_cf={uid_short}&"
        f"resolution={urllib.parse.quote(DEFAULT_RESOLUTION)}&"
        f"carrier={urllib.parse.quote(DEFAULT_CARRIER)}&"
        f"network={DEFAULT_NETWORK}&"
        f"isEmulator=0&"
        f"longitude=default&latitude=default&imei=default&mac=default&"
        f"androidID={DEVICE_ID}&"
        f"systemVersion=36&deviceType=PLC110&product=huajia&systemName=android&"
        f"ydUniqueId={uid_long}"
    )


def _urs_post(url: str, plain: str):
    hex_params = _aes_encrypt_hex(plain)
    text, set_cookies = _post_form(
        url,
        {"params": hex_params, "id": _URS_APP_ID, "mConfig": _URS_MCONFIG},
        _URS_HEADERS,
    )
    return _json_or_empty(text), text, set_cookies


def _is_plain_ok(msg) -> bool:
    return str(msg).strip().lower() in ("ok", '"ok"', "'ok'")


def _parse_msg_fields(msg) -> dict:
    if msg is None:
        return {}
    plain_token = _decrypt_msg(msg).split("#")[0]
    fields = {}
    for chunk in plain_token.split("&"):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            fields[k] = v
    return fields


def _extract_token(payload: dict, text: str) -> str:
    code = str(payload.get("result", "?"))
    if code not in ("200", "201"):
        detail = payload.get("cnMsg") or payload.get("msg") or text[:200]
        raise RuntimeError(f"登录失败[{code}]：{detail}")
    msg = payload.get("msg")
    if msg is None:
        raise RuntimeError(f"登录成功但没有 msg，原始响应：{text[:300]}")
    if _is_plain_ok(msg):
        raise RuntimeError(f"登录成功但 msg 为 'ok'，无 token；原始响应：{text[:300]}")
    try:
        fields = _parse_msg_fields(msg)
    except Exception as e:
        raise RuntimeError(f"msg 解密失败：{e}；原始响应：{text[:300]}")
    token = fields.get("token", "")
    if not token:
        raise RuntimeError(f"msg 里没有 token：{fields}；原始响应：{text[:300]}")
    return token


def _login_sid_headers() -> dict:
    # 按抓包：cv=a3.15.1, UA=okhttp/5.3.2, 时区 Asia/Hong_Kong, Cookie: sid=
    return {
        "X-Requested-With": "XMLHttpRequest",
        "x-csrf-token": "",
        "app-color-mode": "0",
        "cv": LOGIN_CLIENT_VERSION,
        "deviceid": DEVICE_ID,
        "Cookie": "sid=",
        "X-Android-Requester-Version": "1",
        "x-channel": "oppo",
        "X-PS-Timezone-ID": LOGIN_TIMEZONE,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": LOGIN_USER_AGENT,
    }


def _exchange_sid(urs_token: str) -> str:
    # app_id 就是 URS 的 id（903BFC7A…），不是 E35ADB2A…
    data = {
        "urs_token": urs_token,
        "app_id": _URS_APP_ID,
        "login_type": "2",
        "maf": "OnePlus",
        "model": "PLC110",
        "channel": "oppo",
        "resolution": "1272x2800",
        "screen_size": "6.83",
        "rom_version": "16",
    }
    text, set_cookies = _post_form(_URL_APP_LOGIN, data, _login_sid_headers())
    payload = _json_or_empty(text)
    code = payload.get("code")
    if code != 200:
        raise RuntimeError(
            f"换 sid 失败 code={code} "
            f"{payload.get('error') or payload.get('msg') or text[:200]}"
        )
    session = (payload.get("data") or {}).get("session") or {}
    sid = _cookie_value(set_cookies, "sid") or str(session.get("sid") or "")
    if not sid:
        raise RuntimeError("画加返回成功但没有下发 sid（可能触发风控，需要在 App 内重新登录）")
    return sid


def login_by_password(mobile: str, password: str) -> str:
    """密码登录（明文结构参照验证码登录的 device_fields，密码字段按抓包推测）"""
    if not mobile or not password:
        raise RuntimeError("手机号和密码不能为空")
    uid_short = secrets.token_hex(20)
    uid_long = secrets.token_hex(64)
    rtid = secrets.token_hex(16)
    plain = (
        f"rtid={rtid}&pdtVersion=3.15.1&"
        f"{_device_fields(uid_short, uid_long)}&"
        f"password={urllib.parse.quote(password, safe='')}&isMd5=0&"
        f"mobile={_wire_mobile(mobile)}&loginException=3&needLeakInfo=1"
    )
    payload, text, _ = _urs_post(_URL_PWD_LOGIN, plain)
    token = _extract_token(payload, text)
    return _exchange_sid(token)


def send_sms_code(mobile: str):
    """
    login1 发短信，返回 (uid_short, uid_long)。
    login2 必须复用同一对 uid，设备指纹才一致。
    """
    if not mobile:
        raise RuntimeError("手机号不能为空")
    uid_short = secrets.token_hex(20)   # 40 hex
    uid_long = secrets.token_hex(64)    # 128 hex
    rtid = secrets.token_hex(16)
    plain = (
        f"rtid={rtid}&pdtVersion=3.15.1&"
        f"{_device_fields(uid_short, uid_long)}&"
        f"mobile={_wire_mobile(mobile)}&referer="
    )
    payload, text, _ = _urs_post(_URL_LOGIN1, plain)
    code = str(payload.get("result", "?"))
    if code not in ("200", "201"):
        detail = payload.get("cnMsg") or payload.get("msg") or text[:200]
        raise RuntimeError(f"发送验证码失败[{code}]：{detail}")
    return uid_short, uid_long


def verify_sms_code(mobile: str, smscode: str, uid_short: str, uid_long: str) -> str:

    if not smscode:
        raise RuntimeError("验证码不能为空")
    rtid = secrets.token_hex(16)
    plain = (
        f"rtid={rtid}&pdtVersion=3.15.1&"
        f"{_device_fields(uid_short, uid_long)}&"
        f"smscode={urllib.parse.quote(smscode, safe='')}&"
        f"mobile={_wire_mobile(mobile)}&"
        f"loginException=3&needLeakInfo=1"
    )
    payload, text, _ = _urs_post(_URL_LOGIN2, plain)
    token = _extract_token(payload, text)
    return _exchange_sid(token)


# ============================================================
# 配置文件
# ============================================================
def _load_config_file() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        log_info(f"读取配置文件失败: {e}")
        return {}


def _save_config_file(data: dict):
    try:
        data["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_info(f"配置已保存到 {CONFIG_FILE}")
    except Exception as e:
        log_info(f"保存配置文件失败: {e}")


def _login_flow() -> bool:
    global USER_COOKIE
    print("\n请选择登录方式:")
    print("  1. 密码登录")
    print("  2. 验证码登录")
    while True:
        choice = input("\n请选择 (1/2): ").strip()
        if choice in ("1", "2"):
            break
        print("无效选择")
    try:
        if choice == "1":
            mobile = input("手机号: ").strip()
            password = input("密码: ").strip()
            sid = login_by_password(mobile, password)
        else:
            mobile = input("手机号: ").strip()
            print("正在发送验证码...")
            uid_short, uid_long = send_sms_code(mobile)
            print("短信已发送")
            smscode = input("请输入短信验证码: ").strip()
            sid = verify_sms_code(mobile, smscode, uid_short, uid_long)
    except Exception as exc:
        log_info(f"登录失败：{exc}")
        return False
    USER_COOKIE = f"sid={sid}"
    log_info(f"✓ 登录成功，sid={sid}")
    return True


def init_identity() -> bool:
    global DEVICE_ID, USER_COOKIE
    cfg = _load_config_file()

    device_id = (cfg.get("device_id") or "").strip()
    if not device_id:
        device_id = secrets.token_hex(8)
        print(f"\n未找到设备ID，已自动生成: {device_id}")
        print("（该 ID 会与登录后的 sid 绑定并固定使用；如需更换请编辑 huajia_config.json）")
        cfg["device_id"] = device_id
        _save_config_file(cfg)
        log_info(f"设备ID 已生成并保存: {device_id}")
    DEVICE_ID = device_id

    saved_sid = (cfg.get("sid") or "").strip()
    if saved_sid:
        print(f"\n检测到配置文件中的 sid: {saved_sid[:20]}{'...' if len(saved_sid) > 20 else ''}")
        print("  [回车] 使用此 sid")
        print("  [r] 重新登录（覆盖配置）")
        choice = input("选择: ").strip().lower()
        if choice != "r":
            USER_COOKIE = f"sid={saved_sid}"
            log_info("使用配置文件中的 sid")
            return True
        log_info("用户选择重新登录")

    if not _login_flow():
        return False

    cfg = _load_config_file()
    cfg["device_id"] = DEVICE_ID
    cfg["sid"] = USER_COOKIE[len("sid="):]
    _save_config_file(cfg)
    return True


# ============================================================
# 工具
# ============================================================
def extract_goods_id(input_str):
    input_str = input_str.strip()
    pattern = r'https?://huajia\.163\.com/main/goods/details/([A-Za-z0-9]+)'
    match = re.search(pattern, input_str)
    if match:
        return match.group(1)
    if re.match(r'^[A-Za-z0-9]+$', input_str):
        return input_str
    return None


class EmailNotifier:
    @staticmethod
    def send_email(subject: str, content: str, goods_id: str, to_email: str = USER_EMAIL) -> bool:
        if not to_email or not EMAIL_USER or not EMAIL_PASSWORD:
            log_info("未配置邮箱，跳过邮件发送")
            return False
        try:
            msg = MIMEText(content, 'plain', 'utf-8')
            msg['From'] = Header(f"画加订单系统<{EMAIL_USER}>")
            msg['To'] = Header(to_email)
            msg['Subject'] = Header(subject)
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.sendmail(EMAIL_USER, [to_email], msg.as_string())
            log_info("邮件发送成功")
            return True
        except Exception as e:
            log_info(f"邮件发送失败: {str(e)}")
            return False


# ============================================================
# 抢单模块
# ============================================================
class GoodsChecker:
    def __init__(self, goods_id, shared_session):
        self.goods_id = goods_id
        self.shared_session = shared_session

    async def get_goods_info(self) -> Dict:
        detail_url = f"https://huajia.163.com/napp/store/goods/detail?goods_id={self.goods_id}"
        async with self.shared_session.get(detail_url) as resp:
            if resp.status != 200:
                raise Exception(f"获取商品详情失败，状态码：{resp.status}")
            data = await resp.json()
            if data.get("code") != 200:
                raise Exception(f"商品详情接口返回错误：{data}")
            return data["data"]["goods"]


class OrderManager:
    def __init__(self, goods_id, shared_session):
        self.goods_id = goods_id
        self.shared_session = shared_session
        self.payload = None
        self.success = False
        self.success_result = None
        self.success_request_id = 0
        self._start_time = None
        self._success_lock = asyncio.Lock()
        self._request_count = 0
        self._all_results = []

    async def prepare_order(self, goods_info):
        agreement_url = (
            f"https://huajia.163.com/app/v1/config/agreement?"
            f"token=zNHIQXZN6I7aWdltW4bURY9DPCsL6dFgvugOoInV5UagysGrhoLFt4Fw2LKsaOgu&"
            f"id=116&target=buy_goods&goods_id={self.goods_id}"
        )
        self.payload = {
            "goods_id": self.goods_id,
            "agreement_urls": [agreement_url],
            "version": goods_info["version"],
            "price": goods_info["price"]
        }
        log_debug("订单数据准备完成")

    async def submit_order_with_method(self, request_id: int, pay_method: str):
        if self.success or not self.payload:
            return False
        payload = self.payload.copy()
        payload["pay_method"] = pay_method
        create_url = "https://huajia.163.com/napp/store/order/create"
        send_time = time.time()
        send_time_str = datetime.fromtimestamp(send_time).strftime('%H:%M:%S.%f')[:-3]
        try:
            async with self.shared_session.post(create_url, json=payload) as resp:
                recv_time = time.time()
                recv_time_str = datetime.fromtimestamp(recv_time).strftime('%H:%M:%S.%f')[:-3]
                result = await resp.json()
                request_elapsed = (recv_time - send_time) * 1000
                total_elapsed = (recv_time - self._start_time) * 1000 if self._start_time else 0
                self._request_count += 1
                self._all_results.append({
                    'request_id': request_id, 'pay_method': pay_method,
                    'send_time': send_time_str, 'recv_time': recv_time_str,
                    'request_elapsed': request_elapsed, 'total_elapsed': total_elapsed,
                    'http_status': resp.status, 'code': result.get('code'),
                    'error': result.get('error', ''), 'extra': result.get('extra', ''),
                })
                if result.get("code") == 200:
                    status_icon = "✅成功"
                elif result.get("code") == 1000 and (
                        "库存不足" in result.get("error", "") or result.get("extra") == "out_of_stock"):
                    status_icon = "❌库存不足"
                elif result.get("code") == 1000:
                    status_icon = "❌code=1000"
                else:
                    status_icon = f"❌code={result.get('code')}"
                log_debug(
                    f"[#{request_id}][{pay_method}] {send_time_str}→{recv_time_str} | "
                    f"耗时:{request_elapsed:.1f}ms | 总耗时:{total_elapsed:.0f}ms | "
                    f"HTTP:{resp.status} | {status_icon} | "
                    f"error:\"{result.get('error', '')}\" | extra:\"{result.get('extra', '')}\""
                )
                if result.get("code") == 200:
                    async with self._success_lock:
                        if not self.success:
                            self.success = True
                            self.success_result = result
                            self.success_request_id = request_id
                            log_info("🎉 抢单成功！")
                            return True
                return False
        except asyncio.TimeoutError:
            fail_time = time.time()
            fail_time_str = datetime.fromtimestamp(fail_time).strftime('%H:%M:%S.%f')[:-3]
            elapsed = (fail_time - send_time) * 1000
            log_debug(f"[#{request_id}][{pay_method}] {send_time_str}→{fail_time_str} | 耗时:{elapsed:.1f}ms | ⏱️超时")
            self._all_results.append({
                'request_id': request_id, 'pay_method': pay_method,
                'send_time': send_time_str, 'recv_time': fail_time_str,
                'request_elapsed': elapsed, 'error': '超时'
            })
            return False
        except (aiohttp.ClientConnectionError, aiohttp.ServerDisconnectedError) as e:
            fail_time = time.time()
            fail_time_str = datetime.fromtimestamp(fail_time).strftime('%H:%M:%S.%f')[:-3]
            elapsed = (fail_time - send_time) * 1000
            log_debug(f"[#{request_id}][{pay_method}] {send_time_str}→{fail_time_str} | 耗时:{elapsed:.1f}ms | 🔌{type(e).__name__}")
            self._all_results.append({
                'request_id': request_id, 'pay_method': pay_method,
                'send_time': send_time_str, 'recv_time': fail_time_str,
                'request_elapsed': elapsed, 'error': type(e).__name__
            })
            return False
        except Exception as e:
            fail_time = time.time()
            fail_time_str = datetime.fromtimestamp(fail_time).strftime('%H:%M:%S.%f')[:-3]
            elapsed = (fail_time - send_time) * 1000
            log_debug(f"[#{request_id}][{pay_method}] {send_time_str}→{fail_time_str} | 耗时:{elapsed:.1f}ms | ❌{type(e).__name__}:{str(e)[:50]}")
            self._all_results.append({
                'request_id': request_id, 'pay_method': pay_method,
                'send_time': send_time_str, 'recv_time': fail_time_str,
                'request_elapsed': elapsed, 'error': f'{type(e).__name__}:{str(e)[:50]}'
            })
            return False

    def notify_result(self, success: bool, data=None, error_msg: str = ""):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        goods_url = f"https://huajia.163.com/main/goods/details/{self.goods_id}"
        if DEBUG_MODE and logger:
            log_info(f"\n{'='*80}")
            log_info(f"📊 抢单结束统计")
            log_info(f"{'='*80}")
            log_info(f"总完成请求数: {self._request_count}")
            if self._all_results:
                code_200 = [r for r in self._all_results if r.get('code') == 200]
                code_1000_stock = [r for r in self._all_results if r.get('code') == 1000 and (
                            '库存不足' in str(r.get('error', '')) or r.get('extra') == 'out_of_stock')]
                code_1000_other = [r for r in self._all_results if
                                   r.get('code') == 1000 and r not in code_1000_stock]
                other_code = [r for r in self._all_results if r.get('code') not in [200, 1000] and 'code' in r]
                conn_error = [r for r in self._all_results if 'error' in r and 'code' not in r]
                log_info(f"✅ 成功 (code=200):       {len(code_200)} 次")
                log_info(f"❌ 库存不足 (code=1000):  {len(code_1000_stock)} 次")
                log_info(f"❌ 其他1000错误:         {len(code_1000_other)} 次")
                log_info(f"❌ 其他code:             {len(other_code)} 次")
                log_info(f"❌ 连接/超时:            {len(conn_error)} 次")
                times = [r.get('request_elapsed', 0) for r in self._all_results if r.get('request_elapsed')]
                if times:
                    log_info(f"\n⏱️ 请求耗时: 平均{sum(times) / len(times):.1f}ms | 最快{min(times):.1f}ms | 最慢{max(times):.1f}ms")
                log_info(f"\n📋 所有请求详情:")
                for r in sorted(self._all_results, key=lambda x: x.get('request_id', 0)):
                    rid = r.get('request_id', '?')
                    pm = r.get('pay_method', '?')
                    st = r.get('send_time', '?')
                    rt = r.get('recv_time', '?')
                    el = r.get('request_elapsed', 0)
                    code = r.get('code', 'N/A')
                    error = r.get('error', '')[:40]
                    if r.get('code') == 200:
                        status = "✅"
                    elif r.get('code') == 1000 and '库存不足' in str(error):
                        status = "❌缺货"
                    elif r.get('code') == 1000:
                        status = "❌1K"
                    elif '超时' in str(error):
                        status = "⏱️"
                    elif 'error' in r:
                        status = "🔌"
                    else:
                        status = "❌"
                    log_info(f"#{rid:>3} {pm:6} {st}→{rt} {el:6.1f}ms {status} code={code} {error}")
            log_info(f"{'='*80}\n")
        if success:
            subject = f"🎉 画加订单抢单成功 - {self.goods_id}"
            content = (
                f"商品链接：{goods_url}\n"
                f"抢单时间：{current_time}\n"
                f"成功请求编号：#{self.success_request_id}\n"
                f"总请求数：{self._request_count}\n\n"
                f"{USER_PS}"
            )
            if data:
                content += f"\n\n服务器返回: {json.dumps(data, ensure_ascii=False)}"
            log_info(f"🎉 抢单成功！商品ID: {self.goods_id}")
        else:
            subject = f"❌ 画加订单抢单失败 - {self.goods_id}"
            content = f"商品链接：{goods_url}\n时间：{current_time}\n原因：{error_msg}\n总请求数：{self._request_count}"
            log_info(f"❌ 抢单失败: {error_msg}")
        if USER_EMAIL and EMAIL_USER and EMAIL_PASSWORD:
            EmailNotifier.send_email(subject, content, self.goods_id, USER_EMAIL)
        else:
            print(f"\n{'='*50}\n{subject}\n{content}\n{'='*50}\n")


class AutoOrderSystem:
    def __init__(self, goods_id):
        self.goods_id = goods_id
        base_headers = {
            "Host": "huajia.163.com",
            "x-requested-with": "XMLHttpRequest",
            "app-color-mode": "0",
            "cv": "a2.75.0",
            "deviceid": DEVICE_ID,
            "content-type": "application/json",
            "cookie": USER_COOKIE,
            "x-android-requester-version": "1",
            "accept-encoding": "gzip",
            "user-agent": "okhttp/4.11.0"
        }
        self.connector = aiohttp.TCPConnector(
            ssl=False,
            limit=CONNECTOR_LIMIT,
            limit_per_host=CONNECTOR_LIMIT_PER_HOST,
            ttl_dns_cache=600,
            use_dns_cache=True,
            keepalive_timeout=KEEPALIVE_TIMEOUT,
            enable_cleanup_closed=True,
            force_close=False,
        )
        timeout = aiohttp.ClientTimeout(total=3, connect=1)
        self.shared_session = aiohttp.ClientSession(
            headers=base_headers,
            connector=self.connector,
            timeout=timeout
        )
        self.goods_checker = GoodsChecker(goods_id, self.shared_session)
        self.order_manager = OrderManager(goods_id, self.shared_session)
        self._stop_event = asyncio.Event()
        self._pending_tasks = set()

    async def warmup_connections(self):
        log_debug("🔥 预热连接池...")
        warmup_start = time.time()
        detail_url = f"https://huajia.163.com/napp/store/goods/detail?goods_id={self.goods_id}"
        create_url = "https://huajia.163.com/napp/store/order/create"

        async def warmup_detail():
            try:
                async with self.shared_session.get(detail_url) as resp:
                    await resp.read()
            except Exception:
                pass

        async def warmup_create():
            try:
                async with self.shared_session.options(create_url) as resp:
                    pass
            except Exception:
                pass

        tasks = []
        for _ in range(10):
            tasks.append(warmup_detail())
            tasks.append(warmup_create())
        await asyncio.gather(*tasks, return_exceptions=True)
        log_debug(f"预热完成，耗时 {(time.time() - warmup_start) * 1000:.1f}ms")

    async def timing_mode(self):
        log_info(f"启动定时模式，商品ID: {self.goods_id}")
        try:
            await self.warmup_connections()
            goods_info = await self.goods_checker.get_goods_info()
            log_debug(f"商品: 价格={goods_info.get('price')}, 库存={goods_info.get('stock')}")
            stock = goods_info.get("stock", 0)
            scheduled_time = goods_info.get("scheduled_sale_time")
            if not scheduled_time:
                if stock > 0:
                    log_info("商品已开售，立即抢单！")
                    await self._start_ordering_continuous(goods_info)
                else:
                    log_info("商品已售罄")
                    self.order_manager.notify_result(False, error_msg="商品已售罄")
                return
            await self.order_manager.prepare_order(goods_info)
            await self._wait_and_order(goods_info, scheduled_time)
        except Exception as e:
            log_info(f"定时模式出错: {str(e)}")
            import traceback
            log_debug(traceback.format_exc())
            self.order_manager.notify_result(False, error_msg=str(e))

    async def _wait_and_order(self, goods_info, scheduled_time):
        target_ts = scheduled_time - PRECISION_OFFSET
        now_ts = time.time()
        wait_seconds = target_ts - now_ts
        log_debug(f"目标: {datetime.fromtimestamp(scheduled_time).strftime('%H:%M:%S.%f')[:-3]}, "
                  f"当前: {datetime.fromtimestamp(now_ts).strftime('%H:%M:%S.%f')[:-3]}, "
                  f"剩余: {wait_seconds:.3f}秒")
        while wait_seconds > MIN_WAIT_THRESHOLD and not self._stop_event.is_set():
            check_interval = min(wait_seconds - MIN_WAIT_THRESHOLD, TIMING_MODE_CHECK_INTERVAL)
            if check_interval > 0:
                await asyncio.sleep(check_interval)
                try:
                    new_info = await self.goods_checker.get_goods_info()
                    new_stock = new_info.get("stock", 0)
                    new_scheduled = new_info.get("scheduled_sale_time")
                    if new_stock > 0 and not new_scheduled:
                        log_info("商品提前开售！")
                        await self._start_ordering_continuous(new_info)
                        return
                    if new_stock == 0 and not new_scheduled:
                        log_info("商品已售罄")
                        self.order_manager.notify_result(False, error_msg="商品已售罄")
                        return
                    if new_scheduled and new_scheduled != scheduled_time:
                        log_info(f"开售时间更新: {datetime.fromtimestamp(new_scheduled)}")
                        scheduled_time = new_scheduled
                        target_ts = scheduled_time - PRECISION_OFFSET
                        await self.order_manager.prepare_order(new_info)
                except Exception as e:
                    log_debug(f"检查失败: {e}")
            now_ts = time.time()
            wait_seconds = target_ts - now_ts
        if wait_seconds > PREWARM_BEFORE_SECONDS:
            pre_sleep = wait_seconds - PREWARM_BEFORE_SECONDS
            await asyncio.sleep(pre_sleep)
            now_ts = time.time()
            wait_seconds = target_ts - now_ts
            log_debug(f"⚡ 抢单前 {wait_seconds:.1f} 秒重新预热...")
            await self.warmup_connections()
            now_ts = time.time()
            wait_seconds = target_ts - now_ts
        if wait_seconds > 0 and not self._stop_event.is_set():
            if wait_seconds > 0.01:
                await asyncio.sleep(wait_seconds - 0.005)
                now_ts = time.time()
                wait_seconds = target_ts - now_ts
            while wait_seconds > 0 and not self._stop_event.is_set():
                now_ts = time.time()
                wait_seconds = target_ts - now_ts
                if wait_seconds > 0.0005:
                    await asyncio.sleep(0.0001)
        actual = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        target = datetime.fromtimestamp(target_ts).strftime('%H:%M:%S.%f')[:-3]
        offset = (time.time() - target_ts) * 1000
        log_debug(f"⏰ 时间到！实际:{actual} 目标:{target} 偏差:{offset:+.1f}ms")
        await self._start_ordering_continuous(goods_info)

    async def _start_ordering_continuous(self, goods_info):
        if not self.order_manager.payload:
            try:
                await self.order_manager.prepare_order(goods_info)
            except Exception as e:
                log_info(f"准备订单失败: {str(e)}")
                self.order_manager.notify_result(False, error_msg=str(e))
                return
        self.order_manager._start_time = time.time()
        log_info("🚀 开始抢单！")
        request_id = 0
        tasks_created = []
        while not self._stop_event.is_set() and request_id < MAX_REQUESTS:
            request_id += 1
            task = asyncio.create_task(self._send_dual_requests(request_id))
            tasks_created.append(task)
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)
            await asyncio.sleep(REQUEST_INTERVAL)
        log_debug(f"已发送 {len(tasks_created)} 轮请求，等待响应...")
        try:
            await asyncio.wait_for(asyncio.gather(*tasks_created, return_exceptions=True), timeout=10)
        except asyncio.TimeoutError:
            log_debug("等待超时(10秒)")
        if self.order_manager.success:
            self.order_manager.notify_result(True, data=self.order_manager.success_result)
        else:
            self.order_manager.notify_result(False, error_msg=f"共{self.order_manager._request_count}个请求，无成功")

    async def _send_dual_requests(self, request_id: int):
        try:
            tasks = [
                self.order_manager.submit_order_with_method(request_id, pm)
                for pm in ["wxSDK", "alipay"]
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            log_debug(f"[#{request_id}] 异常: {e}")

    def stop(self):
        self._stop_event.set()

    async def cleanup(self):
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        if self._pending_tasks:
            try:
                await asyncio.wait_for(asyncio.wait(self._pending_tasks), timeout=2)
            except asyncio.TimeoutError:
                pass
        if self.shared_session and not self.shared_session.closed:
            await self.shared_session.close()
        if self.connector and not self.connector.closed:
            await self.connector.close()


# ============================================================
# 配置修改
# ============================================================
def modify_config():
    script_path = os.path.abspath(sys.argv[0])
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    config_start = content.find('# ========== 可修改配置 ==========')
    config_end = content.find('# 【配置结束】')
    if config_start == -1 or config_end == -1:
        print("错误：无法定位配置段")
        return
    config_block = content[config_start:config_end + len('# 【配置结束】')]
    script_vars = {}
    var_pattern = re.compile(r'^(\s*)(\w+)\s*=\s*(.+?)(\s*#.*)?$')
    for line in config_block.split('\n'):
        match = var_pattern.match(line)
        if not match:
            continue
        indent = match.group(1)
        var_name = match.group(2)
        var_value = match.group(3).strip()
        comment = match.group(4) or ''
        if var_value.startswith('"') and var_value.endswith('"'):
            raw_value, vtype = var_value[1:-1], 'str'
        elif var_value.startswith("'") and var_value.endswith("'"):
            raw_value, vtype = var_value[1:-1], 'str'
        elif var_value in ('True', 'False'):
            raw_value, vtype = var_value, 'bool'
        elif '.' in var_value:
            try:
                float(var_value)
                raw_value, vtype = var_value, 'float'
            except ValueError:
                raw_value, vtype = var_value, 'str'
        else:
            try:
                int(var_value)
                raw_value, vtype = var_value, 'int'
            except ValueError:
                raw_value, vtype = var_value, 'str'
        script_vars[var_name] = {
            'indent': indent, 'value': raw_value, 'type': vtype, 'comment': comment,
        }
    json_cfg = _load_config_file()
    items = [
        ("USER_EMAIL", "script", "接收通知的邮箱", True),
        ("USER_PS", "script", "邮件备注信息", True),
        ("SMTP_SERVER", "script", "SMTP服务器", False),
        ("SMTP_PORT", "script", "SMTP端口", False),
        ("EMAIL_USER", "script", "发件邮箱", False),
        ("EMAIL_PASSWORD", "script", "邮箱密码/授权码", False),
        ("REQUEST_INTERVAL", "script", "请求间隔(秒)", False),
        ("MAX_REQUESTS", "script", "最大请求轮数", False),
        ("PRECISION_OFFSET", "script", "抢跑时间(秒)", False),
        ("PREWARM_BEFORE_SECONDS", "script", "抢单前预热秒数", False),
        ("LOGIN_CLIENT_VERSION", "script", "换 sid 的 cv", False),
        ("LOGIN_USER_AGENT", "script", "换 sid 的 UA", False),
        ("LOGIN_TIMEZONE", "script", "换 sid 的时区", False),
        ("DEBUG_MODE", "script", "调试模式(True/False)", False),
        ("device_id", "json", "设备ID（与 sid 绑定，修改后建议重新登录）", True),
        ("sid", "json", "登录 sid（修改后需重启生效）", True),
    ]
    while True:
        print("\n" + "=" * 50)
        print("配置修改")
        print("=" * 50)
        for i, (key, source, desc, is_important) in enumerate(items, 1):
            marker = " *" if is_important else ""
            if source == "script":
                if key in script_vars:
                    value = script_vars[key]['value']
                else:
                    continue
            else:
                value = json_cfg.get(key, "")
            display = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            tag = "[脚本]" if source == "script" else "[json]"
            print(f"{i:2d}. {tag}[{key}] {desc}{marker}")
            print(f"    当前值: {display}")
        print("\n操作: 输入序号修改 / s 保存退出 / q 不保存退出")
        choice = input("请选择: ").strip().lower()
        if choice == 'q':
            print("已取消修改")
            return
        if choice == 's':
            backup_name = os.path.basename(script_path) + '.bak'
            backup_path = None
            for p in (os.path.join(os.getcwd(), backup_name),
                      os.path.join('/tmp', backup_name),
                      os.path.join(os.path.expanduser('~'), backup_name)):
                try:
                    with open(p, 'w', encoding='utf-8') as f:
                        f.write(content)
                    backup_path = p
                    break
                except PermissionError:
                    continue
            new_lines = []
            for line in config_block.split('\n'):
                match = var_pattern.match(line)
                if match and match.group(2) in script_vars:
                    info = script_vars[match.group(2)]
                    v, t, c, ind = info['value'], info['type'], info['comment'], info['indent']
                    if t == 'str':
                        new_line = f'{ind}{match.group(2)} = "{v}"{c}'
                    elif t == 'bool':
                        new_line = f'{ind}{match.group(2)} = {v}{c}'
                    elif t == 'int':
                        new_line = f'{ind}{match.group(2)} = {int(float(v))}{c}'
                    elif t == 'float':
                        new_line = f'{ind}{match.group(2)} = {float(v)}{c}'
                    else:
                        new_line = f'{ind}{match.group(2)} = {v}{c}'
                    new_lines.append(new_line)
                    continue
                new_lines.append(line)
            new_block = '\n'.join(new_lines)
            new_content = content[:config_start] + new_block + content[config_end + len('# 【配置结束】'):]
            try:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"\n脚本配置已保存！备份: {backup_path or '未备份'}")
            except PermissionError:
                print(f"\n错误：无法写入 {script_path}")
            _save_config_file(json_cfg)
            print("请重启脚本使配置生效")
            sys.exit(0)
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                key, source, desc, _ = items[idx]
                if source == "script":
                    if key not in script_vars:
                        print("该配置项不存在")
                        continue
                    current = script_vars[key]['value']
                else:
                    current = json_cfg.get(key, "")
                print(f"\n修改 [{source}] {key} ({desc})\n当前值: {current}")
                if key == "device_id":
                    print("警告：修改设备ID后，当前 sid 可能失效，建议同时重新登录")
                new_value = input("新值: ").strip()
                if not new_value:
                    print("已取消")
                    continue
                if source == "script":
                    vtype = script_vars[key]['type']
                    if vtype == 'bool':
                        script_vars[key]['value'] = 'True' if new_value.lower() in ('true', '1', 'yes') else 'False'
                    elif vtype == 'int':
                        try:
                            script_vars[key]['value'] = str(int(float(new_value)))
                        except ValueError:
                            print("请输入有效数字")
                            continue
                    elif vtype == 'float':
                        try:
                            script_vars[key]['value'] = str(float(new_value))
                        except ValueError:
                            print("请输入有效数字")
                            continue
                    else:
                        script_vars[key]['value'] = new_value
                else:
                    if key == "sid":
                        new_value = new_value[len("sid="):] if new_value.startswith("sid=") else new_value
                    json_cfg[key] = new_value
                print(f"{key} 已更新")
            else:
                print("无效序号")
        else:
            print("无效输入")


# ============================================================
# main
# ============================================================
async def main():
    global logger
    print("=" * 50)
    print("      画加自动抢单脚本（含登录）")
    print("=" * 50)
    print("AES: 纯 Python（FIPS-197）")
    print("密钥: 48ec81b2…（请求/响应共用）")
    print("验证码字段: smscode")
    print()
    print("请选择模式:")
    print("1. 定时抢单")
    print("2. 随机监控")
    print("3. 修改配置")
    while True:
        choice = input("\n请输入选择 (1/2/3): ").strip()
        if choice in ("1", "2", "3"):
            break
        print("无效选择")
    if choice == "3":
        modify_config()
        return
    if not init_identity():
        print("未获得有效身份，退出")
        return
    while True:
        print("\n请输入商品链接或商品ID：")
        user_input = input("> ").strip()
        if not user_input:
            continue
        goods_id = extract_goods_id(user_input)
        if goods_id:
            print(f"✓ 商品ID: {goods_id}")
            break
        print("✗ 格式错误，请重新输入")
    logger = setup_logging(goods_id)
    log_info(f"使用设备ID: {DEVICE_ID}")
    log_info(f"使用Cookie: {USER_COOKIE[:20]}{'...' if len(USER_COOKIE) > 20 else ''}")
    print(f"\n当前配置:")
    print(f"  调试模式: {'开启' if DEBUG_MODE else '关闭'}")
    print(f"  请求间隔: {REQUEST_INTERVAL}秒")
    print(f"  最大请求: {MAX_REQUESTS}轮")
    print(f"  抢跑时间: {PRECISION_OFFSET}秒")
    print(f"  抢单前预热: {PREWARM_BEFORE_SECONDS}秒")
    print()
    system = AutoOrderSystem(goods_id)
    try:
        if choice == "1":
            await system.timing_mode()
        else:
            log_info("随机模式启动...（当前实现同定时模式）")
            await system.timing_mode()
    except KeyboardInterrupt:
        log_info("用户中断")
        system.stop()
    except Exception as e:
        log_info(f"异常: {e}")
        import traceback
        log_debug(traceback.format_exc())
    finally:
        await system.cleanup()
    input("\n按回车键退出...")


if __name__ == "__main__":
    if "--test-aes" in sys.argv:
        self_test_aes()
        print("AES 自检通过 ✓（请求/响应同密钥 + hex/base64 msg + \"ok\" 识别）")
        sys.exit(0)
    asyncio.run(main())