"""
Helm IO Module - Specialized Helm chart processing
Integrated from uncomment project with enhancements
"""
import tarfile
import yaml
import re
import os
from io import BytesIO
from typing import Dict, Any, List, Optional

from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, FormatProcessingError


class HelmIOModule:
    """Advanced Helm chart processing with subchart support"""

    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.stats = {
            "archives_processed": 0,
            "values_files_found": 0,
            "skipped_files": 0,
            "subcharts_processed": 0
        }

        # Regex for Helm template tags
        self.helm_tag_regex = re.compile(r'\{\{.*?\}\}', re.DOTALL)

    def read_all_charts(self, helm_dir: str) -> Dict[str, Any]:
        """Process all Helm charts in directory and merge values"""
        aggregated_data = {}

        if not os.path.exists(helm_dir):
            self.tracer.warning(f"Helm directory does not exist: {helm_dir}")
            return aggregated_data

        # Process .tgz archives
        for filename in os.listdir(helm_dir):
            if filename.endswith(".tgz"):
                archive_path = os.path.join(helm_dir, filename)
                self.tracer.info(f"Processing Helm archive: {filename}")
                chart_data = self._process_tgz(archive_path)
                self._deep_merge(aggregated_data, chart_data)
                self.stats["archives_processed"] += 1

        # Process directory-based charts
        for item in os.listdir(helm_dir):
            item_path = os.path.join(helm_dir, item)
            if os.path.isdir(item_path):
                chart_data = self._process_chart_directory(item_path)
                if chart_data:
                    self._deep_merge(aggregated_data, chart_data)

        return aggregated_data

    def read_single_chart(self, chart_path: str) -> Dict[str, Any]:
        """Process single Helm chart (directory or .tgz)"""
        if chart_path.endswith(".tgz"):
            return self._process_tgz(chart_path)
        elif os.path.isdir(chart_path):
            return self._process_chart_directory(chart_path)
        else:
            raise FormatProcessingError(f"Invalid Helm chart path: {chart_path}")

    def _process_tgz(self, tgz_path: str) -> Dict[str, Any]:
        """Extract and process .tgz Helm archive"""
        chart_data = {}

        try:
            with tarfile.open(tgz_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("values.yaml") and member.isfile():
                        f = tar.extractfile(member)
                        if not f:
                            continue

                        raw_content = f.read().decode('utf-8', errors='ignore')
                        processed_data = self._process_values_content(raw_content, member.name)

                        if processed_data:
                            key_path = self._infer_key_path(member.name)
                            if key_path:
                                self._nest_data(chart_data, key_path, processed_data)
                                self.stats["subcharts_processed"] += 1
                            else:
                                self._deep_merge(chart_data, processed_data)

                            self.stats["values_files_found"] += 1

        except Exception as e:
            self.tracer.error(f"Failed to process Helm archive {tgz_path}: {str(e)}")
            raise FormatProcessingError(f"Helm archive processing failed: {str(e)}")

        return chart_data

    def _process_chart_directory(self, chart_dir: str) -> Dict[str, Any]:
        """Process directory-based Helm chart"""
        chart_data = {}

        # Look for values.yaml in root
        values_path = os.path.join(chart_dir, "values.yaml")
        if os.path.exists(values_path):
            with open(values_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            processed_data = self._process_values_content(raw_content, values_path)
            if processed_data:
                chart_data = processed_data
                self.stats["values_files_found"] += 1

        # Process subcharts
        charts_dir = os.path.join(chart_dir, "charts")
        if os.path.exists(charts_dir):
            for subchart in os.listdir(charts_dir):
                subchart_path = os.path.join(charts_dir, subchart)
                if os.path.isdir(subchart_path):
                    subchart_data = self._process_chart_directory(subchart_path)
                    if subchart_data:
                        self._nest_data(chart_data, [subchart], subchart_data)
                        self.stats["subcharts_processed"] += 1

        return chart_data

    def _process_values_content(self, content: str, source_path: str) -> Optional[Dict[str, Any]]:
        """Process values.yaml content with Helm tag sanitization"""
        try:
            # Sanitize Helm template tags
            sanitized_content = self._sanitize_helm_content(content)

            # Parse YAML
            data = yaml.safe_load(sanitized_content)
            return data if data else {}

        except yaml.YAMLError as e:
            self.tracer.warning(f"Skipped {source_path} - YAML syntax error (likely complex template)")
            self.stats["skipped_files"] += 1
            return None

    def _sanitize_helm_content(self, content: str) -> str:
        """Replace Helm template tags with safe comments"""
        # Replace {{ ... }} with comments to preserve line structure
        return self.helm_tag_regex.sub("# [HELM_TAG]", content)

    def _infer_key_path(self, internal_path: str) -> List[str]:
        """
        Infer subchart key path from archive internal path
        Example: 'chart/charts/subchart/values.yaml' -> ['subchart']
        """
        parts = internal_path.split('/')
        keys = []

        for i, part in enumerate(parts):
            if part == "charts" and i + 1 < len(parts):
                next_part = parts[i + 1]
                if next_part != "values.yaml":
                    keys.append(next_part)

        return keys

    def _nest_data(self, root: Dict[str, Any], keys: List[str], data: Dict[str, Any]):
        """Nest data under key path"""
        current = root
        for key in keys[:-1]:
            current = current.setdefault(key, {})

        if keys:
            last_key = keys[-1]
            if last_key in current:
                self._deep_merge(current[last_key], data)
            else:
                current[last_key] = data

    def _deep_merge(self, base: Dict[str, Any], source: Dict[str, Any]):
        """Recursively merge dictionaries"""
        for key, value in source.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def extract_chart_metadata(self, chart_path: str) -> Dict[str, Any]:
        """Extract Chart.yaml metadata"""
        metadata = {}

        if chart_path.endswith(".tgz"):
            try:
                with tarfile.open(chart_path, "r:gz") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith("Chart.yaml"):
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode('utf-8')
                                metadata = yaml.safe_load(content) or {}
                                break
            except Exception as e:
                self.tracer.warning(f"Failed to extract metadata from {chart_path}: {str(e)}")

        elif os.path.isdir(chart_path):
            chart_yaml = os.path.join(chart_path, "Chart.yaml")
            if os.path.exists(chart_yaml):
                try:
                    with open(chart_yaml, 'r', encoding='utf-8') as f:
                        metadata = yaml.safe_load(f) or {}
                except Exception as e:
                    self.tracer.warning(f"Failed to read Chart.yaml from {chart_path}: {str(e)}")

        return metadata

    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary"""
        return self.stats