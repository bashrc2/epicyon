__filename__ = "semantic.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"


def isAccusatory(content: str, translate: {}, threshold=3) -> bool:
    """Indicates whether the given content is an accusatory post
    """
    words = ('you', 'your', "you're", 'if you', 'you are')

    if translate:
        wordsTranslated = []
        for wrd in words:
            translated = translate[wrd]
            if '|' not in translated:
                if translated not in wordsTranslated:
                    wordsTranslated.append(translated)
            else:
                # handle differing genders
                words2 = translated.split('|')
                for wrd2 in words2:
                    if wrd2.strip() not in wordsTranslated:
                        wordsTranslated.append(translated)
    else:
        wordsTranslated = words

    contentLower = content.lower()
    ctr = 0
    for wrd in wordsTranslated:
        ctr += contentLower.count(wrd + ' ')
    if ctr >= threshold:
        return True
    return False


def labelAccusatoryPost(postJsonObject: {}, translate: {}, threshold=3):
    """If a post is accusatory and it doesn't mention anyone
    specific and isn't a reply and it doesn't have a content
    warning then add a default 'accusatory' content warning
    """
    if not postJsonObject.get('object'):
        return
    if not isinstance(postJsonObject['object'], dict):
        return
    if not postJsonObject['object'].get('content'):
        return
    if not postJsonObject['object'].get('type'):
        return
    if postJsonObject['object']['type'] == 'Article':
        return
    if postJsonObject['object'].get('inReplyTo'):
        return
    if not isinstance(postJsonObject['object']['content'], str):
        return
    if '@' in postJsonObject['object']['content']:
        return
    if not isAccusatory(postJsonObject['object']['content'],
                        translate, threshold):
        return
    cwStr = translate['Accusatory']
    if postJsonObject['object'].get('summary'):
        if cwStr not in postJsonObject['object']['summary']:
            postJsonObject['object']['summary'] = \
                cwStr + ', ' + postJsonObject['object']['summary']
    else:
        postJsonObject['object']['summary'] = cwStr
    postJsonObject['object']['sensitive'] = True
