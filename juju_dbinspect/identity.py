import re

SERVICE_REGEX = re.compile("^([a-z][a-z0-9]*(-[a-z0-9]*[a-z][a-z0-9]*)*)$")


def is_machine(s):
    return s.isdigit()


def is_unit(s):
    if not '/' in s:
        return False
    svc, u = s.split('/', 1)
    return u.isdigit() and is_service(svc)


def is_service(s):
    return bool(SERVICE_REGEX.match(s))
