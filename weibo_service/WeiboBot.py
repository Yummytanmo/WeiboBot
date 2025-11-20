# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options as FirefoxOptions

import threading
from time import sleep
from datetime import datetime

class WeiboBot:
    def __init__(self, bot_info):
        self.account_id=bot_info['account_id']
        self.cookie=bot_info['cookie']
            
        self.proxy = bot_info.get('proxy', None)
        self.online_state = bot_info.get('online_state', 'off')
        self.run_states = False

        self.seleniumLock = threading.Lock()
        self.bot = self._init_bot(proxy=self.proxy)
        self.bot.maximize_window()
        self.bot.implicitly_wait(10)

    def _init_bot(self, proxy):
        firefox_options = FirefoxOptions()

        firefox_options.set_preference('permissions.default.image', 2)
        firefox_options.set_preference('dom.webnotifications.enabled', False) 

        firefox_options.set_preference("general.useragent.override", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0")
        firefox_options.set_preference("intl.accept_languages", "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7")
        
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference('useAutomationExtension', False)
        
        firefox_options.set_preference("privacy.resistFingerprinting", True)
        
        firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("--disable-web-security")
        firefox_options.add_argument("--disable-blink-features")
        firefox_options.add_argument("--disable-blink-features=AutomationControlled")
        firefox_options.set_preference('security.enterprise_roots.enabled', True)
        
        firefox_options.add_argument('--headless')

        firefox_options.add_argument('--disable-gpu')
        firefox_options.add_argument("--disable-images")

        if proxy is not None:
            host, port = proxy.split(":")
            firefox_options.set_preference('network.proxy.type', 1)
            firefox_options.set_preference('network.proxy.http', host)
            firefox_options.set_preference('network.proxy.http_port', int(port))
            firefox_options.set_preference('network.proxy.ssl', host)
            firefox_options.set_preference('network.proxy.ssl_port', int(port))
        
        return webdriver.Firefox(options=firefox_options)

    def login(self):
        with self.seleniumLock:
            try:
                self.bot.get('https://weibo.com/')
                self.bot.delete_all_cookies()
                sleep(10)

                for element in self.cookie.split('; '):
                    name, value = element.split('=', 1)
                    cookie_dict = {
                        'domain': '.weibo.com',
                        'name': name,
                        'value': value,
                        "expires": '',
                        'path': '/',
                        'httpOnly': True,
                        'HostOnly': False,
                        'Secure': False
                    }
                    self.bot.add_cookie(cookie_dict)
                
                self.bot.refresh()
                sleep(10)

                self.username = WebDriverWait(self.bot, 50).until(
                    lambda driver: driver.find_element(
                        By.XPATH, 
                        "//*[@id='app']/div[2]/div[1]/div/div[1]/div/div/div[2]/div/div[1]/a[5]/div/div/div"
                    ).get_attribute('title'),
                    "获取用户名超时"
                )

                self.online_state = 'on'
                self.run_states = True

                self.fans = []
                self._get_fans_list()

                print(self.username, "登陆")

                return True
        
            except TimeoutException as e:
                print(f"{self.account_id} 登录超时:", str(e))
                return False

            except Exception as e:
                print(f"{self.account_id} 登录发生错误:", str(e))
                return False

    def post(self, content):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")
                    
                self.bot.get('https://weibo.com')
                
                content_area = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "[placeholder='有什么新鲜事想分享给大家？']"
                    ))
                )
                content_area.send_keys(content)
                
                post_button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='homeWrap']/div[1]/div/div[4]/div/div[5]/button"
                    ))
                )
                post_button.click()
                sleep(5)
                
                weibo_id = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='woo-box-flex woo-box-alignCenter woo-box-justifyCenter head-info_info_2AspQ']/a"
                    ))
                ).get_attribute('href').split('/')[-1]

                username = self.username
                post_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                print(self.username, f"发布微博{self.account_id}/{weibo_id}:", content)

                return {
                    'account_id': self.account_id,
                    'weibo_id': weibo_id,
                    'username': username,
                    'post_time': post_time,
                    'post_content': content,
                }
        
            except TimeoutException as e:
                print(self.username, "发帖超时:", str(e))
                return None

            except Exception as e:
                print(self.username, "发帖发生错误:", str(e))
                return None

    def repost(self, account_id, weibo_id, repost_text=''):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")
                    
                self.bot.get(f'https://weibo.com/{account_id}/{weibo_id}#repost')

                if repost_text != '':
                    content_area = WebDriverWait(self.bot, 50).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR,
                            "[placeholder='说说分享心得']"
                        ))
                    )
                    content_area.send_keys(repost_text)
                sleep(5)

                post_button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='composerEle']/div[2]/div/div[3]/div/button"
                    ))
                )
                post_button.click()
                sleep(5)

                weibo_content = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='detail_wbtext_4CRf9']"
                    ))
                ).text

                print(self.username, f"转发微博{account_id}/{weibo_id}:", repost_text)

                return {
                    'account_id': self.account_id,
                    'username': self.username,
                    'repost_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'repost_content': repost_text,
                    'repost_account_id': account_id,
                    'repost_weibo_id': weibo_id,
                    "weibo_content": weibo_content,
                }
            
            except TimeoutException as e:
                print(self.username, "转发超时:", str(e))
                return None

            except Exception as e:
                print(self.username, "转发发生错误:", str(e))
                return None

    def comment(self, account_id, weibo_id, comment):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")
                    
                self.bot.get(f'https://weibo.com/{account_id}/{weibo_id}')
                
                content_area = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "[placeholder='发布你的评论']"
                    ))
                )
                content_area.send_keys(comment)
                sleep(5)
                
                post_button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='composerEle']/div[2]/div/div[3]/div/button"
                    ))
                )
                post_button.click()
                
                weibo_content = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='detail_wbtext_4CRf9']"
                    ))
                ).text

                print(self.username, f"评论微博{account_id}/{weibo_id}:", comment)

                return {
                    'account_id': self.account_id,
                    'username': self.username,
                    'comment_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'comment_content': comment,
                    'comment_account_id': account_id,
                    'comment_weibo_id': weibo_id,
                    'weibo_content': weibo_content,
                }
            
            except TimeoutException as e:
                print(self.username, "评论超时:", str(e))
                return None
            
            except Exception as e:
                print(self.username, "评论发生错误:", str(e))
                return None

    def like(self, account_id, weibo_id):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")
                    
                self.bot.get(f'https://weibo.com/{account_id}/{weibo_id}')

                like_button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='app']/div[2]/div[2]/div[2]/main/div/div/div[2]/article/footer/div/div[1]/div/div[3]/div/button"
                    ))
                )
                like_button.click()

                weibo_content = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='detail_wbtext_4CRf9']"
                    ))
                ).text

                print(self.username, f"点赞微博{account_id}/{weibo_id}")

                return {
                    'account_id': self.account_id,
                    'username': self.username,
                    'like_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'like_account_id': account_id,
                    'like_weibo_id': weibo_id,
                    'weibo_content': weibo_content
                }
        
            except TimeoutException as e:
                print(self.username, "点赞超时:", str(e))
                return None
            
            except Exception as e:
                print(self.username, "点赞发生错误:", str(e))
                return None


    def follow(self, account_id):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")
                    
                self.bot.get(f'https://weibo.com/u/{account_id}')
                
                follow_button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='app']/div[2]/div[2]/div[2]/main/div/div/div[2]/div[2]/div[3]/span/button"
                    ))
                )                    
                follow_button.click()
                
                print(self.username, "关注用户:", account_id)

                return {
                    'account_id': self.account_id,
                    'username': self.username,
                    'follow_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'follow_account_id': account_id,
                }
            
            except TimeoutException as e:
                print(self.username, "关注超时:", str(e))
                return None
            except Exception as e:
                print(self.username, "关注发生错误:", str(e))
                return None
    
    def unfollow(self, account_id):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")
                    
                self.bot.get(f'https://weibo.com/u/{account_id}')

                button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='app']/div[2]/div[2]/div[2]/main/div/div/div[2]/div[2]/div[3]/span/button"
                    ))
                )
                button.click() 

                unfollow_button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='app']/div[2]/div[2]/div[2]/main/div/div/div[2]/div[2]/div[3]/div/div/div[4]"
                    ))
                )
                unfollow_button.click()

                confirm_button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='app']/div[4]/div[1]/div/div[2]/button[2]"
                    ))
                )
                confirm_button.click()

                print(self.username, "取关用户:", account_id)

                return {
                    'account_id': self.account_id,
                    'username': self.username,
                    'unfollow_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'unfollow_account_id': account_id,
                }

            except TimeoutException as e:
                print(self.username, "取关超时:", str(e))
                return None
            
            except Exception as e:
                print(self.username, "取关发生错误:", str(e))
                return None
        
    def _get_comment(self, max_num=10):
        try:
            js_script = """
                var processNode = function(node) {
                    var text = '';
                    if (node.nodeType === Node.TEXT_NODE) {
                        var trimmed = node.textContent.trim();
                        if (trimmed) text += trimmed + ' ';
                    }
                    else if (node.tagName === 'IMG') {
                        var alt = node.getAttribute('alt') || '';
                        if (alt) text += alt + ' ';
                    }
                    else if (node.nodeType === Node.ELEMENT_NODE) {
                        for (var i = 0; i < node.childNodes.length; i++) {
                            text += processNode(node.childNodes[i]);
                        }
                    }
                    return text;
                };

                var span = arguments[0];
                var rawText = processNode(span);
                return rawText.replace(/\s+/g, ' ').trim();
            """
            
            comments = []
            fail_cnt = 0

            while (len(comments) < max_num):
                try:
                    elements = WebDriverWait(self.bot, 20).until(
                        EC.presence_of_all_elements_located((
                            By.XPATH,
                            "//*[@class='con1 woo-box-item-flex']"
                        ))
                    )
                except Exception:
                    elements = []
                
                new_comment = 0
                for element in elements:
                    span = WebDriverWait(element, 10).until(
                        EC.presence_of_element_located((
                            By.XPATH, 
                            ".//*[@class='text']/span"
                        ))
                    )
                    comment = self.bot.execute_script(js_script, span)
        
                    if comment not in comments:
                        comments.append(comment)
                        new_comment += 1

                    if len(comments) == max_num:
                        break
                
                if new_comment == 0:
                    fail_cnt += 1
                    if fail_cnt == 3:
                        break
                
                self.bot.execute_script('window.scrollBy(0, 500);')
                sleep(3)
            
            return comments
    
        except Exception as e:
            print(self.username, "获取微博评论发生错误:", str(e))
            return []

    def get_weibo_info(self, account_id, weibo_id, max_num=10):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")
                
                self.bot.get(f'https://weibo.com/{account_id}/{weibo_id}')
                sleep(10)

                username = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='ALink_default_2ibt1 head_cut_2Zcft head_name_24eEB']/span"
                    ))
                ).text
            
                time = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='woo-box-flex woo-box-alignCenter woo-box-justifyCenter head-info_info_2AspQ']/a"
                    ))
                ).text
                dt = datetime.strptime(time, "%y-%m-%d %H:%M")
                time = dt.strftime("%Y-%m-%d %H:%M:%S")
            
                weibo_text = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='detail_wbtext_4CRf9']"
                    ))
                ).text
            
                try:
                    self.bot.implicitly_wait(0)
                    user_tag = WebDriverWait(self.bot, 20).until(
                        EC.presence_of_element_located((
                            By.XPATH,
                            "//*[@class='con woo-box-item-flex']"
                        ))
                    ).text
                except Exception:
                    user_tag = ''
                finally:
                    self.bot.implicitly_wait(10)

                try:
                    self.bot.implicitly_wait(0)
                    weibo_img_elements = WebDriverWait(self.bot, 20).until(
                        EC.presence_of_all_elements_located((
                            By.XPATH,
                            "//*[@class='picture picture-box_row_30Iwo']//*[@class='woo-picture-img']"
                        ))
                    )
                    weibo_imgs = [img_element.get_attribute('src') for img_element in weibo_img_elements]
                except Exception:
                    weibo_imgs = []
                finally:
                    self.bot.implicitly_wait(10)

                try:
                    self.bot.implicitly_wait(0)
                    weibo_video = WebDriverWait(self.bot, 20).until(
                        lambda driver: driver.find_element(
                            By.XPATH, 
                            "(//*[contains(@class,'detail_wbtext_')]//a[@target='_blank'])[last()]"
                        ).get_attribute('href')
                    )
                    if 'video' not in weibo_video:
                        weibo_video = ''
                except Exception as e:
                    weibo_video = ''
                finally:
                    self.bot.implicitly_wait(10)

                repost_num = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='woo-box-flex woo-box-alignCenter woo-box-justifyCenter toolbar_retweet_1L_U5 toolbar_wrap_np6Ug']/span"
                    ))
                ).text
                if repost_num == '转发':
                    repost_num = '0'
            
                comment_num = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='woo-box-flex woo-box-alignCenter woo-box-justifyCenter toolbar_wrap_np6Ug toolbar_cur_JoD5A']/span"
                    ))
                ).text
                if comment_num == '评论':
                    comment_num = '0'

                like_num = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@class='woo-like-main toolbar_btn_Cg9tz']/span[2]"
                    ))
                ).text
                if like_num == '赞':
                    like_num = '0'

                comment = self._get_comment(max_num)
                
                print(self.username, "浏览微博", account_id, weibo_id)

                return {
                    "account_id": account_id,
                    "weibo_id": weibo_id,

                    "username": username,
                    "user_tag": user_tag,
                    "time": time,

                    "text": weibo_text,
                    "imgs": weibo_imgs,
                    "video": weibo_video,

                    "repost_num": repost_num,
                    "comment_num": comment_num,
                    "comment": comment,
                    "like_num": like_num,

                    "browse_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
            except TimeoutException as e:
                print(self.username, "获取微博信息超时:", str(e))
                return None
            
            except Exception as e:
                print(self.username, "获取微博信息发生错误:", str(e))
                return None

    def get_hot_weibos(self, max_num=10):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")
                
                self.bot.get('https://weibo.com/hot')
                sleep(10)

                weibos = []
                while len(weibos) < max_num:
                    cur_weibos = WebDriverWait(self.bot, 50).until(
                        EC.presence_of_all_elements_located((
                            By.XPATH,
                            "//*[@class='woo-box-flex woo-box-alignCenter woo-box-justifyCenter head-info_info_2AspQ']/a"
                        ))
                    )
                    for cur_weibo in cur_weibos:  
                        url = cur_weibo.get_attribute('href')
                        weibo = {
                            "account_id": url.split('/')[-2],
                            "weibo_id": url.split('/')[-1]
                        }

                        if weibo not in weibos:
                            weibos.append(weibo)

                        if (len(weibos) == max_num):
                            break

                    self.bot.execute_script('window.scrollBy(0, 1000);')
                    sleep(5)
                
                print(self.username, "获取热门微博:", weibos)

                return weibos

            except TimeoutException as e:
                print(self.username, "获取热门微博超时:", str(e))
                return []
            except Exception as e:
                print(self.username, "获取热门微博发生错误:", str(e))
                return []

    def get_homepage_weibos(self, max_num=10):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")

                self.bot.get('https://weibo.com/')
                sleep(10)
                
                weibos = []
                while len(weibos) < max_num:
                    cur_weibos = WebDriverWait(self.bot, 50).until(
                        EC.presence_of_all_elements_located((
                            By.XPATH,
                            "//*[@class='woo-box-flex woo-box-alignCenter woo-box-justifyCenter head-info_info_2AspQ']/a"
                        ))
                    )
                    for cur_weibo in cur_weibos:  
                        url = cur_weibo.get_attribute('href')
                        weibo = {
                            "account_id": url.split('/')[-2],
                            "weibo_id": url.split('/')[-1]
                        }

                        if weibo not in weibos:
                            weibos.append(weibo)

                        if (len(weibos) == max_num):
                            break

                    self.bot.execute_script('window.scrollBy(0, 1000);')
                    sleep(5)
                
                print(self.username, "获取首页微博:", weibos)
                
                return weibos
            
            except TimeoutException as e:
                print(self.username, "获取首页微博超时:", str(e))
                return []
            except Exception as e:
                print(self.username, "获取首页微博发生错误:", str(e))
                return []

    def _get_fans_list(self):
        try:
            self.bot.get(f'https://weibo.com/u/page/follow/{self.account_id}?relate=fans')
            
            button = WebDriverWait(self.bot, 50).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//*[@id='app']/div[2]/div[2]/div[2]/main/div/div/div[2]/div/div[1]/div/div/span/div/button"
                ))
            ) 
            button.click()
            
            button = WebDriverWait(self.bot, 50).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//*[@id='app']/div[2]/div[2]/div[2]/main/div/div/div[2]/div/div[1]/div/div/div/div/button[2]"
                ))
            ) 
            button.click()

            fail_cnt = 0
            while True:
                fans = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_all_elements_located((
                        By.XPATH,
                        "//*[@class='ALink_none_1w6rm UserCard_item_TrVS0']"
                    ))
                )
                new_fan_cnt = 0
                for fan in fans:
                    fan_account_id = fan.get_attribute('href').split('/')[-1]                            
                    if fan_account_id not in self.fans:
                        self.fans.append(fan_account_id)
                        new_fan_cnt += 1

                if new_fan_cnt == 0:
                    fail_cnt += 1
                if fail_cnt == 3:
                    break

                self.bot.execute_script('window.scrollBy(0, 500);')
                sleep(2)

        except TimeoutException as e:
            print(self.username, "获取粉丝列表超时:", str(e))
        except Exception as e:
            print(self.username, "获取粉丝列表发生错误:", str(e))

    def update_fans_list(self):
        with self.seleniumLock:
            try:
                if self.online_state != 'on':
                    raise Exception("未登录")

                self.bot.get(f'https://weibo.com/u/page/follow/{self.account_id}?relate=fans')

                button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='app']/div[2]/div[2]/div[2]/main/div/div/div[2]/div/div[1]/div/div/span/div/button"
                    ))
                ) 
                button.click()
                
                button = WebDriverWait(self.bot, 50).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//*[@id='app']/div[2]/div[2]/div[2]/main/div/div/div[2]/div/div[1]/div/div/div/div/button[2]"
                    ))
                ) 
                button.click()

                cur_fans = []
                fail_cnt = 0
                while True:
                    fans = WebDriverWait(self.bot, 50).until(
                        EC.presence_of_all_elements_located((
                            By.XPATH,
                            "//*[@class='ALink_none_1w6rm UserCard_item_TrVS0']"
                        ))
                    )
                    new_fan_cnt = 0
                    for fan in fans:
                        fan_account_id = fan.get_attribute('href').split('/')[-1]                            
                        if fan_account_id not in cur_fans:
                            cur_fans.append(fan_account_id)
                            new_fan_cnt += 1

                    if new_fan_cnt == 0:
                        fail_cnt += 1
                    if fail_cnt == 3:
                        break

                    self.bot.execute_script('window.scrollBy(0, 500);')
                    sleep(2)

                follows = []
                unfollows = []
                
                for fan in cur_fans:
                    if fan not in self.fans:
                        follows.append(fan)
                for fan in self.fans:
                    if fan not in cur_fans:
                        unfollows.append(fan)

                self.fans = cur_fans
                print(f"{self.username} 获取粉丝列表")
                return {
                    "fans": self.fans,
                    "follows": follows,
                    "unfollows": unfollows,
                }

            except TimeoutException as e:
                print(self.username, "获取粉丝列表超时:", str(e))
                return None
            except Exception as e:
                print(self.username, "获取粉丝列表发生错误:", str(e))
                return None
