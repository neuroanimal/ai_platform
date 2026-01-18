"""
Path Query Module - JSONPath, JSONPathExt, and XPath support
"""
import json
import xml.etree.ElementTree as ET
from typing import Any, List, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum
import re

try:
    import jsonpath_ng
    from jsonpath_ng import parse as jsonpath_parse
    from jsonpath_ng.ext import parse as jsonpath_ext_parse
    JSONPATH_AVAILABLE = True
except ImportError:
    JSONPATH_AVAILABLE = False

try:
    import lxml.etree as lxml_ET
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

class QueryType(Enum):
    JSONPATH = "jsonpath"
    JSONPATH_EXT = "jsonpath_ext"
    XPATH = "xpath"

@dataclass
class QueryResult:
    success: bool
    results: List[Any]
    query: str
    query_type: QueryType
    error: Optional[str] = None
    metadata: Optional[Dict] = None

class PathQueryProcessor:
    """Universal path query processor for JSON and XML data"""
    
    def __init__(self):
        self.jsonpath_cache = {}
        self.xpath_cache = {}
    
    def query_json(self, data: Union[Dict, List, str], query: str, 
                   query_type: QueryType = QueryType.JSONPATH) -> QueryResult:
        """Query JSON data using JSONPath or JSONPathExt"""
        
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                return QueryResult(False, [], query, query_type, f"Invalid JSON: {e}")
        
        try:
            if query_type == QueryType.JSONPATH:
                return self._query_jsonpath(data, query)
            elif query_type == QueryType.JSONPATH_EXT:
                return self._query_jsonpath_ext(data, query)
            else:
                return QueryResult(False, [], query, query_type, f"Invalid query type for JSON: {query_type}")
        except Exception as e:
            return QueryResult(False, [], query, query_type, str(e))
    
    def query_xml(self, data: Union[ET.Element, str], query: str) -> QueryResult:
        """Query XML data using XPath"""
        
        if isinstance(data, str):
            try:
                data = ET.fromstring(data)
            except ET.ParseError as e:
                return QueryResult(False, [], query, QueryType.XPATH, f"Invalid XML: {e}")
        
        try:
            return self._query_xpath(data, query)
        except Exception as e:
            return QueryResult(False, [], query, QueryType.XPATH, str(e))
    
    def _query_jsonpath(self, data: Any, query: str) -> QueryResult:
        """Execute JSONPath query"""
        if not JSONPATH_AVAILABLE:
            return QueryResult(False, [], query, QueryType.JSONPATH, 
                             "jsonpath-ng library not available")
        
        # Use cached parser if available
        if query not in self.jsonpath_cache:
            try:
                self.jsonpath_cache[query] = jsonpath_parse(query)
            except Exception as e:
                return QueryResult(False, [], query, QueryType.JSONPATH, f"Invalid JSONPath: {e}")
        
        parser = self.jsonpath_cache[query]
        matches = parser.find(data)
        
        results = [match.value for match in matches]
        metadata = {
            'match_count': len(matches),
            'paths': [str(match.full_path) for match in matches]
        }
        
        return QueryResult(True, results, query, QueryType.JSONPATH, metadata=metadata)
    
    def _query_jsonpath_ext(self, data: Any, query: str) -> QueryResult:
        """Execute JSONPath Extended query"""
        if not JSONPATH_AVAILABLE:
            return QueryResult(False, [], query, QueryType.JSONPATH_EXT, 
                             "jsonpath-ng library not available")
        
        # Use cached parser if available
        cache_key = f"ext_{query}"
        if cache_key not in self.jsonpath_cache:
            try:
                self.jsonpath_cache[cache_key] = jsonpath_ext_parse(query)
            except Exception as e:
                return QueryResult(False, [], query, QueryType.JSONPATH_EXT, f"Invalid JSONPath Extended: {e}")
        
        parser = self.jsonpath_cache[cache_key]
        matches = parser.find(data)
        
        results = [match.value for match in matches]
        metadata = {
            'match_count': len(matches),
            'paths': [str(match.full_path) for match in matches]
        }
        
        return QueryResult(True, results, query, QueryType.JSONPATH_EXT, metadata=metadata)
    
    def _query_xpath(self, element: ET.Element, query: str) -> QueryResult:
        """Execute XPath query"""
        try:
            # Handle namespaces if present
            namespaces = self._extract_namespaces(element)
            
            if LXML_AVAILABLE:
                # Use lxml for better XPath support
                lxml_element = lxml_ET.fromstring(ET.tostring(element))
                results = lxml_element.xpath(query, namespaces=namespaces)
            else:
                # Use standard library (limited XPath support)
                results = element.findall(query, namespaces)
            
            # Convert results to serializable format
            serialized_results = []
            for result in results:
                if hasattr(result, 'tag'):  # Element
                    serialized_results.append({
                        'tag': result.tag,
                        'text': result.text,
                        'attrib': result.attrib,
                        'xml': ET.tostring(result, encoding='unicode')
                    })
                elif hasattr(result, 'strip'):  # Text
                    serialized_results.append(result)
                else:  # Other types
                    serialized_results.append(str(result))
            
            metadata = {
                'match_count': len(results),
                'namespaces': namespaces,
                'xpath_engine': 'lxml' if LXML_AVAILABLE else 'stdlib'
            }
            
            return QueryResult(True, serialized_results, query, QueryType.XPATH, metadata=metadata)
            
        except Exception as e:
            return QueryResult(False, [], query, QueryType.XPATH, str(e))
    
    def _extract_namespaces(self, element: ET.Element) -> Dict[str, str]:
        """Extract namespaces from XML element"""
        namespaces = {}
        
        # Get namespaces from root element
        for prefix, uri in element.attrib.items():
            if prefix.startswith('xmlns'):
                if ':' in prefix:
                    ns_prefix = prefix.split(':', 1)[1]
                else:
                    ns_prefix = ''
                namespaces[ns_prefix] = uri
        
        # Extract from tag if it contains namespace
        if '}' in element.tag:
            uri, tag = element.tag[1:].split('}', 1)
            if 'default' not in namespaces:
                namespaces['default'] = uri
        
        return namespaces
    
    def batch_query(self, data: Any, queries: List[Dict[str, Any]]) -> List[QueryResult]:
        """Execute multiple queries on the same data"""
        results = []
        
        for query_info in queries:
            query = query_info['query']
            query_type = QueryType(query_info.get('type', 'jsonpath'))
            
            if query_type in [QueryType.JSONPATH, QueryType.JSONPATH_EXT]:
                result = self.query_json(data, query, query_type)
            else:
                result = self.query_xml(data, query)
            
            results.append(result)
        
        return results
    
    def build_jsonpath_from_keys(self, keys: List[str]) -> str:
        """Build JSONPath expression from list of keys"""
        if not keys:
            return "$"
        
        path_parts = ["$"]
        for key in keys:
            if key.isdigit():
                path_parts.append(f"[{key}]")
            elif self._is_valid_identifier(key):
                path_parts.append(f".{key}")
            else:
                path_parts.append(f"['{key}']")
        
        return "".join(path_parts)
    
    def build_xpath_from_path(self, path_elements: List[str]) -> str:
        """Build XPath expression from list of path elements"""
        if not path_elements:
            return "/"
        
        xpath_parts = []
        for element in path_elements:
            if element.startswith('@'):
                xpath_parts.append(element)  # Attribute
            elif '[' in element and ']' in element:
                xpath_parts.append(element)  # Element with predicate
            else:
                xpath_parts.append(element)  # Simple element
        
        return "/" + "/".join(xpath_parts)
    
    def _is_valid_identifier(self, key: str) -> bool:
        """Check if key is a valid identifier for dot notation"""
        return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key) is not None
    
    def extract_values_by_pattern(self, data: Any, pattern: str, 
                                 data_type: str = 'json') -> QueryResult:
        """Extract values matching a pattern"""
        
        if data_type == 'json':
            # Convert pattern to JSONPath if needed
            if not pattern.startswith('$'):
                pattern = f"$..{pattern}"
            return self.query_json(data, pattern, QueryType.JSONPATH_EXT)
        else:
            # Convert pattern to XPath if needed
            if not pattern.startswith('/'):
                pattern = f"//{pattern}"
            return self.query_xml(data, pattern)
    
    def find_all_paths(self, data: Any, data_type: str = 'json') -> List[str]:
        """Find all possible paths in the data structure"""
        paths = []
        
        if data_type == 'json':
            self._collect_json_paths(data, "$", paths)
        else:
            self._collect_xml_paths(data, "/", paths)
        
        return paths
    
    def _collect_json_paths(self, data: Any, current_path: str, paths: List[str]):
        """Recursively collect all JSON paths"""
        paths.append(current_path)
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{current_path}.{key}" if current_path != "$" else f"$.{key}"
                self._collect_json_paths(value, new_path, paths)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_path = f"{current_path}[{i}]"
                self._collect_json_paths(item, new_path, paths)
    
    def _collect_xml_paths(self, element: ET.Element, current_path: str, paths: List[str]):
        """Recursively collect all XML paths"""
        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        new_path = f"{current_path}/{tag_name}" if current_path != "/" else f"/{tag_name}"
        paths.append(new_path)
        
        # Add attribute paths
        for attr_name in element.attrib:
            attr_path = f"{new_path}/@{attr_name}"
            paths.append(attr_path)
        
        # Recurse into children
        for child in element:
            self._collect_xml_paths(child, new_path, paths)
    
    def validate_query_syntax(self, query: str, query_type: QueryType) -> QueryResult:
        """Validate query syntax without executing"""
        try:
            if query_type == QueryType.JSONPATH:
                if JSONPATH_AVAILABLE:
                    jsonpath_parse(query)
                    return QueryResult(True, [], query, query_type, 
                                     metadata={'syntax': 'valid'})
                else:
                    return QueryResult(False, [], query, query_type, 
                                     "jsonpath-ng library not available")
            
            elif query_type == QueryType.JSONPATH_EXT:
                if JSONPATH_AVAILABLE:
                    jsonpath_ext_parse(query)
                    return QueryResult(True, [], query, query_type, 
                                     metadata={'syntax': 'valid'})
                else:
                    return QueryResult(False, [], query, query_type, 
                                     "jsonpath-ng library not available")
            
            elif query_type == QueryType.XPATH:
                # Basic XPath syntax validation
                if self._validate_xpath_syntax(query):
                    return QueryResult(True, [], query, query_type, 
                                     metadata={'syntax': 'valid'})
                else:
                    return QueryResult(False, [], query, query_type, 
                                     "Invalid XPath syntax")
            
            else:
                return QueryResult(False, [], query, query_type, 
                                 f"Unknown query type: {query_type}")
        
        except Exception as e:
            return QueryResult(False, [], query, query_type, f"Syntax error: {e}")
    
    def _validate_xpath_syntax(self, xpath: str) -> bool:
        """Basic XPath syntax validation"""
        # Check for balanced brackets
        if xpath.count('[') != xpath.count(']'):
            return False
        
        # Check for balanced parentheses
        if xpath.count('(') != xpath.count(')'):
            return False
        
        # Check for valid XPath characters
        invalid_chars = ['<', '>', '&']
        if any(char in xpath for char in invalid_chars):
            return False
        
        return True