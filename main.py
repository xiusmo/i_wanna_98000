#!/usr/bin/env python3
# -*- coding: utf8 -*-

import argparse
import datetime
import math
import random
import re
import sys
import time
import os

import requests

# 常量定义
APP_USER_AGENT = 'MiFit/5.3.0 (iPhone; iOS 14.7.1; Scale/3.00)'
LOGIN_URL_TEMPLATE = 'https://api-user.huami.com/registrations/{user_path}/tokens'
TOKEN_LOGIN_URL = 'https://account.huami.com/v2/client/login'
APP_TOKEN_URL_TEMPLATE = (
    'https://account-cn.huami.com/v1/client/app_tokens'
    '?app_name=com.xiaomi.hm.health'
    '&dn=api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com'
    '&login_token={login_token}'
)
DATA_SUBMIT_URL_TEMPLATE = 'https://api-mifit-cn.huami.com/v1/data/band_data.json?&t={timestamp}'

# 北京时区
BJ_TZ = datetime.timezone(datetime.timedelta(hours=8))
# 从环境变量读取每日最大基础步数和浮动比例，如解析失败使用默认值
raw_max = os.getenv('MAX_DAILY_STEPS')
try:
    MAX_DAILY_STEPS = int(raw_max) if raw_max and raw_max.strip() else 60000
except ValueError:
    MAX_DAILY_STEPS = 60000
raw_var = os.getenv('VARIATION_RATIO')
try:
    VARIATION_RATIO = float(raw_var) if raw_var and raw_var.strip() else 0.05
except ValueError:
    VARIATION_RATIO = 0.05
today_str = datetime.datetime.now(BJ_TZ).strftime('%Y-%m-%d')


def parse_args():
    """解析命令行参数：用户和密码列表，用#分隔。"""
    parser = argparse.ArgumentParser(description='自动提交步数脚本')
    parser.add_argument('users', help='用户名列表，用#分隔')
    parser.add_argument('passwords', help='密码列表，用#分隔，与用户名顺序对应')
    return parser.parse_args()


def get_system_timestamp_ms():
    """获取当前系统时间戳，单位毫秒。"""
    return int(time.time() * 1000)


def generate_step_range():
    """根据当前分钟生成基础步数并给出小范围浮动区间。"""
    # 当前北京时间分钟数
    now = datetime.datetime.now(BJ_TZ)
    minute_of_day = now.hour * 60 + now.minute
    # 计算基础步数，随着时间线性增加
    base = int(MAX_DAILY_STEPS * minute_of_day / (24 * 60))
    # 小范围浮动
    variation = int(base * VARIATION_RATIO)
    low = max(base - variation, 0)
    high = base + variation
    return low, high


def extract_access_code(location_url):
    """从重定向 URL 中提取 access code。"""
    match = re.search(r'(?<=access=).*?(?=&)', location_url)
    return match.group(0) if match else None


def login(user, password):
    """登录获取 login_token 和 user_id。"""
    is_phone = bool(re.match(r'\d{11}$', user))
    user_path = f'+86{user}' if is_phone else user
    # 第一步获取 access code
    url1 = LOGIN_URL_TEMPLATE.format(user_path=user_path)
    headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'User-Agent': APP_USER_AGENT}
    data1 = {
        'client_id': 'HuaMi',
        'password': password,
        'redirect_uri': 'https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html',
        'token': 'access'
    }
    resp1 = requests.post(url1, data=data1, headers=headers, allow_redirects=False)
    code = extract_access_code(resp1.headers.get('Location', ''))
    if not code:
        return None, None

    # 第二步通过 access code 登录
    data2 = {
        'app_name': 'com.xiaomi.hm.health',
        'app_version': '6.3.5',
        'code': code,
        'country_code': 'CN',
        'device_id': '2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1',
        'device_model': 'phone',
        'grant_type': 'access_token',
        'third_name': 'huami_phone' if is_phone else 'email'
    }
    # 区分手机和邮箱的参数差异
    if not is_phone:
        data2.update({
            'allow_registration': 'false',
            'dn': 'api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com',
            'lang': 'zh_CN',
            'os_version': '1.5.0',
            'source': 'com.xiaomi.hm.health'
        })
    resp2 = requests.post(TOKEN_LOGIN_URL, data=data2, headers=headers).json()
    token_info = resp2.get('token_info', {})
    return token_info.get('login_token'), token_info.get('user_id')


def get_app_token(login_token):
    """根据 login_token 获取 apptoken。"""
    headers = {'User-Agent': APP_USER_AGENT}
    url = APP_TOKEN_URL_TEMPLATE.format(login_token=login_token)
    resp = requests.get(url, headers=headers).json()
    return resp.get('token_info', {}).get('app_token')


def submit_steps(login_token, user_id, step):
    """提交指定步数并返回服务器返回的 message。"""
    timestamp = get_system_timestamp_ms()
    with open('upload_json.txt', 'r', encoding='utf-8') as f:
        data_json = f.read()
        
    finddate = re.compile(r".*?date%22%3A%22(.*?)%22%2C%22data.*?")
    findstep = re.compile(r".*?ttl%5C%22%3A(.*?)%2C%5C%22dis.*?")
    data_json = re.sub(finddate.findall(data_json)[0], today_str, data_json)
    data_json = re.sub(findstep.findall(data_json)[0], str(step), data_json)
    
    url = DATA_SUBMIT_URL_TEMPLATE.format(timestamp=timestamp)
    headers = {'apptoken': get_app_token(login_token), 'Content-Type': 'application/x-www-form-urlencoded'}
    payload = f'userid={user_id}&last_sync_data_time=1597306380&device_type=0&last_deviceid=DA932FFFFE8816E7&data_json={data_json}'
    print(f"[DEBUG] 正在提交步数: user_id={user_id}, step={step}")
    print(f"[DEBUG] 提交URL: {url}")
    print(f"[DEBUG] Payload: {payload[:200]}... (截断)")
    resp = requests.post(url, data=payload, headers=headers).json()
    print(f"[DEBUG] 响应内容: {resp}")
    return resp.get('message', '')


def main():
    args = parse_args()
    users = args.users.split('#')
    passwords = args.passwords.split('#')
    if len(users) != len(passwords):
        print('用户名和密码数量不匹配')
        sys.exit(1)

    min_steps, max_steps = generate_step_range()
    if min_steps == 0 or max_steps == 0:
        print('当前主人设置了0步数，本次不提交')
        sys.exit(0)

    for user, passwd in zip(users, passwords):
        token, user_id = login(user, passwd)
        if not token:
            print(f'{user} 登录失败')
            continue
        step = random.randint(min_steps, max_steps)
        message = submit_steps(token, user_id, step)
        # 使用北京时间输出
        now_str = datetime.datetime.now(BJ_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{now_str}] 账号：{user[:3]}****{user[7:]} 步数：{step} 结果：{message}')


if __name__ == '__main__':
    main()
