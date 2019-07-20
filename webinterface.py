__filename__ = "webinterface.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json

def htmlHeader(lang='en') -> str:
    htmlStr= \
        '<!DOCTYPE html>\n' \
        '<html lang="'+lang+'">\n' \
        '  <meta charset="utf-8">\n' \
        '  <style>\n' \
        '    @import url("epicyon.css");\n' \
        '  </style>\n' \
        '  <body>\n'
    return htmlStr

def htmlFooter() -> str:
    htmlStr= \
        '  </body>\n' \
        '</html>\n'
    return htmlStr

def htmlProfile(profileJson: {}) -> str:
    """Show the profile page as html
    """
    return htmlHeader()+"<h1>Profile page</h1>"+htmlFooter()

def htmlFollowing(followingJson: {}) -> str:
    """Show the following collection as html
    """
    return htmlHeader()+"<h1>Following collection</h1>"+htmlFooter()

def htmlFollowers(followersJson: {}) -> str:
    """Show the followers collection as html
    """
    return htmlHeader()+"<h1>Followers collection</h1>"+htmlFooter()

def htmlInbox(inboxJson: {}) -> str:
    """Show the inbox as html
    """
    return htmlHeader()+"<h1>Inbox</h1>"+htmlFooter()

def htmlOutbox(outboxJson: {}) -> str:
    """Show the Outbox as html
    """
    return htmlHeader()+"<h1>Outbox</h1>"+htmlFooter()

def htmlIndividualPost(postJsonObject: {}) -> str:
    """Show an individual post as html
    """
    return htmlHeader()+"<h1>Post</h1>"+htmlFooter()

def htmlPostReplies(postJsonObject: {}) -> str:
    """Show the replies to an individual post as html
    """
    return htmlHeader()+"<h1>Replies</h1>"+htmlFooter()
