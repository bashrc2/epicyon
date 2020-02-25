__filename__ = "blog.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import time
import os
from collections import OrderedDict
from datetime import datetime
from datetime import date
from dateutil.parser import parse
from shutil import copyfile
from shutil import copyfileobj
from pprint import pprint

from content import replaceEmojiFromTags
from webinterface import getIconsDir
from webinterface import getPostAttachmentsAsHtml
from webinterface import htmlHeader
from webinterface import htmlFooter
from webinterface import addEmbeddedElements
from utils import getNicknameFromActor
from utils import getDomainFromActor
from posts import createBlogsTimeline


def noOfBlogReplies(baseDir: str,httpPrefix: str,translate: {}, \
                    nickname: str,domain: str,domainFull: str, \
                    postJsonObject: {}) -> int:
    """Returns the number of replies on the post
    """
    if not postJsonObject['object'].get('id'):
        return 0
    postFilename= \
        baseDir+'/accounts/'+nickname+'@'+domain+'/tlblogs/'+ \
        postJsonObject['object']['id'].replace('/','#')+'.replies'
    if not os.path.isfile(postFilename):
        return 0
    with open(postFilename, "r") as f:
        lines = f.readlines()
        return len(lines)
    return 0


def htmlBlogPostContent(authorized: bool, \
                        baseDir: str,httpPrefix: str,translate: {}, \
                        nickname: str,domain: str,domainFull: str, \
                        postJsonObject: {}, \
                        handle: str,restrictToDomain: bool) -> str:
    """Returns the content for a single blog post
    """
    linkedAuthor=False
    actor=''
    blogStr=''
    messageLink=''
    if postJsonObject['object'].get('id'):
        messageLink=postJsonObject['object']['id'].replace('/statuses/','/')
    if postJsonObject['object'].get('summary'):
        blogStr+='<h1><a href="'+messageLink+'">'+postJsonObject['object']['summary']+'</a></h1>\n'

    # get the handle of the author
    if postJsonObject['object'].get('attributedTo'):
        actor=postJsonObject['object']['attributedTo']
        authorNickname=getNicknameFromActor(actor)
        if authorNickname:
            authorDomain,authorPort=getDomainFromActor(actor)
            if authorDomain:
                # author must be from the given domain
                if restrictToDomain and authorDomain != domain:
                    return ''
                handle=authorNickname+'@'+authorDomain
    else:
        # posts from the domain are expected to have an attributedTo field
        if restrictToDomain:
            return ''
        
    if postJsonObject['object'].get('published'):
        if 'T' in postJsonObject['object']['published']:
            blogStr+='<h3>'+postJsonObject['object']['published'].split('T')[0]
            if handle:
                if handle.startswith(nickname+'@'+domain):
                    blogStr+= \
                        ' <a href="'+httpPrefix+'://'+domainFull+ \
                        '/users/'+nickname+'">'+handle+'</a>'
                    linkedAuthor=True
                else:
                    if author:
                        blogStr+= \
                            ' <a href="'+author+'">'+handle+'</a>'
                        linkedAuthor=True
                    else:
                        blogStr+=' '+handle
            blogStr+='</h3>\n'

    avatarLink=''
    replyStr=''
    announceStr=''
    likeStr=''
    bookmarkStr=''
    deleteStr=''
    muteStr=''
    isMuted=False
    attachmentStr,galleryStr= \
        getPostAttachmentsAsHtml(postJsonObject,'tlblogs',translate, \
                                 isMuted,avatarLink, \
                                 replyStr,announceStr,likeStr, \
                                 bookmarkStr,deleteStr,muteStr)
    if attachmentStr:
        blogStr+='<br><center>'+attachmentStr+'</center>'

    if postJsonObject['object'].get('content'):
        contentStr= \
            addEmbeddedElements(translate, \
                                postJsonObject['object']['content'])
        if postJsonObject['object'].get('tag'):
            contentStr= \
                replaceEmojiFromTags(contentStr, \
                                     postJsonObject['object']['tag'],'content')
        blogStr+='<br>'+contentStr+'\n'

    blogStr+='<br><hr>\n'

    if not authorized:
        replies= \
            noOfBlogReplies(baseDir,httpPrefix,translate, \
                            nickname,domain,domainFull, \
                            postJsonObject)
        if replies>0:
            blogStr+= \
                '<p class="blogreplies">'+ \
                translate['Replies'].lower()+': '+str(replies)+'</p>'

    if not linkedAuthor:
        blogStr+= \
            '<p class="about"><a class="about" href="'+httpPrefix+'://'+domainFull+ \
            '/users/'+nickname+'">'+translate['About the author']+'</a></p>\n'
    return blogStr


def htmlBlogPost(authorized: bool, \
                 baseDir: str,httpPrefix: str,translate: {}, \
                 nickname: str,domain: str,domainFull: str, \
                 postJsonObject: {}) -> str:
    """Returns a html blog post
    """
    blogStr=''

    cssFilename=baseDir+'/epicyon-blog.css'
    if os.path.isfile(baseDir+'/blog.css'):
        cssFilename=baseDir+'/blog.css'
    with open(cssFilename, 'r') as cssFile:
        blogCSS=cssFile.read()
        blogStr=htmlHeader(cssFilename,blogCSS)

        blogStr+= \
            htmlBlogPostContent(authorized,baseDir,httpPrefix,translate, \
                                nickname,domain,domainFull,postJsonObject, \
                                None,False)
        
        return blogStr+htmlFooter()
    return None

def htmlBlogPage(authorized: bool, session, \
                 baseDir: str,httpPrefix: str,translate: {}, \
                 nickname: str,domain: str,port: int, \
                 noOfItems: int,pageNumber: int) -> str:
    """Returns a html blog page containing posts
    """
    if ' ' in nickname or '@' in nickname or '\n' in nickname:
        return None
    blogStr=''    

    cssFilename=baseDir+'/epicyon-blog.css'
    if os.path.isfile(baseDir+'/blog.css'):
        cssFilename=baseDir+'/blog.css'
    with open(cssFilename, 'r') as cssFile:
        blogCSS=cssFile.read()
        blogStr=htmlHeader(cssFilename,blogCSS)

        blogsIndex= \
            baseDir+'/accounts/'+nickname+'@'+domain+'/tlblogs.index'
        if not os.path.isfile(blogsIndex):
            return blogStr+htmlFooter()

        timelineJson= \
            createBlogsTimeline(session,baseDir, \
                                nickname,domain,port,httpPrefix, \
                                noOfItems,False,False,pageNumber)

        if not timelineJson:
            return blogStr+htmlFooter()

        domainFull=domain
        if port:
            if port!=80 and port!=443:
                domainFull=domain+':'+str(port)

        if pageNumber!=None:
            iconsDir=getIconsDir(baseDir)
            navigateStr='<p>'
            if pageNumber>1:
                # show previous button
                navigateStr+= \
                    '<a href="'+httpPrefix+'://'+domainFull+'/blog/'+nickname+'?page='+str(pageNumber-1)+'">'+ \
                    '<img loading="lazy" alt="<" title="<" '+ \
                    'src="/'+iconsDir+ \
                    '/prev.png" class="buttonprev"/></a>\n'
            if len(timelineJson['orderedItems'])>=noOfItems:
                # show next button
                navigateStr+= \
                    '<a href="'+httpPrefix+'://'+domainFull+'/blog/'+nickname+'?page='+str(pageNumber+1)+'">'+ \
                    '<img loading="lazy" alt=">" title=">" '+ \
                    'src="/'+iconsDir+ \
                    '/prev.png" class="buttonnext"/></a>\n'
            navigateStr+='</p>'
            blogStr+=navigateStr
        
        for item in timelineJson['orderedItems']:
            if item['type']!='Create':
                continue

            blogStr+= \
                htmlBlogPostContent(authorized,baseDir,httpPrefix,translate, \
                                    nickname,domain,domainFull,item, \
                                    None,True)

        if len(timelineJson['orderedItems'])>=noOfItems:
            blogStr+=navigateStr

        return blogStr+htmlFooter()
    return None


def getBlogIndexesForAccounts(baseDir: str) -> {}:
    """ Get the index files for blogs for each account
    and add them to a dict
    """
    blogIndexes={}
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if 'inbox@' in acct:
                continue
            accountDir=os.path.join(baseDir+'/accounts', acct)
            blogsIndex=accountDir+'/tlblogs.index'
            if os.path.isfile(blogsIndex):
                blogIndexes[acct]=blogsIndex
    return blogIndexes

def noOfBlogAccounts(baseDir: str) -> int:
    """Returns the number of blog accounts
    """
    ctr=0
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if 'inbox@' in acct:
                continue
            accountDir=os.path.join(baseDir+'/accounts', acct)
            blogsIndex=accountDir+'/tlblogs.index'
            if os.path.isfile(blogsIndex):
                ctr+=1
    return ctr

def singleBlogAccountNickname(baseDir: str) -> str:
    """Returns the nickname of a single blog account
    """
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for acct in dirs:
            if '@' not in acct:
                continue
            if 'inbox@' in acct:
                continue
            accountDir=os.path.join(baseDir+'/accounts', acct)
            blogsIndex=accountDir+'/tlblogs.index'
            if os.path.isfile(blogsIndex):
                return acct.split('@')[0]
    return None

def htmlBlogView(authorized: bool, \
                 session,baseDir: str,httpPrefix: str, \
                 translate: {},domain: str,port: int, \
                 noOfItems: int) -> str:
    """Show the blog main page
    """
    blogStr=''

    cssFilename=baseDir+'/epicyon-blog.css'
    if os.path.isfile(baseDir+'/blog.css'):
        cssFilename=baseDir+'/blog.css'
    with open(cssFilename, 'r') as cssFile:
        blogCSS=cssFile.read()
        blogStr=htmlHeader(cssFilename,blogCSS)

        if noOfBlogAccounts(baseDir) <= 1:
            nickname=singleBlogAccountNickname(baseDir)
            if nickname:
                return htmlBlogPage(authorized,session, \
                                    baseDir,httpPrefix,translate, \
                                    nickname,domain,port, \
                                    noOfItems,1)

        domainFull=domain
        if port:
            if port!=80 and port!=443:
                domainFull=domain+':'+str(port)

        for subdir, dirs, files in os.walk(baseDir+'/accounts'):
            for acct in dirs:
                if '@' not in acct:
                    continue
                if 'inbox@' in acct:
                    continue
                accountDir=os.path.join(baseDir+'/accounts', acct)
                blogsIndex=accountDir+'/tlblogs.index'
                if os.path.isfile(blogsIndex):
                    blogStr+='<p class="blogaccount">'
                    blogStr+= \
                        '<a href="'+ \
                        httpPrefix+'://'+domainFull+'/blog/'+ \
                        acct.split('@')[0]+'">'+acct+'</a>'
                    blogStr+='</p>'

        return blogStr+htmlFooter()
    return None
