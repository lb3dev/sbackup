#!/usr/bin/env python

import sys

if not (sys.version_info >= (3, 6, 0)):
    print("Exiting... Python version 3.6+ is required to run sbackup.py")
    exit(1)

import argparse
import json
import logging
import os
import shutil
from pathlib import Path

config_default_directory = Path.home() / ".sbackup"
config_file_name = "sbackup.json"
logs_directory_name = "logs"

methods = {}
backups = {}


def execute_command(command, name):
    logging.info("Running " + name + " command:")
    logging.info(command)
    os.system(command)


def is_remote(path):
    return ':' in path


def verify_src_and_dst(src, dst):
    src_path = Path(src).expanduser()
    dst_path = Path(dst).expanduser()
    return (src_path.exists() and (src_path.is_file() or src_path.is_dir())) \
        and (is_remote(dst) or (dst_path.exists() and (dst_path.is_dir())))


def do_backups():
    global methods, backups
    counter = 0
    for backup in backups:
        counter = counter + 1
        logging.info("----------------------------------")
        logging.info("Processing backup #" + str(counter))

        method = backup["method"]
        src = backup["src"]
        dst = backup["dst"]

        if method in methods:
            backup_command = methods[method]["command"]
            if shutil.which(backup_command) is None:
                logging.info("Skipped backup, command not found: " + backup_command)
                continue
            if not verify_src_and_dst(src, dst):
                logging.info("Skipped backup, invalid src or dst (" + src + " to " + dst + ")")
                continue

            if "pre" in backup:
                execute_command(backup["pre"], "prehook")

            backup_command_params = methods[method]["params"]
            final_command_args = [backup_command] + backup_command_params.split(' ') + [src, dst]
            final_command = ' '.join(final_command_args)
            execute_command(final_command, "backup")

            if "post" in backup:
                execute_command(backup["post"], "posthook")
        else:
            logging.info("Skipped backup, backup method not found: " + method)
            continue


def load_config():
    global methods, backups
    config_file = config_default_directory / config_file_name
    if config_file.exists() and config_file.is_file():
        with config_file.open() as f:
            config = json.load(f)
            methods = config["methods"]
            backups = config["backups"]
            logging.info("Loaded backup configuration file from: " + str(config_file))
    else:
        logging.info("Exiting... No configuration file found at: " + str(config_file))
        exit(1)


def parse_arguments():
    global config_default_directory
    parser = argparse.ArgumentParser()
    parser.add_argument("-cd", "--config-directory", help="Directory that contains sbackup.py configs", type=str)
    args = parser.parse_args()
    if args.config_directory:
        config_default_directory = Path(args.config_directory).expanduser()


def configure_logging():
    logging.basicConfig(stream=sys.stdout, format="[backup] %(asctime)s %(levelname)-6s: %(message)s",
                        level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
    logs_directory = config_default_directory / logs_directory_name
    logs_directory.mkdir(exist_ok=True)


def sbackup():
    parse_arguments()
    configure_logging()

    logging.info("Started backups")
    load_config()
    do_backups()
    logging.info("Completed backups")


if __name__ == '__main__':
    sbackup()
