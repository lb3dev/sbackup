#!/usr/bin/env python

import sys

if not (sys.version_info >= (3, 6, 0)):
    print("Exiting... Python version 3.6+ is required to run sbackup.py")
    exit(1)

import argparse
import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

config_default_directory = Path.home() / ".sbackup"
config_file_name = "sbackup.json"
logs_directory_name = "logs"
logs_file_name_prefix = "sbackup_"
logs_file_name_suffix = ".log"
run_remote = False

methods = {}
backups = {}


def execute_command(command, name):
    logging.info("Running " + name + " command:")
    logging.info(command)
    result = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    for line in iter(result.stdout.readline, b''):
        line = line.decode(sys.stdout.encoding)
        logging.info(line)
    result.stdout.close()
    result.wait()


def is_remote(path):
    return ':' in path


def verify_src(src):
    src_path = Path(src).expanduser()
    result = src_path.exists() and (src_path.is_file() or src_path.is_dir())
    if not result:
        logging.info("Skipped backup. Source path is invalid: " + src)
    return result


def verify_dst(dst):
    dst_path = Path(dst).expanduser()
    result = is_remote(dst) or (dst_path.exists() and (dst_path.is_file() or dst_path.is_dir()))
    if not result:
        logging.info("Skipped backup. Destination path is invalid: " + dst)
    return result


def verify_run_local_or_remote_backups(dst):
    if (not run_remote) and is_remote(dst):
        logging.info("Skipped backup. Remote backups skipped")
        return False
    elif run_remote and (not is_remote(dst)):
        logging.info("Skipped backup. Local backups skipped")
        return False
    return True


def verify_backup_method(method):
    if not (method in methods):
        logging.info("Skipped backup, backup method not found: " + method)
        return False
    backup_command = methods[method]["command"]
    if shutil.which(backup_command) is None:
        logging.info("Skipped backup. Command not found: " + backup_command)
        return False
    return True


def do_backups():
    counter = 0
    for backup in backups:
        counter = counter + 1
        logging.info("----------------------------------")
        logging.info("Processing backup #" + str(counter))

        method = backup["method"]
        src = backup["src"]
        dst = backup["dst"]
        skip_check = backup.get("skip_check", False)

        if not verify_run_local_or_remote_backups(dst):
            continue

        if not verify_src(src):
            continue

        if "pre" in backup:
            execute_command(backup["pre"], "prehook")

        if (not skip_check) and (not verify_dst(dst)):
            continue

        if not verify_backup_method(method):
            continue

        backup_command = methods[method]["command"]
        backup_command_params = methods[method]["params"]
        final_command_args = [backup_command] + backup_command_params.split(' ') + [src, dst]
        final_command = ' '.join(final_command_args)
        execute_command(final_command, "backup")

        if "post" in backup:
            execute_command(backup["post"], "posthook")


def load_config():
    global methods, backups
    config_file = config_default_directory / config_file_name
    if config_file.exists() and config_file.is_file():
        with config_file.open() as f:
            config = json.load(f)
            methods = config["methods"]
            backups = config["backups"]
            logging.info("Loaded backup configuration file from: " + str(config_file.absolute()))
    else:
        logging.info("Exiting... No configuration file found at: " + str(config_file.absolute()))
        exit(1)


def parse_arguments():
    global config_default_directory, run_remote
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Directory that contains sbackup.py configs", type=str)
    parser.add_argument("-r", "--remote", help="Run remote backups only", action="store_true")
    args = parser.parse_args()
    run_remote = args.remote
    if args.config:
        config_default_directory = Path(args.config).expanduser()


def configure_logging():
    formatter = logging.Formatter("%(asctime)s %(levelname)-5s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logs_directory = config_default_directory / logs_directory_name
    logs_directory.mkdir(exist_ok=True)

    log_file_name = logs_file_name_prefix + datetime.now().strftime("%Y-%m-%d") + logs_file_name_suffix
    file_handler = logging.FileHandler(logs_directory / log_file_name)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def sbackup():
    parse_arguments()
    configure_logging()

    logging.info("Started backups")
    load_config()
    do_backups()
    logging.info("Completed backups")


if __name__ == '__main__':
    sbackup()
