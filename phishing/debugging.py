"""A set of functions to help debuging"""


import logging
import config
import os
from logging.handlers import TimedRotatingFileHandler


def configure_logger():
    format = "%(created)f|%(pathname)s|%(message)s"

    if not os.path.exists(config.log_dir):
        os.makedirs(config.log_dir)
    access_log_file = os.path.join(config.log_dir,
                                   "access_{port}.log".format(port=config.port))
    access_log_handler = TimedRotatingFileHandler(access_log_file,
                                                  when="midnight")
    access_log_formatter = logging.Formatter("%(created)f|%(message)s")
    access_log_handler.setFormatter(access_log_formatter)
    access_logger = logging.getLogger('tornado.access')
    access_logger.addHandler(access_log_handler)
    access_logger.propagate = False

    error_log_file = os.path.join(config.log_dir,
                                  "error_{port}.log".format(port=config.port))
    error_log_handler = TimedRotatingFileHandler(error_log_file,
                                                 when="midnight")
    error_log_formatter = logging.Formatter(format)
    error_log_handler.setFormatter(error_log_formatter)
    error_logger = logging.getLogger('tornado.application')
    error_logger.addHandler(error_log_handler)
    error_logger.propagate = False

    gen_log_file = os.path.join(config.log_dir,
                                "gen_{port}.log".format(port=config.port))
    gen_log_handler = TimedRotatingFileHandler(gen_log_file,
                                               when="midnight")
    gen_log_formatter = logging.Formatter(format)
    gen_log_handler.setFormatter(gen_log_formatter)
    gen_logger = logging.getLogger('tornado.general')
    gen_logger.setLevel(logging.DEBUG if config.debug else logging.WARNING)
    gen_logger.addHandler(gen_log_handler)
    gen_logger.warning("tornado started (pid:{0}).".format(os.getpid()))
    gen_logger.propagate = False
