#!/usr/bin/env python
from pyFMG.fortimgr import FortiManager
from getpass import getpass
from datetime import datetime
from os import path
import logging

log_msg = logging.getLogger(f"priLogger.{__name__}")

_now = datetime.now()

class LockException(Exception):
    pass


class CommitException(Exception):
    pass


class BackupException(Exception):
    pass


class ScriptException(Exception):
    pass


class FGTinADOMException(Exception):
    pass

def  raise_exception(exception, error):
    log_msg.error(error)
    raise exception(error)

def toggle_lock(f):
    """
    Decorator that locks an ADOM before performing the requested
    action, and then unlocks it again
    """

    def _wrapper(*args, **kwargs):
        """
        Function to be applied on top of all deorated methods
        """
        fmg = kwargs["fmg"]
        adom = kwargs["adom_name"]
        code, res = lock_adom(fmg=fmg, adom_name=adom)
        if code != 0:
            raise_exception(LockException, "Unable to lock ADOM")
        log_msg.debug(f" {code} {res} : Successfully locked ADOM {adom}")
        results = f(*args, **kwargs)
        code, res = commit_adom(fmg=fmg, adom_name=adom)
        if code != 0:
            raise_exception(CommitException, "Unable to commit ADOM")
        log_msg.debug(f" {code} {res} : Successfully committed changes to ADOM {adom}")
        code, res = unlock_adom(fmg=fmg, adom_name=adom)
        if code != 0:
            raise_exception(LockException, "Unable to unlock ADOM")
        log_msg.debug(f" {code} {res} : Successfully unlocked ADOM {adom}")
        return results
    return _wrapper


def lock_adom(fmg, adom_name):
    code, res = fmg.lock_adom(adom_name)
    return code, res


def unlock_adom(fmg, adom_name):
    code, res = fmg.unlock_adom(adom_name)
    return code, res


def commit_adom(fmg, adom_name):
    code, res = fmg.commit_changes(adom_name)
    return code, res


@toggle_lock
def backup_config(fmg=None, adom_name=None, fgt_name=None):
    '''
    Backs up standard config using sys/proxy/json call from FortiManager
    Config is placed into _backups/ directory.
    '''
    backup_name = (
        f'_backups/Backup_{fgt_name}_{_now.strftime("%m-%d-%Y-%H-%M-%S")}.conf'
    )
    url_proxyjson = "/sys/proxy/json"
    proxydata = {
        "action": "get",
        "payload": {"scope": "global"},
        "resource": "/api/v2/monitor/system/config/backup",
        "target": [f"adom/{adom_name}/device/{fgt_name}"],
    }
    code, res = fmg.execute(url_proxyjson, data=proxydata)
    if code == 0:
        bresult = res[0].get('status', {}).get('code')
        if bresult == -6:
            raise_exception(FGTinADOMException, 'Problem calling sys/proxy/json against FGT in ADOM. Try refreshing connection from Dashboard > Connection Summary widget > Connectivity > refresh icon. ')
        with open(backup_name, "w") as bk:
            for line in res[0]["response"]:
                bk.write(line)
    else:
        raise_exception(BackupException, f"No results received before writing backup file {backup_name}")
    if path.exists(backup_name):
        log_msg.info(f"Successfully backed up config for {backup_name} ")
    else:
        raise_exception(BackupException, f"Unable to backup file {backup_name}")



@toggle_lock
def generate_script(fmg=None, adom_name=None, fgt_name=None, script_data=None):
    '''
    Uploads Jinja2 generated configuration text to specified ADOM as a CLI script.
    '''
    script_name = f"_interop_{fgt_name}_{_now.strftime('%m-%d-%Y-%H-%M-%S')}"
    code, res = fmg.set(
        f"/dvmdb/adom/{adom_name}/script/",
        content=script_data,
        name=script_name,
        type="cli",
        target="remote_device",
    )
    if not res:
        raise_exception(ScriptException, f"Script {script_name} failed during creation.")
    log_msg.info(f"Successfully created script in FMG {adom_name} named {script_name}")


def process(rcmds, **cfg):
    '''
    Connects to FortiManager API and executes backup + script upload.
    '''
    with FortiManager(
        cfg["fmg_addr"],
        cfg["fmg_uname"],
        getpass("\nEnter in you FMG API admin password: "),
        debug=cfg["verbosity_level"],
        disable_request_warnings=True,
    ) as fmg:
        backup_config(fmg=fmg, adom_name=cfg["adom_name"], fgt_name=cfg["fgt_name"])
        generate_script(
            fmg=fmg,
            adom_name=cfg["adom_name"],
            fgt_name=cfg["fgt_name"],
            script_data=rcmds,
        )
