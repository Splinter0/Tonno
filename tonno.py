import os
import sys
import time
import argparse
import threading
import random
from tqdm import tqdm
from collections import OrderedDict
from huepy import bold, green, orange
sys.path.append(os.path.join(sys.path[0], 'instabot/'))
from instabot import Bot

# SETTINGS

username = ""
password = ""

influencers = "influencers/targets.txt"
toFollow = "toFollow.txt"


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

    def threadUsers(self, l):
        d = len(l) / 4
        self.threads = []
        self.threads.append(UserLoader(l[:d], self.bot))
        self.threads.append(UserLoader(l[d:(d*2)], self.bot))
        self.threads.append(UserLoader(l[(d*2):(d*3)], self.bot))
        self.threads.append(UserLoader(l[(d*3):-1], self.bot))

        for t in self.threads:
            t.start()

        while self.threads:
            for t in self.threads:
                if t.stopped():
                    self.threads.remove(t)
                    self.targets += t.users

            time.sleep(5)


    def createFollowers(self, save):
        self.tmp = []
        for i in self.influencers:
            users = self.bot.get_user_followers(i)
            if len(self.tmp) > 0:
                ex = list(set(users) - set(self.tmp))
                self.tmp += ex
            else:
                self.tmp += users

        self.targets = []
        self.bot.verbosity = False
        self.threadUsers(self.tmp)
        #self.bot.verbosity = True
        for t in self.targets:
            if t.id in self.bot.skipped_file or t.id in self.bot.unfollowed_file:
                self.targets.remove(t)

        self.targets = sorted(self.targets, key= lambda t: self.scoreUser(t), reverse=True)
        if len(self.targets) > self.followNum:
            self.targets = self.targets[:self.followNum]

        self.targets = [t.id for t in self.targets]

        print("Saving targets to "+save)
        self.targetsFile = File(save)
        self.targetsFile.save_list(self.targets)
        done = File("influencers/done.txt")
        done.save_list(self.influencers)

    def massFollow(self, load=None):
        if load != None:
            self.targets = self.bot.read_list_from_file(load)
        self.bot.follow_users(self.targets)

    def massUnfollow(self, load=None):
        if load != None:
            self.targets = self.bot.read_list_from_file(load)
        self.bot.unfollow_users(self.targets)

    def followPhase(self, mixed=False):
        print("Follow phase")
        self.influencers = self.bot.read_list_from_file("influencers/targets.txt")
        done = self.bot.read_list_from_file("influencers/done.txt")
        for i in self.influencers:
            if i in done:
                self.influencers.remove(i)

        if len(self.influencers) > 0:
            if not mixed:
                self.influencers = [self.influencers[0]]
            start = time.time()
            self.createFollowers(toFollow)
            print("Loading all "+str(len(self.targets))+" users took : " + str(time.time() - start))
            start = time.time()
            self.massFollow()
            print("Following all "+str(len(self.targets))+" users took : " + str(time.time() - start))

        else:
            self.bot.console_print("---NEEDS TARGETS!---", 'red')
            with open("NEEDS_TARGETS", "w") as n:
                n.write("PUT SOME FUCKING TARGETS IN influencers/targets.txt")
            time.sleep(600)
            self.followPhase()

    def unfollowPhase(self):
        pass

class UserLoader(threading.Thread):
    def __init__(self, l, bot):
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self.list = l
        self.users = []
        self.bot = bot

    def run(self):
        for t in tqdm(self.list):
            user_id = self.bot.convert_to_user_id(t)
            if self.bot.check_user(user_id):
                self.users.append(User(user_id, self.bot.get_user_info(user_id)))

        self.stop()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

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
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('-a', type=str, help="Action : follow, unfollow")
    parser.add_argument('-n', type=int, help="Number to follow", default=1000)
    args = parser.parse_args()
    followNum = args.n
    tonno = TonnoBot(username, password, followNum)
    tonno.login()
    if args.a == "follow":
        tonno.bot.console_print("Running Follow Phase, DO NOT STOP!", 'green')
        tonno.followPhase()
    else:
        tonno.bot.console_print("Running Unfollow Phase, DO NOT STOP!", 'green')
        tonno.unfollowPhase()
    """while True:
        tonno.bot.console_print("Running Follow Phase, DO NOT STOP!", 'green')
        tonno.followPhase()
        tonno.bot.console_print("Going to sleep for 5 days, SAFE TO STOP", 'yellow')
        time.sleep(10)
        #time.sleep(432000)
        tonno.bot.console_print("Running Unfollow Phase, DO NOT STOP!", 'green')
        tonno.unfollowPhase()
        tonno.bot.console_print("Going to sleep for 1 day, SAFE TO STOP", 'yellow')
        time.sleep(10)
        #time.sleep(86400)"""

if __name__ == '__main__':
    main()

    """
    SOME DATA
    Follow rate = 1 follower / 20s
    Unfollow rate = 1 unfollow / 20s
    Process user = 1 user / 3s
    """
