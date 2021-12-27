__filename__ = "webapp_question.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from question import isQuestion
from utils import remove_id_ending
from utils import acct_dir


def insertQuestion(base_dir: str, translate: {},
                   nickname: str, domain: str, port: int,
                   content: str,
                   post_json_object: {}, pageNumber: int) -> str:
    """ Inserts question selection into a post
    """
    if not isQuestion(post_json_object):
        return content
    if len(post_json_object['object']['oneOf']) == 0:
        return content
    messageId = remove_id_ending(post_json_object['id'])
    if '#' in messageId:
        messageId = messageId.split('#', 1)[0]
    pageNumberStr = ''
    if pageNumber:
        pageNumberStr = '?page=' + str(pageNumber)

    votesFilename = \
        acct_dir(base_dir, nickname, domain) + '/questions.txt'

    showQuestionResults = False
    if os.path.isfile(votesFilename):
        if messageId in open(votesFilename).read():
            showQuestionResults = True

    if not showQuestionResults:
        # show the question options
        content += '<div class="question">'
        content += \
            '<form method="POST" action="/users/' + \
            nickname + '/question' + pageNumberStr + '">\n'
        content += \
            '<input type="hidden" name="messageId" value="' + \
            messageId + '">\n<br>\n'
        for choice in post_json_object['object']['oneOf']:
            if not choice.get('type'):
                continue
            if not choice.get('name'):
                continue
            content += \
                '<input type="radio" name="answer" value="' + \
                choice['name'] + '"> ' + choice['name'] + '<br><br>\n'
        content += \
            '<input type="submit" value="' + \
            translate['Vote'] + '" class="vote"><br><br>\n'
        content += '</form>\n</div>\n'
    else:
        # show the responses to a question
        content += '<div class="questionresult">\n'

        # get the maximum number of votes
        maxVotes = 1
        for questionOption in post_json_object['object']['oneOf']:
            if not questionOption.get('name'):
                continue
            if not questionOption.get('replies'):
                continue
            votes = 0
            try:
                votes = int(questionOption['replies']['totalItems'])
            except BaseException:
                print('EX: insertQuestion unable to convert to int')
            if votes > maxVotes:
                maxVotes = int(votes+1)

        # show the votes as sliders
        questionCtr = 1
        for questionOption in post_json_object['object']['oneOf']:
            if not questionOption.get('name'):
                continue
            if not questionOption.get('replies'):
                continue
            votes = 0
            try:
                votes = int(questionOption['replies']['totalItems'])
            except BaseException:
                print('EX: insertQuestion unable to convert to int 2')
            votesPercent = str(int(votes * 100 / maxVotes))

            content += \
                '<p>\n' + \
                '  <label class="labels">' + \
                questionOption['name'] + '</label><br>\n' + \
                '  <svg class="voteresult">\n' + \
                '    <rect width="' + votesPercent + \
                '%" class="voteresultbar" />\n' + \
                '  </svg>' + \
                '  <label class="labels">' + votesPercent + '%</label>\n' + \
                '</p>\n'

            questionCtr += 1
        content += '</div>\n'
    return content
