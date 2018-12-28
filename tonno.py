import os
import sys
import threading
import schedule
import random
from collections import OrderedDict
from huepy import bold, green, orange
sys.path.append(os.path.join(sys.path[0], 'instabot/'))
from instabot import Bot

# SETTINGS

username = ""
password = ""
influencers = "influencers.txt"
toFollow = "toFollow.txt"
followNum = 2000


# FUNCS

class TonnoBot(object):
    def __init__(self, username, password, followNum):
        self.username = username
        self.password = password
        self.followNum = followNum

        self.bot = Bot(max_follows_per_day=self.followNum, max_unfollows_per_day=self.followNum)

    def login(self):
        self.bot.login(username=self.username, password=self.password)
        self.bot.filter_private_users = False
        self.bot.filter_business_accounts = False
        self.bot.filter_verified_account = False
        self.bot.min_following_to_follow = 0
        self.bot.max_following_to_follow = 100000000000
        self.bot.max_followers_to_following_ratio = 100000000000
        self.bot.max_following_to_followers_ratio = 100000000000

    def checkForList(self):
        pass

    def scoreUser(self, user):
        if 'media_count' in user.info:
            return user.info["media_count"]
        else:
            return 0

    def createFollowers(self, inf, save):
        self.influencers = self.bot.read_list_from_file(inf)
        self.tmp = []
        for i in self.influencers:
            self.tmp += self.bot.get_user_followers(i)

        self.targets = []
        for t in self.tmp:
            user_id = self.convert_to_user_id(t)
            if self.bot.check_user(user_id):
                self.targets.append(User(user_id, self.bot.get_user_info(user_id)))

        self.targets = sorted(self.targets, key= lambda t: self.scoreUser(t), reverse=True)
        if len(self.targets) > self.followNum:
            self.targets = self.targets[:self.followNum]

        self.targets = [t.id for t in self.targets]

        print("Saving targets to "+save)
        self.targetsFile = File(save)
        self.targetsFile.save_list(self.targets)

    def massFollow(self, load=None):
        if load != None:
            self.targets = self.bot.read_list_from_file(load)
        self.bot.follow_users(self.targets)


    def run_threaded(self, job_fn):
        job_thread = threading.Thread(target=job_fn)
        job_thread.start()

class User(object):
    def __init__(self, id, info):
        self.id = id
        self.info = info

class File(object):
    def __init__(self, fname, verbose=True):
        self.fname = fname
        self.verbose = verbose
        open(self.fname, 'a').close()

    @property
    def list(self):
        with open(self.fname, 'r') as f:
            lines = [x.strip('\n') for x in f.readlines()]
            return [x for x in lines if x]

    @property
    def set(self):
        return set(self.list)

    def __iter__(self):
        for i in self.list:
            yield next(iter(i))

    def __len__(self):
        return len(self.list)

    def append(self, item, allow_duplicates=False):
        if self.verbose:
            msg = "Adding '{}' to `{}`.".format(item, self.fname)
            print(bold(green(msg)))

        if not allow_duplicates and str(item) in self.list:
            msg = "'{}' already in `{}`.".format(item, self.fname)
            print(bold(orange(msg)))
            return

        with open(self.fname, 'a') as f:
            f.write('{item}\n'.format(item=item))

    def remove(self, x):
        x = str(x)
        items = self.list
        if x in items:
            items.remove(x)
            msg = "Removing '{}' from `{}`.".format(x, self.fname)
            print(bold(green(msg)))
            self.save_list(items)

    def random(self):
        return random.choice(self.list)

    def remove_duplicates(self):
        return list(OrderedDict.fromkeys(self.list))

    def save_list(self, items):
        with open(self.fname, 'w') as f:
            for item in items:
                f.write('{item}\n'.format(item=item))

def main():
    print("Running TonnoSubito bot")
    print("Current script's schedule:")
    tonno = TonnoBot(username, password, followNum)
    tonno.login()
    tonno.createFollowers(influencers, toFollow)
    tonno.run_threaded(tonno.massFollow())
    """
    follow_followers_list = bot.read_list_from_file("follow_followers.txt")
    print("Going to follow followers of:", follow_followers_list, " in ")
    schedule.every(1).hour.do(run_threaded, stats)
    schedule.every(8).hours.do(run_threaded, like_hashtags)
    schedule.every(2).hours.do(run_threaded, like_timeline)
    schedule.every(1).days.at("16:00").do(run_threaded, like_followers_from_random_user_file)
    schedule.every(2).days.at("11:00").do(run_threaded, follow_followers)
    schedule.every(16).hours.do(run_threaded, comment_medias)
    schedule.every(1).days.at("08:00").do(run_threaded, unfollow_non_followers)
    schedule.every(12).hours.do(run_threaded, follow_users_from_hastag_file)
    schedule.every(6).hours.do(run_threaded, comment_hashtag)
    schedule.every(1).days.at("21:28").do(run_threaded, upload_pictures)
    schedule.every(4).days.at("07:50").do(run_threaded, put_non_followers_on_blacklist)
    
    while True:
        schedule.run_pending()
        time.sleep(1)
    
    tasks_list = []
    for item in follow_followers_list:
        tasks_list.append((bot.follow_followers, {'user_id': item, 'nfollows': 500}))
    
    for func, arg in tasks_list:
        func(**arg)
    """

if __name__ == '__main__':
    main()
