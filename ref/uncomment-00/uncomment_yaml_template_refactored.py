#!/usr/bin/env python3
"""
Modular YAML Uncommenting Tool
Refactored version of uncomment_yaml_template.py with improved structure and modularity.
"""

import os
import sys
import json
import glob
import yaml
from box import Box
from yamllint.config import YamlLintConfig
from yamllint import linter
from prettyformatter import pprint as pp

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.constants import *
from core.arg_parser import parse_arguments, print_configuration
from core.yaml_utils import *
from core.path_utils import loop_through_nodes, print_keys
from core.value_fixer import fix_values


class YAMLProcessor:
    """Main YAML processing class."""
    
    def __init__(self, config):
        self.config = config
        self.map_path_mrcf = {}
        self.map_path_helm = {}
        self.priorities = DEFAULT_PRIORITIES
        
    def load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config['config_yaml_file'], "r", encoding=ENCODING) as config_file:
                config_content = config_file.read()
                config_data = yaml.safe_load(config_content)
                self.priorities = config_data.get("priorities", DEFAULT_PRIORITIES)
        except FileNotFoundError:
            print(f"Config file not found: {self.config['config_yaml_file']}, using defaults")
    
    def load_mrcf_data(self):
        """Load MRCF JSON data."""
        if not self.config['mrcf_json_file']:
            return
            
        with open(self.config['mrcf_json_file'], "r", encoding=ENCODING) as mrcf_file:
            mrcf_json = json.load(mrcf_file)
            for param in mrcf_json["parameters"]:
                if "path" not in param:
                    print("FATAL ERROR: missing 'path' field in parameter:")
                    pp(param)
                    continue
                path = param["path"].replace("[N]", "").replace("[0]", "").replace("[1]", "").replace("[2]", "")
                self.map_path_mrcf[path] = param
    
    def load_helm_data(self):
        """Load Helm charts data."""
        if not self.config['helm_charts_folder']:
            return
            
        box_settings = {"allow_duplicate_keys": None}
        
        for root, dirs, files in os.walk(self.config['helm_charts_folder']):
            for file in files:
                if str(file) == 'values.yaml':
                    path = str(root) + os.sep + file
                    values = Box.from_yaml(
                        yaml_string=None, 
                        filename=path, 
                        encoding=ENCODING, 
                        errors="strict", 
                        box_duplicates='ignore', 
                        allow_duplicate_keys=None, 
                        ruamel_attrs=box_settings
                    )
                    path = str(root).replace("\\", "/").replace("/charts/", DELIMITER)
                    if path.startswith("./"):
                        path = path[2:]
                    loop_through_nodes(values, None, path, DELIMITER, self.map_path_helm)
    
    def preprocess_yaml_content(self, content):
        """Preprocess YAML content to handle special cases."""
        updated_content = content
        block_started = False
        opening_row = None
        closing_row = None
        out_yaml_array = []
        
        for old_row in content.split('\n'):
            new_row = old_row.rstrip()
            remove_comment_char = False
            
            # Handle JSON blocks
            if new_row.lstrip().startswith('#') and '{' in new_row:
                block_started = True
                opening_row = new_row
                closing_row = opening_row.replace("{", "}")
                remove_comment_char = True
            elif new_row == closing_row:
                block_started = False
                remove_comment_char = True
            elif block_started:
                remove_comment_char = True
            
            if remove_comment_char:
                new_row = new_row.replace('#', ' ', 1)
                indent_lvl = indent_level(new_row)
                if indent_lvl % 2 == 1:
                    new_row = new_row[1:]
                new_row = f"@@@{new_row}@@@"
            elif self._should_mark_special_content(new_row):
                if not new_row.startswith("@@@"):
                    new_row = f"@@@{new_row}@@@"
            elif 'Deployment: {}' in new_row:
                new_row = new_row.replace(': {}', ':')
                if not new_row.startswith("@@@"):
                    new_row = f"@@@{new_row}@@@"
            
            out_yaml_array.append(new_row)
        
        updated_content = '\n'.join(out_yaml_array)
        updated_content = "#\n" + updated_content
        if not updated_content.endswith("\n"):
            updated_content += "\n"
        
        return updated_content
    
    def _should_mark_special_content(self, row):
        """Check if row should be marked as special content."""
        special_patterns = [
            'Version: 1.0, Date:', '.  Misuse,', 'personal information. Handle',
            'USER, PLEASE EXIT', '-XX:', '-Xmn:', '-Xms:', '-Xmx:', '-Xlog:',
            'JAVA_OPTS'
        ]
        
        special_starts = ['-Xm', '-Xlog', '-D', '"y":"', '"x":"', '"kty":"', '"kid":"', '"crv":"', "jwks: '{"]
        special_exact = ["]}'", "}", "{"]
        
        return (any(pattern in row for pattern in special_patterns) or
                any(row.lstrip().startswith(start) for start in special_starts) or
                row.strip() in special_exact or
                row.count('"') == 1)
    
    def process_yaml_blocks(self, content, template_file):
        """Process YAML content by blocks."""
        last_block = ""
        last_row = ""
        yaml_len = len(content)
        print(f"Processing {yaml_len} chars of YAML content...")
        
        blocks = []
        block_num = -1
        status = 0
        original_rows = content.split('\n')
        row_num = len(original_rows)
        
        for i in range(yaml_len - 1, 0, -1):
            ch = content[i]
            last_row = ch + last_row
            
            if ch == "\n":
                row_num -= 1
                act_row = first_row(last_row).strip()
                last_row_is_json = act_row.startswith('@@@') and act_row.endswith('@@@')
                last_row_is_yaml, last_row_content = is_correct_yaml(act_row, row_num)
                
                if last_row_is_json:
                    last_row = last_row.replace('@@@', '')
                elif not last_row_is_yaml:
                    if self._is_allowed_content(last_row_content):
                        last_row_is_yaml = True
                    else:
                        print(f"Wrong YAML content found in '{template_file}', breaking the tool...")
                        sys.exit(1)
                
                comment = last_row.strip().startswith("#")
                comment_only = comment and last_row.strip().endswith("#")
                
                if comment_only:
                    last_block = last_row + last_block
                elif comment:
                    last_row_uncom = uncomment_row(last_row)
                    last_row_uncom_is_yaml, _ = is_correct_yaml(first_row(last_row_uncom), row_num)
                    last_block_uncom = last_row_uncom + last_block
                    last_block_uncom_is_yaml, _ = is_correct_yaml(last_block_uncom, row_num)
                    
                    if last_block_uncom_is_yaml:
                        last_row = last_row_uncom
                        last_block = last_block_uncom
                        status = 1
                    elif last_row_uncom_is_yaml:
                        ind1 = indent_level(first_row(last_row_uncom))
                        ind2 = indent_level(first_row(last_block))
                        
                        if ind1 > ind2:
                            last_block = last_row_uncom + last_block
                            block_num += 1
                            blocks.append(last_block)
                            last_block = ""
                            status = 2
                        else:
                            status = 3
                            last_block = last_row_uncom + last_block
                    else:
                        last_block = last_row + last_block
                        status = 4
                else:
                    last_block = last_row + last_block
                    status = 5
                
                last_row = ""
        
        if status > 0 and status != 2:
            block_num += 1
            blocks.append(last_block)
        
        return ''.join(reversed(blocks))
    
    def _is_allowed_content(self, content):
        """Check if content is allowed even if not valid YAML."""
        if not isinstance(content, str):
            return False
        
        allowed_patterns = [
            "dced.excluded.paths", "dced.agent.restore.type",
            "The usage of this system is monitored and audited",
            "IF YOU ARE NOT AN AUTHORIZED USER STOP",
            "Important legal notice"
        ]
        
        return any(pattern in content for pattern in allowed_patterns)
    
    def check_and_fix_indentation(self, content):
        """Check and fix indentation issues."""
        rows = content.split("\n")
        
        for row_num, row in enumerate(rows):
            lvl = indent_level(row)
            if lvl % 2 == 1:
                print(f"Unexpected odd indentation level {lvl} in row #{row_num}")
                
                row_prev = rows[row_num - 1] if row_num > 0 else None
                row_next = rows[row_num + 1] if row_num < len(rows) - 1 else None
                
                if row_prev and row_next:
                    lvl_prev = indent_level(row_prev)
                    lvl_next = indent_level(row_next)
                    
                    if lvl_prev + 1 == lvl and lvl_next + 1 == lvl:
                        if not row_prev.lstrip().startswith("#") and row_prev.rstrip().endswith(":"):
                            rows[row_num] = " " + rows[row_num]
                        else:
                            rows[row_num] = rows[row_num][1:]
        
        return "\n".join(rows)
    
    def process_file(self, yaml_template_path):
        """Process a single YAML template file."""
        if UNCOMMENTED_SUFFIX in yaml_template_path or not yaml_template_path.endswith(YAML_EXTENSION):
            print(f"\nWarning! Skipping processing of a file: {yaml_template_path}\n")
            return
        
        # Generate output file paths
        base_path = yaml_template_path.replace(YAML_EXTENSION, "")
        output_files = {
            'uncommented': f"{base_path}{UNCOMMENTED_SUFFIX}{YAML_EXTENSION}",
            'fixed': f"{base_path}{UNCOMMENTED_SUFFIX}_fixed{YAML_EXTENSION}",
            'rewritten1': f"{base_path}{UNCOMMENTED_SUFFIX}_fixed_rewritten1_by_ruamel{YAML_EXTENSION}",
            'rewritten2': f"{base_path}{UNCOMMENTED_SUFFIX}_fixed_rewritten2_by_pyyaml{YAML_EXTENSION}",
            'set': f"{base_path}{UNCOMMENTED_SUFFIX}_set{YAML_EXTENSION}",
            'set_rewritten1': f"{base_path}{UNCOMMENTED_SUFFIX}_set_rewritten1_by_ruamel{YAML_EXTENSION}",
            'set_rewritten2': f"{base_path}{UNCOMMENTED_SUFFIX}_set_rewritten2_by_pyyaml{YAML_EXTENSION}"
        }
        
        print(f"\nProcessing: {yaml_template_path}")
        
        # Read and process input file
        with open(yaml_template_path, "r", encoding=ENCODING) as in_file:
            content = in_file.read()
            
            if "#" in content and any(row.lstrip().startswith("#") for row in content.split("\n")):
                content = self.preprocess_yaml_content(content)
                content = self.process_yaml_blocks(content, yaml_template_path)
                content = content.replace("__name__", "")[1:]  # postprocess
                content = self.check_and_fix_indentation(content)
        
        # Write uncommented file
        with open(output_files['uncommented'], "w", encoding=ENCODING, newline='\n') as out_file:
            out_file.write(content)
        
        # Process with yamllint and fix errors
        content = self._fix_yaml_errors(content, output_files)
        
        # Generate rewritten versions if needed
        if FORCE_REWRITING:
            self._generate_rewritten_versions(content, output_files)
        
        # Fix placeholder values
        if "{{" in content and "}}" in content:
            content_with_values = fix_values(content, self.map_path_mrcf, self.map_path_helm, 
                                           self.config['system_size'], self.priorities)
            
            if content_with_values != content:
                with open(output_files['set'], "w", encoding=ENCODING, newline='\n') as out_file:
                    out_file.write(content_with_values)
                
                self._generate_rewritten_versions(content_with_values, {
                    'rewritten1': output_files['set_rewritten1'],
                    'rewritten2': output_files['set_rewritten2']
                })
    
    def _fix_yaml_errors(self, content, output_files):
        """Fix YAML linting errors."""
        updated = False
        
        for _ in range(MAX_NUM_OF_ERRORS_TO_BE_FIXED):
            input_file = output_files['fixed'] if updated else output_files['uncommented']
            
            try:
                with open(input_file, "r", encoding=ENCODING) as yaml_file:
                    yamllint_conf = YamlLintConfig("extends: relaxed\nrules:\n  indentation:\n    spaces: 2\n    indent-sequences: 'whatever'")
                    errors = list(linter.run(yaml_file, yamllint_conf))
                    
                    yaml_file.seek(0)
                    content_rows = yaml_file.read().split("\n")
                
                error_count = 0
                for error in errors:
                    if error.level == "error" and error.rule != "line-length":
                        if self._fix_single_error(error, content_rows):
                            error_count += 1
                
                if error_count > 0:
                    fixed_content = "\n".join(content_rows)
                    with open(output_files['fixed'], "w", encoding=ENCODING, newline='\n') as out_file:
                        out_file.write(fixed_content)
                    updated = True
                    content = fixed_content
                else:
                    break
                    
            except Exception as e:
                print(f"Error processing YAML: {e}")
                break
        
        return content
    
    def _fix_single_error(self, error, content_rows):
        """Fix a single YAML error."""
        row_num = int(error.line) - 1
        
        if error.rule is None:  # Syntax error
            if ("expected <block end>, but found '<block sequence start>'" in error.message or
                "expected <block end>, but found '<block mapping start>'" in error.message):
                
                if ": []" in content_rows[row_num - 1]:
                    content_rows[row_num - 1] = content_rows[row_num - 1].replace(": []", ":")
                    return True
                elif ": {}" in content_rows[row_num - 1]:
                    content_rows[row_num - 1] = content_rows[row_num - 1].replace(": {}", ":")
                    return True
            elif "could not find expected ':'" in error.message:
                content_rows[row_num - 1] = "#" + content_rows[row_num - 1] + "  # detected as commented text"
                return True
        elif error.rule == "key-duplicates":
            content_rows[row_num] = "#" + content_rows[row_num] + "  # detected as duplicate"
            return True
        
        return False
    
    def _generate_rewritten_versions(self, content, output_files):
        """Generate rewritten versions using different YAML processors."""
        if 'rewritten1' in output_files:
            with open(output_files['rewritten1'], "w", encoding=ENCODING, newline='\n') as out_file:
                rewritten1 = process_yaml_file1(content)
                rewritten1 = rewritten1.replace(": null}: null}", "}}")  # postprocess
                out_file.write(rewritten1)
        
        if 'rewritten2' in output_files:
            with open(output_files['rewritten2'], "w", encoding=ENCODING, newline='\n') as out_file:
                preprocessed = content.replace("{{", "").replace("}}", "")  # preprocess
                rewritten2 = process_yaml_file0(preprocessed)
                out_file.write(rewritten2)
    
    def run(self):
        """Main execution method."""
        print(f"Number of arguments given: {len(sys.argv)}")
        print_configuration(self.config)
        
        # Load all data sources
        self.load_config()
        self.load_mrcf_data()
        self.load_helm_data()
        
        # Process all matching files
        for yaml_path in glob.glob(self.config['yaml_template_file'], recursive=True):
            self.process_file(yaml_path)
        
        print("\nAll done.\n")


def main():
    """Main entry point."""
    config = parse_arguments()
    processor = YAMLProcessor(config)
    processor.run()


if __name__ == "__main__":
    main()