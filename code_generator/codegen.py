#!/usr/bin/env python
from jinja2 import Environment, FileSystemLoader
import logging

log_msg = logging.getLogger(f"priLogger.{__name__}")

class TemplateException(Exception):
    pass


def gen_template(cfg):
    file_loader = FileSystemLoader("code_generator/templates")
    env = Environment(loader=file_loader, trim_blocks=True)
    template = env.get_template("interop.j2")
    rendered_template = template.render(yvars=cfg)
    if rendered_template:
        log_msg.info("Template has been rendered successfully")
        return rendered_template
    else:
        log_msg.error("Template was not rendered. Exiting..")
        raise TemplateException("ERROR: Template not rendered")
