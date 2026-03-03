import re

WINDOWS_SEP = '\\'
NON_WINDOWS_SEP = '/'


def encode_path(path: str) -> str:
    labels_seperator: chr = NON_WINDOWS_SEP
    if path[0] == NON_WINDOWS_SEP:
        path = path[1:]
    else:
        path = path[0] + path[2:]
        labels_seperator = WINDOWS_SEP
    labels = path.split(labels_seperator)
    labels = [encode_label(label) for label in labels]
    return '.'.join(labels).removesuffix('.')


def encode_label(label: str) -> str:
    return label.encode('utf-8').hex()


def decode_path(path: str) -> str:
    labels = path.split('.')
    labels = [decode_label(label) for label in labels]
    return '.'.join(labels)


def decode_label(label: str) -> str:
    return bytes.fromhex(label).decode('utf-8')


def get_raw_sub_path(sub_path: str, raw_path: str) -> str:
    sep = NON_WINDOWS_SEP
    num_sep = 2
    if raw_path[0] != sep:
        sep = WINDOWS_SEP
        num_sep = 1
    num_sep += sub_path.count(".")
    pattern = f'^([^{re.escape(sep)}]*{re.escape(sep)}?)' + '{' + str(num_sep) + '}'
    raw_sub_path = re.match(pattern, raw_path).group(0)
    if sub_path.count(".") != 0 or sep != WINDOWS_SEP:
        raw_sub_path = raw_sub_path.removesuffix(sep)
    return raw_sub_path
