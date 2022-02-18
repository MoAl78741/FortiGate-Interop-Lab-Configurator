#!/usr/bin/env python
import code_generator.codegen as cg
import fmg_operations.fmgops as fo
from yaml import full_load
import logging.config
from logging_config import logging_schema
from os import makedirs

# create directories
makedirs("_logs/", exist_ok=True)
makedirs("_backups/", exist_ok=True)

# setup logging
logging.config.dictConfig(logging_schema)
log_msg = logging.getLogger("priLogger")

config_file = "config.yaml"


class YAMLException(Exception):
    pass


def yaml_values(config_file) -> dict:
    """
    Open YAML and assign var cfg to file
    :param config_file: path of yaml file
    :return dict
    """
    try:
        with open(config_file, mode="rt") as yfile:
            return full_load(yfile)
    except IOError:
        log_msg.error(f"Config file: {config_file} is missing. Exiting..")
        exit(1)


def main():
    cfg = yaml_values(config_file)
    if not cfg:
        raise YAMLException(f"Unable to parse {config_file}")
    log_msg.debug(f"Successfully processed {config_file}")

    rendered_cmds = cg.gen_template(cfg)
    fo.process(rendered_cmds, **cfg)


if __name__ == "__main__":
    main()
