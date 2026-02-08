"""
YAML Processing Engine for AI Platform
Provides engine-level interface for YAML uncommenting functionality
"""
from typing import Dict, Optional, Any
from code.common.tool.yaml_uncommenter import YAMLUncommenter


class YAMLProcessingEngine:
    """Engine wrapper for YAML processing functionality."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.uncommenter = YAMLUncommenter()

    def process_template(self, input_path: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """Process YAML template with engine interface."""
        try:
            success = self.uncommenter.process(
                input_path=input_path,
                output_path=output_path,
                mrcf_path=kwargs.get('mrcf_path'),
                helm_path=kwargs.get('helm_path'),
                system_size=kwargs.get('system_size', 'standard-system')
            )

            return {
                'success': success,
                'input_path': input_path,
                'output_path': output_path,
                'message': 'Processing completed' if success else 'Processing failed'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Processing error: {e}'
            }

    def get_capabilities(self) -> Dict[str, Any]:
        """Return engine capabilities."""
        return {
            'name': 'YAML Processing Engine',
            'version': '1.0.0',
            'supports': [
                'yaml_uncommenting',
                'mrcf_integration',
                'helm_integration',
                'multi_flavor_support'
            ],
            'flavors': ['small-system', 'standard-system', 'large-system']
        }