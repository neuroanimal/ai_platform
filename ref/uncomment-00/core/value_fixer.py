import sys
from config.constants import *
from core.yaml_utils import indent_level


def fix_values(yaml_content, map_path_mrcf, map_path_helm, system_size, priorities):
    """Fix placeholder values in YAML content based on priorities."""
    row_num = 0
    in_rows = yaml_content.replace('\n\n', '\n').replace('\n\n', '\n').replace('\n\n', '\n').split("\n")
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
            key, val = _parse_yaml_row(row_before_comment, row_typ)
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
            
            # Compose path from parent keys
            if row_num > 0:
                _build_full_path(paths, in_rows, row_num, ind_lvl, level_reached)
            
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
    
    system_size_mapped = SYSTEM_SIZE_MAPPING.get(system_size)
    
    for path in value_of_path.keys():
        key = path.split('/')[-1]
        value = value_of_path[path]
        
        if value is None or not isinstance(value, str):
            continue
        
        value = value.replace("_or_", '"|"').strip()
        if value.strip().startswith("{{"):
            _process_placeholder_value(path, value, key, in_rows, out_rows, row_num_of_path,
                                     map_path_mrcf, map_path_helm, system_size, system_size_mapped, priorities)
    
    output = "\n".join(out_rows)
    return output


def _parse_yaml_row(row_before_comment, row_typ):
    """Parse a YAML row to extract key and value."""
    key = None
    val = None
    
    if row_before_comment.lstrip().startswith('-'):
        key_row = row_before_comment.strip()[1:].strip()
        if row_before_comment.strip().endswith(':'):
            key = key_row.strip()[0:-1].strip()
        elif ':' in row_before_comment:
            key_value_pair = key_row.strip().split(':', 1)
            key = key_value_pair[0]
            val = key_value_pair[1]
    elif row_before_comment.strip().endswith(('|', '<', '>')):
        key = row_before_comment.strip()[0:-1].strip()
    elif row_before_comment.strip().endswith(('[]', '{}')):
        key = row_before_comment.strip()[0:-2].strip()
        val = [] if row_before_comment.strip().endswith('[]') else {}
    elif row_before_comment.strip().endswith(':'):
        key = row_before_comment.strip()[0:-1].strip()
    elif ':' in row_before_comment:
        key_value_pair = row_before_comment.strip("").split(':', 1)
        key = key_value_pair[0].strip()
        val = key_value_pair[1].strip()
    
    return key, val


def _build_full_path(paths, in_rows, row_num, ind_lvl, level_reached):
    """Build full path by traversing parent keys."""
    for i in range(row_num - 1, -1, -1):
        ind_lvl_i = indent_level(in_rows[i])
        
        if in_rows[i].lstrip().startswith('#'):
            if VERBOSE:
                print(f"\t\tContinue as row {i} is a comment: {in_rows[i]}")
            if i <= 0:
                if VERBOSE:
                    print(f"\t\tEnd of loop and not found any parent key, so still path[{row_num}] == {paths[row_num]}")
                break
            continue
        elif ind_lvl_i > ind_lvl:
            if VERBOSE:
                print(f"\t\tContinue? as level[{i}]:{ind_lvl_i} > level:{ind_lvl}")
            continue
        elif ind_lvl_i == ind_lvl:
            if VERBOSE:
                print(f"\t\tContinue as level[{i}]:{ind_lvl_i} == level:{ind_lvl}")
            continue
        elif paths[i] not in ["", "/"] and paths[row_num].startswith(paths[i]):
            if VERBOSE:
                print(f"\t\t\tBreak as path[{i}]={paths[i]} is beginning/parent of path[{row_num}]={paths[row_num]}")
            break
        else:
            delimiter = ''
            new_path = paths[i] + delimiter + paths[row_num]
            if VERBOSE:
                print(f"\tlevel[{i}]={ind_lvl_i} + {ind_lvl}=level, path[{row_num}] = path[{i}] + path[{row_num}] => {paths[i]} + {paths[row_num]} = {new_path}")
            paths[row_num] = new_path
            
            if ind_lvl_i == 0:
                level_reached[row_num] = 0
                if VERBOSE:
                    print(f"\t\t\tBreak as level_reached[row_num:{row_num}] == 0")
                break
            elif level_reached[i] == 0:
                if VERBOSE:
                    print(f"\t\t\tBreak as level_reached[i:{i}] == 0")
                break
            else:
                if VERBOSE:
                    print("\t\t\tBreak as we added full-path parent")
                break


def _process_placeholder_value(path, value, key, in_rows, out_rows, row_num_of_path,
                             map_path_mrcf, map_path_helm, system_size, system_size_mapped, priorities):
    """Process a placeholder value based on priorities."""
    row_num = row_num_of_path[path]
    print(f"Value from row {row_num} to fix now {path} = {value}")
    
    in_row = in_rows[row_num].replace("_or_", '"|"')
    out_row = out_rows[row_num].replace("_or_", '"|"')
    print(f"\tInput row {row_num} is: {in_row}")
    
    # Get values from different sources
    mrcf_data = _get_mrcf_data(path, map_path_mrcf)
    helm_data = map_path_helm.get(path)
    
    taken = False
    for priority in priorities:
        if taken:
            break
        
        if priority == "MRCF.recommended_value" and mrcf_data.get("recommended_value") is not None:
            taken = _update_row_value(key, value, mrcf_data["recommended_value"], out_row, out_rows, row_num, priority)
        elif priority == "MRCF.default_per_flavor" and mrcf_data.get("defaults") is not None:
            if system_size_mapped is None:
                print(f"FATAL ERROR! System size '{system_size}' unsupported. Possible values are: 'small-system', 'standard-system', 'large-system'.")
                sys.exit(1)
            chosen_value = mrcf_data["defaults"].get(system_size_mapped)
            if chosen_value is not None:
                taken = _update_row_value(key, value, chosen_value, out_row, out_rows, row_num, priority)
        elif priority == "MRCF.default" and mrcf_data.get("default") is not None:
            taken = _update_row_value(key, value, mrcf_data["default"], out_row, out_rows, row_num, priority)
        elif priority == "MRCF.example" and mrcf_data.get("example") is not None:
            taken = _update_row_value(key, value, mrcf_data["example"], out_row, out_rows, row_num, priority)
        elif priority == "YAML.default_per_flavor":
            taken = _process_yaml_flavor_value(key, value, system_size, out_row, out_rows, row_num, priority)
        elif priority == "HELM.default" and helm_data is not None:
            taken = _update_row_value(key, value, helm_data, out_row, out_rows, row_num, priority)
    
    print(f"\tOutput row {row_num} is: {out_rows[row_num]}")


def _get_mrcf_data(path, map_path_mrcf):
    """Extract MRCF data for a given path."""
    if path not in map_path_mrcf:
        print(f"Warning: Cannot find path {path} in MRCF parameters, please check it manually!")
        return {}
    
    all_from_mrcf = map_path_mrcf[path]
    result = {
        "default": all_from_mrcf.get("default"),
        "example": all_from_mrcf.get("example"),
        "recommended_value": all_from_mrcf.get("recommended_value"),
        "defaults": {}
    }
    
    for _key in list(all_from_mrcf.keys()):
        if isinstance(_key, bool):
            print(f"Warning: Found key {_key} which is not a string-type value:\n{all_from_mrcf}")
            _key = 'true' if _key else 'false'
        elif isinstance(_key, str) and _key.startswith("default_"):
            result["defaults"][_key] = all_from_mrcf[_key]
    
    return result


def _update_row_value(key, old_value, new_value, out_row, out_rows, row_num, priority):
    """Update row with new value."""
    print(f"\t{priority}: {new_value}")
    
    if isinstance(new_value, bool):
        new_value = "true" if new_value else "false"
    elif isinstance(new_value, int):
        new_value = str(new_value)
    elif isinstance(new_value, str):
        new_value = new_value.strip("\"'")
        new_value = f'"{new_value}"'
    
    origin_row = key + ": " + old_value.strip()
    update_row = key + ": " + new_value
    out_row = out_row.replace(origin_row, update_row)
    out_rows[row_num] = out_row
    print(f"\t\tUpdating row:\n\t\t\t{origin_row}\n\t\t\t\t->\n\t\t\t{update_row}")
    return True


def _process_yaml_flavor_value(key, value, system_size, out_row, out_rows, row_num, priority):
    """Process YAML flavor-specific values."""
    value_nice = value.replace('{{', '').replace('}}', '').strip()
    vals = value_nice.split('|')
    
    # Type detection and conversion
    if not ((value_nice.startswith('"') and value_nice.endswith('"')) or 
            (value_nice.startswith("'") and value_nice.endswith("'"))):
        try:
            value_nice = int(value_nice)
        except ValueError:
            try:
                value_nice = float(value_nice)
            except ValueError:
                if value_nice in ("true", "false"):
                    value_nice = value_nice == "true"
                elif value_nice == "null":
                    value_nice = None
                else:
                    value_nice = f'"{value_nice}"'
    
    # Build value mapping
    if len(vals) < 2:
        val = {"any-system value": value_nice}
    elif len(vals) == 2:
        val = {"small-system value": vals[0], "standard-system value": vals[1]}
    else:
        val = {"small-system value": vals[0], "standard-system value": vals[1], "large-system value": vals[2]}
    
    val_chosen = val.get(system_size + " value", value_nice)
    if isinstance(val_chosen, str):
        val_chosen = val_chosen.strip("\"'")
        val_chosen = f'"{val_chosen}"'
    
    print(f"\t{priority} chosen: {val_chosen}")
    
    origin_row = key + ": " + value.strip()
    if val_chosen is None:
        update_row = key + ": null"
    else:
        update_row = key + ": " + str(val_chosen)
    
    out_row = out_row.replace(origin_row, update_row)
    out_rows[row_num] = out_row
    print(f"\t\tUpdating row:\n\t\t\t{origin_row}\n\t\t\t\t->\n\t\t\t{update_row}")
    return True