"""
Specialized Excel Processing Module
Supports Parameter Description XLS, LLD XLSX, and various column formats
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

class ExcelType(Enum):
    PARAMETER_DESCRIPTION = "parameter_description"
    LLD = "lld"
    LLD_TEMPLATE = "lld_template"
    GENERIC_COLUMNS = "generic_columns"

class ProductType(Enum):
    # Cloud-Core products
    CCRC = "ccrc"
    CCDM = "ccdm"
    CCSM = "ccsm"
    CCPC = "ccpc"
    CCES = "cces"

    # Packet-Core products
    PCC = "pcc"
    PCG = "pcg"

    # Generic
    NETWORK = "network"
    CUSTOMER = "customer"

class DeploymentDay(Enum):
    DAY0 = "day0"  # deployment
    DAY1 = "day1"  # initial configuration
    DAYN = "dayn"  # reconfiguration

@dataclass
class ExcelMetadata:
    excel_type: ExcelType
    product_type: Optional[ProductType] = None
    deployment_day: Optional[DeploymentDay] = None
    version: Optional[str] = None
    description: Optional[str] = None

@dataclass
class ProcessedExcelData:
    data: pd.DataFrame
    metadata: ExcelMetadata
    sheets: Dict[str, pd.DataFrame]
    column_mappings: Dict[str, str]
    validation_results: List[str]

class SpecializedExcelProcessor:
    """Processor for specialized Excel formats"""

    def __init__(self):
        self.parameter_columns = {
            'parameter': ['parameter', 'param', 'name', 'field'],
            'description': ['description', 'desc', 'comment'],
            'mandatory': ['mandatory', 'required', 'req', 'obligation'],
            'type': ['type', 'data_type', 'format'],
            'default': ['default', 'default_value', 'def_val'],
            'example': ['example', 'sample', 'ex'],
            'constraints': ['constraints', 'validation', 'rules'],
            'day': ['day', 'deployment_day', 'config_day']
        }

        self.lld_sections = {
            'overview': ['overview', 'summary', 'introduction'],
            'architecture': ['architecture', 'design', 'structure'],
            'interfaces': ['interfaces', 'apis', 'endpoints'],
            'data_flow': ['data_flow', 'flow', 'process'],
            'configuration': ['configuration', 'config', 'settings'],
            'deployment': ['deployment', 'install', 'setup']
        }

    def process_excel(self, file_path: str, excel_type: Optional[ExcelType] = None) -> ProcessedExcelData:
        """Process specialized Excel file"""

        # Auto-detect Excel type if not provided
        if not excel_type:
            excel_type = self._detect_excel_type(file_path)

        # Load Excel file
        excel_data = pd.read_excel(file_path, sheet_name=None)

        # Extract metadata
        metadata = self._extract_metadata(file_path, excel_data, excel_type)

        # Process based on type
        if excel_type == ExcelType.PARAMETER_DESCRIPTION:
            return self._process_parameter_description(excel_data, metadata)
        elif excel_type == ExcelType.LLD:
            return self._process_lld(excel_data, metadata)
        elif excel_type == ExcelType.LLD_TEMPLATE:
            return self._process_lld_template(excel_data, metadata)
        else:
            return self._process_generic_columns(excel_data, metadata)

    def _detect_excel_type(self, file_path: str) -> ExcelType:
        """Auto-detect Excel type from filename and content"""
        filename = Path(file_path).name.lower()

        if any(keyword in filename for keyword in ['param', 'parameter', 'config']):
            return ExcelType.PARAMETER_DESCRIPTION
        elif 'lld' in filename and 'template' in filename:
            return ExcelType.LLD_TEMPLATE
        elif 'lld' in filename:
            return ExcelType.LLD
        else:
            return ExcelType.GENERIC_COLUMNS

    def _extract_metadata(self, file_path: str, excel_data: Dict[str, pd.DataFrame],
                         excel_type: ExcelType) -> ExcelMetadata:
        """Extract metadata from Excel file"""
        filename = Path(file_path).name.lower()

        # Detect product type
        product_type = None
        for product in ProductType:
            if product.value in filename:
                product_type = product
                break

        # Detect deployment day
        deployment_day = None
        for day in DeploymentDay:
            if day.value in filename:
                deployment_day = day
                break

        # Extract version from filename
        version_match = re.search(r'v(\d+\.?\d*)', filename)
        version = version_match.group(1) if version_match else None

        return ExcelMetadata(
            excel_type=excel_type,
            product_type=product_type,
            deployment_day=deployment_day,
            version=version,
            description=f"{excel_type.value} for {product_type.value if product_type else 'generic'}"
        )

    def _process_parameter_description(self, excel_data: Dict[str, pd.DataFrame],
                                     metadata: ExcelMetadata) -> ProcessedExcelData:
        """Process Parameter Description Excel"""

        # Find main sheet with parameters
        main_sheet = self._find_main_parameter_sheet(excel_data)
        df = excel_data[main_sheet]

        # Map columns to standard names
        column_mappings = self._map_parameter_columns(df.columns)
        df_mapped = df.rename(columns=column_mappings)

        # Validate parameter structure
        validation_results = self._validate_parameter_structure(df_mapped)

        # Process day-specific parameters if applicable
        if metadata.deployment_day:
            df_mapped = self._filter_by_deployment_day(df_mapped, metadata.deployment_day)

        return ProcessedExcelData(
            data=df_mapped,
            metadata=metadata,
            sheets=excel_data,
            column_mappings=column_mappings,
            validation_results=validation_results
        )

    def _process_lld(self, excel_data: Dict[str, pd.DataFrame],
                    metadata: ExcelMetadata) -> ProcessedExcelData:
        """Process Low-Level Design Excel"""

        # Combine all sheets into structured format
        combined_data = []
        column_mappings = {}

        for sheet_name, df in excel_data.items():
            section_type = self._classify_lld_section(sheet_name)

            # Add section metadata to each row
            df_with_section = df.copy()
            df_with_section['lld_section'] = section_type
            df_with_section['sheet_name'] = sheet_name

            combined_data.append(df_with_section)

        # Combine all sheets
        main_df = pd.concat(combined_data, ignore_index=True, sort=False)

        validation_results = self._validate_lld_structure(main_df)

        return ProcessedExcelData(
            data=main_df,
            metadata=metadata,
            sheets=excel_data,
            column_mappings=column_mappings,
            validation_results=validation_results
        )

    def _process_lld_template(self, excel_data: Dict[str, pd.DataFrame],
                            metadata: ExcelMetadata) -> ProcessedExcelData:
        """Process LLD Template Excel"""

        # Extract template structure
        template_structure = {}
        column_mappings = {}

        for sheet_name, df in excel_data.items():
            # Identify template sections and placeholders
            template_info = self._extract_template_info(df)
            template_structure[sheet_name] = template_info

        # Create main DataFrame with template metadata
        main_df = pd.DataFrame(template_structure).T

        validation_results = self._validate_template_structure(template_structure)

        return ProcessedExcelData(
            data=main_df,
            metadata=metadata,
            sheets=excel_data,
            column_mappings=column_mappings,
            validation_results=validation_results
        )

    def _process_generic_columns(self, excel_data: Dict[str, pd.DataFrame],
                               metadata: ExcelMetadata) -> ProcessedExcelData:
        """Process generic column-based Excel"""

        # Use first sheet as main data
        main_sheet = list(excel_data.keys())[0]
        df = excel_data[main_sheet]

        # Analyze column patterns
        column_mappings = self._analyze_column_patterns(df.columns)

        validation_results = [f"Processed {len(df)} rows with {len(df.columns)} columns"]

        return ProcessedExcelData(
            data=df,
            metadata=metadata,
            sheets=excel_data,
            column_mappings=column_mappings,
            validation_results=validation_results
        )

    def _find_main_parameter_sheet(self, excel_data: Dict[str, pd.DataFrame]) -> str:
        """Find the main sheet containing parameters"""
        for sheet_name in excel_data.keys():
            if any(keyword in sheet_name.lower() for keyword in ['param', 'config', 'main']):
                return sheet_name
        return list(excel_data.keys())[0]  # Default to first sheet

    def _map_parameter_columns(self, columns: List[str]) -> Dict[str, str]:
        """Map Excel columns to standard parameter column names"""
        mappings = {}

        for col in columns:
            col_lower = col.lower().strip()

            for standard_name, variants in self.parameter_columns.items():
                if any(variant in col_lower for variant in variants):
                    mappings[col] = standard_name
                    break

        return mappings

    def _validate_parameter_structure(self, df: pd.DataFrame) -> List[str]:
        """Validate parameter structure"""
        results = []

        # Check required columns
        required_cols = ['parameter', 'description']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            results.append(f"Missing required columns: {missing_cols}")

        # Check for empty parameters
        if 'parameter' in df.columns:
            empty_params = df['parameter'].isna().sum()
            if empty_params > 0:
                results.append(f"Found {empty_params} rows with empty parameter names")

        # Check mandatory field consistency
        if 'mandatory' in df.columns:
            mandatory_values = df['mandatory'].unique()
            valid_values = ['mandatory', 'optional', 'conditional', 'required', 'req', 'opt']
            invalid_values = [v for v in mandatory_values if str(v).lower() not in valid_values]
            if invalid_values:
                results.append(f"Invalid mandatory values: {invalid_values}")

        if not results:
            results.append("Parameter structure validation passed")

        return results

    def _filter_by_deployment_day(self, df: pd.DataFrame, day: DeploymentDay) -> pd.DataFrame:
        """Filter parameters by deployment day"""
        if 'day' not in df.columns:
            return df

        # Filter rows matching the deployment day
        day_filter = df['day'].str.lower().str.contains(day.value, na=False)
        return df[day_filter]

    def _classify_lld_section(self, sheet_name: str) -> str:
        """Classify LLD sheet into section type"""
        sheet_lower = sheet_name.lower()

        for section_type, keywords in self.lld_sections.items():
            if any(keyword in sheet_lower for keyword in keywords):
                return section_type

        return 'other'

    def _validate_lld_structure(self, df: pd.DataFrame) -> List[str]:
        """Validate LLD structure"""
        results = []

        # Check section distribution
        if 'lld_section' in df.columns:
            section_counts = df['lld_section'].value_counts()
            results.append(f"LLD sections: {dict(section_counts)}")

        # Check for required LLD elements
        required_sections = ['overview', 'architecture']
        if 'lld_section' in df.columns:
            present_sections = df['lld_section'].unique()
            missing_sections = [sec for sec in required_sections if sec not in present_sections]
            if missing_sections:
                results.append(f"Missing recommended LLD sections: {missing_sections}")

        if not any("Missing" in result for result in results):
            results.append("LLD structure validation passed")

        return results

    def _extract_template_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract template information from DataFrame"""
        template_info = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': df.columns.tolist(),
            'placeholders': []
        }

        # Find template placeholders (cells with {{}} or similar patterns)
        for col in df.columns:
            for idx, value in df[col].items():
                if isinstance(value, str) and ('{{' in value or '<<' in value or '${' in value):
                    template_info['placeholders'].append({
                        'column': col,
                        'row': idx,
                        'placeholder': value
                    })

        return template_info

    def _validate_template_structure(self, template_structure: Dict) -> List[str]:
        """Validate template structure"""
        results = []

        total_placeholders = sum(len(info.get('placeholders', [])) for info in template_structure.values())
        results.append(f"Found {total_placeholders} template placeholders")

        # Check for consistent template patterns
        placeholder_patterns = set()
        for sheet_info in template_structure.values():
            for placeholder in sheet_info.get('placeholders', []):
                pattern = self._extract_placeholder_pattern(placeholder['placeholder'])
                placeholder_patterns.add(pattern)

        results.append(f"Template patterns used: {list(placeholder_patterns)}")

        return results

    def _extract_placeholder_pattern(self, placeholder: str) -> str:
        """Extract placeholder pattern type"""
        if '{{' in placeholder:
            return 'mustache'
        elif '<<' in placeholder:
            return 'angle_brackets'
        elif '${' in placeholder:
            return 'shell_variable'
        else:
            return 'unknown'

    def _analyze_column_patterns(self, columns: List[str]) -> Dict[str, str]:
        """Analyze generic column patterns"""
        patterns = {}

        for col in columns:
            col_lower = col.lower().strip()

            # Identify common patterns
            if any(keyword in col_lower for keyword in ['id', 'identifier', 'key']):
                patterns[col] = 'identifier'
            elif any(keyword in col_lower for keyword in ['name', 'title', 'label']):
                patterns[col] = 'name'
            elif any(keyword in col_lower for keyword in ['desc', 'description', 'comment']):
                patterns[col] = 'description'
            elif any(keyword in col_lower for keyword in ['date', 'time', 'timestamp']):
                patterns[col] = 'temporal'
            elif any(keyword in col_lower for keyword in ['status', 'state', 'condition']):
                patterns[col] = 'status'
            elif any(keyword in col_lower for keyword in ['value', 'amount', 'count', 'number']):
                patterns[col] = 'numeric'
            else:
                patterns[col] = 'generic'

        return patterns

    def convert_to_mrcf(self, processed_data: ProcessedExcelData) -> Dict[str, Any]:
        """Convert processed Excel data to MRCF format"""
        mrcf_data = {}

        for idx, row in processed_data.data.iterrows():
            if 'parameter' in row:
                param_name = row['parameter']
                mrcf_data[param_name] = {
                    'description': row.get('description', ''),
                    'mandatory': row.get('mandatory', 'optional'),
                    'format': row.get('type', 'string'),
                    'type': row.get('type', 'string'),
                    'default': row.get('default', ''),
                    'example': row.get('example', ''),
                    'constraints': row.get('constraints', ''),
                    'deployment_day': row.get('day', ''),
                    'product_type': processed_data.metadata.product_type.value if processed_data.metadata.product_type else '',
                    'excel_type': processed_data.metadata.excel_type.value
                }

        return mrcf_data