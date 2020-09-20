#!/usr/bin/env python

import json
import os
import shutil
from pathlib import Path

CONFIG_FILE_DEFAULT_PATH = ".sbackup"
CONFIG_FILE_NAME = "backup.json"

methods = {}
backups = {}


def sb_print(message):
    print("[backup] " + message)


def is_remote(path):
    return ':' in path


def verify_src_and_dst(src, dst):
    src_path = Path(src)
    dst_path = Path(dst)
    return (src_path.exists() and (src_path.is_file() or src_path.is_dir())) \
        and (is_remote(dst) or (dst_path.exists() and (dst_path.is_dir())))


def do_backups():
    global methods, backups
    counter = 0
    for backup in backups:
        counter = counter + 1
        sb_print("")
        sb_print("Processing backup #" + str(counter))

        method = backup["method"]
        src = backup["src"]
        dst = backup["dst"]

        if method in methods:
            backup_command = methods[method]["command"]
            if shutil.which(backup_command) is None:
                sb_print("Skipped backup, command not found: " + backup_command)
                continue
            if not verify_src_and_dst(src, dst):
                sb_print("Skipped backup, invalid src or dst (" + src + " to " + dst + ")")
                continue

            if "pre" in backup:
                prehook = backup["pre"]
                sb_print("Running prehook command:")
                sb_print(prehook)
                os.system(prehook)

            backup_command_params = methods[method]["params"]
            final_command_args = [backup_command] + backup_command_params.split(' ') + [src, dst]
            final_command = ' '.join(final_command_args)
            sb_print("Running backup:")
            sb_print(final_command)
            os.system(final_command)

            if "post" in backup:
                posthook = backup["post"]
                sb_print("Running posthook command:")
                sb_print(posthook)
                os.system(posthook)
        else:
            sb_print("Skipped backup, backup method not found: " + method)
            continue
    sb_print("Completed backups")


def load_config():
    global methods, backups
    config_file = Path.home() / CONFIG_FILE_DEFAULT_PATH / CONFIG_FILE_NAME
    if config_file.exists() and config_file.is_file():
        with config_file.open() as f:
            config = json.load(f)
            methods = config["methods"]
            backups = config["backups"]
            sb_print("Loaded backup configuration file")
    else:
        sb_print("Exiting... No configuration file found at: " + str(config_file))
        exit(1)


def sbackup():
    load_config()
    do_backups()


if __name__ == '__main__':
    sbackup()
