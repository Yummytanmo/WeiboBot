from accounts import account_list
from WeiboBot import WeiboBot
from WeiboAct import *
account = account_list[0]

bot = WeiboBot(account)
bot.login()
get_homepage_weibos(bot, 1)
get_hot_weibos(bot, 1)
