import io
import json
import os
import re
import sys
import glob
from box import Box
import yaml
from ruamel import yaml as yml
from yamllint.config import YamlLintConfig
from yamllint import linter
# from IPython.display import display
from prettyformatter import pprint as pp
# from pprint import PrettyPrinter


### yamel = yml.YAML()
yamel = yml.YAML(typ='rt', pure=True)
### yamel = yml.YAML(typ='unsafe', pure=True)
yamel.preserve_quotes = True
yaml.preserve_quotes = True
yml.preserve_quotes = True

yml.allow_duplicate_keys = None  # True  # None
yaml.allow_duplicate_keys = True
yamel.allow_duplicate_keys = None  # True  # None

delim = "/"

fl = yaml.FullLoader
dl = yml.RoundTripLoader
dd = yml.RoundTripDumper
# dd.process_scalar = process_scalar
# PP = PrettyPrinter(indent=2)
# ppp = PP.pprint


DEBUG = False  # True  # False
VERBOSE = False  # True  # False
FORCE_REWRITING = True
STOP_ON_RUAMEL_ERROR = False  # True  # False
STOP_ON_PYYAML_ERROR = False
MAX_NUM_OF_ERRORS_TO_BE_FIXED = 2000  # 20


def print_keys(mydict):
    print("\n".join([k for k in mydict.keys()]))


def fix_values(yaml_content, map_path_mrcf, map_path_helm, system_size, priorities):
    row_num = 0
    output = ""
    in_rows = yaml_content.replace('\n\n','\n').replace('\n\n','\n').replace('\n\n','\n').split("\n")
    out_rows = []
    parent_paths = []
    paths = []
    level_reached = []
    value_of_path = {}
    row_num_of_path = {}
    for row in in_rows:
        if DEBUG:
            print(f"\nDEBUG: Processing row #{row_num}: {row}")
        paths.append("")
        parent_paths.append("")
        level_reached.append("")

        ind_lvl = indent_level(row)
        level_reached[row_num] = ind_lvl

        row_before_comment = None
        comment_in_row = None
        row_typ = None
        key = None
        val = None
        if row.strip().startswith('#'):
            row_typ = 'comment'
            comment_in_row = row.split("#", 1)[1]
        elif '#' in row:
            comment_in_row = row.split("#", 1)[1]
            row_before_comment = row.split("#", 1)[0]
        else:
            row_before_comment = row
        if DEBUG:
            print(f"\nDEBUG: Comment in row? #{row_num}: {comment_in_row}")
        if row_before_comment:
            paths[row_num] = "/"
            if row_before_comment.lstrip().startswith('-'):
                row_typ = 'array_item'
                ######### ind_lvl += 2  #########
                key_row = row_before_comment.strip()[1:].strip()
                if row_before_comment.strip().endswith(':'):
                    row_typ = 'array_item_object_parent'
                    key = key_row.strip()[0:-1].strip()
                    out_rows.append(row)
                elif ':' in row_before_comment:
                    row_typ = 'array_item_object_kvp'
                    key_value_pair = key_row.strip().split(':', 1)
                    key = key_value_pair[0]
                    val = key_value_pair[1]
                    if "{{" in val and "}}" in val:
                        if "_or_" in val:
                            alt_vals = val.strip(" \t\"\"''")[2:-2].split("_or_")
                            if DEBUG:
                                print(f"DETECTED ITEM PLACEHOLDER WITH ALTERNATIVE VALUES: {alt_vals}")
                    out_rows.append(row)
                else:
                    row_typ = 'array_item_object_leaf'
                    out_rows.append(row)
            elif row_before_comment.strip().endswith('|'):
                row_typ = 'multiline_string'
                key = row_before_comment.strip()[0:-1].strip()
                # val = ...  # TODO
                out_rows.append(row)
            elif row_before_comment.strip().endswith('<'):
                row_typ = 'multiline_something1'
                key = row_before_comment.strip()[0:-1].strip()
                # val = ...  # TODO
                out_rows.append(row)
            elif row_before_comment.strip().endswith('>'):
                row_typ = 'multiline_something2'
                key = row_before_comment.strip()[0:-1].strip()
                # val = ...  # TODO
                out_rows.append(row)
            elif row_before_comment.strip().endswith('[]'):
                row_typ = 'array_empty'
                key = row_before_comment.strip()[0:-2].strip()
                val = []
                out_rows.append(row)
            elif row_before_comment.strip().endswith('{}'):
                row_typ = 'object_empty'
                key = row_before_comment.strip()[0:-2].strip()
                val = {}
                out_rows.append(row)
            elif row_before_comment.strip().endswith(':'):
                row_typ = 'object_parent'
                key = row_before_comment.strip()[0:-1].strip()
                out_rows.append(row)
            elif ':' in row_before_comment:
                row_typ = 'object_kvp'
                key_value_pair = row_before_comment.strip("").split(':', 1)
                key = key_value_pair[0].strip()
                val = key_value_pair[1].strip()
                if "{{" in val and "}}" in val:
                    if "_or_" in val:
                        alt_vals = val.strip()[2:-2].strip("{}\t\"\"''").split("_or_")
                        if DEBUG:
                            print(f"\tDETECTED PLACEHOLDER WITH ALTERNATIVE VALUES: {alt_vals}")
                out_rows.append(row)
            else:
                row_typ = 'object_leaf'
                out_rows.append(row)

            if DEBUG:
                print(f"\tkey = '{key}'")
            if key:
                paths[row_num] += key
            if DEBUG:
                print(f"\tpath[{row_num}] = '{paths[row_num]}'")
            parent_paths[row_num] = "/".join(paths[row_num].split("/")[0:-1])
            if parent_paths[row_num] == "":
                parent_paths[row_num] = "/"
            if DEBUG:
                print(f"\tparent[{row_num}] = '{parent_paths[row_num]}'")

            # compose path from parent keys
            if row_num > 0:
            ### if row_num > 1:
                for i in range(row_num - 1, -1, -1):
                ### for i in range(row_num - 1, row_num - 2, -1):
                    ind_lvl_i = indent_level(in_rows[i])
                    # level_reached[row_num] = ind_lvl_i
                    if in_rows[i].lstrip().startswith('#'):
                        if VERBOSE:
                            print(f"\t\tContinue as row {i} is a comment: {in_rows[i]}")
                        if i <= 0:
                            if VERBOSE:
                                print(f"\t\tEnd of loop and not found any parent key, so still path[{row_num}] == {paths[row_num]}")
                            break
                        continue  # break
                    elif ind_lvl_i > ind_lvl:
                        if VERBOSE:
                            print(f"\t\tContinue? as level[{i}]:{ind_lvl_i} > level:{ind_lvl}")
                        continue  # break
                    elif ind_lvl_i == ind_lvl:
                        if VERBOSE:
                            print(f"\t\tContinue as level[{i}]:{ind_lvl_i} == level:{ind_lvl}")
                        continue
                    elif paths[i] not in ["", "/"] and paths[row_num].startswith(paths[i]):
                        # eg.: /global/security/policyBinding/create starts with /global/security
                        if VERBOSE:
                            print(f"\t\t\tBreak as path[{i}]={paths[i]} is beginning/parent of path[{row_num}]={paths[row_num]}")
                        break
                    else:
                        delimiter = ''  # '/'
                        new_path = paths[i] + delimiter + paths[row_num]
                        if VERBOSE:
                            print(f"\tlevel[{i}]={ind_lvl_i} + {ind_lvl}=level, path[{row_num}] = path[{i}] + path[{row_num}] => {paths[i]} + {paths[row_num]} = {new_path}")
                        paths[row_num] = new_path
                        if ind_lvl_i == 0:
                            # already reached zero level
                            # unfortunately often we should not break on reaching level 0, as it is just empty row delimiting sections
                            # it would be better to remove empty rows before processing
                            level_reached[row_num] = 0
                            if VERBOSE:
                                print(f"\t\t\tBreak as level_reached[row_num:{row_num}] == 0")
                            break
                        elif level_reached[i] == 0:
                            if VERBOSE:
                                print(f"\t\t\tBreak as level_reached[i:{i}] == 0")
                            break
                        else:
                            # we break as we added full-path parent
                            if VERBOSE:
                                print("\t\t\tBreak as we added full-path parent")
                            break
                        ### elif paths[row_num].startswith(parent_paths[i] + delimiter + paths[i]):
                        ###     break
                if VERBOSE:
                    print(f"\tLoop finished with path[{row_num}] == {paths[row_num]}")
            else:
                if VERBOSE:
                    print(f"\tzero path[{row_num}] = '{paths[row_num]}'")
            row_num_of_path[paths[row_num]] = row_num
            value_of_path[paths[row_num]] = val

        elif row_typ == 'comment':
            out_rows.append(row)
            if VERBOSE:
                print(f"\tcomment row path[{row_num}] = \"{paths[row_num]}\"")
        elif in_rows[row_num].strip() == "":
            out_rows.append(row)
            if VERBOSE:
                print(f"\tempty row path[{row_num}] = \"{paths[row_num]}\"")
        else:
            out_rows.append(row)
            if VERBOSE:
                print(f"\tunknown row path[{row_num}] = \"{paths[row_num]}\"")

        if DEBUG:
            print(f"DEBUG: The output_row[{row_num}]: {out_rows[row_num]}")
            print(f"DEBUG: The output_path[{row_num}]   = \"{paths[row_num]}\"")
        row_num += 1
    # print(f"Paths detected in YAML template:\n")
    # pp(paths)
    # print()
    system_size_mapping = {
        "small-system": "default_small_system_profile",
        "standard-system": "default_standard_system_profile",
        "large-system": "default_large_system_profile",
    }
    system_size_mapped = system_size_mapping[system_size] if system_size in system_size_mapping else None
    path_num = 0
    for path in value_of_path.keys():
        key = path.split('/')[-1]
        value = value_of_path[path]
        if value is None:
            continue
        elif isinstance(value, str):
            value = value.replace("_or_", '"|"').strip()
            if value.strip().startswith("{{"):
                row_num = row_num_of_path[path]
                print(f"Value from row {row_num} to fix now {path} = {value}")
                in_row = in_rows[row_num].replace("_or_", '"|"')
                out_row = out_rows[row_num].replace("_or_", '"|"')
                print(f"\tInput row {row_num} is: {in_row}")
                default_from_mrcf = None
                defaults_from_mrcf = None
                example_from_mrcf = None
                recomen_from_mrcf = None
                if path in map_path_mrcf:
                    all_from_mrcf = map_path_mrcf[path]
                    default_from_mrcf = all_from_mrcf["default"] if "default" in all_from_mrcf else None
                    for _key in list(all_from_mrcf.keys()):
                        if isinstance(_key, bool):
                            print(f"Warning: Found key {_key} which is not a string-type value:\n{all_from_mrcf}")
                            if _key:
                                _key = 'true'
                            else:
                                _key = 'false'
                        elif isinstance(_key, str) and _key.startswith("default_"):
                            if defaults_from_mrcf is None:
                                defaults_from_mrcf = {}
                            defaults_from_mrcf[_key] = all_from_mrcf[_key]
                    example_from_mrcf = all_from_mrcf["example"] if "example" in all_from_mrcf else None
                    recomen_from_mrcf = all_from_mrcf["recommended_value"] if "recommended_value" in all_from_mrcf else None
                else:
                    print(f"Warning: Cannot find path {path} in MRCF parameters, please check it manually!")
                # if path in map_path_helm:
                default_from_helm = map_path_helm[path] if path in map_path_helm else None
                # else:
                #     print(f"Warning: Cannot find path {path} in HELM charts, please check it manually!")
                taken = False
                for priority in priorities:
                    if priority == "MRCF.recommended_value":
                        print(f"\t{priority}: {recomen_from_mrcf}")
                        if not taken and recomen_from_mrcf is not None:
                            taken = True
                            if isinstance(recomen_from_mrcf, bool):
                                if recomen_from_mrcf:
                                    recomen_from_mrcf = "true"
                                else:
                                    recomen_from_mrcf = "false"
                            elif isinstance(recomen_from_mrcf, int):
                                recomen_from_mrcf = str(recomen_from_mrcf)
                            elif isinstance(recomen_from_mrcf, str):
                                recomen_from_mrcf = recomen_from_mrcf.strip("\"\'")
                                recomen_from_mrcf = f"\"{recomen_from_mrcf}\""
                            origin_row = key + ": " + value.strip()
                            update_row = key + ": " + recomen_from_mrcf
                            out_row = out_row.replace(origin_row, update_row)
                            out_rows[row_num] = out_row
                            print(f"\t\tUpdating row:\n\t\t\t{origin_row}\n\t\t\t\t->\n\t\t\t{update_row}")
                    elif priority == "MRCF.default_per_flavor":
                        print(f"\t{priority} available: {defaults_from_mrcf}")
                        # default_small_system_profile
                        # default_standard_system_profile
                        # default_large_system_profile
                        if not taken and defaults_from_mrcf is not None:
                            if system_size_mapped is None:
                                print(f"FATAL ERROR! System size '{system_size}' unsupported. Possible values are: 'small-system', 'standard-system', 'large-system'.")
                                sys.exit(1)
                            defaults_from_mrcf_chosen = defaults_from_mrcf[system_size_mapped] if system_size_mapped in defaults_from_mrcf else None
                            if isinstance(defaults_from_mrcf_chosen, bool):
                                if defaults_from_mrcf_chosen:
                                    defaults_from_mrcf_chosen = "true"
                                else:
                                    defaults_from_mrcf_chosen = "false"
                            elif isinstance(defaults_from_mrcf_chosen, int):
                                defaults_from_mrcf_chosen = str(defaults_from_mrcf_chosen)
                            elif isinstance(defaults_from_mrcf_chosen, str):
                                defaults_from_mrcf_chosen = defaults_from_mrcf_chosen.strip("\"\'")
                                defaults_from_mrcf_chosen = f"\"{defaults_from_mrcf_chosen}\""
                            print(f"\t{priority} chosen: {defaults_from_mrcf_chosen}")
                            if defaults_from_mrcf_chosen is not None:
                                taken = True
                                origin_row = key + ": " + value.strip()
                                update_row = key + ": " + defaults_from_mrcf_chosen
                                out_row = out_row.replace(origin_row, update_row)
                                out_rows[row_num] = out_row
                                print(f"\t\tUpdating row:\n\t\t\t{origin_row}\n\t\t\t\t->\n\t\t\t{update_row}")
                    elif priority == "MRCF.default":
                        if isinstance(default_from_mrcf, bool):
                            if default_from_mrcf:
                                default_from_mrcf = "true"
                            else:
                                default_from_mrcf = "false"
                        elif isinstance(default_from_mrcf, int):
                            default_from_mrcf = str(default_from_mrcf)
                        elif isinstance(default_from_mrcf, str):
                            default_from_mrcf = default_from_mrcf.strip("\"\'")
                            default_from_mrcf = f"\"{default_from_mrcf}\""
                        print(f"\t{priority}: {default_from_mrcf}")
                        if not taken and default_from_mrcf is not None:
                            if isinstance(default_from_mrcf, str):
                                if default_from_mrcf in value:
                                    taken = True
                                    origin_row = key + ": " + value.strip()
                                    update_row = key + ": " + default_from_mrcf
                                    out_row = out_row.replace(origin_row, update_row)
                                    out_rows[row_num] = out_row
                                    print(f"\t\tUpdating row:\n\t\t\t{origin_row}\n\t\t\t\t->\n\t\t\t{update_row}")
                    elif priority == "MRCF.example":
                        print(f"\t{priority}: {example_from_mrcf}")
                        if isinstance(example_from_mrcf, bool):
                            if example_from_mrcf:
                                example_from_mrcf = "true"
                            else:
                                example_from_mrcf = "false"
                        elif isinstance(example_from_mrcf, int):
                            example_from_mrcf = str(example_from_mrcf)
                        elif isinstance(example_from_mrcf, str):
                            example_from_mrcf = example_from_mrcf.strip("\"\'")
                            example_from_mrcf = f"\"{example_from_mrcf}\""
                        if not taken and example_from_mrcf is not None:
                            taken = True
                            origin_row = key + ": " + value.strip()
                            update_row = key + ": " + example_from_mrcf
                            out_row = out_row.replace(origin_row, update_row)
                            out_rows[row_num] = out_row
                            print(f"\t\tUpdating row:\n\t\t\t{origin_row}\n\t\t\t\t->\n\t\t\t{update_row}")
                    elif priority == "YAML.default_per_flavor":
                        # small-system value
                        # standard-system value
                        # large-system value
                        value_nice = value.replace('{{', '').replace('}}', '').strip()  # .replace("'", "").replace('"', '')
                        print(f"\tTEMP.value_nice = ({value_nice.__class__.__module__}.{value_nice.__class__.__name__}) {value_nice}")
                        vals = value_nice.split('|')
                        is_integer = False
                        is_float = False
                        is_bool = False
                        if not ((value_nice.startswith("\"") and value_nice.endswith("\"")) or (value_nice.startswith("\'") and value_nice.endswith("\'"))):
                            # no sense to convert to integer/float/boolean if this is already for sure a string "..." or '...' (surrounded by quotation marks)
                            try:
                                int(value_nice)
                                is_integer = True
                            except ValueError:
                                try:
                                    float(value_nice)
                                    is_float = True
                                except ValueError:
                                    if value_nice in ("true", "false"):
                                        is_bool = True
                                    # else:
                                    #     try:
                                    #         bool(value_nice)  # bool("10Gi") returned True :(
                                    #         is_bool = True
                                    #     except ValueError:
                                    #         pass
                            if value_nice == "null":
                                value_nice = None
                            elif not(is_integer or is_float or is_bool):
                                print(f"\tTEMP.value_nice (not int/float/bool) = ({value_nice.__class__.__module__}.{value_nice.__class__.__name__}) {value_nice}")
                                value_nice = f'"{value_nice}"'
                            elif is_integer:
                                value_nice = int(value_nice)
                            elif is_float:
                                value_nice = float(value_nice)
                            elif is_bool:
                                if value_nice == "true":
                                    value_nice = True
                                elif value_nice == "false":
                                    value_nice = False
                                # else:
                                #     value_nice = bool(value_nice)
                            print(f"\tTEMP.value_nice = ({value_nice.__class__.__module__}.{value_nice.__class__.__name__}) {value_nice}")
                        val = None
                        if len(vals) < 2:
                            val = {
                                "any-system value": value_nice
                            }
                        elif len(vals) == 2:
                            val = {
                                "small-system value": vals[0],
                                "standard-system value": vals[1]
                            }
                        elif len(vals) > 2:
                            val = {
                                "small-system value": vals[0],
                                "standard-system value": vals[1],
                                "large-system value": vals[2]
                            }
                        print(f"\tTEMP.val = ({val.__class__.__module__}.{val.__class__.__name__}) {val}")
                        print(f"\t{priority} available: {val}")
                        val_chosen = val[system_size + " value"] if system_size + " value" in val else value_nice
                        if isinstance(val_chosen, str):
                            val_chosen = val_chosen.strip("\"\'")
                            val_chosen = f"\"{val_chosen}\""
                        print(f"\t{priority} chosen: {val_chosen}")
                        if not taken:
                            taken = True
                            origin_row = key + ": " + value.strip()
                            if val_chosen is None:
                                update_row = key + ": null"
                            else:
                                update_row = key + ": " + str(val_chosen)
                            out_row = out_row.replace(origin_row, update_row)
                            out_rows[row_num] = out_row
                            print(f"\t\tUpdating row:\n\t\t\t{origin_row}\n\t\t\t\t->\n\t\t\t{update_row}")
                    elif priority == "HELM.default":
                        print(f"\t{priority}: {default_from_helm}")
                        if not taken and default_from_helm is not None:
                            taken = True
                            if isinstance(default_from_helm, str):
                                default_from_helm = default_from_helm.strip("\"\'")
                                default_from_helm = f"\"{default_from_helm}\""
                            origin_row = key + ": " + value.strip()
                            update_row = key + ": " + default_from_helm
                            out_row = out_row.replace(origin_row, update_row)
                            out_rows[row_num] = out_row
                            print(f"\t\tUpdating row:\n\t\t\t{origin_row}\n\t\t\t\t->\n\t\t\t{update_row}")
                print(f"\tOutput row {row_num} is: {out_row}")
        path_num += 1
    output = "\n".join(out_rows)
    return output


# the scalar emitter from emitter.py
def process_scalar(self):
    if self.analysis is None:
        self.analysis = self.analyze_scalar(self.event.value)
    if self.style is None:
        self.style = self.choose_scalar_style()
    split = (not self.simple_key_context)
    # VVVVVVVVVVVVVVVVVVVV added
    if split:  # not a key
        is_string = True
        if self.event.value and self.event.value[0].isdigit():
            is_string = False
        # insert extra tests for scalars that should not be ?
        if is_string:
            self.style = "'"
    # ^^^^^^^^^^^^^^^^^^^^
    # if self.analysis.multiline and split    \
    #         and (not self.style or self.style in '\'\"'):
    #     self.write_indent()
    if self.style == '"':
        self.write_double_quoted(self.analysis.scalar, split)
    elif self.style == '\'':
        self.write_single_quoted(self.analysis.scalar, split)
    elif self.style == '>':
        self.write_folded(self.analysis.scalar)
    elif self.style == '|':
        self.write_literal(self.analysis.scalar)
    else:
        self.write_plain(self.analysis.scalar, split)
    self.analysis = None
    self.style = None
    if self.event.comment:
        self.write_post_comment(self.event)


def loop_through_nodes(node, prev_key, path, delim, _map_path_helm, lookup_in_helm_tree=True):
    if not isinstance(node, dict) and not isinstance(node, list):
        print(f"loop_through_nodes(node=({node.__class__.__module__ + '.' + node.__class__.__name__}){node}), prev_key='{prev_key}', path='{path}', delim='{delim}', _map_path_helm")
        exit(1)
    if isinstance(node, list):
        item_num = 0
        for val in node:
            if prev_key is None:
                kkk = f"[{item_num}]"
            else:
                kkk = prev_key  + f"[{item_num}]"
            this_is_leaf = False
            item_num += 1
            if isinstance(val, str):
                this_is_leaf = True
                pass
            elif isinstance(val, int):
                this_is_leaf = True
                pass
            elif isinstance(val, float):
                this_is_leaf = True
                pass
            elif isinstance(val, bool):
                this_is_leaf = True
                pass
            # elif isinstance(val, list):
            #     pass
            else:
                loop_through_nodes(val, kkk, path, delim, _map_path_helm, lookup_in_helm_tree)
            if this_is_leaf:
                if lookup_in_helm_tree:
                    _map_path_helm[kkk] = {
                        "values": [
                            val
                        ],
                        "files": [
                            [path]
                        ]
                    }
                else:
                    _map_path_helm[kkk] = val
        return
    for key,value in node.items():
        safe_key = str(key)
        if isinstance(key, bool):
            if not key:
                safe_key = 'false'
            elif key:
                safe_key = 'true'
        # print(f"path={path}, prev_key={prev_key}, key=({key.__class__.__module__ + '.' + key.__class__.__name__}){key}, safe_key=({safe_key.__class__.__module__ + '.' + safe_key.__class__.__name__}){safe_key}")
        if delim in safe_key or "." in safe_key or "/" in safe_key:
            safe_key = "(" + safe_key + ")"  # support for special keys containing . or /
        if prev_key is not None:
            kk=str(prev_key)+delim+str(safe_key)
        else:
            kk=str(safe_key)
        if delim == '/' and not kk.startswith(delim):
            kk = delim + kk
        if isinstance(value, str):
            if value.find("\n") != -1:
                vv=value.replace("\n", "\\n")
            else:
                vv=value
            ########### print(str(path)+"\t"+str(kk)+"\t"+str(vv)),
            if kk in _map_path_helm:
                prev_vv_dict = _map_path_helm[kk]
                if lookup_in_helm_tree:
                    if "values" not in prev_vv_dict:
                        prev_vv_dict["values"] = []
                        prev_vv_dict["files"] = []
                    if vv not in prev_vv_dict["values"]:
                        prev_vv_dict["values"].append(vv)
                        prev_vv_dict["files"].append([path])
                    else:
                        idx = prev_vv_dict["values"].index(vv)
                        if path not in prev_vv_dict["files"][idx]:
                            prev_vv_dict["files"][idx].append(path)
                elif prev_vv_dict:
                    print(f"WARNING! Overwriting {kk} param from {prev_vv_dict} to {vv} at path {path}")
                    _map_path_helm[kk] = vv
                    # TODO: we can consider appending already existing value instead of overwriting it
                else:
                    _map_path_helm[kk] = vv
            else:
                if lookup_in_helm_tree:
                    _map_path_helm[kk] = {
                        "values": [
                            vv
                        ],
                        "files": [
                            [path]
                        ]
                    }
                else:
                    _map_path_helm[kk] = vv
        elif isinstance(value, dict):
            loop_through_nodes(value, kk, path, delim, _map_path_helm, lookup_in_helm_tree)
        elif isinstance(value, list):
            item_num = 0
            for val in value:
                kkk = kk  + f"[{item_num}]"
                this_is_leaf = False
                item_num += 1
                if isinstance(val, str):
                    this_is_leaf = True
                    pass
                elif isinstance(val, int):
                    this_is_leaf = True
                    pass
                elif isinstance(val, float):
                    this_is_leaf = True
                    pass
                elif isinstance(val, bool):
                    this_is_leaf = True
                    pass
                # elif isinstance(val, list):
                #     pass
                else:
                    loop_through_nodes(val, kkk, path, delim, _map_path_helm, lookup_in_helm_tree)
                if this_is_leaf:
                    if lookup_in_helm_tree:
                        _map_path_helm[kkk] = {
                            "values": [
                                val
                            ],
                            "files": [
                                [path]
                            ]
                        }
                    else:
                        _map_path_helm[kkk] = val
        else:
            if lookup_in_helm_tree:
                _map_path_helm[kk] = {
                    "values": [
                        value
                    ],
                    "files": [
                        [path]
                    ]
                }
            else:
                _map_path_helm[kk] = value


def is_correct_yaml(last_block, row_num):
    if VERBOSE:
        print(f"Is this correct YAML in row #{row_num}:\n'{last_block}'\n?")
    try:
        ### correct_yaml = yml.load(last_block, Loader=dl)
        correct_yaml = yamel.load(last_block)
        if correct_yaml is None:
            # this is emptiness or comment section
            if last_block.strip("\n\t ").startswith("#"):
                # this is comment
                # print(f"Comment block is told to be YAML: '{last_block}'. Dict of it: ({correct_yaml.__class__.__module__ + '.' + correct_yaml.__class__.__name__}) {correct_yaml}")
                return True, correct_yaml
            else:
                # print(f"Empty block is told to be YAML: '{last_block}'. Dict of it: ({correct_yaml.__class__.__module__ + '.' + correct_yaml.__class__.__name__}) {correct_yaml}")
                return True, correct_yaml
        elif isinstance(correct_yaml, str):
            # print(f"This is rather string, not YAML: '{last_block}'")
            if DEBUG:
                print(f"DEBUG: False => Possible incorrect YAML due to: '{last_block}' is rather a String, not YAML content")
                # raise Exception("TEXT")
            # return "TEXT"
            return False, correct_yaml
        elif isinstance(correct_yaml, list):
            # prevent considering as YAML comments like below:
            # - The default value 10000 for fsGroup will be used when no other value will be set.
            first_item = list(correct_yaml)[0]
            if isinstance(first_item, str) and ":" not in first_item and " " in first_item:
                # considering at as comment text
                print(f"Considering as comment text array/list item: {last_block}")
                return False, correct_yaml
            elif last_block.lstrip().startswith('- 10.40.0.'):
                print("--------------------------------------------------------------------------------------------------")
                print(f"WARNING! Considering as comment text IP item: {last_block}")
                print("--------------------------------------------------------------------------------------------------")
                return False, correct_yaml
            elif isinstance(first_item, str) and len(first_item.strip().split(' ')) > 2:
                print("--------------------------------------------------------------------------------------------------")
                print(f"WARNING! Considering as comment text with several spaces inside: {last_block}")
                print("--------------------------------------------------------------------------------------------------")
                return False, correct_yaml
            elif isinstance(first_item, str) and len(first_item.strip().split(':')) > 3:
                print("--------------------------------------------------------------------------------------------------")
                print(f"WARNING! Considering as comment text with special characters like colon: {last_block}")
                print("--------------------------------------------------------------------------------------------------")
                return False, correct_yaml
            else:
                # print(f"Array/list item block is told to be YAML in row {row_num}: '{last_block}'. Dict of it: ({correct_yaml.__class__.__module__ + '.' + correct_yaml.__class__.__name__}) {correct_yaml}")
                return True, correct_yaml
        elif isinstance(correct_yaml, yml.comments.CommentedSeq):
            print(f"Potentially commented array/list item block is told to be YAML: '{last_block}'. Dict of it: ({correct_yaml.__class__.__module__ + '.' + correct_yaml.__class__.__name__}) {correct_yaml}")
            return True, correct_yaml
        elif isinstance(correct_yaml, dict):
            # print(f"Object/dictionary/map block is told to be YAML: '{last_block}'. Dict of it: ({correct_yaml.__class__.__module__ + '.' + correct_yaml.__class__.__name__}) {correct_yaml}")
            keys = list(dict(correct_yaml).keys())
            # print(f"Object/dictionary/map block keys: {keys}")
            key = keys[0]
            if ( key[0].isupper() or " " in key ) and key not in (
                'IPv4',
                'IPv6',
                'VirtualTapBroker',
                'NFStatusNotify',
                'DUAL_STACK_INBOUND_PASSTHROUGH',
                'PILOT_ENABLE_INBOUND_PASSTHROUGH',
                'ETCD_SNAPSHOT_COUNT',
                'ETCD_QUOTA_BACKEND_BYTES',
                'ENABLE_TLS_ON_SIDECAR_INGRESS',
                'ENABLE_AUTO_SNI',
                'CLOUD_PLATFORM',
            ) and not key.startswith("PREFIX-") and not key.startswith("ENABLE_") and not key.startswith("ETCD_"):
                print("--------------------------------------------------------------------------------------------------")
                print(f"WARNING! Considering as comment text KVP block like title: {key}: {correct_yaml[key]}")
                print("--------------------------------------------------------------------------------------------------")
                # catches edge cases looking like title, so like below:
                #   Important: this section must not be uncommented if previous section of
                #   To stream all metrics from UDR, PF, NRF Agent and ADP services ucomment following blocks. ATTENTION: ADP services generate lot of metrics and streaming them all can have impact on PM Server performance.
                #   Depending on the metrics wanted to be streamed outside uncomment ONE of filtering options below:
                #   nf_node_type, one of: NRF,UDM-AUSF,UDR,NSSF,5G_UDM (All the NFs within the same cluster)
                #   ip protocol stack mode ipv6: ipv4 or ipv6
                #   ip protocol stack mode ipv6: true or false
                #   NOTE:
                # except:
                #   IPv4:
                #   IPv6:
                return False, correct_yaml
            elif key in ["supportedGps", "proxy.istio.io/config"] and isinstance(correct_yaml[key], str):
                """
                supportedGps: fifteen-min thirty-min one-hour twelve-hour one-day one-min five-min
                supportedGps: "fifteen-min thirty-min one-hour twelve-hour one-day one-min five-min"
                supportedGps: 'fifteen-min thirty-min one-hour twelve-hour one-day one-min five-min'
                """
                return True, correct_yaml
            elif correct_yaml[key] and isinstance(correct_yaml[key], str) and len(correct_yaml[key].strip().split(' ')) > 2 and not (correct_yaml[key].strip().startswith('"') and correct_yaml[key].strip().endsswith('"')):
                # edge cases are listed below:
                # case: cleanupSchedule: "0 0 1 * * ?"
                if key == "cleanupSchedule" or (key == 'filter' and correct_yaml[key].startswith("ruby")):
                    return True, correct_yaml
                # others:
                # catches edge cases looking like title, so like below:
                #   Indicates which streaming method is chosen by all services to write log records:
                #     indirect: stdout to infrastructure logging framework
                #     direct: - direct streaming to the Log Aggregator
                #     dual: -   stdout to infrastructure logging framework and direct streaming to Log Aggregator
                #     When global.logShipper.deployment.type is "daemonset", this value must be set to "indirect"
                #     When global.logShipper.deployment.type is "sidecar", this value must be set to "dual"
                print("--------------------------------------------------------------------------------------------------")
                print(f"WARNING! Considering as comment text KVP block with value like title: {key}: {correct_yaml[key]}")
                print("--------------------------------------------------------------------------------------------------")
                return False, correct_yaml
            else:
                # print(f"Object/dictionary/map block KVP: {key} = {correct_yaml[key]}")
                pass
            return True, correct_yaml
        elif isinstance(correct_yaml, yml.comments.CommentedMap):
            print(f"Potentially commented object/dictionary/map block is told to be YAML: '{last_block}'. Dict of it: ({correct_yaml.__class__.__module__ + '.' + correct_yaml.__class__.__name__}) {correct_yaml}")
            return True, correct_yaml
        elif ":" not in last_block:
            print(f"Strange block is told to be YAML: '{last_block}'. Dict of it: ({correct_yaml.__class__.__module__ + '.' + correct_yaml.__class__.__name__}) {correct_yaml}")
            return True, correct_yaml
        else:
            # print(f"KVP block is told to be YAML: '{last_block}'. Dict of it: ({correct_yaml.__class__.__module__ + '.' + correct_yaml.__class__.__name__}) {correct_yaml}")
            return True, correct_yaml
    except (yml.scanner.ScannerError, yml.composer.ComposerError, yml.parser.ParserError) as ex:
        if DEBUG:
            print(f"Incorrect YAML block: {last_block}\nException was: {ex}")
        return False, None


def first_row(rows):
    return rows.strip("\n").split('\n')[0]


def indent_level(yaml_row_arg, delimiter=" ", tab_size=2, clean_chars="\r\n"):
    yaml_row = yaml_row_arg.lstrip(clean_chars).replace("\t", delimiter * tab_size)
    level = 0
    for i in range(0, len(yaml_row)):
        level = i
        if yaml_row[i] != delimiter:
            break
    # print(f"Indentation level of row '{yaml_row}' is: {level}")
    if yaml_row.lstrip().startswith('-'):
         level += 2  #############
    return level


def check_and_fix_indentation_level(yaml_content_as_str):
    row_num = 0
    rows = yaml_content_as_str.split("\n")
    for row in rows:
        lvl = indent_level(row)
        if lvl % 2 == 1:
            print(f"Unexpected odd indentation level {lvl} in row #{row_num}, details are below:")
            row_prev = rows[row_num - 1] or None
            row_next = rows[row_num + 1] or None
            lvl_prev = lvl
            lvl_next = lvl
            if row_prev:
                lvl_prev = indent_level(row_prev)
                print(f"  Please be aware of level {lvl_prev} of prev row #{row_num - 1}:\t\t{row_prev}")
            print(f"  Please be aware of level {lvl} of curr row #{row_num}:\t\t{row}")
            if row_next:
                lvl_next = indent_level(row_next)
                print(f"  Please be aware of level {lvl_next} of next row #{row_num + 1}:\t\t{row_next}")
            if row_prev and row_next:
                if lvl_prev + 1 == lvl and lvl_next + 1 == lvl:
                    if not row_prev.lstrip().startswith("#") and row_prev.rstrip().endswith(":"):
                        rows[row_num] = " " + rows[row_num]
                        print(f"  Note changed level (type A) {lvl}->{lvl + 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                    else:
                        rows[row_num] = rows[row_num][1:]
                        print(f"  Note changed level (type B) {lvl}->{lvl - 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                elif lvl_prev + 1 == lvl and lvl_next == lvl:
                    if not row_prev.lstrip().startswith("#") and row_prev.rstrip().endswith(":"):
                        rows[row_num] = " " + rows[row_num]
                        print(f"  Note changed level (type C) {lvl}->{lvl + 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                    else:
                        rows[row_num] = rows[row_num][1:]
                        print(f"  Note changed level (type D) {lvl}->{lvl - 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                elif lvl_prev + 1 == lvl and lvl_next == lvl + 1:
                    if not row_prev.lstrip().startswith("#") and row_prev.rstrip().endswith(":"):
                        rows[row_num] = " " + rows[row_num]
                        print(f"  Note changed level (type E) {lvl}->{lvl + 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                    else:
                        rows[row_num] = rows[row_num][1:]
                        print(f"  Note changed level (type F) {lvl}->{lvl - 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                elif lvl_prev + 1 == lvl and lvl_next +3 < lvl:
                    if not row_prev.lstrip().startswith("#") and row_prev.rstrip().endswith(":"):
                        rows[row_num] = " " + rows[row_num]
                        print(f"  Note changed level (type G) {lvl}->{lvl + 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                    else:
                        rows[row_num] = rows[row_num][1:]
                        print(f"  Note changed level (type H) {lvl}->{lvl - 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                elif (lvl_prev == lvl or lvl_prev == lvl + 1) and lvl_next == lvl + 1:
                    rows[row_num] = " " + rows[row_num]
                    print(f"  Note changed level (type I) {lvl}->{lvl + 1} of curr row #{row_num}:\t\t{rows[row_num]}")
                elif lvl_prev > lvl and lvl_next > lvl:
                    lvl_min = min(lvl_prev, lvl_next)
                    lvl_prev_parity = lvl_prev % 2 == 0
                    lvl_next_parity = lvl_next % 2 == 0
                    lvl_curr_parity = lvl % 2 == 0
                    if lvl_prev_parity == lvl_next_parity == lvl_curr_parity:
                        # skip change
                        print(f"  Please note unchanged level (type J) {lvl}->{lvl_min} of curr row #{row_num}:\t\t{rows[row_num]}")
                    else:
                        rows[row_num] = (" "*lvl_min) + rows[row_num].strip()
                        print(f"  Note changed level (type J) {lvl}->{lvl_min} of curr row #{row_num}:\t\t{rows[row_num]}")
                elif lvl_prev > lvl + 1 and (lvl_next + 1 == lvl or lvl_next - 1 == lvl):
                    rows[row_num] = (" "*lvl_next) + rows[row_num].strip()
                    print(f"  Note changed level (type K) {lvl}->{lvl_next} of curr row #{row_num}:\t\t{rows[row_num]}")
        row_num += 1
    yaml_out = "\n".join(rows)
    return yaml_out


def uncomment_row(row):
    # uncom_row = row.replace("#", "", 1)
    lvl_before_uncom = indent_level(row)
    uncom_row = re.sub("[#]+", "", row, count=1)
    lvl_after_uncom = indent_level(uncom_row)
    diff_lvl_before_after_uncom = lvl_after_uncom - lvl_before_uncom  # lenght of commenting characters ###
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


def preprocess_yaml_file0(in_yaml_content):
    return in_yaml_content.replace("{{", "").replace("}}", "")


def preprocess_yaml_file1(in_yaml_content):
    updated_yaml_content = in_yaml_content
    updated_yaml_content = updated_yaml_content.replace("{{\"", "{{")
    updated_yaml_content = updated_yaml_content.replace("\"}}", "}}")
    updated_yaml_content = updated_yaml_content.replace("[|", "|")
    updated_yaml_content = updated_yaml_content.replace("]}}", "}}")
    updated_yaml_content = updated_yaml_content.replace("{{", "\"{{")
    updated_yaml_content = updated_yaml_content.replace("}}", "}}\"")
    updated_yaml_content = updated_yaml_content.replace("\"|\"", "|")
    return updated_yaml_content


def preprocess_yaml_file2(in_yaml_content):
    updated_yaml_content = in_yaml_content

    block_started = False
    # indent_lvl_on_opening = 0
    opening_row = None
    closing_row = None
    out_yaml_array = []
    row_nr = 0
    for old_row in in_yaml_content.split('\n'):
        new_row = old_row.rstrip()  # prevent error:    trailing spaces  (trailing-spaces)
        # prevent problem with JSON data { ... } in YAML file
        remove_comment_char_and_ensure_indent_is_ok = False
        curly_open = '\x7b'
        regex_str = f'^#[ ]*{curly_open}$'
        regex_bytes = bytes(regex_str, encoding='UTF-8')
        regex = re.compile(regex_bytes)
        if regex.match(bytes(new_row.lstrip(), encoding="UTF-8")):
            block_started = True
            # indent_lvl_on_opening = indent_level(new_row)
            opening_row = new_row
            closing_row = opening_row.replace("{", "}")
            remove_comment_char_and_ensure_indent_is_ok = True
        elif new_row == closing_row:  # (' '*indent_lvl_on_opening) + '}':
            block_started = False
            remove_comment_char_and_ensure_indent_is_ok = True
        elif block_started:
            remove_comment_char_and_ensure_indent_is_ok = True
        if remove_comment_char_and_ensure_indent_is_ok:
            new_row = new_row.replace('#', ' ', 1)
            indent_lvl = indent_level(new_row)
            if indent_lvl % 2 == 1:
                new_row = new_row[1:]
            new_row = f"@@@{new_row}@@@"
        elif (
            'Version: 1.0, Date:' in new_row or
            '.  Misuse,' in new_row or
            'personal information. Handle' in new_row or
            'USER, PLEASE EXIT' in new_row or
            "-XX:" in new_row or
            "-Xmn:" in new_row or
            "-Xms:" in new_row or
            "-Xmx:" in new_row or
            "-Xlog:" in new_row or
            "JAVA_OPTS" in new_row or
            new_row.lstrip().startswith("-Xm") or
            new_row.lstrip().startswith("-Xlog") or
            new_row.lstrip().startswith("-D") or
            new_row.strip() == "]}'" or
            new_row.strip() == "}" or
            new_row.strip() == "{" or
            new_row.lstrip().startswith('"y":"') or
            new_row.lstrip().startswith('"x":"') or
            new_row.lstrip().startswith('"kty":"') or
            new_row.lstrip().startswith('"kid":"') or
            new_row.lstrip().startswith('"crv":"') or
            new_row.lstrip().startswith("jwks: '{") or
            new_row.count('"') == 1
        ):
            if not new_row.startswith("@@@"):
                new_row = f"@@@{new_row}@@@"
        elif 'Deployment: {}' in new_row:
            new_row = new_row.replace(': {}', ':')
            if not new_row.startswith("@@@"):
                new_row = f"@@@{new_row}@@@"
        out_yaml_array.append(new_row)
        row_nr += 1
    if DEBUG:
        print(f"Preprocessed {row_nr} rows")
    updated_yaml_content = '\n'.join(out_yaml_array)

    # updated_yaml_content = updated_yaml_content.replace("\"|\"", "_or_")
    # updated_yaml_content = updated_yaml_content.replace("[|", "|")
    # updated_yaml_content = updated_yaml_content.replace("]}}", "}}")
    # updated_yaml_content = updated_yaml_content.replace("size: {{size", "size: '{{size")
    # updated_yaml_content = updated_yaml_content.replace("}}gb", "}}gb'")

    updated_yaml_content = "#\n" + updated_yaml_content
    if not updated_yaml_content.endswith("\n"):
        updated_yaml_content += "\n"
    return updated_yaml_content


def postprocess_yaml_file1(in_yaml_content):
    ##### return in_yaml_content[1:].replace(": null}: null}", "}}")
    return in_yaml_content.replace(": null}: null}", "}}")


def postprocess_yaml_file2(in_yaml_content):
    ##### return in_yaml_content[1:].replace("__name__", "")
    return in_yaml_content.replace("__name__", "")[1:]


def postprocess_yaml_file2b(in_yaml_content):
    # hardcoded
    # return re.sub("^    trustedCertificateListName[:]", "        trustedCertificateListName:", in_yaml_content)
    return in_yaml_content


def preprocess_yaml_file2b(in_yaml_content):
    # hardcoded
    out_yaml_content = in_yaml_content
    if (
        "\n    #        trustedCertificateListName:" in in_yaml_content
        and
        "\n        #        asymmetricKeyCertificateName:" in in_yaml_content
    ):
        out_yaml_content = out_yaml_content.replace(
            "\n    #        trustedCertificateListName:",
            "\n        #        trustedCertificateListName:"
        )
    if (
        "\n    dataCenters:" in in_yaml_content
        and
        "\n        #        service:" in in_yaml_content
    ):
        out_yaml_content = out_yaml_content.replace(
            "\n        #        service:",
            "\n        service:"
        )
        out_yaml_content = out_yaml_content.replace(
            "\n        #    egress:",
            "\n        egress:"
        )
        out_yaml_content = out_yaml_content.replace(
            "\n        #    georeplication:",
            "\n        georeplication:"
        )

    str1from = "  #  cire-is-application-sys-info-handler:\n  #    asih:\n  #      applicationId:\n  cire-is-application-sys-info-handler:"
    str1to   = "  cire-is-application-sys-info-handler:\n    asih:\n      applicationId:"
    if str1from in out_yaml_content:
        out_yaml_content = out_yaml_content.replace(str1from, str1to)

    str2from = "  # IP Stack version:\n  # - ipv4\n  # - ipv6"
    str2to   = "  # IP Stack version:\n  # - ipv4 (for IP Stack version 4)\n  # - ipv6 (for IP Stack version 6)"
    if str2from in out_yaml_content:
        out_yaml_content = out_yaml_content.replace(str2from, str2to)
    str2from = "# IP Stack version:\n# - ipv4"
    str2to   = "# IP Stack version:\n# - ipv4 (this is for IP Stack version 4)"
    if str2from in out_yaml_content:
        out_yaml_content = out_yaml_content.replace(str2from, str2to)
    str2from = "# IP Stack version:\n# - ipv6"
    str2to   = "# IP Stack version:\n# - ipv6 (this is for IP Stack version 6)"
    if str2from in out_yaml_content:
        out_yaml_content = out_yaml_content.replace(str2from, str2to)

    str3from = "#       max_shards: 200"
    str3to   = "#        max_shards: 200"
    if str3from in out_yaml_content:
        out_yaml_content = out_yaml_content.replace(str3from, str3to)

    str4from = "  #security:\n  #  tls:\n  #    agentToBro:\n  #      enabled: true"
    str4to   = "    #security:\n    #  tls:\n    #    agentToBro:\n    #      enabled: true"
    if str4from in out_yaml_content:
        out_yaml_content = out_yaml_content.replace(str4from, str4to)

    return out_yaml_content


def process_yaml_file0(in_yaml_content):
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


def tr(s):
    return s.replace('_or_', '"|"')


def process_yaml_file1(in_yaml_content):
    ### in_out_yaml = yml.load(in_yaml_content, Loader=dl)
    if STOP_ON_RUAMEL_ERROR:
        in_out_yaml = yamel.load(in_yaml_content)
    else:
        try:
            in_out_yaml = yamel.load(in_yaml_content)
        except (yml.scanner.ScannerError, yml.composer.ComposerError, yml.parser.ParserError) as ex:
            print("CRITICAL! RUEMAL ERROR ON LOADING YAML CONTENT: %s", ex)
            return ""
    ### out_yaml_content = yml.dump(in_out_yaml, Dumper=dd)
    buf = io.BytesIO()  # sys.stdout
    # buf = sys.stdout
    # out_yaml_content = yamel.dump(data=str.encode(in_out_yaml), stream=buf, transform=tr)
    out_yaml_content = yamel.dump(data=in_out_yaml, stream=buf)
    if out_yaml_content is None:
        # print("WARNING! Unfortunately dumped content is None :(")
        byt = buf.getvalue()
        ##### buf.seek(0)
        ##### byt = buf.read()
        out_yaml_content = bytes.decode(byt, "UTF-8")
    return out_yaml_content


def process_yaml_file2(in_yaml_content, yaml_template_file):
    # out_yaml_content = "" # ???
    last_block = ""
    last_row = ""
    yaml_len = len(in_yaml_content)
    print(f"Processing {yaml_len} chars of YAML content...")
    assert yaml_len > 0
    blocks = []
    block_num = -1
    status = 0
    original_rows = in_yaml_content.split('\n')
    row_num = len(original_rows)
    it_was_json = False
    lvl_json = -1
    for i in range(yaml_len - 1, 0, -1):
        ch = in_yaml_content[i]
        # print(f"Reading character: {ch}")
        last_row = ch + last_row
        if ch == "\n":
            row_num -= 1
            act_row = first_row(last_row).strip()
            last_row_is_json = act_row.startswith('@@@') and act_row.endswith('@@@')
            last_row_is_yaml, last_row_content = is_correct_yaml(act_row, row_num)
            ### print(f"Last row: '{last_row}' is correct YAML? {last_row_is_yaml}")
            # it_is_json = last_row.strip('\r\n\t ,') == '}' or last_row.rstrip('\r\n\t ,').endswith('{')
            # if not it_was_json and it_is_json:
            #     last_block = last_row + last_block
            #     actual_row = first_row(last_row)
            #     lvl_json_current = indent_level(actual_row)
            #     if lvl_json_current == lvl_json:
            #         it_was_json = False
            #     else:
            #         it_was_json = True
            #         lvl_json = lvl_json_current
            #     continue
            # elif it_was_json and not it_is_json:
            #     last_block = last_row + last_block
            #     continue
            # elif it_was_json and it_is_json:
            #     last_block = last_row + last_block
            #     actual_row = first_row(last_row)
            #     lvl_json_current = indent_level(actual_row)
            #     if lvl_json_current == lvl_json:
            #         it_was_json = False
            #     else:
            #         it_was_json = True
            #         lvl_json = lvl_json_current
            #     continue
            # elif not it_was_json and not it_is_json:
            #    pass
            if last_row_is_json:
                last_row = last_row.replace('@@@', '')
            elif not last_row_is_yaml:
                if isinstance(last_row_content, str) and (
                    "dced.excluded.paths" in last_row_content or
                    "dced.agent.restore.type" in last_row_content or
                    "The usage of this system is monitored and audited" in last_row_content or
                    "IF YOU ARE NOT AN AUTHORIZED USER STOP" in last_row_content or
                    "Important legal notice" in last_row_content
                ):
                    last_row_is_yaml = True
                else:
                    print(f"Wrong YAML content found in '{yaml_template_file}', breaking the tool...")
                    print(f"Last row processed was: '{act_row}', but is this correct YAML? {last_row_is_yaml}, and it is ({last_row_content.__class__.__name__}) {last_row_content}")
                    sys.exit(1)
                    # break
            elif last_row_is_yaml == "TEXT" and "#" not in last_row:
                print(f"WARNING! Not sure what is this text in '{yaml_template_file}' file: '{last_row.replace('\n', '\\n')}'")
                pass
            comment = last_row.strip().startswith("#")
            comment_only = comment and last_row.strip().endswith("#")
            if comment_only:
                last_block = last_row + last_block
            elif comment:
                last_row_uncom = uncomment_row(last_row)
                last_row_uncom_is_yaml, last_row_uncom_content = is_correct_yaml(first_row(last_row_uncom), row_num)
                if VERBOSE:
                    print(f"Last row uncommented: '{last_row_uncom}' is correct YAML? {last_row_uncom_is_yaml}")
                last_block_uncom = last_row_uncom + last_block
                last_block_uncom_is_yaml, last_block_uncom_content = is_correct_yaml(last_block_uncom, row_num)
                if VERBOSE:
                    print(f"Last block uncommented: '{last_block_uncom}' is correct YAML? {last_block_uncom_is_yaml}")
                if last_block_uncom_is_yaml == "TEXT":
                    print("WARNING! Problematic block:")
                    print(last_block)
                    print(" ->")
                    print(last_block_uncom)
                    raise Exception("TEXT_IN_BLOCK")
                elif last_block_uncom_is_yaml:
                    last_row = last_row_uncom
                    last_block = last_block_uncom
                    status = 1
                elif last_row_uncom_is_yaml == "TEXT":
                    if last_row.lstrip().startswith("#") and not last_row_uncom.lstrip().startswith("#"):
                        print(f"WARNING! Using original problematic row: {last_row.strip(' \t\r\n')}")
                        last_row_uncom = last_row
                    else:
                        print("WARNING! Problematic row:")
                        # print(original_rows[row_num])
                        # print(" ->")
                        print(last_row)
                        print(" ->")
                        print(last_row_uncom)
                        raise Exception("TEXT_IN_ROW")
                elif last_row_uncom_is_yaml:
                    ind1 = indent_level(first_row(last_row_uncom))
                    ind2 = indent_level(first_row(last_block))
                    # print(f"ind1: {ind1}")
                    # print(f"ind2: {ind2}")
                    if ind1 > ind2:
                        last_block = last_row_uncom + last_block  ### ??? ###
                        block_num += 1
                        blocks.append(last_block)
                        last_block = ""
                        status = 2
                    else:
                        status = 3
                        ### ??? ###
                        last_block = last_row_uncom + last_block
                        ## last_block_is_yaml = is_correct_yaml(last_block, row_num)
                        ## print(f"Last block: '{last_block}' is correct YAML? {last_block_is_yaml}")
                else:
                    last_block = last_row + last_block
                    ## last_block_is_yaml = is_correct_yaml(last_block, row_num)
                    ## print(f"Last block: '{last_block}' is correct YAML? {last_block_is_yaml}")
                    status = 4
            else:
                last_block = last_row + last_block
                ## last_block_is_yaml = is_correct_yaml(last_block, row_num)
                ## print(f"Last block: '{last_block}' is correct YAML? {last_block_is_yaml}")
                status = 5
            last_row = ""
            ### out_yaml_content = last_block # ???
    if status > 0 and status != 2:
        block_num += 1
        blocks.append(last_block)
        last_block = ""
    out_yaml_content_from_blocks = ""
    if len(blocks) > 0:
        for block in blocks:
            out_yaml_content_from_blocks = block + out_yaml_content_from_blocks
    # out_yaml_content_from_blocks += out_yaml_content  # ??? wrong, not needed
    return out_yaml_content_from_blocks


def wrong_syntax():
    print(
        "\n"
        f"Usage:\n\tpython3 {SCRIPT}"
        " $PATH_TO_INPUT_YAML_TEMPLATE_FILE \\ \n"
        "              [ --mrcf $PATH_TO_INPUT_MRCF_JSON_FILE ] \\ \n"
        "              [ --helm $PATH_TO_INPUT_HELM_CHARTS_FOLDER ] \\ \n"
        "              [ --flavor $SYSTEM_SIZE ] \\ \n"
        "              [ --config $PATH_TO_CONFIG_YAML_FILE ]"
        "\n"
        "Where:\n"
        "\t$PATH_TO_INPUT_YAML_TEMPLATE_FILE -- is a path to values YAML template file from CSAR (mandatory)\n"
        "\t$PATH_TO_INPUT_MRCF_JSON_FILE     -- is a path to MRCF JSON file from CPI or from Git (optional)\n"
        "\t$PATH_TO_INPUT_HELM_CHARTS_FOLDER -- is a path to HELM Charts folder, eg. relative path to helm subfolder (optional)\n"
        "\t$SYSTEM_SIZE                      -- is a name of the flavor/profile/system size and can be: small-system, standard-system, large-system (optional)\n"
        "\t$PATH_TO_CONFIG_YAML_FILE         -- is a path to config.yaml file containing configuration like priorities from where to take values to set up (optional)\n"
    )
    sys.exit(1)


class MyConstructor(yml.RoundTripConstructor):
    def construct_mapping(self, node, datatyp, deep = False):
        if not isinstance(node, yml.nodes.MappingNode):
            raise Exception(
                None, None, f'ConstructorError: expected a mapping node, but found {node.id!s}', node.start_mark,
            )
        print(f"DEBUG: MyConstructor::datatyp = {datatyp}")
        ret_val = datatyp
        for key_node, value_node in node.value:
            # keys can be list -> deep
            key = self.construct_object(key_node, deep=True)
            assert isinstance(key, str)
            value = self.construct_object(value_node, deep=deep)
            ret_val.append((key, value))
        print(f"DEBUG: MyConstructor::ret_val = {ret_val}")
        return ret_val

    def construct_yaml_map(self, node):
        data = []
        yield data
        self.construct_mapping(node, data, deep=True)

MyConstructor.add_constructor(
    'tag:yaml.org,2002:map', MyConstructor.construct_yaml_map
)


if __name__ == "__main__":
    SCRIPT = sys.argv[0]
    if len(sys.argv) not in [2, 4, 6, 8, 10]:
        wrong_syntax()

    print(f"Number of arguments given: {len(sys.argv)}")
    PATH_TO_INPUT_YAML_TEMPLATE_FILE = sys.argv[1]
    PATH_TO_INPUT_MRCF_JSON_FILE = None
    PATH_TO_INPUT_HELM_CHARTS_FOLDER = None
    SYSTEM_SIZE = "standard-system"
    PATH_TO_CONFIG_YAML_FILE = './config.yaml'
    if len(sys.argv) == 2:
        pass
    elif len(sys.argv) == 4:
        if sys.argv[2] == "--mrcf":
            PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[3]
        elif sys.argv[2] == "--helm":
            PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[3]
        elif sys.argv[2] == "--flavor":
            SYSTEM_SIZE = sys.argv[3]
        elif sys.argv[2] == "--config":
            PATH_TO_CONFIG_YAML_FILE = sys.argv[3]
    elif len(sys.argv) == 6:
        if sys.argv[2] == "--mrcf":
            PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[3]
            if sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
            elif sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
        elif sys.argv[2] == "--helm":
            PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[3]
            if sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
            elif sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
        elif sys.argv[2] == "--flavor":
            SYSTEM_SIZE = sys.argv[3]
            if sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
            elif sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
        elif sys.argv[2] == "--config":
            PATH_TO_CONFIG_YAML_FILE = sys.argv[3]
            if sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
            elif sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
            elif sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
    elif len(sys.argv) == 8:
        if sys.argv[2] == "--mrcf":
            PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[3]
            if sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
                if sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
            elif sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
                if sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
                if sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                elif sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
        elif sys.argv[2] == "--helm":
            PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[3]
            if sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
                if sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
            elif sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                elif sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
        elif sys.argv[2] == "--flavor":
            SYSTEM_SIZE = sys.argv[3]
            if sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
                if sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
            elif sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                elif sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
        elif sys.argv[2] == "--config":
            PATH_TO_CONFIG_YAML_FILE = sys.argv[3]
            if sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
                if sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                elif sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
            elif sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                elif sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
            elif sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                elif sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
    elif len(sys.argv) == 10:
        if sys.argv[2] == "--mrcf":
            PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[3]
            if sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
                if sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
                    if sys.argv[8] == "--config":
                        PATH_TO_CONFIG_YAML_FILE = sys.argv[9]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
                    if sys.argv[8] == "--flavor":
                        SYSTEM_SIZE = sys.argv[9]
            elif sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
                if sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                    if sys.argv[8] == "--config":
                        PATH_TO_CONFIG_YAML_FILE = sys.argv[9]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
                    if sys.argv[8] == "--helm":
                        PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[9]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
                if sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                    if sys.argv[8] == "--flavor":
                        SYSTEM_SIZE = sys.argv[9]
                elif sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
                    if sys.argv[8] == "--helm":
                        PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[9]
        elif sys.argv[2] == "--helm":
            PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[3]
            if sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
                if sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
                    if sys.argv[8] == "--config":
                        PATH_TO_CONFIG_YAML_FILE = sys.argv[9]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
                    if sys.argv[8] == "--flavor":
                        SYSTEM_SIZE = sys.argv[9]
            elif sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                    if sys.argv[8] == "--config":
                        PATH_TO_CONFIG_YAML_FILE = sys.argv[9]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
                    if sys.argv[8] == "--mrcf":
                        PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[9]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                    if sys.argv[8] == "--flavor":
                        SYSTEM_SIZE = sys.argv[9]
                elif sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
                    if sys.argv[8] == "--mrcf":
                        PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[9]
        elif sys.argv[2] == "--flavor":
            SYSTEM_SIZE = sys.argv[3]
            if sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
                if sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                    if sys.argv[8] == "--config":
                        PATH_TO_CONFIG_YAML_FILE = sys.argv[9]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
                    if sys.argv[8] == "--helm":
                        PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[9]
            elif sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                    if sys.argv[8] == "--config":
                        PATH_TO_CONFIG_YAML_FILE = sys.argv[9]
                elif sys.argv[6] == "--config":
                    PATH_TO_CONFIG_YAML_FILE = sys.argv[7]
                    if sys.argv[8] == "--mrcf":
                        PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[9]
            elif sys.argv[4] == "--config":
                PATH_TO_CONFIG_YAML_FILE = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                    if sys.argv[8] == "--helm":
                        PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[9]
                elif sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                    if sys.argv[8] == "--mrcf":
                        PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[9]
        elif sys.argv[2] == "--config":
            PATH_TO_CONFIG_YAML_FILE = sys.argv[3]
            if sys.argv[4] == "--mrcf":
                PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[5]
                if sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                    if sys.argv[8] == "--flavor":
                        SYSTEM_SIZE = sys.argv[9]
                elif sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
                    if sys.argv[8] == "--helm":
                        PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[9]
            elif sys.argv[4] == "--helm":
                PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                    if sys.argv[8] == "--flavor":
                        SYSTEM_SIZE = sys.argv[9]
                elif sys.argv[6] == "--flavor":
                    SYSTEM_SIZE = sys.argv[7]
                    if sys.argv[8] == "--mrcf":
                        PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[9]
            elif sys.argv[4] == "--flavor":
                SYSTEM_SIZE = sys.argv[5]
                if sys.argv[6] == "--mrcf":
                    PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[7]
                    if sys.argv[8] == "--helm":
                        PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[9]
                elif sys.argv[6] == "--helm":
                    PATH_TO_INPUT_HELM_CHARTS_FOLDER = sys.argv[7]
                    if sys.argv[8] == "--mrcf":
                        PATH_TO_INPUT_MRCF_JSON_FILE = sys.argv[9]
    else:
        wrong_syntax()

    print("Input used:")
    print()
    print(f"\t$SCRIPT = {SCRIPT}")
    print(f"\t$PATH_TO_INPUT_YAML_TEMPLATE_FILE = {PATH_TO_INPUT_YAML_TEMPLATE_FILE}")
    if PATH_TO_INPUT_MRCF_JSON_FILE:
        print(f"\t$PATH_TO_INPUT_MRCF_JSON_FILE = {PATH_TO_INPUT_MRCF_JSON_FILE}")
    if PATH_TO_INPUT_HELM_CHARTS_FOLDER:
        print(f"\t$PATH_TO_INPUT_HELM_CHARTS_FOLDER = {PATH_TO_INPUT_HELM_CHARTS_FOLDER}")
    print(f"\t$PATH_TO_CONFIG_YAML_FILE = {PATH_TO_CONFIG_YAML_FILE}")
    print()

    priorities = [
        "MRCF.recommended_value",
        "MRCF.default_per_flavor",
        "MRCF.default",
        "YAML.default_per_flavor",
        "HELM.default",
        "MRCF.example",
    ]
    with open(PATH_TO_CONFIG_YAML_FILE, "r", encoding="UTF-8") as config_yaml_file:
        config_yaml_content = config_yaml_file.read()
        config = yaml.safe_load(config_yaml_content)
        priorities = config["priorities"]

    map_path_mrcf = {}
    map_path_helm = {}

    if PATH_TO_INPUT_MRCF_JSON_FILE:
        with open(PATH_TO_INPUT_MRCF_JSON_FILE, "r", encoding="UTF-8") as mrcf_json_file:
            mrcf_json = json.load(mrcf_json_file)
            for param in mrcf_json["parameters"]:
                if "path" not in param:
                    print("FATAL ERROR: missing 'path' field in parameter:\n")
                    pp(param)
                    continue
                path = param["path"].replace("[N]", "").replace("[0]", "").replace("[1]", "").replace("[2]", "")
                map_path_mrcf[path] = param
        # print(f"MRCF:\n")
        # # display(map_path_mrcf.keys())
        # print_keys(map_path_mrcf)
        # print()

    if PATH_TO_INPUT_HELM_CHARTS_FOLDER:
        box_settings = {
            # "Constructor": MyConstructor,
            "allow_duplicate_keys": None
        }
        for root, dirs, files in os.walk(PATH_TO_INPUT_HELM_CHARTS_FOLDER):
            for file in files:
                if str(file) == 'values.yaml':
                    path = str(root) + os.sep + file
                    #print(path),
                    # Load from yaml file
                    # Here it is also possible to use PyYAML arguments,
                    # for example to specify different loaders e.g. SafeLoader or FullLoader
                    ### values = Box.from_yaml(filename=path, box_duplicates='ignore', ruamel_attrs=box_settings)
                    values = Box.from_yaml(yaml_string=None, filename=path, encoding="UTF-8", errors="strict", box_duplicates='ignore', Constructor=MyConstructor, allow_duplicate_keys=None, ruamel_attrs=box_settings)
                    path = str(root).replace("\\", "/").replace("/charts/", delim)
                    if path.startswith("./"):
                        path = path[2:]
                    loop_through_nodes(values, None, path, delim, map_path_helm)
        # print(f"HELM:\n")
        # # display(map_path_helm)
        # pp(map_path_helm)
        # print()

    for yaml_template_path in glob.glob(PATH_TO_INPUT_YAML_TEMPLATE_FILE, recursive=True):

        if "_uncommented" in yaml_template_path or not yaml_template_path.endswith('.yaml'):
            print(f"\nWarning! Skipping processing of a file or a folder: {yaml_template_path}\n")
            continue

        PATH_TO_OUTPUT_UNCOMMENTED_YAML_TEMPLATE_FILE = yaml_template_path.replace(".yaml", "_uncommented.yaml")
        PATH_TO_OUTPUT_UNCOMMENTED_FIXED_YAML_TEMPLATE_FILE = yaml_template_path.replace(".yaml", "_uncommented_fixed.yaml")
        PATH_TO_OUTPUT_UNCOMMENTED_FIXED_REWRITTEN1_YAML_TEMPLATE_FILE = yaml_template_path.replace(".yaml", "_uncommented_fixed_rewritten1_by_ruamel.yaml")
        PATH_TO_OUTPUT_UNCOMMENTED_FIXED_REWRITTEN2_YAML_TEMPLATE_FILE = yaml_template_path.replace(".yaml", "_uncommented_fixed_rewritten2_by_pyyaml.yaml")
        PATH_TO_OUTPUT_UNCOMMENTED_SET_YAML_TEMPLATE_FILE = yaml_template_path.replace(".yaml", "_uncommented_set.yaml")
        PATH_TO_OUTPUT_UNCOMMENTED_SET_REWRITTEN1_YAML_TEMPLATE_FILE = yaml_template_path.replace(".yaml", "_uncommented_set_rewritten1_by_ruamel.yaml")
        PATH_TO_OUTPUT_UNCOMMENTED_SET_REWRITTEN2_YAML_TEMPLATE_FILE = yaml_template_path.replace(".yaml", "_uncommented_set_rewritten2_by_pyyaml.yaml")

        print()
        print("Input used:")
        print()
        print(f"\t$PATH_TO_INPUT_YAML_TEMPLATE_FILE = {yaml_template_path}")
        print()
        print("Output used:")
        print()
        print(f"\t$PATH_TO_OUTPUT_UNCOMMENTED_YAML_TEMPLATE_FILE = {PATH_TO_OUTPUT_UNCOMMENTED_YAML_TEMPLATE_FILE}")
        print(f"\t$PATH_TO_OUTPUT_UNCOMMENTED_FIXED_YAML_TEMPLATE_FILE = {PATH_TO_OUTPUT_UNCOMMENTED_FIXED_YAML_TEMPLATE_FILE}")
        print(f"\t$PATH_TO_OUTPUT_UNCOMMENTED_FIXED_REWRITTEN1_YAML_TEMPLATE_FILE (Ryamel package) = {PATH_TO_OUTPUT_UNCOMMENTED_FIXED_REWRITTEN1_YAML_TEMPLATE_FILE}")
        print(f"\t$PATH_TO_OUTPUT_UNCOMMENTED_FIXED_REWRITTEN2_YAML_TEMPLATE_FILE (PyYaml package) = {PATH_TO_OUTPUT_UNCOMMENTED_FIXED_REWRITTEN2_YAML_TEMPLATE_FILE}")
        print(f"\t$PATH_TO_OUTPUT_UNCOMMENTED_SET_YAML_TEMPLATE_FILE = {PATH_TO_OUTPUT_UNCOMMENTED_SET_YAML_TEMPLATE_FILE}")
        print(f"\t$PATH_TO_OUTPUT_UNCOMMENTED_SET_REWRITTEN1_YAML_TEMPLATE_FILE (Ryamel package) = {PATH_TO_OUTPUT_UNCOMMENTED_SET_REWRITTEN1_YAML_TEMPLATE_FILE}")
        print(f"\t$PATH_TO_OUTPUT_UNCOMMENTED_SET_REWRITTEN2_YAML_TEMPLATE_FILE (PyYaml package) = {PATH_TO_OUTPUT_UNCOMMENTED_SET_REWRITTEN2_YAML_TEMPLATE_FILE}")
        print()

        with open(yaml_template_path, "r", encoding="UTF-8") as in_yaml_file:
            in_yaml_content = in_yaml_file.read()
            out_yaml_content = in_yaml_content
            if "#" in in_yaml_content:
                found_comment_row = False
                for row in in_yaml_content.split("\n"):
                    if row.lstrip().startswith("#"):
                        found_comment_row = True
                        break
                if found_comment_row:
                    out_yaml_content = preprocess_yaml_file2(out_yaml_content)
                    out_yaml_content = preprocess_yaml_file2b(out_yaml_content)
                    with open(PATH_TO_OUTPUT_UNCOMMENTED_YAML_TEMPLATE_FILE + "-1pre", "w", encoding="UTF-8", newline='\n') as out_yaml_file_tmp1:
                        out_yaml_file_tmp1.write(out_yaml_content)
                    out_yaml_content = process_yaml_file2(out_yaml_content, yaml_template_path)
                    with open(PATH_TO_OUTPUT_UNCOMMENTED_YAML_TEMPLATE_FILE + "-2pro", "w", encoding="UTF-8", newline='\n') as out_yaml_file_tmp2:
                        out_yaml_file_tmp2.write(out_yaml_content)
                    out_yaml_content = postprocess_yaml_file2(out_yaml_content)
                    with open(PATH_TO_OUTPUT_UNCOMMENTED_YAML_TEMPLATE_FILE + "-3post", "w", encoding="UTF-8", newline='\n') as out_yaml_file_tmp3:
                        out_yaml_file_tmp3.write(out_yaml_content)
                    out_yaml_content = check_and_fix_indentation_level(out_yaml_content)

        with open(PATH_TO_OUTPUT_UNCOMMENTED_YAML_TEMPLATE_FILE, "w", encoding="UTF-8", newline='\n') as out_yaml_file:
            out_yaml_file.write(out_yaml_content)

        updated = False
        fixable_syntax_errors = None

        # while fixable_syntax_errors is None or fixable_syntax_errors > 0:
        for tryout in range(0, MAX_NUM_OF_ERRORS_TO_BE_FIXED):
            if fixable_syntax_errors is not None and fixable_syntax_errors < 1:
                break

            in_again_yaml_file = PATH_TO_OUTPUT_UNCOMMENTED_YAML_TEMPLATE_FILE
            if updated:
                in_again_yaml_file = PATH_TO_OUTPUT_UNCOMMENTED_FIXED_YAML_TEMPLATE_FILE
                updated = False
            fixable_syntax_errors = 0
            in_yaml_content_uncom_rows = None
            with open(in_again_yaml_file, "r", encoding="UTF-8") as in_yaml_file_uncom:
                yamllint_conf = YamlLintConfig("extends: relaxed\nrules:\n  indentation:\n    spaces: 2\n    indent-sequences: 'whatever'")
                gen = linter.run(in_yaml_file_uncom, yamllint_conf)
                yamllint_errors = list(gen)
                in_yaml_content_uncom = in_yaml_file_uncom.seek(0)
                in_yaml_content_uncom = in_yaml_file_uncom.read()
                in_yaml_content_uncom_rows = in_yaml_content_uncom.split("\n")
                # with open(yaml_template_path, "r", encoding="UTF-8") as in_yaml_file_ori:
                #    in_yaml_content_ori = in_yaml_file_ori.seek(0)
                #    in_yaml_content_ori = in_yaml_file_ori.read()
                in_yaml_content_ori_rows = in_yaml_content.split("\n")  # in_yaml_content_ori.split("\n")
                for yamllint_error in yamllint_errors:
                    if yamllint_error.level == "error" and yamllint_error.rule != "line-length":
                        print(f"YAML Linting error: ({yamllint_error.__class__.__module__ + '.' + yamllint_error.__class__.__name__}) {yamllint_error}")
                        print("YAML Linting error details:")
                        row_num = int(yamllint_error.line) - 1
                        print(f"\t Line: {yamllint_error.line} (#{row_num}/{len(in_yaml_content_uncom_rows)})")
                        print(f"\t Column: {yamllint_error.column}")
                        print(f"\t Description: {yamllint_error.desc}")
                        print(f"\t Rule: {yamllint_error.rule}")
                        print(f"\t Level: {yamllint_error.level}")
                        if yamllint_error.rule is None:
                            # Syntax error
                            ctx = "\tContext:\n"
                            ctx += str(row_num - 2) + " | " + in_yaml_content_uncom_rows[row_num - 2] + "\n"
                            ctx += str(row_num - 1) + " | " + in_yaml_content_uncom_rows[row_num - 1] + "\n"
                            ctx += str(row_num + 0) + " | " + in_yaml_content_uncom_rows[row_num + 0] + "\n"
                            ctx += str(row_num + 1) + " | " + in_yaml_content_uncom_rows[row_num + 1] + "\n"
                            ctx += str(row_num + 2) + " | " + in_yaml_content_uncom_rows[row_num + 2] + "\n"
                            if "expected <block end>, but found '<block sequence start>'" in yamllint_error.message \
                            or "expected <block end>, but found '<block mapping start>'" in yamllint_error.message:
                                updated_this = False
                                # skip comments rows between code row aaa: [] or aaa: {} and next code row
                                row_num_to_find = row_num - 1
                                row_num_to_find_parent = 0
                                # find first up row which is not a comment
                                for row_num_to_find_iter in range(row_num - 1, 0, -1):
                                    row_num_to_find = row_num_to_find_iter
                                    if not in_yaml_content_uncom_rows[row_num_to_find_iter].lstrip().startswith("#"):
                                        break
                                # find first up parent row (ending with :) on stream without comments
                                for row_num_to_find_iter in range(row_num - 1, 0, -1):
                                    row_num_to_find_parent = row_num_to_find_iter
                                    # remove comments
                                    row_to_check = re.sub("[ ]*[#]+.*", "", in_yaml_content_uncom_rows[row_num_to_find_iter], count=1)
                                    # check if it is some-level parent object, so ends with :
                                    if row_to_check.lstrip().endswith(":"):
                                        break
                                prev_val = in_yaml_content_uncom_rows[row_num_to_find]
                                if ": []" in in_yaml_content_uncom_rows[row_num_to_find]:
                                    in_yaml_content_uncom_rows[row_num_to_find] = in_yaml_content_uncom_rows[row_num_to_find].replace(": []", ":")
                                    updated_this = True
                                    fixable_syntax_errors += 1
                                elif ": {}" in in_yaml_content_uncom_rows[row_num_to_find]:
                                    in_yaml_content_uncom_rows[row_num_to_find] = in_yaml_content_uncom_rows[row_num_to_find].replace(": {}", ":")
                                    updated_this = True
                                    fixable_syntax_errors += 1
                                already_updated = updated_this
                                if not updated_this:
                                    # more complex scenario, we need to check MRCF and/or HELM charts, for example:
                                    # cire-secc-commonsvc:
                                    #   cire-data-wide-column-database-cd:
                                    #     cassandra:
                                    #       jvmOptions:
                                    #         set:
                                    #           - "-Djdk.tls.acknowledgeCloseNotify=true"
                                    #         #List of remote seed nodes. Specified by IP address or hostname.
                                    #         #E.g:
                                    #         #    - 10.40.0.1
                                    #         #    - 10.40.0.2
                                    #         #      remoteSeedNodes:  <- first problem is here
                                    #         #        - VIP0
                                    #         #        - VIP1
                                    #         #    service:            <- second problem is here
                                    #         #      annotations:
                                    #         #        cloudProviderLB:
                                    #         #          #list of cloud provider annotations. Example AWS annotation
                                    #         #          service.beta.kubernetes.io/aws-load-balancer-type: "external"
                                    #         #      externalIPFamily: <- third doubt is here
                                    #         #      #Service desired route for external traffic via node-local (Local) or cluster-wide (Cluster) endpoints.
                                    #         #      #Supported values are Local or Cluster, default is set to Local.
                                    #         #      externalTrafficPolicy: Local   <- 4th doubt is here
                                    #         #      certificates:
                                    #         # A name referring to a key/certificate created through the Certificate Manager.
                                    #         #        asymmetricKeyCertificateName: cire-data-wide-column-database-cd-external-cql-server-cert-key/cire-data-wide-column-database-cd-external-cql-server-cert-key-cert
                                    #         # A name referring to a list of trusted certificates (CAs) created through the Certificate Manager.
                                    #     #        trustedCertificateListName: cire-data-wide-column-database-cd-external-cql-server-ca  <- 5th problem
                                    block_to_find_arr = []
                                    for row_num_to_find_block in range(row_num - 1, 0, -1):
                                        row_to_find_block = in_yaml_content_uncom_rows[row_num_to_find_block]
                                        # store row in block
                                        block_to_find_arr.insert(0, row_to_find_block)  # insert at the beginning
                                        # skip comment row
                                        if row_to_find_block.lstrip('\t\r\n ').startswith('#'):
                                            continue
                                        # end loop when found most parent node
                                        block_row_indents = indent_level(row_to_find_block)
                                        if block_row_indents == 0:
                                            break
                                    block_to_find = "\n".join(block_to_find_arr)
                                    print(f"DEBUG: row_num_to_find_parent = {row_num_to_find_parent} : {in_yaml_content_uncom_rows[row_num_to_find_parent]}")
                                    print(f"DEBUG: row_num_to_find = {row_num_to_find}: {in_yaml_content_uncom_rows[row_num_to_find]}")
                                    print(f"DEBUG: row_num = {row_num}: {in_yaml_content_uncom_rows[row_num]}")
                                    print(f"DEBUG: block_to_find:\n{block_to_find}")
                                    # check in Ruamel.YAML
                                    ### block_to_find_rewritten = process_yaml_file1(block_to_find)
                                    ### block_to_find_dict = yamel.load(block_to_find_rewritten)
                                    block_to_find_dict = yamel.load(block_to_find)
                                    print(f"DEBUG: block_to_find_dict = {block_to_find_dict}")
                                    map_path_block_to_find = {}
                                    loop_through_nodes(block_to_find_dict, None, in_again_yaml_file + "_block", '/', map_path_block_to_find, False)
                                    print(f"DEBUG: map_path_block_to_find: {map_path_block_to_find}")
                                    pp(map_path_block_to_find)
                                    # take key of last element from map_path_block_to_find
                                    map_path_block_to_find_last = list(map_path_block_to_find.keys())[-1]
                                    parent_path_found = map_path_block_to_find_last
                                    current_key = in_yaml_content_uncom_rows[row_num].split(":", 1)[0].lstrip(' \t\r\n')
                                    good_path_found = None
                                    # expexted_indent_level = indent_level(in_yaml_content_uncom_rows[row_num])
                                    while len(parent_path_found) > 0:
                                        tmp_path_found = parent_path_found + '/' + current_key
                                        if tmp_path_found in map_path_mrcf:
                                            good_path_found = tmp_path_found
                                            break
                                        parent_path_found = parent_path_found.rsplit('/', 1)[0]
                                        # expexted_indent_level -= 2
                                    if good_path_found:
                                        print(f"DEBUG: MRCF parent_path_found = {parent_path_found}")
                                        print(f"DEBUG: MRCF good_path_found = {good_path_found}")
                                        pp(map_path_mrcf[good_path_found])
                                        existing_indent_level = indent_level(in_yaml_content_uncom_rows[row_num])
                                        expexted_indent_level = 2 * parent_path_found.count('/')
                                        delta_of_indent_level = existing_indent_level - expexted_indent_level
                                        print(f"DEBUG: existing_indent_level = {existing_indent_level}")
                                        print(f"DEBUG: expexted_indent_level = {expexted_indent_level}")
                                        print(f"DEBUG: delta_of_indent_level = {delta_of_indent_level}")
                                        good_row = expexted_indent_level * " " + in_yaml_content_uncom_rows[row_num].strip(" \t\r\n")
                                        print(f"DEBUG: good_row = {good_row}")
                                        in_yaml_content_uncom_rows[row_num] = good_row
                                        updated_this = True
                                        fixable_syntax_errors += 1
                                        # fixable_syntax_errors += 0.1
                                        # fixable_syntax_errors -= 1
                                        ### fixable_syntax_errors -= 0.1
                                        # additional bonus fixes !!!!!!!!!!!!
                                        for next_row_num in range(row_num + 1, len(in_yaml_content_uncom_rows)):
                                            it_is_comment_row = in_yaml_content_uncom_rows[next_row_num].lstrip(" \t\r\n").startswith("#")
                                            # if it_is_comment_row:
                                            #     # comment row so skip it
                                            #     continue
                                            lvlvl = indent_level(in_yaml_content_uncom_rows[next_row_num])
                                            if it_is_comment_row and lvlvl <= expexted_indent_level + 2:
                                                continue  # break
                                            expexted_indent_level_here = lvlvl - delta_of_indent_level
                                            if expexted_indent_level_here < 0:
                                                break
                                            in_yaml_content_uncom_rows[next_row_num] = " " * expexted_indent_level_here + in_yaml_content_uncom_rows[next_row_num].lstrip(" \t\r\n")
                                            # fixable_syntax_errors += 0.1
                                            ### fixable_syntax_errors -= 0.1
                                if updated_this:
                                    if prev_val == in_yaml_content_uncom_rows[row_num_to_find + 0]:
                                        # really not updated, exactly the same, so change status
                                        updated_this = False
                                    elif already_updated and row_num - row_num_to_find > 2:
                                        ctx = "\tContext:\n"
                                        ctx += str(row_num_to_find - 2) + " | " + in_yaml_content_uncom_rows[row_num_to_find - 2] + "\n"
                                        ctx += str(row_num_to_find - 1) + " | " + in_yaml_content_uncom_rows[row_num_to_find - 1] + "\n"
                                        ctx += str(row_num_to_find + 0) + " | " + prev_val + "\n"
                                        ctx += str(row_num_to_find + 1) + " | " + in_yaml_content_uncom_rows[row_num_to_find + 1] + "\n"
                                        ctx += str(row_num_to_find + 2) + " | " + in_yaml_content_uncom_rows[row_num_to_find + 2] + "\n"
                                        ctx += "\t-> Updated to:\n"
                                        ctx += str(row_num_to_find - 2) + " | " + in_yaml_content_uncom_rows[row_num_to_find - 2] + "\n"
                                        ctx += str(row_num_to_find - 1) + " | " + in_yaml_content_uncom_rows[row_num_to_find - 1] + "\n"
                                        ctx += str(row_num_to_find + 0) + " | " + in_yaml_content_uncom_rows[row_num_to_find + 0] + "\n"
                                        ctx += str(row_num_to_find + 1) + " | " + in_yaml_content_uncom_rows[row_num_to_find + 1] + "\n"
                                        ctx += str(row_num_to_find + 2) + " | " + in_yaml_content_uncom_rows[row_num_to_find + 2] + "\n"
                                        updated = True
                                    else:
                                        ctx += "\t-> Updated to:\n"
                                        ctx += str(row_num - 2) + " | " + in_yaml_content_uncom_rows[row_num - 2] + "\n"
                                        ctx += str(row_num - 1) + " | " + in_yaml_content_uncom_rows[row_num - 1] + "\n"
                                        ctx += str(row_num + 0) + " | " + in_yaml_content_uncom_rows[row_num + 0] + "\n"
                                        ctx += str(row_num + 1) + " | " + in_yaml_content_uncom_rows[row_num + 1] + "\n"
                                        ctx += str(row_num + 2) + " | " + in_yaml_content_uncom_rows[row_num + 2] + "\n"
                                        updated = True
                            elif "could not find expected ':'" in yamllint_error.message:
                                if in_yaml_content_ori_rows[row_num - 1].lstrip().startswith("#"):
                                    # it looks it is not a yaml content row, but some string, so better to comment it back to original
                                    in_yaml_content_uncom_rows[row_num - 1] = "#" + in_yaml_content_uncom_rows[row_num - 1] + "  # detected that it is YAML content row, but some commented text"
                                    updated = True
                                    ## print(f"INFO: Supported case in row {row_num}, but please check it once. Looks like commented text instead of YAML content row: {in_yaml_content_uncom_rows[row_num - 1]}")
                                    ## print(ctx)
                                    ## exit(21)
                                    pass
                                else:
                                    print(f"WARNING: Unsupported case in row {row_num - 1}, please check it! Looks like text instead of YAML content row: {in_yaml_content_uncom_rows[row_num - 1]}")
                                    print(ctx)
                                    exit(20)
                            print(ctx)
                        elif yamllint_error.rule == "key-duplicates":
                            # Duplicate
                            print(f"\tRemoved duplicate:\n{in_yaml_content_uncom_rows[row_num]}")
                            # in_yaml_content_uncom_rows[row_num] = ""
                            # del in_yaml_content_uncom_rows[row_num]
                            in_yaml_content_uncom_rows[row_num] = "#" + in_yaml_content_uncom_rows[row_num] + "  # detected that it is duplicate"
                            updated = True
                            pass
                        elif yamllint_error.rule == "indentation":
                            # Possible wrong level of indentation
                            pass
                        elif yamllint_error.rule in ["new-line-at-end-of-file", "trailing-spaces"]:
                            # Not important for me
                            pass
                        else:
                            print(f"Unsupported error rule: {yamllint_error.rule}")
                            exit(10)

            if updated:
                in_yaml_content_uncom_fixed = "\n".join(in_yaml_content_uncom_rows)
                with open(PATH_TO_OUTPUT_UNCOMMENTED_FIXED_YAML_TEMPLATE_FILE, "w", encoding="UTF-8", newline='\n') as out_yaml_file_uncom_fixed:
                    out_yaml_content_uncom_fixed = postprocess_yaml_file2b(in_yaml_content_uncom_fixed)
                    out_yaml_file_uncom_fixed.write(out_yaml_content_uncom_fixed)
                    in_yaml_content_uncom = out_yaml_content_uncom_fixed
                fixable_syntax_errors = None

        if updated or FORCE_REWRITING:
            with open(PATH_TO_OUTPUT_UNCOMMENTED_FIXED_REWRITTEN1_YAML_TEMPLATE_FILE, "w", encoding="UTF-8", newline='\n') as out_yaml_file_uncom_rewr1:
                out_yaml_content_uncom1 = process_yaml_file1(in_yaml_content_uncom)
                out_yaml_content_uncom1 = postprocess_yaml_file1(out_yaml_content_uncom1)
                out_yaml_file_uncom_rewr1.write(out_yaml_content_uncom1)

            with open(PATH_TO_OUTPUT_UNCOMMENTED_FIXED_REWRITTEN2_YAML_TEMPLATE_FILE, "w", encoding="UTF-8", newline='\n') as out_yaml_file_uncom_rewr2:
                out_yaml_content_uncom2 = preprocess_yaml_file0(in_yaml_content_uncom)
                out_yaml_content_uncom2 = process_yaml_file0(out_yaml_content_uncom2)
                out_yaml_file_uncom_rewr2.write(out_yaml_content_uncom2)

        if "{{" in in_yaml_content_uncom and "}}" in in_yaml_content_uncom:
            # using priorities from config.yaml to set values in yaml template according to that priorities
            in_yaml_content_uncom_set = fix_values(in_yaml_content_uncom, map_path_mrcf, map_path_helm, SYSTEM_SIZE, priorities)

            if len(in_yaml_content_uncom_set) != len(in_yaml_content_uncom) or in_yaml_content_uncom_set != in_yaml_content_uncom:
                with open(PATH_TO_OUTPUT_UNCOMMENTED_SET_YAML_TEMPLATE_FILE, "w", encoding="UTF-8", newline='\n') as out_yaml_file_uncom_set:
                    out_yaml_file_uncom_set.write(in_yaml_content_uncom_set)
                    in_yaml_content_uncom = in_yaml_content_uncom_set

                with open(PATH_TO_OUTPUT_UNCOMMENTED_SET_REWRITTEN1_YAML_TEMPLATE_FILE, "w", encoding="UTF-8", newline='\n') as out_yaml_file_uncom_rewr1:
                    out_yaml_content_uncom1 = process_yaml_file1(in_yaml_content_uncom)
                    out_yaml_content_uncom1 = postprocess_yaml_file1(out_yaml_content_uncom1)
                    out_yaml_file_uncom_rewr1.write(out_yaml_content_uncom1)

                with open(PATH_TO_OUTPUT_UNCOMMENTED_SET_REWRITTEN2_YAML_TEMPLATE_FILE, "w", encoding="UTF-8", newline='\n') as out_yaml_file_uncom_rewr2:
                    out_yaml_content_uncom2 = preprocess_yaml_file0(in_yaml_content_uncom)
                    out_yaml_content_uncom2 = process_yaml_file0(out_yaml_content_uncom2)
                    out_yaml_file_uncom_rewr2.write(out_yaml_content_uncom2)

    print()
    print("All done.")
    print()

