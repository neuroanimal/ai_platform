import re
import io
from ruamel import yaml as yml
import yaml
from config.constants import *

# Initialize YAML processors
yamel = yml.YAML(typ='rt', pure=True)
yamel.preserve_quotes = True
yaml.preserve_quotes = True
yml.preserve_quotes = True

yml.allow_duplicate_keys = None
yaml.allow_duplicate_keys = True
yamel.allow_duplicate_keys = None

fl = yaml.FullLoader
dl = yml.RoundTripLoader
dd = yml.RoundTripDumper


def indent_level(yaml_row_arg, delimiter=" ", tab_size=TAB_SIZE, clean_chars=CLEAN_CHARS):
    """Calculate indentation level of a YAML row."""
    yaml_row = yaml_row_arg.lstrip(clean_chars).replace("\t", delimiter * tab_size)
    level = 0
    for i in range(0, len(yaml_row)):
        level = i
        if yaml_row[i] != delimiter:
            break
    if yaml_row.lstrip().startswith('-'):
        level += 2
    return level


def first_row(rows):
    """Get first row from multi-line string."""
    return rows.strip("\n").split('\n')[0]


def uncomment_row(row):
    """Remove comment characters from a YAML row."""
    lvl_before_uncom = indent_level(row)
    uncom_row = re.sub("[#]+", "", row, count=1)
    lvl_after_uncom = indent_level(uncom_row)
    diff_lvl_before_after_uncom = lvl_after_uncom - lvl_before_uncom

    if diff_lvl_before_after_uncom > 0:
        if lvl_before_uncom % 2 == 0:
            if lvl_after_uncom % 2 == 1:
                lf_prefix = ""
                if row.startswith("\n"):
                    num_of_lf = indent_level(row, delimiter="\n", tab_size=0, clean_chars=" ")
                    lf_prefix = "\n" * num_of_lf
                if row.lstrip(" \t\r\n").startswith('# '):
                    uncom_row = lf_prefix + uncom_row.lstrip("\n")[1:]
                else:
                    uncom_row = lf_prefix + " " + uncom_row.lstrip("\n")
    return uncom_row


def is_correct_yaml(last_block, row_num):
    """Check if a block is valid YAML."""
    if VERBOSE:
        print(f"Is this correct YAML in row #{row_num}:\n'{last_block}'\n?")

    try:
        correct_yaml = yamel.load(last_block)
        if correct_yaml is None:
            if last_block.strip("\n\t ").startswith("#"):
                return True, correct_yaml
            else:
                return True, correct_yaml
        elif isinstance(correct_yaml, str):
            if DEBUG:
                print(f"DEBUG: False => Possible incorrect YAML due to: '{last_block}' is rather a String, not YAML content")
            return False, correct_yaml
        elif isinstance(correct_yaml, list):
            first_item = list(correct_yaml)[0]
            if isinstance(first_item, str) and ":" not in first_item and " " in first_item:
                print(f"Considering as comment text array/list item: {last_block}")
                return False, correct_yaml
            elif last_block.lstrip().startswith('- 10.40.0.'):
                print("WARNING! Considering as comment text IP item")
                return False, correct_yaml
            elif isinstance(first_item, str) and len(first_item.strip().split(' ')) > 2:
                print("WARNING! Considering as comment text with several spaces inside")
                return False, correct_yaml
            elif isinstance(first_item, str) and len(first_item.strip().split(':')) > 3:
                print("WARNING! Considering as comment text with special characters like colon")
                return False, correct_yaml
            else:
                return True, correct_yaml
        elif isinstance(correct_yaml, yml.comments.CommentedSeq):
            return True, correct_yaml
        elif isinstance(correct_yaml, dict):
            keys = list(dict(correct_yaml).keys())
            key = keys[0]

            excluded_keys = ['IPv4', 'IPv6', 'VirtualTapBroker', 'NFStatusNotify',
                           'DUAL_STACK_INBOUND_PASSTHROUGH', 'PILOT_ENABLE_INBOUND_PASSTHROUGH',
                           'ETCD_SNAPSHOT_COUNT', 'ETCD_QUOTA_BACKEND_BYTES',
                           'ENABLE_TLS_ON_SIDECAR_INGRESS', 'ENABLE_AUTO_SNI']

            if ((key[0].isupper() or " " in key) and key not in excluded_keys and
                not key.startswith("PREFIX-") and not key.startswith("ENABLE_") and
                not key.startswith("ETCD_")):
                print("WARNING! Considering as comment text KVP block like title")
                return False, correct_yaml
            elif key in ["supportedGps", "proxy.istio.io/config"] and isinstance(correct_yaml[key], str):
                return True, correct_yaml
            elif (correct_yaml[key] and isinstance(correct_yaml[key], str) and
                  len(correct_yaml[key].strip().split(' ')) > 2 and
                  not (correct_yaml[key].strip().startswith('"') and correct_yaml[key].strip().endswith('"'))):
                if key == "cleanupSchedule" or (key == 'filter' and correct_yaml[key].startswith("ruby")):
                    return True, correct_yaml
                print("WARNING! Considering as comment text KVP block with value like title")
                return False, correct_yaml
            else:
                return True, correct_yaml
        elif isinstance(correct_yaml, yml.comments.CommentedMap):
            return True, correct_yaml
        elif ":" not in last_block:
            return True, correct_yaml
        else:
            return True, correct_yaml
    except (yml.scanner.ScannerError, yml.composer.ComposerError, yml.parser.ParserError) as ex:
        if DEBUG:
            print(f"Incorrect YAML block: {last_block}\nException was: {ex}")
        return False, None


def process_yaml_file0(in_yaml_content):
    """Process YAML using PyYAML."""
    if STOP_ON_PYYAML_ERROR:
        in_out_yaml = yaml.safe_load(in_yaml_content)
    else:
        try:
            in_out_yaml = yaml.safe_load(in_yaml_content)
        except (yaml.scanner.ScannerError, yaml.composer.ComposerError, yaml.parser.ParserError) as ex:
            print("CRITICAL! PYYAML ERROR ON LOADING YAML CONTENT: %s", ex)
            return ""
    out_yaml_content = yaml.dump(in_out_yaml)
    return out_yaml_content


def process_yaml_file1(in_yaml_content):
    """Process YAML using Ruamel.YAML."""
    if STOP_ON_RUAMEL_ERROR:
        in_out_yaml = yamel.load(in_yaml_content)
    else:
        try:
            in_out_yaml = yamel.load(in_yaml_content)
        except (yml.scanner.ScannerError, yml.composer.ComposerError, yml.parser.ParserError) as ex:
            print("CRITICAL! RUEMAL ERROR ON LOADING YAML CONTENT: %s", ex)
            return ""

    buf = io.BytesIO()
    out_yaml_content = yamel.dump(data=in_out_yaml, stream=buf)
    if out_yaml_content is None:
        byt = buf.getvalue()
        out_yaml_content = bytes.decode(byt, ENCODING)
    return out_yaml_content