""" Copyright (c) Trainline Limited, 2016. All rights reserved. See LICENSE.txt in the project root for license information. """
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

import os
import re
import traceback
import logging
import simplejson
import numbers

class LogWrapper(object):
    """ Instanciates logging wrapper to add useful information to all logs without repeating code """

    def __init__(self):
        """ Initialise logger """
        self.logger = logging.getLogger(__name__)

    def debug(self, message):
        """ Debug """
        self.logger.debug("%s - %s", function_name(), message)

    def info(self, message):
        """ Info """
        self.logger.info("%s - %s", function_name(), message)

    def warn(self, message):
        """ Warn """
        self.logger.warn("%s - %s", function_name(), message)

    def error(self, message):
        """ Error """
        self.logger.error("%s - %s", function_name(), message, exc_info=True)

    def critical(self, message):
        """ Critical """
        self.logger.critical("%s - %s", function_name(), message, exc_info=True)

class LogWrapperMultiprocess(object):
    """ Instanciates logging wrapper to add useful information to all logs without repeating code """

    @classmethod
    def install_mp_handler(cls, logger=None):
        """Wraps the handlers in the given Logger with an MultiProcessingHandler.
        :param logger: whose handlers to wrap. By default, the root logger."""
        import multiprocessing_logging
        if logger is None:
            logger = logging.getLogger()
        for i, orig_handler in enumerate(list(logger.handlers)):
            handler = multiprocessing_logging.MultiProcessingHandler(
                'mp-handler-{0}'.format(i), sub_handler=orig_handler)
            logger.removeHandler(orig_handler)
            logger.addHandler(handler)

    def __init__(self):
        """ Initialise logger """
        self.logger = logging.getLogger()
        self.install_mp_handler()

    @classmethod
    def process_name(cls):
        """ Return current process name for multithreaded envs """
        import multiprocessing
        mp_name = multiprocessing.current_process().name
        if mp_name is None:
            mp_name = "Main"
        return mp_name

    def debug(self, message):
        """ Debug """
        self.logger.debug("%s %s - %s", self.process_name(), function_name(), message)

    def info(self, message):
        """ Info """
        self.logger.info("%s %s - %s", self.process_name(), function_name(), message)

    def warn(self, message):
        """ Warn """
        self.logger.warn("%s %s - %s", self.process_name(), function_name(), message)

    def error(self, message):
        """ Error """
        self.logger.error("%s %s - %s", self.process_name(), function_name(), message, exc_info=True)

    def critical(self, message):
        """ Critical """
        self.logger.critical("%s %s - %s", self.process_name(), function_name(), message, exc_info=True)

def to_bool(value):
    """Converts 'something' to boolean. Raises exception for invalid formats
   Possible True  values: 1, True, "1", "TRue", "yes", "y", "t"
   Possible False values: 0, False, None, [], {}, "", "0", "faLse", "no", "n", "f", 0.0, ..."""
    if str(value).lower() in ("yes", "y", "true", "t", "1"):
        return True
    if str(value).lower() in ("no", "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"):
        return False
    raise Exception('Invalid value for boolean conversion: ' + str(value))

def to_list(value):
    """ Create an array from any kind of object """
    initial_list = [x.strip() for x in value.translate(None, '!@#$[]{}\'"').split(',')]
    return [x for x in initial_list if x]

def function_name():
    """ Return the name of the function calling this code """
    return traceback.extract_stack(None, 3)[0][2]

def json_encode(input_object):
    """ Encode and returns a JSON stream """
    return simplejson.dumps(input_object)

def json_decode(string):
    """ Decode a JSON stream and returns a python dictionary version """
    log = LogWrapper()
    try:
        decoded_json = simplejson.loads(string)
    except simplejson.JSONDecodeError:
        log.error('Can\'t decode JSON string: %s' % string)
        return None
    return decoded_json

def generate_sensu_check(check_name=None,
                         command=None,
                         handlers=['default'],
                         interval=120,
                         ocurrences=5,
                         refresh=300,
                         subscribers=['sensu-base'],
                         standalone=True,
                         timeout=120,
                         aggregate=False,
                         alert_after=600,
                         realert_every=30,
                         runbook='Needs information',
                         sla='No SLA defined',
                         team=None,
                         notification_email=False,
                         ticket=False,
                         project=False,
                         slack=False,
                         page=False,
                         tip='Fill me up with information',
                         tags=[],
                         **kwargs):
    """ Generates a valid json for a sensu check """
    # Checks validity of input
    if check_name is None:
        raise SyntaxError('Cannot create sensu check without a name')
    if command is None:
        raise SyntaxError('Need a valid command to create sensu check')
    if team is None:
        raise SyntaxError('Need to specify a valid team to assign events from this sensu check')
    # Check numbers
    for number in [interval, ocurrences, refresh, timeout, alert_after, realert_every]:
        if not isinstance(number, numbers.Number):
            raise SyntaxError('This parameter should be a number, instead I have %s' % number)
    content = {'checks':{check_name:{'command': command,
                                     'handlers': handlers,
                                     'interval': interval,
                                     'ocurrences': ocurrences,
                                     'refresh': refresh,
                                     'subscribers': subscribers,
                                     'standalone': standalone,
                                     'timeout': timeout,
                                     'aggregate': aggregate,
                                     'alert_after': alert_after,
                                     'realert_every': realert_every,
                                     'runbook': runbook,
                                     'sla': sla,
                                     'team': team,
                                     'notification_email': notification_email,
                                     'ticket': ticket,
                                     'project': project,
                                     'slack': slack,
                                     'page': page,
                                     'tip': tip,
                                     'tags': tags}}}
    for key, value in kwargs.iteritems():
        content.update({key: value})
    return json_encode(content)

def compare_file_write(filename=None, content=None):
    """ The function compares a file against a string of content and writes the file if it differs """
    log = LogWrapper()
    if filename is None or content is None:
        log.info('Cannot write new file %s as nothing to compare against' % filename)
        return False
    if os.path.isfile(filename):
        with open(filename, "r") as original_file:
            orig_file_string = original_file.read()
            if re.sub('[ \n]', '', orig_file_string) == re.sub('[ \n]', '', content):
                log.debug('File %s has not changed' % filename)
                write_file = False
            else:
                log.info('File %s changed, refreshing' % filename)
                write_file = True
    else:
        write_file = True

    # Creating destination directory files
    if write_file is True:
        log.debug('Writing file %s' % filename)
        with open(filename, 'w') as em_file:
            em_file.write(content)
        return True
    else:
        return False

def compare_purge_dir(file_list=[], directory=None, pattern=None):
    """ The function compares a file against a string of content and writes the file if it differs """
    log = LogWrapper()
    if directory is None:
        log.info('Cannot purge directory as no directory specified')
        return False
    local_directory = os.walk(directory)
    for _, _, local_files in local_directory:
        for local_file in local_files:
            if pattern is not None:
                if not local_file.startswith(pattern):
                    log.debug('File %s is outside our realm, skipping...' % local_file)
                    continue
            full_local_filename = "%s/%s" % (directory, local_file)
            if full_local_filename not in file_list:
                log.debug('Checking file %s' % full_local_filename)
                # Remove this file as it shoudldn't be here
                log.info('Removing file %s' % full_local_filename)
                try:
                    os.remove(full_local_filename)
                except OSError:
                    log.debug('Can\'t delete file %s, continuing' % full_local_filename)
    return True
