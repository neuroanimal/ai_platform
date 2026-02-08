"""
YAML Uncommenting Tool for AI Platform
Integration of battle-tested uncomment-00 logic
"""
import os
import re
import json
from typing import Dict, Optional, Tuple
from ruamel import yaml as yml

from ai_platform.common.util.trace_handler import TraceHandler
from ai_platform.common.util.error_handler import ErrorHandler, BaseEngineError
from ai_platform.common.util.path_handler import PathHandler
from ai_platform.common.util.template_validator import TemplateValidator


class YAMLUncommenter:
    """YAML uncommenting tool with uncomment-00 core logic."""

    def __init__(self, log_path: str = None):
        self.yamel = yml.YAML(typ='rt', pure=True)
        self.yamel.preserve_quotes = True
        self.yamel.allow_duplicate_keys = None

        self.tracer = TraceHandler("YAMLUncommenter", log_path)
        self.path_handler = PathHandler()
        self.validator = TemplateValidator(self.tracer)
        self.max_fixes = 2000

    def process(self, input_path: str, output_path: str,
                mrcf_path: Optional[str] = None,
                helm_path: Optional[str] = None,
                system_size: str = "standard-system") -> bool:
        """Process YAML template file."""
        try:
            self.tracer.info(f"Processing: {input_path}")

            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Store original content for validation loop
            self.original_lines = content.split('\n')

            mrcf_data = self._load_mrcf(mrcf_path) if mrcf_path else {}
            helm_data = self._load_helm(helm_path) if helm_path else {}

            if "#" in content:
                content = self._preprocess(content)
                content = self._process_yaml_file(content, input_path)
                content = self._postprocess(content)
                content = self._fix_indentation(content)

            content = self._validation_loop(content, mrcf_data)

            if "{{" in content and "}}" in content:
                content = self._fix_values(content, mrcf_data, helm_data, system_size)

            with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)

            self.tracer.info(f"Successfully written: {output_path}")
            return True

        except Exception as e:
            ErrorHandler.handle(BaseEngineError(f"Processing failed: {e}"), self.tracer)
            return False

    def _load_mrcf(self, path: str) -> Dict:
        """Load MRCF data."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                result = {}
                for param in data.get("parameters", []):
                    if "path" in param:
                        clean_path = param["path"].replace("[N]", "").replace("[0]", "")
                        result[clean_path] = param
                self.tracer.info(f"Loaded {len(result)} MRCF parameters")
                return result
        except Exception as e:
            self.tracer.warning(f"Failed to load MRCF: {e}")
            return {}

    def _load_helm(self, path: str) -> Dict:
        """Load Helm data."""
        result = {}
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file == 'values.yaml':
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = self.yamel.load(f)
                            self._flatten_dict(data, result, "")
            self.tracer.info(f"Loaded {len(result)} Helm values")
        except Exception as e:
            self.tracer.warning(f"Failed to load Helm: {e}")
        return result

    def _flatten_dict(self, data, result: Dict, prefix: str):
        """Flatten nested dictionary."""
        if isinstance(data, dict):
            for k, v in data.items():
                new_key = f"{prefix}/{k}" if prefix else f"/{k}"
                if isinstance(v, (dict, list)):
                    self._flatten_dict(v, result, new_key)
                else:
                    result[new_key] = v
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_key = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    self._flatten_dict(item, result, new_key)
                else:
                    result[new_key] = item

    def _preprocess(self, content: str) -> str:
        """Preprocess content (from uncomment-00)."""
        block_started = False
        opening_row = None
        closing_row = None
        out_rows = []

        for row in content.split('\n'):
            new_row = row.rstrip()
            remove_comment = False

            if new_row.lstrip().startswith('#') and '{' in new_row:
                block_started = True
                opening_row = new_row
                closing_row = opening_row.replace("{", "}")
                remove_comment = True
            elif new_row == closing_row:
                block_started = False
                remove_comment = True
            elif block_started:
                remove_comment = True

            if remove_comment:
                new_row = new_row.replace('#', ' ', 1)
                if self._indent_level(new_row) % 2 == 1:
                    new_row = new_row[1:]
                new_row = f"@@@{new_row}@@@"
            elif self._is_special_content(new_row):
                new_row = f"@@@{new_row}@@@"

            out_rows.append(new_row)

        result = '\n'.join(out_rows)
        return "#\n" + result + ("\n" if not result.endswith("\n") else "")

    def _is_special_content(self, row: str) -> bool:
        """Check if row contains special content."""
        patterns = ['Version: 1.0, Date:', 'JAVA_OPTS', '-XX:', '-Xm', '-Xlog', '-D']
        special_vals = ['}', '{', "]}'"]
        return any(p in row for p in patterns) or row.strip() in special_vals

    def _process_yaml_file(self, content: str, template_file: str) -> str:
        """Process YAML content by blocks (from uncomment-00)."""
        last_block = ""
        last_row = ""
        blocks = []
        row_num = len(content.split('\n'))

        for i in range(len(content) - 1, 0, -1):
            ch = content[i]
            last_row = ch + last_row

            if ch == "\n":
                row_num -= 1
                act_row = last_row.strip("\n").split('\n')[0].strip()

                if act_row.startswith('@@@') and act_row.endswith('@@@'):
                    last_row = last_row.replace('@@@', '')
                    last_block = last_row + last_block
                    last_row = ""
                    continue

                is_yaml, _ = self._is_correct_yaml(act_row)
                if not is_yaml and not self._is_allowed_content(act_row):
                    self.tracer.debug(f"Invalid YAML at row {row_num}")

                comment = last_row.strip().startswith("#")
                comment_only = comment and last_row.strip().endswith("#")

                # Debug: trace enableCrashDumps line
                if 'enableCrashDumps' in act_row:
                    self.tracer.debug(f"Row {row_num}: enableCrashDumps found")
                    self.tracer.debug(f"  act_row: {act_row}")
                    self.tracer.debug(f"  comment: {comment}, comment_only: {comment_only}")
                    self.tracer.debug(f"  last_row: {repr(last_row[:80])}")

                if comment_only:
                    last_block = last_row + last_block
                elif comment:
                    last_row_uncom = self._uncomment_row(last_row)
                    last_block_uncom = last_row_uncom + last_block
                    is_block_yaml, _ = self._is_correct_yaml(last_block_uncom)

                    if is_block_yaml:
                        last_row = last_row_uncom
                        last_block = last_block_uncom
                    else:
                        is_row_yaml, _ = self._is_correct_yaml(last_row_uncom.strip("\n").split('\n')[0].strip())
                        if is_row_yaml:
                            ind1 = self._indent_level(last_row_uncom.strip("\n").split('\n')[0])
                            ind2 = self._indent_level(last_block.strip("\n").split('\n')[0]) if last_block.strip() else 0
                            if ind1 > ind2:
                                last_block = last_row_uncom + last_block
                                blocks.append(last_block)
                                last_block = ""
                            else:
                                last_block = last_row_uncom + last_block
                        else:
                            last_block = last_row + last_block
                else:
                    last_block = last_row + last_block

                last_row = ""

        if last_block:
            blocks.append(last_block)

        result = ""
        for block in blocks:
            result = block + result

        return result



    def _is_correct_yaml(self, content: str) -> Tuple[bool, any]:
        """Check if content is valid YAML (from uncomment-00)."""
        try:
            parsed = self.yamel.load(content)

            if parsed is None:
                return True, parsed

            if isinstance(parsed, str):
                return False, parsed

            if isinstance(parsed, list):
                if not parsed:
                    return True, parsed
                first_item = parsed[0]
                if isinstance(first_item, str):
                    if ":" not in first_item and " " in first_item:
                        return False, parsed
                    if first_item.startswith('10.40.0.'):
                        return False, parsed
                    if len(first_item.strip().split(' ')) > 2:
                        return False, parsed
                    if len(first_item.strip().split(':')) > 3:
                        return False, parsed
                return True, parsed

            if isinstance(parsed, dict):
                keys = list(parsed.keys())
                if not keys:
                    return True, parsed
                key = keys[0]

                special_keys = ['IPv4', 'IPv6', 'VirtualTapBroker', 'NFStatusNotify',
                               'DUAL_STACK_INBOUND_PASSTHROUGH', 'PILOT_ENABLE_INBOUND_PASSTHROUGH',
                               'ETCD_SNAPSHOT_COUNT', 'ETCD_QUOTA_BACKEND_BYTES',
                               'ENABLE_TLS_ON_SIDECAR_INGRESS', 'ENABLE_AUTO_SNI', 'CLOUD_PLATFORM']

                if (key[0].isupper() or " " in key) and key not in special_keys:
                    if not key.startswith("PREFIX-") and not key.startswith("ENABLE_") and not key.startswith("ETCD_"):
                        return False, parsed

                val = parsed[key]
                if key in ["supportedGps", "proxy.istio.io/config"]:
                    return True, parsed
                if val and isinstance(val, str) and len(val.strip().split(' ')) > 2:
                    if not (val.strip().startswith('"') and val.strip().endswith('"')):
                        if key not in ["cleanupSchedule"] and not (key == 'filter' and val.startswith("ruby")):
                            return False, parsed

                return True, parsed

            return True, parsed

        except Exception:
            return False, None

    def _is_allowed_content(self, content: str) -> bool:
        """Check if content is allowed even if not valid YAML."""
        allowed = ["dced.excluded.paths", "dced.agent.restore.type",
                  "The usage of this system is monitored and audited",
                  "IF YOU ARE NOT AN AUTHORIZED USER STOP",
                  "Important legal notice"]
        return any(pattern in content for pattern in allowed)

    def _uncomment_row(self, row: str) -> str:
        """Remove comment characters from row (from uncomment-00)."""
        lvl_before = self._indent_level(row)
        uncom_row = re.sub("[#]+", "", row, count=1)
        lvl_after = self._indent_level(uncom_row)
        diff_lvl = lvl_after - lvl_before

        if diff_lvl > 0:
            if lvl_before % 2 == 0 and lvl_after % 2 == 1:
                lf_prefix = ""
                if row.startswith("\n"):
                    num_lf = row.count("\n") - len(row.lstrip("\n"))
                    lf_prefix = "\n" * num_lf
                if row.lstrip(" \t\r\n").startswith('# '):
                    uncom_row = lf_prefix + uncom_row.lstrip("\n")[1:]
                else:
                    uncom_row = lf_prefix + " " + uncom_row.lstrip("\n")

        return uncom_row

    def _postprocess(self, content: str) -> str:
        """Postprocess content."""
        result = content.replace("__name__", "")
        if result.startswith("#\n"):
            result = result[2:]
        elif result.startswith("#"):
            result = result[1:]
        return result

    def _fix_indentation(self, content: str) -> str:
        """Fix indentation issues."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            lvl = self._indent_level(line)
            if lvl % 2 == 1 and i > 0 and i < len(lines) - 1:
                if not lines[i-1].lstrip().startswith("#") and lines[i-1].rstrip().endswith(":"):
                    lines[i] = " " + lines[i]
                else:
                    lines[i] = lines[i][1:] if len(lines[i]) > 0 else lines[i]
        return '\n'.join(lines)

    def _validation_loop(self, content: str, mrcf_data: Dict) -> str:
        """Validation loop with auto-fixing (from uncomment-00)."""
        lines = content.split('\n')

        for tryout in range(self.max_fixes):
            issues = self.validator.validate('\n'.join(lines))
            fixable = 0

            for issue in issues:
                if issue['level'] != 'error' or issue['rule'] == 'line-length':
                    continue

                line_no = issue['line'] - 1
                if line_no >= len(lines):
                    continue

                # Debug: log if line has inline comment
                if '#' in lines[line_no] and not lines[line_no].lstrip().startswith('#'):
                    self.tracer.debug(f"Line {issue['line']} has inline comment: {lines[line_no][:80]}")
                    self.tracer.debug(f"Issue: {issue['rule']} - {issue['message']}")

                if ': []' in lines[line_no]:
                    lines[line_no] = lines[line_no].replace(': []', ':')
                    fixable += 1
                elif ': {}' in lines[line_no]:
                    lines[line_no] = lines[line_no].replace(': {}', ':')
                    fixable += 1
                elif issue['rule'] == 'key-duplicates':
                    lines[line_no] = "#" + lines[line_no] + "  # duplicate"
                    fixable += 1
                elif "could not find expected ':'" in issue['message']:
                    # Check if line was originally commented (text, not YAML)
                    if line_no < len(self.original_lines) and self.original_lines[line_no].lstrip().startswith('#'):
                        lines[line_no] = "#" + lines[line_no] + "  # text"
                        fixable += 1

            if fixable == 0:
                break

        return '\n'.join(lines)

    def _fix_values(self, content: str, mrcf_data: Dict, helm_data: Dict, system_size: str) -> str:
        """Fix placeholder values."""
        lines = content.split('\n')
        size_map = {"small-system": 0, "standard-system": 1, "large-system": 2}

        for i, line in enumerate(lines):
            if "{{" in line and "}}" in line and ":" in line:
                key = line.split(':')[0].strip()
                value = line.split(':', 1)[1].strip()
                path = f"/{key}"

                if path in mrcf_data:
                    rec_val = mrcf_data[path].get("recommended_value")
                    if rec_val:
                        lines[i] = line.replace(value, f'"{rec_val}"')
                        self.tracer.trace_decision("value_fix", f"MRCF: {path}")
                        continue

                if path in helm_data:
                    lines[i] = line.replace(value, f'"{helm_data[path]}"')
                    self.tracer.trace_decision("value_fix", f"Helm: {path}")
                    continue

                clean_val = value.replace('{{', '').replace('}}', '').strip()
                if '|' in clean_val:
                    vals = clean_val.split('|')
                    idx = size_map.get(system_size, 1)
                    if idx < len(vals):
                        lines[i] = line.replace(value, f'"{vals[idx]}"')
                        self.tracer.trace_decision("value_fix", f"Flavor: {system_size}")

        return '\n'.join(lines)

    def _indent_level(self, line: str) -> int:
        """Calculate indentation level."""
        level = 0
        for char in line:
            if char == ' ':
                level += 1
            elif char == '\t':
                level += 2
            else:
                break
        if line.lstrip().startswith('-'):
            level += 2
        return level
