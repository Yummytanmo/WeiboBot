import sqlite3
import random
from time import sleep

POST, LIKE, COMMENT, REPOST, FOLLOW, UNFOLLOW = 1, 2, 3, 4, 5, 6

def post(bot, post_content):
    # sleep(random.uniform(5, 10))
    info = bot.post(post_content)

    try:
        conn = sqlite3.connect('WeiboAct.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ActionLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action INTEGER,
                uid VARCHAR(12),
                user_name VARCHAR(30),
                time TIMESTAMP,
                action_content VARCHAR(2000),
                object VARCHAR(12),
                object_content VARCHAR(2000)
            )
        ''')

        cursor.execute('''
            INSERT INTO ActionLog 
            (action, uid, user_name, time, action_content, object)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            POST,
            info['account_id'],
            info['username'],
            info['post_time'],
            info['post_content'],
            info['weibo_id'],
        ))
 
        conn.commit()
    except sqlite3.Error as e:
        print("Database error:", e)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()
    
    return info

def repost(bot, repost_account_id, repost_weibo_id, repost_content=''):
    # sleep(random.uniform(5, 10))
    info = bot.repost(repost_account_id, repost_weibo_id, repost_content)

    try:
        conn = sqlite3.connect('WeiboAct.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ActionLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action INTEGER,
                uid VARCHAR(12),
                user_name VARCHAR(30),
                time TIMESTAMP,
                action_content VARCHAR(2000),
                object VARCHAR(12),
                object_content VARCHAR(2000)
            )
        ''')

        cursor.execute('''
            INSERT INTO ActionLog 
            (action, uid, user_name, time, action_content, object, object_content)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            REPOST,
            info['account_id'],
            info['username'],
            info['repost_time'],
            info['repost_content'],
            info['repost_account_id'] + '/' + info['repost_weibo_id'],
            info['weibo_content']
        ))

        conn.commit()
    except sqlite3.Error as e:
        print("Database error:", e)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()
    
    return info
    
def comment(bot, comment_account_id, comment_weibo_id, comment_content):
    # sleep(random.uniform(5, 10))
    info = bot.comment(comment_account_id, comment_weibo_id, comment_content)
    
    try:
        conn = sqlite3.connect('WeiboAct.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ActionLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action INTEGER,
                uid VARCHAR(12),
                user_name VARCHAR(30),
                time TIMESTAMP,
                action_content VARCHAR(2000),
                object VARCHAR(12),
                object_content VARCHAR(2000)
            )
        ''')

        cursor.execute('''
            INSERT INTO ActionLog 
            (action, uid, user_name, time, action_content, object, object_content)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            COMMENT,
            info['account_id'],
            info['username'],
            info['comment_time'],
            info['comment_content'],
            info['comment_account_id'] + '/' + info['comment_weibo_id'],
            info['weibo_content']
        ))

        conn.commit()
    
    except sqlite3.Error as e:
        print("Database error:", e)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return info

def like(bot, like_account_id, like_weibo_id):
    # sleep(random.uniform(5, 10))
    info = bot.like(like_account_id, like_weibo_id)

    try:
        conn = sqlite3.connect('WeiboAct.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ActionLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action INTEGER,
                uid VARCHAR(12),
                user_name VARCHAR(30),
                time TIMESTAMP,
                action_content VARCHAR(2000),
                object VARCHAR(12),
                object_content VARCHAR(2000)
            )
        ''')

        cursor.execute('''
            INSERT INTO ActionLog 
            (action, uid, user_name, time, object, object_content)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            LIKE,
            info['account_id'],
            info['username'],
            info['like_time'],
            info['like_account_id'] + '/' + info['like_weibo_id'],
            info['weibo_content']
        ))

        conn.commit()
    
    except sqlite3.Error as e:
        print("Database error:", e)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return info

def follow(bot, follow_account_id):
    # sleep(random.uniform(5, 10))
    info = bot.follow(follow_account_id)

    try:
        conn = sqlite3.connect('WeiboAct.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ActionLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action INTEGER,
                uid VARCHAR(12),
                user_name VARCHAR(30),
                time TIMESTAMP,
                action_content VARCHAR(2000),
                object VARCHAR(12),
                object_content VARCHAR(2000)
            )
        ''')

        cursor.execute('''
            INSERT INTO ActionLog 
            (action, uid, user_name, time, object)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            FOLLOW,
            info['account_id'],
            info['username'],
            info['follow_time'],
            info['follow_account_id'],
        ))

        conn.commit()
    
    except sqlite3.Error as e:
        print("Database error:", e)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return info

def unfollow(bot, unfollow_account_id):
    # sleep(random.uniform(5, 10))
    info = bot.unfollow(unfollow_account_id)

    try:
        conn = sqlite3.connect('WeiboAct.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ActionLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action INTEGER,
                uid VARCHAR(12),
                user_name VARCHAR(30),
                time TIMESTAMP,
                action_content VARCHAR(2000),
                object VARCHAR(12),
                object_content VARCHAR(2000)
            )
        ''')

        cursor.execute('''
            INSERT INTO ActionLog 
            (action, uid, user_name, time, object)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            UNFOLLOW,
            info['account_id'],
            info['username'],
            info['unfollow_time'],
            info['unfollow_account_id'],
        ))

        conn.commit()
    
    except sqlite3.Error as e:
        print("Database error:", e)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return info

def get_hot_weibos(bot, max_num=10):
    # sleep(random.uniform(5, 10))
    weibos = bot.get_hot_weibos(max_num=max_num)

    weibo_infos = []
    for weibo in weibos:
        info = bot.get_weibo_info(weibo['account_id'], weibo['weibo_id'])
        weibo_infos.append(info)
    
    for info in weibo_infos:
        try:
            conn = sqlite3.connect('WeiboAct.db')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS BrowseInformation (
                    uid VARCHAR(12),
                    weibo_id VARCHAR(12),
                    user_name VARCHAR(30),
                    user_tag VARCHAR(100),
                    time TIMESTAMP,
                    text VARCHAR(2000),
                    img VARCHAR(200),
                    video VARCHAR(200),
                    repost VARCHAR(12),
                    like VARCHAR(12),
                    comment VARCHAR(12),
                    comment_content VARCHAR(50000),
                    browse_time TIMESTAMP,
                    browser_uid VARCHAR(12),
                    browse_type INTEGER,
                    PRIMARY KEY(uid, weibo_id, browser_uid, browse_type)
                )
            ''')
            cursor.execute('''
                INSERT INTO BrowseInformation 
                (uid, weibo_id, user_name, user_tag, time, text, img, video, repost, like, comment, comment_content, browse_time, browser_uid, browse_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                info['account_id'],
                info['weibo_id'],
                info['username'],
                info['user_tag'],
                info['time'],
                info['text'],
                str(info['imgs']),
                info['video'],
                info['repost_num'],
                info['like_num'],
                info['comment_num'],
                str(info['comment']),
                info['browse_time'],
                bot.account_id,
                0
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
        except sqlite3.Error as e:
            print("Database error:", e)
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    return weibo_infos

def get_homepage_weibos(bot, max_num=10):
    weibos = bot.get_homepage_weibos(max_num=max_num)

    weibo_infos = []
    for weibo in weibos:
        info = bot.get_weibo_info(weibo['account_id'], weibo['weibo_id'])
        weibo_infos.append(info)
        
    for info in weibo_infos:
        try:
            conn = sqlite3.connect('WeiboAct.db')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS BrowseInformation (
                    uid VARCHAR(12),
                    weibo_id VARCHAR(12),
                    user_name VARCHAR(30),
                    user_tag VARCHAR(100),
                    time TIMESTAMP,
                    text VARCHAR(2000),
                    img VARCHAR(200),
                    video VARCHAR(200),
                    repost VARCHAR(12),
                    like VARCHAR(12),
                    comment VARCHAR(12),
                    comment_content VARCHAR(50000),
                    browse_time TIMESTAMP,
                    browser_uid VARCHAR(12),
                    browse_type INTEGER,
                    PRIMARY KEY(uid, weibo_id, browser_uid, browse_type)
                )
            ''')
            cursor.execute('''
                INSERT INTO BrowseInformation 
                (uid, weibo_id, user_name, user_tag, time, text, img, video, repost, like, comment, comment_content, browse_time, browser_uid, browse_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                info['account_id'],
                info['weibo_id'],
                info['username'],
                info['user_tag'],
                info['time'],
                info['text'],
                str(info['imgs']),
                info['video'],
                info['repost_num'],
                info['like_num'],
                info['comment_num'],
                str(info['comment']),
                info['browse_time'],
                bot.account_id,
                1,
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
        except sqlite3.Error as e:
            print("Database error:", e)
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    return weibo_infos

def update_fans_list(bot):
    # sleep(random.uniform(5, 10))
    info = bot.update_fans_list()
    return info
