"""
YAML IO Module - Enhanced YAML processing with comment preservation
Integrated from uncomment project with improvements
"""
from ruamel.yaml import YAML
from typing import Dict, Any, Optional
import io
import os

from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, FormatProcessingError


class YAMLIOModule:
    """Advanced YAML I/O with comment preservation and preprocessing"""
    
    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        
        self.stats = {
            "files_read": 0,
            "files_written": 0,
            "preprocessing_hits": 0,
            "postprocessing_hits": 0
        }
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read YAML file with preprocessing"""
        try:
            if not os.path.exists(file_path):
                raise FormatProcessingError(f"YAML file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Preprocessing
            processed_content = self._preprocessing(content)
            
            # Parse YAML
            data = self.yaml.load(processed_content)
            if data is None:
                data = {}
            
            self.stats["files_read"] += 1
            self.tracer.info(f"Successfully loaded YAML: {file_path}")
            return data
            
        except Exception as e:
            error_msg = f"Failed to read YAML file {file_path}: {str(e)}"
            self.tracer.error(error_msg)
            raise FormatProcessingError(error_msg)
    
    def write_file(self, data: Dict[str, Any], output_path: str) -> bool:
        """Write YAML file with postprocessing"""
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Use buffer for postprocessing
            stream = io.StringIO()
            self.yaml.dump(data, stream)
            content = stream.getvalue()
            
            # Postprocessing
            final_content = self._postprocessing(content)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            self.stats["files_written"] += 1
            self.tracer.info(f"Successfully wrote YAML: {output_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to write YAML file {output_path}: {str(e)}"
            self.tracer.error(error_msg)
            raise FormatProcessingError(error_msg)
    
    def read_raw_lines(self, file_path: str) -> list:
        """Read YAML file as raw lines for template processing"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.readlines()
        except Exception as e:
            error_msg = f"Failed to read raw YAML lines from {file_path}: {str(e)}"
            self.tracer.error(error_msg)
            raise FormatProcessingError(error_msg)
    
    def write_raw_lines(self, lines: list, output_path: str) -> bool:
        """Write raw lines to YAML file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            self.stats["files_written"] += 1
            self.tracer.info(f"Successfully wrote raw YAML lines: {output_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to write raw YAML lines to {output_path}: {str(e)}"
            self.tracer.error(error_msg)
            raise FormatProcessingError(error_msg)
    
    def _preprocessing(self, content: str) -> str:
        """Preprocess YAML content before parsing"""
        original_content = content
        
        # Remove problematic Helm tags that break YAML parsing
        # content = re.sub(r'\{\{-.*?-\}\}', '# [HELM_TAG]', content, flags=re.DOTALL)
        
        # Add more preprocessing rules as needed
        
        if content != original_content:
            self.stats["preprocessing_hits"] += 1
            self.tracer.debug("Applied preprocessing to YAML content")
        
        return content
    
    def _postprocessing(self, content: str) -> str:
        """Postprocess YAML content before writing"""
        original_content = content
        
        # Ensure file ends with newline
        if not content.endswith('\n'):
            content += '\n'
        
        # Remove excessive blank lines
        import re
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        if content != original_content:
            self.stats["postprocessing_hits"] += 1
            self.tracer.debug("Applied postprocessing to YAML content")
        
        return content
    
    def validate_yaml(self, file_path: str) -> bool:
        """Validate YAML file syntax"""
        try:
            self.read_file(file_path)
            return True
        except FormatProcessingError:
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary"""
        return self.stats