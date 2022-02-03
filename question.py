__filename__ = "question.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from utils import locate_post
from utils import load_json
from utils import save_json
from utils import has_object_dict


def question_update_votes(base_dir: str, nickname: str, domain: str,
                          reply_json: {}) -> ({}, str):
    """ For a given reply update the votes on a question
    Returns the question json object if the vote totals were changed
    """
    if not has_object_dict(reply_json):
        return None, None
    if not reply_json['object'].get('inReplyTo'):
        return None, None
    if not reply_json['object']['inReplyTo']:
        return None, None
    if not isinstance(reply_json['object']['inReplyTo'], str):
        return None, None
    if not reply_json['object'].get('name'):
        return None, None
    in_reply_to = reply_json['object']['inReplyTo']
    question_post_filename = \
        locate_post(base_dir, nickname, domain, in_reply_to)
    if not question_post_filename:
        return None, None
    question_json = load_json(question_post_filename)
    if not question_json:
        return None, None
    if not has_object_dict(question_json):
        return None, None
    if not question_json['object'].get('type'):
        return None, None
    if question_json['type'] != 'Question':
        return None, None
    if not question_json['object'].get('oneOf'):
        return None, None
    if not isinstance(question_json['object']['oneOf'], list):
        return None, None
    if not question_json['object'].get('content'):
        return None, None
    reply_vote = reply_json['object']['name']
    # does the reply name field match any possible question option?
    found_answer = None, None
    for possible_answer in question_json['object']['oneOf']:
        if not possible_answer.get('name'):
            continue
        if possible_answer['name'] == reply_vote:
            found_answer = possible_answer
            break
    if not found_answer:
        return None, None
    # update the voters file
    voters_file_separator = ';;;'
    voters_filename = question_post_filename.replace('.json', '.voters')
    if not os.path.isfile(voters_filename):
        # create a new voters file
        try:
            with open(voters_filename, 'w+') as voters_file:
                voters_file.write(reply_json['actor'] +
                                  voters_file_separator +
                                  found_answer + '\n')
        except OSError:
            print('EX: unable to write voters file ' + voters_filename)
    else:
        if reply_json['actor'] not in open(voters_filename).read():
            # append to the voters file
            try:
                with open(voters_filename, 'a+') as voters_file:
                    voters_file.write(reply_json['actor'] +
                                      voters_file_separator +
                                      found_answer + '\n')
            except OSError:
                print('EX: unable to append to voters file ' + voters_filename)
        else:
            # change an entry in the voters file
            with open(voters_filename, 'r') as voters_file:
                lines = voters_file.readlines()
                newlines = []
                save_voters_file = False
                for vote_line in lines:
                    if vote_line.startswith(reply_json['actor'] +
                                            voters_file_separator):
                        new_vote_line = reply_json['actor'] + \
                            voters_file_separator + found_answer + '\n'
                        if vote_line == new_vote_line:
                            break
                        save_voters_file = True
                        newlines.append(new_vote_line)
                    else:
                        newlines.append(vote_line)
                if save_voters_file:
                    try:
                        with open(voters_filename, 'w+') as voters_file:
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
        with open(voters_filename, 'r') as voters_file:
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


def is_question(postObjectJson: {}) -> bool:
    """ is the given post a question?
    """
    if postObjectJson['type'] != 'Create' and \
       postObjectJson['type'] != 'Update':
        return False
    if not has_object_dict(postObjectJson):
        return False
    if not postObjectJson['object'].get('type'):
        return False
    if postObjectJson['object']['type'] != 'Question':
        return False
    if not postObjectJson['object'].get('oneOf'):
        return False
    if not isinstance(postObjectJson['object']['oneOf'], list):
        return False
    return True
