__filename__ = "question.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.4.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from utils import locate_post
from utils import load_json
from utils import save_json
from utils import has_object_dict
from utils import text_in_file
from utils import dangerous_markup


def is_vote(base_dir: str, nickname: str, domain: str,
            post_json_object: {}, debug: bool) -> bool:
    """ is the given post a vote on a Question?
    """
    post_obj = post_json_object
    if has_object_dict(post_json_object):
        post_obj = post_json_object['object']

    if not post_obj.get('inReplyTo'):
        return False
    if not isinstance(post_obj['inReplyTo'], str):
        return False
    if not post_obj.get('name'):
        return False

    if debug:
        print('VOTE: ' + str(post_obj))

    # is the replied to post a Question?
    in_reply_to = post_obj['inReplyTo']
    question_post_filename = \
        locate_post(base_dir, nickname, domain, in_reply_to)
    if not question_post_filename:
        if debug:
            print('VOTE REJECT: question does not exist ' + in_reply_to)
        return False
    question_json = load_json(question_post_filename)
    if not question_json:
        if debug:
            print('VOTE REJECT: invalid json ' + question_post_filename)
        return False
    if not has_object_dict(question_json):
        if debug:
            print('VOTE REJECT: question without object ' +
                  question_post_filename)
        return False
    if not question_json['object'].get('type'):
        if debug:
            print('VOTE REJECT: question without type ' +
                  question_post_filename)
        return False
    if question_json['type'] != 'Question':
        if debug:
            print('VOTE REJECT: not a question ' +
                  question_post_filename)
        return False

    # does the question have options?
    if not question_json['object'].get('oneOf'):
        if debug:
            print('VOTE REJECT: question has no options ' +
                  question_post_filename)
        return False
    if not isinstance(question_json['object']['oneOf'], list):
        if debug:
            print('VOTE REJECT: question options is not a list ' +
                  question_post_filename)
        return False

    # does the reply name field match any possible question option?
    reply_vote = post_json_object['name']
    found_answer_json = None
    for possible_answer in question_json['object']['oneOf']:
        if not possible_answer.get('name'):
            continue
        if possible_answer['name'] == reply_vote:
            found_answer_json = possible_answer
            break
    if not found_answer_json:
        if debug:
            print('VOTE REJECT: question answer not found ' +
                  question_post_filename + ' ' + reply_vote)
        return False
    return True


def question_update_votes(base_dir: str, nickname: str, domain: str,
                          reply_json: {}, debug: bool) -> ({}, str):
    """ For a given reply update the votes on a question
    Returns the question json object if the vote totals were changed
    """
    if not is_vote(base_dir, nickname, domain, reply_json, debug):
        return None, None

    post_obj = reply_json
    if has_object_dict(reply_json):
        post_obj = reply_json['object']
    reply_vote = post_obj['name']

    in_reply_to = post_obj['inReplyTo']
    question_post_filename = \
        locate_post(base_dir, nickname, domain, in_reply_to)
    if not question_post_filename:
        return None, None

    question_json = load_json(question_post_filename)
    if not question_json:
        return None, None

    # update the voters file
    voters_file_separator = ';;;'
    voters_filename = question_post_filename.replace('.json', '.voters')
    if not os.path.isfile(voters_filename):
        # create a new voters file
        try:
            with open(voters_filename, 'w+',
                      encoding='utf-8') as voters_file:
                voters_file.write(reply_json['actor'] +
                                  voters_file_separator +
                                  reply_vote + '\n')
        except OSError:
            print('EX: unable to write voters file ' + voters_filename)
    else:
        if not text_in_file(reply_json['actor'], voters_filename):
            # append to the voters file
            try:
                with open(voters_filename, 'a+',
                          encoding='utf-8') as voters_file:
                    voters_file.write(reply_json['actor'] +
                                      voters_file_separator +
                                      reply_vote + '\n')
            except OSError:
                print('EX: unable to append to voters file ' + voters_filename)
        else:
            # change an entry in the voters file
            with open(voters_filename, 'r',
                      encoding='utf-8') as voters_file:
                lines = voters_file.readlines()
                newlines = []
                save_voters_file = False
                for vote_line in lines:
                    if vote_line.startswith(reply_json['actor'] +
                                            voters_file_separator):
                        new_vote_line = reply_json['actor'] + \
                            voters_file_separator + reply_vote + '\n'
                        if vote_line == new_vote_line:
                            break
                        save_voters_file = True
                        newlines.append(new_vote_line)
                    else:
                        newlines.append(vote_line)
                if save_voters_file:
                    try:
                        with open(voters_filename, 'w+',
                                  encoding='utf-8') as voters_file:
                            for vote_line in newlines:
                                voters_file.write(vote_line)
                    except OSError:
                        print('EX: unable to write voters file2 ' +
                              voters_filename)
                else:
                    return None, None

    # update the vote counts
    question_totals_changed = False
    for possible_answer in question_json['object']['oneOf']:
        if not possible_answer.get('name'):
            continue
        total_items = 0
        with open(voters_filename, 'r', encoding='utf-8') as voters_file:
            lines = voters_file.readlines()
            for vote_line in lines:
                if vote_line.endswith(voters_file_separator +
                                      possible_answer['name'] + '\n'):
                    total_items += 1
        if possible_answer['replies']['totalItems'] != total_items:
            possible_answer['replies']['totalItems'] = total_items
            question_totals_changed = True
    if not question_totals_changed:
        return None, None

    # save the question with altered totals
    save_json(question_json, question_post_filename)
    return question_json, question_post_filename


def is_html_question(html_str: str) -> bool:
    """ is the given html string a Question?
    """
    if 'input type="radio" name="answer"' in html_str:
        return True
    return False


def is_question(post_json_object: {}) -> bool:
    """ is the given post a question?
    """
    if post_json_object['type'] != 'Create' and \
       post_json_object['type'] != 'Update':
        return False
    if not has_object_dict(post_json_object):
        return False
    if not post_json_object['object'].get('type'):
        return False
    if post_json_object['object']['type'] != 'Question':
        return False
    if not post_json_object['object'].get('oneOf'):
        return False
    if not isinstance(post_json_object['object']['oneOf'], list):
        return False
    return True


def dangerous_question(question_json: {},
                       allow_local_network_access: bool) -> bool:
    """does the given question contain dangerous markup?
    """
    if question_json.get('oneOf'):
        question_options = question_json['oneOf']
    else:
        question_options = question_json['object']['oneOf']
    for option in question_options:
        if option.get('name'):
            if dangerous_markup(option['name'], allow_local_network_access):
                return True
    return False
