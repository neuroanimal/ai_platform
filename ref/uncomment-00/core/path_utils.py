from config.constants import *


def loop_through_nodes(node, prev_key, path, delim, _map_path_helm, lookup_in_helm_tree=True):
    """Recursively traverse nodes to build path mappings."""
    if not isinstance(node, dict) and not isinstance(node, list):
        print(f"loop_through_nodes(node=({node.__class__.__module__ + '.' + node.__class__.__name__}){node}), prev_key='{prev_key}', path='{path}', delim='{delim}', _map_path_helm")
        exit(1)
    
    if isinstance(node, list):
        item_num = 0
        for val in node:
            if prev_key is None:
                kkk = f"[{item_num}]"
            else:
                kkk = prev_key + f"[{item_num}]"
            this_is_leaf = False
            item_num += 1
            
            if isinstance(val, (str, int, float, bool)):
                this_is_leaf = True
            else:
                loop_through_nodes(val, kkk, path, delim, _map_path_helm, lookup_in_helm_tree)
            
            if this_is_leaf:
                if lookup_in_helm_tree:
                    _map_path_helm[kkk] = {"values": [val], "files": [[path]]}
                else:
                    _map_path_helm[kkk] = val
        return
    
    for key, value in node.items():
        safe_key = str(key)
        if isinstance(key, bool):
            safe_key = 'true' if key else 'false'
        
        if delim in safe_key or "." in safe_key or "/" in safe_key:
            safe_key = "(" + safe_key + ")"
        
        if prev_key is not None:
            kk = str(prev_key) + delim + str(safe_key)
        else:
            kk = str(safe_key)
        
        if delim == '/' and not kk.startswith(delim):
            kk = delim + kk
        
        if isinstance(value, str):
            vv = value.replace("\n", "\\n") if value.find("\n") != -1 else value
            
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
                else:
                    _map_path_helm[kk] = vv
            else:
                if lookup_in_helm_tree:
                    _map_path_helm[kk] = {"values": [vv], "files": [[path]]}
                else:
                    _map_path_helm[kk] = vv
        elif isinstance(value, dict):
            loop_through_nodes(value, kk, path, delim, _map_path_helm, lookup_in_helm_tree)
        elif isinstance(value, list):
            item_num = 0
            for val in value:
                kkk = kk + f"[{item_num}]"
                this_is_leaf = False
                item_num += 1
                
                if isinstance(val, (str, int, float, bool)):
                    this_is_leaf = True
                else:
                    loop_through_nodes(val, kkk, path, delim, _map_path_helm, lookup_in_helm_tree)
                
                if this_is_leaf:
                    if lookup_in_helm_tree:
                        _map_path_helm[kkk] = {"values": [val], "files": [[path]]}
                    else:
                        _map_path_helm[kkk] = val
        else:
            if lookup_in_helm_tree:
                _map_path_helm[kk] = {"values": [value], "files": [[path]]}
            else:
                _map_path_helm[kk] = value


def print_keys(mydict):
    """Print dictionary keys line by line."""
    print("\n".join([k for k in mydict.keys()]))