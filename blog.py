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
from webinterface import contentWarningScriptOpen
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
                    postId: str,depth=0) -> int:
    """Returns the number of replies on the post
    This is recursive, so can handle replies to replies
    """
    if depth>4:
        return 0
    if not postId:
        return 0

    tryPostBox=('tlblogs','inbox','outbox')
    boxFound=False
    for postBox in tryPostBox:
        postFilename= \
            baseDir+'/accounts/'+nickname+'@'+domain+'/'+postBox+'/'+ \
            postId.replace('/','#')+'.replies'
        if os.path.isfile(postFilename):
            boxFound=True
            break
    if not boxFound:
        # post may exist but has no replies
        for postBox in tryPostBox:
            postFilename= \
                baseDir+'/accounts/'+nickname+'@'+domain+'/'+postBox+'/'+ \
                postId.replace('/','#')
            if os.path.isfile(postFilename):
                return 1
        return 0

    replies=0
    with open(postFilename, "r") as f:
        lines = f.readlines()
        for replyPostId in lines:
            replyPostId= \
                replyPostId.replace('\n','').replace('.json','').replace('.replies','')
            replies+= \
                1 + \
                noOfBlogReplies(baseDir,httpPrefix,translate, \
                                nickname,domain,domainFull, \
                                replyPostId,depth+1)
    return replies


def getBlogReplies(baseDir: str,httpPrefix: str,translate: {}, \
                   nickname: str,domain: str,domainFull: str, \
                   postId: str,depth=0) -> str:
    """Returns the number of replies on the post
    """
    if depth>4:
        return ''
    if not postId:
        return ''

    tryPostBox=('tlblogs','inbox','outbox')
    boxFound=False
    for postBox in tryPostBox:
        postFilename= \
            baseDir+'/accounts/'+nickname+'@'+domain+'/'+postBox+'/'+ \
            postId.replace('/','#')+'.replies'
        if os.path.isfile(postFilename):
            boxFound=True
            break
    if not boxFound:
        # post may exist but has no replies
        for postBox in tryPostBox:
            postFilename= \
                baseDir+'/accounts/'+nickname+'@'+domain+'/'+postBox+'/'+ \
                postId.replace('/','#')
            if os.path.isfile(postFilename):
                postFilename= \
                    baseDir+'/accounts/'+nickname+'@'+domain+ \
                    '/postcache/'+ \
                    postId.replace('/','#')+'.html'
                if os.path.isfile(postFilename):
                    with open(postFilename, "r") as postFile:
                        return postFile.read()+'\n'
        return ''

    with open(postFilename, "r") as f:
        lines = f.readlines()
        repliesStr=''
        for replyPostId in lines:
            replyPostId= \
                replyPostId.replace('\n','').replace('.json','').replace('.replies','')
            postFilename= \
                baseDir+'/accounts/'+nickname+'@'+domain+ \
                '/postcache/'+ \
                replyPostId.replace('\n','').replace('/','#')+'.html'
            if not os.path.isfile(postFilename):
                continue
            with open(postFilename, "r") as postFile:
                repliesStr+=postFile.read()+'\n'
            repliesStr+= \
                getBlogReplies(baseDir,httpPrefix,translate, \
                               nickname,domain,domainFull, \
                               replyPostId,depth+1)

        # indicate the reply indentation level
        indentStr='>'
        for indentLevel in range(depth):
            indentStr+=' >'

        return repliesStr.replace(translate['SHOW MORE'],indentStr).replace('?tl=outbox','?tl=tlblogs')
    return ''


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
    titleStr=''
    if postJsonObject['object'].get('summary'):
        titleStr=postJsonObject['object']['summary']
        blogStr+='<h1><a href="'+messageLink+'">'+titleStr+'</a></h1>\n'

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

    if not linkedAuthor:
        blogStr+= \
            '<p class="about"><a class="about" href="'+httpPrefix+'://'+domainFull+ \
            '/users/'+nickname+'">'+translate['About the author']+'</a></p>\n'

    replies= \
        noOfBlogReplies(baseDir,httpPrefix,translate, \
                        nickname,domain,domainFull, \
                        postJsonObject['object']['id'])
    if replies>0:
        if not authorized:
            blogStr+= \
                '<p class="blogreplies">'+ \
                translate['Replies'].lower()+': '+str(replies)+'</p>\n'
        else:
            blogStr+='<h1>'+translate['Replies']+'</h1>\n'
            blogStr+='<script>'+contentWarningScriptOpen()+'</script>\n'
            if not titleStr:
                blogStr+= \
                    getBlogReplies(baseDir,httpPrefix,translate, \
                                   nickname,domain,domainFull, \
                                   postJsonObject['object']['id'])
            else:
                blogStr+= \
                    getBlogReplies(baseDir,httpPrefix,translate, \
                                   nickname,domain,domainFull, \
                                   postJsonObject['object']['id']).replace('>'+titleStr+'<','')
            blogStr+='<br><hr>\n'
    return blogStr


def htmlBlogPostRSS(authorized: bool, \
                    baseDir: str,httpPrefix: str,translate: {}, \
                    nickname: str,domain: str,domainFull: str, \
                    postJsonObject: {}, \
                    handle: str,restrictToDomain: bool) -> str:
    """Returns the RSS feed for a single blog post
    """
    messageLink=''
    if postJsonObject['object'].get('id'):
        messageLink=postJsonObject['object']['id'].replace('/statuses/','/')
        if not restrictToDomain or \
           (restrictToDomain and '/'+domain in messageLink):
            if postJsonObject['object'].get('summary'):
                titleStr=postJsonObject['object']['summary']
                rssStr= '     <item>'
                rssStr+='         <title>'+titleStr+'</title>'
                rssStr+='         <link>'+messageLink+'</link>'
                rssStr+='     </item>'
    return rssStr


def htmlBlogPost(authorized: bool, \
                 baseDir: str,httpPrefix: str,translate: {}, \
                 nickname: str,domain: str,domainFull: str, \
                 postJsonObject: {}) -> str:
    """Returns a html blog post
    """
    blogStr=''

    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        blogCSS=cssFile.read()
        blogStr=htmlHeader(cssFilename,blogCSS)
        blogStr=blogStr.replace('.cwText','.cwTextInactive')

        blogStr+= \
            htmlBlogPostContent(authorized,baseDir,httpPrefix,translate, \
                                nickname,domain,domainFull,postJsonObject, \
                                None,False)

        # show rss link
        iconsDir=getIconsDir(baseDir)
        blogStr+='<p class="rssfeed">'
        blogStr+='<a href="'+httpPrefix+'://'+domainFull+'/blog/'+nickname+'/rss.xml">'
        blogStr+='<img loading="lazy" alt="RSS" title="RSS" src="/'+iconsDir+'/rss.png" />'
        blogStr+='</a></p>'

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

    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'
    with open(cssFilename, 'r') as cssFile:
        blogCSS=cssFile.read()
        blogStr=htmlHeader(cssFilename,blogCSS)
        blogStr=blogStr.replace('.cwText','.cwTextInactive')

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

        # show previous and next buttons
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

        # show rss link
        blogStr+='<p class="rssfeed">'
        blogStr+='<a href="'+httpPrefix+'://'+domainFull+'/blog/'+nickname+'/rss.xml">'
        blogStr+='<img loading="lazy" alt="RSS" title="RSS" src="/'+iconsDir+'/rss.png" />'
        blogStr+='</a></p>'

        return blogStr+htmlFooter()
    return None

def rssHeader(httpPrefix: str,nickname: str,domainFull: str,translate: {}) -> str:
    rssStr="<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
    rssStr+="<rss version=\"2.0\">"
    rssStr+='<channel>'
    rssStr+='    <title>'+translate['Blog']+'</title>'
    rssStr+='    <link>'+httpPrefix+'://'+domainFull+'/users/'+nickname+'/rss.xml'+'</link>'
    return rssStr

def rssFooter() -> str:
    rssStr='</channel>'
    rssStr+='</rss>'
    return rssStr

def htmlBlogPageRSS(authorized: bool, session, \
                    baseDir: str,httpPrefix: str,translate: {}, \
                    nickname: str,domain: str,port: int, \
                    noOfItems: int,pageNumber: int) -> str:
    """Returns an rss feed containing posts
    """
    if ' ' in nickname or '@' in nickname or '\n' in nickname:
        return None

    domainFull=domain
    if port:
        if port!=80 and port!=443:
            domainFull=domain+':'+str(port)

    blogRSS=rssHeader(httpPrefix,nickname,domainFull,translate)

    blogsIndex= \
        baseDir+'/accounts/'+nickname+'@'+domain+'/tlblogs.index'
    if not os.path.isfile(blogsIndex):
        return blogRSS+rssFooter()

    timelineJson= \
        createBlogsTimeline(session,baseDir, \
                            nickname,domain,port,httpPrefix, \
                            noOfItems,False,False,pageNumber)

    if not timelineJson:
        return blogRSS+rssFooter()

    if pageNumber!=None:        
        for item in timelineJson['orderedItems']:
            if item['type']!='Create':
                continue

            blogRSS+= \
                htmlBlogPostRSS(authorized,baseDir,httpPrefix,translate, \
                                nickname,domain,domainFull,item, \
                                None,True)

    return blogRSS+rssFooter()


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

    cssFilename=baseDir+'/epicyon-profile.css'
    if os.path.isfile(baseDir+'/epicyon.css'):
        cssFilename=baseDir+'/epicyon.css'
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
