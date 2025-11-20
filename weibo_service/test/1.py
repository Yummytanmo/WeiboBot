from accounts import account_list
from WeiboBot import WeiboBot

for account in account_list:
    bot = WeiboBot(account)
    bot.login()