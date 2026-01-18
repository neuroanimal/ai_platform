"""
YAML Processor Engine - Integration of uncomment-00 functionality
"""
import os
import re
import io
import json
import glob
import yaml
from ruamel import yaml as yml
from yamllint.config import YamlLintConfig
from yamllint import linter
from box import Box

from common.trace_handler import TraceHandler
from common.error_handler import ErrorHandler


class YAMLProcessorEngine:
    """YAML processing engine integrating uncomment-00 functionality."""
    
    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.config = self._load_default_config()
        self.map_path_mrcf = {}
        self.map_path_helm = {}
        
        # Initialize YAML processors
        self.yamel = yml.YAML(typ='rt', pure=True)
        self.yamel.preserve_quotes = True
        yaml.preserve_quotes = True
        yml.preserve_quotes = True
        yml.allow_duplicate_keys = None
        yaml.allow_duplicate_keys = True
        self.yamel.allow_duplicate_keys = None
    
    def _load_default_config(self):
        """Load default configuration."""
        return {
            'debug': False,
            'verbose': False,
            'force_rewriting': True,
            'stop_on_ruamel_error': False,
            'stop_on_pyyaml_error': False,
            'max_errors_to_fix': 2000,
            'system_size_mapping': {
                "small-system": "default_small_system_profile",
                "standard-system": "default_standard_system_profile", 
                "large-system": "default_large_system_profile",
            },
            'priorities': [
                "MRCF.recommended_value",
                "MRCF.default_per_flavor", 
                "MRCF.default",
                "YAML.default_per_flavor",
                "HELM.default",
                "MRCF.example",
            ]
        }
    
    def process_yaml_template(self, input_path: str, output_path: str, 
                            mrcf_path: str = None, helm_path: str = None, 
                            system_size: str = "standard-system") -> bool:
        """Main processing method."""
        try:
            self.tracer.info(f"Processing YAML template: {input_path}")
            
            # Load external data
            if mrcf_path:
                self._load_mrcf_data(mrcf_path)
            if helm_path:
                self._load_helm_data(helm_path)
            
            # Process file
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply processing pipeline
            if "#" in content and self._has_commented_rows(content):
                content = self._preprocess_content(content)
                content = self._process_blocks(content, input_path)
                content = self._postprocess_content(content)
                content = self._fix_indentation(content)
            
            # Fix YAML errors
            content = self._fix_yaml_errors(content)
            
            # Fix placeholder values
            if "{{" in content and "}}" in content:
                content = self._fix_values(content, system_size)
            
            # Write output
            with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            
            self.tracer.info(f"Successfully processed to: {output_path}")
            return True
            
        except Exception as e:
            ErrorHandler.handle(e, self.tracer)
            return False
    
    def _has_commented_rows(self, content: str) -> bool:
        """Check if content has commented rows."""
        return any(row.lstrip().startswith("#") for row in content.split("\n"))
    
    def _preprocess_content(self, content: str) -> str:
        """Preprocess YAML content."""
        block_started = False
        opening_row = None
        closing_row = None
        out_rows = []
        
        for row in content.split('\n'):
            new_row = row.rstrip()
            remove_comment = False
            
            # Handle JSON blocks
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
        patterns = ['Version: 1.0, Date:', 'JAVA_OPTS', '-XX:', '-Xm']
        return any(p in row for p in patterns) or row.strip() in ['}', '{', "]}'"]
    
    def _process_blocks(self, content: str, template_file: str) -> str:
        """Process YAML content by blocks."""
        last_block = ""
        last_row = ""
        blocks = []
        
        for i in range(len(content) - 1, 0, -1):
            ch = content[i]
            last_row = ch + last_row
            
            if ch == "\n":
                act_row = last_row.strip("\n").split('\n')[0].strip()
                
                if act_row.startswith('@@@') and act_row.endswith('@@@'):
                    last_row = last_row.replace('@@@', '')
                elif not self._is_correct_yaml(act_row):
                    if not self._is_allowed_content(act_row):
                        self.tracer.error(f"Invalid YAML in {template_file}: {act_row}")
                        continue
                
                comment = last_row.strip().startswith("#")
                if comment and not last_row.strip().endswith("#"):
                    uncom_row = self._uncomment_row(last_row)
                    if self._is_correct_yaml(uncom_row.strip("\n").split('\n')[0].strip()):
                        last_row = uncom_row
                        last_block = last_row + last_block
                    else:
                        last_block = last_row + last_block
                else:
                    last_block = last_row + last_block
                
                last_row = ""
        
        if last_block:
            blocks.append(last_block)
        
        return ''.join(reversed(blocks))
    
    def _postprocess_content(self, content: str) -> str:
        """Postprocess content."""
        return content.replace("__name__", "")[1:] if content.startswith("#") else content
    
    def _fix_indentation(self, content: str) -> str:
        """Fix indentation issues."""
        rows = content.split("\n")
        for i, row in enumerate(rows):
            lvl = self._indent_level(row)
            if lvl % 2 == 1 and i > 0 and i < len(rows) - 1:
                prev_lvl = self._indent_level(rows[i-1])
                if not rows[i-1].lstrip().startswith("#") and rows[i-1].rstrip().endswith(":"):
                    rows[i] = " " + rows[i]
                else:
                    rows[i] = rows[i][1:] if len(rows[i]) > 0 else rows[i]
        return "\n".join(rows)
    
    def _fix_yaml_errors(self, content: str) -> str:
        """Fix YAML linting errors."""
        rows = content.split("\n")
        
        try:
            from io import StringIO
            yaml_file = StringIO(content)
            conf = YamlLintConfig("extends: relaxed\nrules:\n  indentation:\n    spaces: 2")
            errors = list(linter.run(yaml_file, conf))
            
            for error in errors:
                if error.level == "error" and error.rule != "line-length":
                    row_num = int(error.line) - 1
                    if row_num < len(rows):
                        if ": []" in rows[row_num]:
                            rows[row_num] = rows[row_num].replace(": []", ":")
                        elif ": {}" in rows[row_num]:
                            rows[row_num] = rows[row_num].replace(": {}", ":")
                        elif error.rule == "key-duplicates":
                            rows[row_num] = "#" + rows[row_num] + "  # duplicate"
        except Exception as e:
            self.tracer.debug(f"YAML error fixing failed: {e}")
        
        return "\n".join(rows)
    
    def _fix_values(self, content: str, system_size: str) -> str:
        """Fix placeholder values."""
        rows = content.split("\n")
        system_size_mapped = self.config['system_size_mapping'].get(system_size)
        
        for i, row in enumerate(rows):
            if "{{" in row and "}}" in row:
                # Extract key and value
                if ":" in row:
                    key = row.split(":")[0].strip()
                    value = row.split(":", 1)[1].strip()
                    
                    # Build path (simplified)
                    path = "/" + key
                    
                    # Try to fix value based on priorities
                    new_value = self._get_replacement_value(path, value, system_size, system_size_mapped)
                    if new_value != value:
                        rows[i] = row.replace(value, new_value)
        
        return "\n".join(rows)
    
    def _get_replacement_value(self, path: str, value: str, system_size: str, system_size_mapped: str) -> str:
        """Get replacement value based on priorities."""
        for priority in self.config['priorities']:
            if priority == "MRCF.recommended_value" and path in self.map_path_mrcf:
                rec_val = self.map_path_mrcf[path].get("recommended_value")
                if rec_val is not None:
                    return f'"{rec_val}"' if isinstance(rec_val, str) else str(rec_val)
            
            elif priority == "HELM.default" and path in self.map_path_helm:
                helm_val = self.map_path_helm[path]
                if helm_val is not None:
                    return f'"{helm_val}"' if isinstance(helm_val, str) else str(helm_val)
            
            elif priority == "YAML.default_per_flavor":
                # Extract values from template
                clean_val = value.replace('{{', '').replace('}}', '').strip()
                if '|' in clean_val:
                    vals = clean_val.split('|')
                    if system_size == "small-system" and len(vals) > 0:
                        return f'"{vals[0]}"'
                    elif system_size == "standard-system" and len(vals) > 1:
                        return f'"{vals[1]}"'
                    elif system_size == "large-system" and len(vals) > 2:
                        return f'"{vals[2]}"'
        
        return value
    
    def _load_mrcf_data(self, path: str):
        """Load MRCF JSON data."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for param in data.get("parameters", []):
                    if "path" in param:
                        clean_path = param["path"].replace("[N]", "").replace("[0]", "")
                        self.map_path_mrcf[clean_path] = param
            self.tracer.info(f"Loaded {len(self.map_path_mrcf)} MRCF parameters")
        except Exception as e:
            self.tracer.error(f"Failed to load MRCF data: {e}")
    
    def _load_helm_data(self, path: str):
        """Load Helm charts data."""
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file == 'values.yaml':
                        file_path = os.path.join(root, file)
                        values = Box.from_yaml(filename=file_path, box_duplicates='ignore')
                        self._traverse_helm_values(values, "", file_path)
            self.tracer.info(f"Loaded {len(self.map_path_helm)} Helm values")
        except Exception as e:
            self.tracer.error(f"Failed to load Helm data: {e}")
    
    def _traverse_helm_values(self, node, path: str, file_path: str):
        """Traverse Helm values recursively."""
        if isinstance(node, dict):
            for key, value in node.items():
                new_path = f"{path}/{key}" if path else f"/{key}"
                if isinstance(value, (dict, list)):
                    self._traverse_helm_values(value, new_path, file_path)
                else:
                    self.map_path_helm[new_path] = value
        elif isinstance(node, list):
            for i, item in enumerate(node):
                new_path = f"{path}[{i}]"
                if isinstance(item, (dict, list)):
                    self._traverse_helm_values(item, new_path, file_path)
                else:
                    self.map_path_helm[new_path] = item
    
    def _indent_level(self, row: str) -> int:
        """Calculate indentation level."""
        level = 0
        for char in row:
            if char == ' ':
                level += 1
            elif char == '\t':
                level += 2
            else:
                break
        if row.lstrip().startswith('-'):
            level += 2
        return level
    
    def _uncomment_row(self, row: str) -> str:
        """Remove comment characters from row."""
        return re.sub("[#]+", "", row, count=1)
    
    def _is_correct_yaml(self, content: str) -> bool:
        """Check if content is valid YAML."""
        try:
            self.yamel.load(content)
            return True
        except:
            return False
    
    def _is_allowed_content(self, content: str) -> bool:
        """Check if content is allowed even if not valid YAML."""
        allowed = ["dced.excluded.paths", "Important legal notice", "USER, PLEASE EXIT"]
        return any(pattern in content for pattern in allowed)