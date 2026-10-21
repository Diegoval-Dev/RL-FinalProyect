import pglast
from pglast.parser import ParseError


def fingerprint(sql: str) -> str | None:
    try:
        return pglast.fingerprint(sql)
    except ParseError:
        return None
