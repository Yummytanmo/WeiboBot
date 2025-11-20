from WeiboBot import WeiboBot
from WeiboAct import *

import threading
import random
from time import sleep

class WeiboActThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        super(WeiboActThread, self).__init__(group, target, name, args, kwargs)

    def run(self):
        if self._target:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        threading.Thread.join(self, *args)
        return self._return

class WeiboBots:
    def __init__(self, account_list):
        self.bots = {}
        self.init_lock = threading.Lock()
        self.semaphore = threading.Semaphore(10)

        threads = []
        for bot_info in account_list:
            thread = threading.Thread(target=self._start_bot, args=(bot_info,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def _start_bot(self, bot_info):
        with self.semaphore:
            bot = WeiboBot(bot_info)

            with self.init_lock:
                self.bots[bot_info['account_id']] = bot

            if bot_info['online_state'] == 'on':
                bot.login()

    def get_state(self, agent_id, n_following=10, n_recommend=10):
        with self.semaphore:
            print(agent_id)
            try:
                bot = self.bots[agent_id]
            except KeyError:
                print(f"Agent {agent_id} not found.")
                return None
            print("get_homepage_weibos")
            following_infos = get_homepage_weibos(bot, n_following)
            print("get_hot_weibos")
            hot_infos = get_hot_weibos(bot, n_recommend)

            return {
                'post_from_followings': [{
                    'uid': info['account_id'],
                    'weibo_id': info['weibo_id'],
                    'user_name': info['username'],
                    'user_tag': info['user_tag'],
                    'time': info['time'],
                    'text': info['text'],
                    'img': info['imgs'],
                    'video': info['video'],
                    'like': info['like_num'],
                    'comment': info['comment_num'],
                    'repost': info['repost_num'],
                } for info in following_infos],

                'post_from_recommends': [{
                    'uid': info['account_id'],
                    'weibo_id': info['weibo_id'],
                    'user_name': info['username'],
                    'user_tag': info['user_tag'],
                    'time': info['time'],
                    'text': info['text'],
                    'img': info['imgs'],
                    'video': info['video'],
                    'like': info['like_num'],
                    'comment': info['comment_num'],
                    'repost': info['repost_num'],
                } for info in hot_infos],
            }

    def update_state(self, action):
        with self.semaphore:
            bot = self.bots[action['agent_id']]
            try:
                if action['type'] == 'post':
                    info = post(bot, action['action_content'])
                    if info == None:
                        return False
                    return info['weibo_id']
            
                if action['type'] == 'repost':
                    account_id, weibo_id = action['object'].split('/')
                    info = repost(bot, account_id, weibo_id, action['action_content'])
                    if info == None:
                        return False
                    return True
            
                if action['type'] == 'comment':
                    account_id, weibo_id = action['object'].split('/')
                    info = comment(bot, account_id, weibo_id, action['action_content'])
                    if info == None:
                        return False
                    return True
                
                if action['type'] == 'like':
                    account_id, weibo_id = action['object'].split('/')
                    info = like(bot, account_id, weibo_id)
                    if info == None:
                        return False
                    return True
                
                if action['type'] == 'follow':
                    info = follow(bot, action['object'])
                    if info == None:
                        return False
                    return True
                
                if action['type'] == 'unfollow':
                    info = unfollow(bot, action['object'])
                    if info == None:
                        return False
                    return True
            except Exception:
                return False

    def get_feedback(self, agent_id, weibo_id=None):
        with self.semaphore:
            bot = self.bots[agent_id]
            
            if weibo_id  == None:
                info = bot.update_fans_list()
                info['fans_number'] = len(info['fans'])
                return info
            else:
                info = bot.get_weibo_info(agent_id, weibo_id, 100)
                return {
                    'like': int(info['like_num']),
                    'comment': int(info['comment_num']),
                    'repost': int(info['repost_num']),
                    'comment_content': info['comment']
                }

    def get_record(self, object):
        with self.semaphore:
            bot = random.choice(list(self.bots.values()))
            agent_id, weibo_id = object.split('/')
            info = bot.get_weibo_info(agent_id, weibo_id)
            return {
                'uid': info['account_id'],
                'weibo_id': info['weibo_id'],
                'user_name': info['username'],
                'user_tag': info['user_tag'],
                'time': info['time'],
                'text': info['text'],
                'img': info['imgs'],
                'video': info['video'],
                'like': info['like_num'],
                'comment': info['comment_num'],
                'repost': info['repost_num'],
            }

    def get_state_thread(self, agent_id, n_following=10, n_recommend=10):
        thread = WeiboActThread(target=self.get_state, args=(
            agent_id,
            n_following,
            n_recommend,
        ))
        thread.start()
        return thread

    def update_state_thread(self, action):
        thread = WeiboActThread(target=self.update_state, args=(
            action,
        ))
        thread.start()
        return thread

    def get_feedback_thread(self, agent_id, weibo_id=None):
        thread = WeiboActThread(target=self.get_feedback, args=(
            agent_id,
            weibo_id,
        ))
        thread.start()
        return thread
    
    def get_record_thread(self, object):
        thread = WeiboActThread(target=self.get_record, args=(
            object,
        ))
        thread.start()
        return thread
    
