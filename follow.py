__filename__ = "follow.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
from pprint import pprint
import os
import sys

def followPerson(username: str, domain: str, followUsername: str, followDomain: str, followFile='following.txt') -> None:
    """Adds a person to the follow list
    """
    handle=username.lower()+'@'+domain.lower()
    handleToFollow=followUsername.lower()+'@'+followDomain.lower()
    baseDir=os.getcwd()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        if handleToFollow in open(filename).read():
            return
        with open(filename, "a") as followfile:
            followfile.write(handleToFollow+'\n')
            return
    with open(filename, "w") as followfile:
        followfile.write(handleToFollow+'\n')

def followerOfPerson(username: str, domain: str, followerUsername: str, followerDomain: str) -> None:
    followPerson(username, domain, followerUsername, followerDomain,'followers.txt')

def unfollowPerson(username: str, domain: str, followUsername: str, followDomain: str,followFile='following.txt') -> None:
    """Removes a person to the follow list
    """
    handle=username.lower()+'@'+domain.lower()
    handleToUnfollow=followUsername.lower()+'@'+followDomain.lower()
    baseDir=os.getcwd()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        if handleToUnfollow not in open(filename).read():
            return
        with open(filename, "r") as f:
            lines = f.readlines()
        with open(filename, "w") as f:
            for line in lines:
                if line.strip("\n") != handleToUnfollow:
                    f.write(line)

def unfollowerOfPerson(username: str, domain: str, followerUsername: str, followerDomain: str) -> None:
    unfollowPerson(username, domain, followerUsername, followerDomain,'followers.txt')

def clearFollows(username: str, domain: str,followFile='following.txt') -> None:
    """Removes all follows
    """
    handle=username.lower()+'@'+domain.lower()
    baseDir=os.getcwd()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        os.remove(filename)

def clearFollowers(username: str, domain: str) -> None:
    clearFollows(username, domain,'followers.txt')
