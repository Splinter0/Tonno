import os
import io
import sys
import time
import random
import argparse
import threading
import contextlib
from tqdm import tqdm
from Queue import Queue
from instabot import Bot
from collections import OrderedDict
from huepy import bold, green, orange
sys.path.append(os.path.join(sys.path[0], 'instabot/'))

# SETTINGS

username = ""
password = ""

influencers = "influencers/targets.txt"
toFollow = "toFollow.txt"
username = "bigtest255"
password = "bigtest2"

places = {
    'Avenyn' : '237978920',
    'Riccardo' : '2073286742985736'
}

# FUNCS

class TonnoBot(object):
    def __init__(self, username, password, followNum):
        self.username = username
        self.password = password
        self.followNum = followNum

        self.bot = Bot(max_follows_per_day=100000000000, max_unfollows_per_day=100000000000)

    def login(self):
        self.bot.login(username=self.username, password=self.password)
        self.bot.filter_private_users = False
        self.bot.filter_business_accounts = False
        self.bot.filter_verified_account = False
        self.bot.filter_previously_followed = True
        self.bot.min_following_to_follow = 0
        self.bot.max_following_to_follow = 100000000000
        self.bot.max_followers_to_following_ratio = 100000000000
        self.bot.max_following_to_followers_ratio = 100000000000
        self.bot.max_follows_per_day = self.followNum
        self.bot.max_unfollows_per_day = self.followNum
        self.targets = []
        self.bot.followed_file.verbose = False
        self.bot.unfollowed_file.verbose = False
        self.bot.skipped_file.verbose = False
        self.running = False

    def validUser(self, user, p=False):
        try:
            v = self.bot.convert_to_user_id(user)
        except:
            v = None
        if v != None:
            return True
        else:
            if p:
                self.bot.console_print("User " + user + " is not valid!", 'red')
            return False

    def addTarget(self, target):
        if self.validUser(target, p=True):
            targets = File("influencers/targets.txt")
            targets.append(target)

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

    def customFollow(self, user_id):
        if not self.bot.reached_limit('follows'):
            self.bot.delay('follow')
            if self.bot.api.follow(user_id):
                self.bot.total['follows'] += 1
                self.bot.followed_file.append(user_id)
                if user_id not in self.bot.following:
                    self.bot.following.append(user_id)
        else:
            self.bot.logger.info("Out of follows for today.")

    def customUnfollow(self, user_id):
        if not self.bot.reached_limit('unfollows'):
            self.bot.delay('unfollow')
            if self.bot.api.unfollow(user_id):
                self.bot.unfollowed_file.append(user_id)
                self.bot.total['unfollows'] += 1
                if user_id in self.bot.following:
                    self.bot.following.remove(user_id)
        else:
            self.bot.logger.info("Out of unfollows for today.")

    def userWorker(self, follow=True):
        while True:
            item = self.queue.get()
            if follow:
                self.customFollow(item)
            else:
                self.customUnfollow(item)
            self.bar.update(1)
            self.queue.task_done()

    def goFollow(self, save, s):
        self.tmp = []
        for i in self.influencers:
            users = self.bot.get_user_followers(i)
            if len(self.tmp) > 0:
                ex = list(set(users) - set(self.tmp))
                self.tmp += ex
            else:
                self.tmp += users

        self.targets = []
        if self.location != None:
            users = self.getUsersFromLocation(self.location)
            self.tmp += list(set(users) - set(self.tmp))
        if self.hashtags != None:
            for hash in self.hashtags:
                users = self.getUsersFromHashtag(hash)
                self.tmp += list(set(users) - set(self.tmp))
        self.bot.verbosity = False
        if s:
            self.threadUsers(self.tmp)
            self.targets = sorted(self.targets, key=lambda t: self.scoreUser(t), reverse=True)
            self.targets = [t.id for t in self.targets]
            if len(self.targets) > self.followNum:
                self.remaining = self.targets[self.followNum:]
                self.targets = self.targets[:self.followNum]


        self.queue = Queue()
        for i in range(2):
            t = threading.Thread(target=self.userWorker)
            t.daemon = True
            t.start()
        if s :
            if len(self.targets) < self.followNum:
                self.followNum = len(self.targets)
            self.bar = tqdm(total=self.followNum)
            for user_id in self.targets:
                self.queue.put(user_id)

            self.queue.join()
        else:
            for t in self.tmp:
                user_id = self.bot.convert_to_user_id(t)
                if self.bot.check_user(user_id) and not user_id in self.bot.skipped_file:
                    self.targets.append(user_id)
                    self.queue.put(user_id)
                else:
                    self.tmp.remove(t)

                if len(self.targets) >= self.followNum:
                    break

            self.queue.join()
            self.remaining = list(set(self.tmp) - set(self.targets))


        self.bot.verbosity = True

        print("Saving targets to "+save)
        self.targetsFile = File(save)
        self.targetsFile.save_list(self.remaining)
        done = File("influencers/done.txt")
        done.save_list(self.influencers)

    def massFollow(self, load=None):
        if load != None:
            self.targets = self.bot.read_list_from_file(load)
        self.bot.follow_users(self.targets)

    def followPhase(self, mixed=False, sorted=True, location=None, hashtags=None):
        print("Follow phase")
        self.influencers = self.bot.read_list_from_file("influencers/targets.txt")
        done = self.bot.read_list_from_file("influencers/done.txt")
        for i in self.influencers:
            if i in done and not self.validUser(i, p=True):
                self.influencers.remove(i)

        self.location = location
        self.hashtags = hashtags

        if len(self.influencers) > 0 or self.location != None or self.hashtags != None:
            if not mixed and len(self.influencers) > 0:
                self.influencers = [self.influencers[0]]
            start = time.time()
            self.goFollow(toFollow, sorted)
            print("Following all "+str(len(self.targets))+" users took : " + str(time.time() - start))

        else:
            self.bot.console_print("---NEEDS TARGETS!---", 'red')
            with open("NEEDS_TARGETS", "w") as n:
                n.write("PUT SOME FUCKING TARGETS IN influencers/targets.txt")
            time.sleep(600)
            self.followPhase()

    def unfollowPhase(self, load=None, all=False):
        if load != None:
            self.targets = self.bot.read_list_from_file(load)
        elif all:
            self.targets = self.bot.following
        elif len(self.targets) == 0:
            self.targets = self.bot.read_list_from_file("followed.txt")

        start = time.time()

        self.bot.verbosity = False
        self.queue = Queue()

        for i in range(2):
            t = threading.Thread(target=self.userWorker, kwargs={'follow':False})
            t.daemon = True
            t.start()
        self.bar = tqdm(total=len(self.targets))
        for user_id in self.targets:
            self.queue.put(user_id)
        self.queue.join()
        print("Unfollowing all " + str(len(self.targets)) + " users took : " + str(time.time() - start))
        self.bot.verbosity = True

    def initial(self):
        self.bot.console_print("Loading data for tracker...", 'yellow')
        self.initialFollowers = self.bot.get_user_followers(self.username)
        self.initialFollowing = self.bot.get_user_following(self.username)

    def tracker(self):
        while self.running:
            self.bot.console_print("Tracker going to sleep for 4 hours...", 'yellow')
            time.sleep(14400)
            with nostdout():
                now = self.bot.get_user_followers(self.username)
                newFollowers = list(set(now) - set(self.initialFollowers))
                now = self.bot.get_user_following(self.username)
                newFollowing = list(set(now) - set(self.initialFollowing))
            count = 0
            for user in newFollowing:
                if user in newFollowers:
                    count += 1
            if count > 0:
                rate = (count/(len(newFollowing)*1.0))*100.0
            else:
                rate = 0.0
            self.bot.console_print("Follow back rate is "+str(rate)+"%", 'green')

    def getUsersFromLocation(self, location):
        users = []
        if self.bot.api.get_location_feed(location):
            result = self.bot.last_json
            for post in result["items"] + result["ranked_items"]:
                try:
                    user = post["user"]["pk"]
                    if user not in users:
                        users.append(user)
                except:
                    pass
            for post in result["story"]["items"]:
                try:
                    user = post["user"]["pk"]
                    if user not in users:
                        users.append(user)
                except:
                    pass

        return users

    def getUsersFromHashtag(self, hashtag):
        if not self.bot.api.get_hashtag_feed(hashtag):
            self.bot.logger.warning("Error while getting hastag feed.")
            return []
        return [i['user']['pk'] for i in self.bot.api.last_json['items']]

@contextlib.contextmanager
def nostdout():
    save_stdout = sys.stdout
    sys.stdout = io.BytesIO()
    yield
    sys.stdout = save_stdout

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
            if self.bot.check_user(user_id) and not user_id in self.bot.skipped_file:
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
            f.write('\n{item}'.format(item=item))

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
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('-a', type=str, help="Action : follow, unfollow, tactic")
    parser.add_argument('-n', type=int, help="Number to follow/unfollow, 0 for all", default=1000)
    parser.add_argument('-u', type=str, help="Username for login", default=username)
    parser.add_argument('-p', type=str, help="Password for login", default=password)
    parser.add_argument('-t', type=str, help="Add account to target", default="")
    parser.add_argument('-l', type=str, help="Location ID to grab followers", default=None)
    parser.add_argument('-hh', help="Hashtags for following users", nargs='+', type=str)
    args = parser.parse_args()
    followNum = args.n
    tonno = TonnoBot(args.u, args.p, followNum)
    tonno.login()

    if args.t != "":
        tonno.addTarget(args.t)
    if args.a == "follow":
        tonno.bot.console_print("Running Follow Phase, DO NOT STOP!", 'green')
        tonno.followPhase(sorted=False, location=args.l)
    elif args.a == "unfollow":
        tonno.bot.console_print("Running Unfollow Phase, DO NOT STOP!", 'green')
        tonno.unfollowPhase(all=args.n == 0)
    elif args.a == "tactic":
        tonno.initial()
        tonno.running = True
        tracker = threading.Thread(target=tonno.tracker)
        tracker.start()
        tonno.bot.console_print("Starting tactic bot!", 'green')
        tonno.bot.console_print("Running Follow Phase, DO NOT STOP!", 'green')
        tonno.followPhase(sorted=False, location=args.l, hashtags=args.hh)
        tonno.bot.console_print("Going to sleep for 5 days, SAFE TO STOP", 'yellow')
        time.sleep(432000)
        tonno.bot.console_print("Running Unfollow Phase, DO NOT STOP!", 'green')
        tonno.unfollowPhase(all=True)
        tonno.bot.console_print("Going to sleep for 1 day, SAFE TO STOP", 'yellow')
        time.sleep(86400)
        tonno.running = False

if __name__ == '__main__':
    main()

    """
    SOME DATA
    Follow rate = 1 follower / 20s
    Unfollow rate = 1 unfollow / 20s
    Process user = 1 user / 3s
    """
