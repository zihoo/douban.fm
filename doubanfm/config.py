#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from threading import Thread
import cPickle as pickle
import ConfigParser
import logging
import time
import os

from doubanfm.API.login import request_token
from doubanfm.check import is_latest, update_package, is_mplayer
from doubanfm.exceptions import ConfigError

is_mplayer()

logger = logging.getLogger('doubanfm')  # get logger

THEME = ['default', 'larapaste', 'monokai', 'tomorrow']
PATH_CONFIG = os.path.expanduser("~/.doubanfm_config")
PATH_HISTORY = os.path.expanduser('~/.doubanfm_history')
PATH_TOKEN = os.path.expanduser('~/.doubanfm_token')
CONFIG = '''
[key]
UP = k
DOWN = j
TOP = g
BOTTOM = G
OPENURL = w
RATE = r
NEXT = n
BYE = b
QUIT = q
PAUSE = p
LOOP = l
MUTE = m
LRC = o
HELP = h
HIGH = i
'''
KEYS = {
    'UP': 'k',
    'DOWN': 'j',
    'TOP': 'g',
    'BOTTOM': 'G',
    'OPENURL': 'w',
    'RATE': 'r',
    'NEXT': 'n',
    'BYE': 'b',
    'QUIT': 'q',
    'PAUSE': 'p',
    'LOOP': 'l',
    'MUTE': 'm',
    'LRC': 'o',
    'HELP': 'h',
    'HIGH': 'i'
    }


class Config(object):
    """
    提供默认值
    """

    def __init__(self):
        self.volume = 50  # 音量
        self.channel = 0  # 频道
        self.theme_id = 0  # 主题
        self.user_name = ''  # 用户名
        self.netease = False  # 是否使用网易320k音乐播放
        self.run_times = 0  # 登陆次数
        self.last_time = time.time()  # 当前登陆时间戳
        self.total_time = 0  # 总共登陆时间
        self.liked = 0  # 加❤歌曲
        self.banned = 0  # 不再播放
        self.played = 0  # 累计播放
        self.is_latest = True

        self.login_data = self.get_login_data()

    def output(self, args):
        def _deco(func):
            def _func():
                print '\033[31m♥\033[0m ' + args,
                tmp = func(self)
                print ' [\033[32m OK \033[0m]'
                return tmp
            return _func
        return _deco

    def get_login_data(self):
        """
        提供登陆的认证

        这里顺带增加了 volume, channel, theme_id , netease, run_times的默认值
        """
        if os.path.exists(PATH_TOKEN):
            # 使用上次登录保存的token
            with open(PATH_TOKEN) as f:
                login_data = pickle.load(f)
            if 'cookies' not in login_data:
                login_data = request_token()
        else:
            # 未登陆
            login_data = request_token()

        self.get_default_set(login_data)
        self.get_user_states(login_data)
        self.get_is_latest_version(login_data)
        Thread(target=self.check_version).start()  # 这里每次异步检测, 下次打开时进行提示

        return login_data

    def check_version(self):
        self.is_latest = is_latest('douban.fm')

    def get_is_latest_version(self, login_data):
        self.is_latest = login_data.get('is_latest', True)
        if not self.is_latest:
            if_update = raw_input('检测到douban.fm有更新, 是否升级?(Y) ')
            if if_update.lower() == 'y':
                update_package('douban.fm')
                with open(PATH_TOKEN, 'w') as f:
                    login_data['is_latest'] = True
                    pickle.dump(login_data, f)
                print '请重新打开douban.fm(升级失败可能需要sudo权限, 试试sudo pip install --upgrade douban.fm)'
                os._exit(0)

    def get_default_set(self, login_data):
        """
        记录退出时的播放状态
        """
        self.cookies = login_data.get('cookies', '')
        self.user_name = login_data.get('user_name', '')
        print '\033[31m♥\033[0m Get local token - Username: \033[33m%s\033[0m' %\
            login_data['user_name']

        self.channel = login_data.get('channel', 0)
        print '\033[31m♥\033[0m Get channel [\033[32m OK \033[0m]'

        self.volume = login_data.get('volume', 50)
        print '\033[31m♥\033[0m Get volume [\033[32m OK \033[0m]'

        self.theme_id = login_data.get('theme_id', 0)
        print '\033[31m♥\033[0m Get theme [\033[32m OK \033[0m]'

        self.netease = login_data.get('netease', False)
        self.keys = self.get_keys()

    def get_user_states(self, login_data):
        """
        统计用户信息
        """
        self.run_times = login_data.get('run_times', 0)
        self.total_time = login_data.get('total_time', 0)

    @output('Get keys')
    def get_keys(self):
        '''
        获取配置并检查是否更改
        '''
        if not os.path.exists(PATH_CONFIG):
            with open(PATH_CONFIG, 'w') as F:
                F.write(CONFIG)
        else:
            config = ConfigParser.ConfigParser()
            with open(PATH_CONFIG) as cfgfile:
                config.readfp(cfgfile)
                options = config.options('key')
                for option in options:
                    option = option.upper()
                    if option in KEYS:
                        KEYS[option] = config.get('key', option)
        return KEYS

    @property
    def history(self):
        try:
            with open(PATH_HISTORY) as f:
                history = pickle.load(f)
        except IOError:
            history = []
        return history

    def save_config(self, volume, channel, theme, netease):
        """
        存储历史记录和登陆信息
        """
        self.login_data['cookies'] = self.cookies
        self.login_data['volume'] = volume
        self.login_data['channel'] = channel
        self.login_data['theme_id'] = theme
        self.login_data['netease'] = netease
        self.login_data['run_times'] = self.run_times + 1
        self.login_data['last_time'] = self.last_time
        self.login_data['total_time'] = self.total_time +\
            time.time() - self.last_time
        self.login_data['is_latest'] = self.is_latest
        with open(PATH_TOKEN, 'w') as f:
            pickle.dump(self.login_data, f)

        # with open(PATH_HISTORY, 'w') as f:
        #     pickle.dump(history, f)


db_config = Config()
