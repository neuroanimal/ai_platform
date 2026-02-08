"""
NETCONF XML Processing Module
Handles NETCONF RPC calls, delimiters, and specialized XML processing
"""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

class NetconfOperation(Enum):
    GET = "get"
    GET_CONFIG = "get-config"
    EDIT_CONFIG = "edit-config"
    COPY_CONFIG = "copy-config"
    DELETE_CONFIG = "delete-config"
    LOCK = "lock"
    UNLOCK = "unlock"
    CLOSE_SESSION = "close-session"
    KILL_SESSION = "kill-session"
    COMMIT = "commit"
    DISCARD_CHANGES = "discard-changes"
    VALIDATE = "validate"

@dataclass
class NetconfMessage:
    message_id: Optional[str]
    operation: Optional[NetconfOperation]
    content: ET.Element
    raw_xml: str
    is_rpc: bool
    is_reply: bool
    error: Optional[str] = None

@dataclass
class NetconfSession:
    messages: List[NetconfMessage]
    capabilities: List[str]
    session_id: Optional[str] = None
    protocol_version: str = "1.0"

class NetconfXMLProcessor:
    """Processor for NETCONF XML messages and sessions"""

    def __init__(self):
        self.netconf_namespace = "urn:ietf:params:xml:ns:netconf:base:1.0"
        self.netconf_delimiters = {
            "1.0": "]]>]]>",
            "1.1": "\n##\n"
        }

        self.operation_mapping = {
            'get': NetconfOperation.GET,
            'get-config': NetconfOperation.GET_CONFIG,
            'edit-config': NetconfOperation.EDIT_CONFIG,
            'copy-config': NetconfOperation.COPY_CONFIG,
            'delete-config': NetconfOperation.DELETE_CONFIG,
            'lock': NetconfOperation.LOCK,
            'unlock': NetconfOperation.UNLOCK,
            'close-session': NetconfOperation.CLOSE_SESSION,
            'kill-session': NetconfOperation.KILL_SESSION,
            'commit': NetconfOperation.COMMIT,
            'discard-changes': NetconfOperation.DISCARD_CHANGES,
            'validate': NetconfOperation.VALIDATE
        }

    def parse_netconf_session(self, session_data: str, version: str = "1.0") -> NetconfSession:
        """Parse complete NETCONF session from raw data"""

        delimiter = self.netconf_delimiters.get(version, self.netconf_delimiters["1.0"])

        # Split session into individual messages
        raw_messages = session_data.split(delimiter)
        raw_messages = [msg.strip() for msg in raw_messages if msg.strip()]

        messages = []
        capabilities = []
        session_id = None

        for raw_msg in raw_messages:
            try:
                message = self.parse_netconf_message(raw_msg)
                messages.append(message)

                # Extract capabilities from hello messages
                if self._is_hello_message(message.content):
                    msg_capabilities = self._extract_capabilities(message.content)
                    capabilities.extend(msg_capabilities)

                    # Extract session ID
                    if not session_id:
                        session_id = self._extract_session_id(message.content)

            except Exception as e:
                # Create error message for unparseable content
                error_msg = NetconfMessage(
                    message_id=None,
                    operation=None,
                    content=None,
                    raw_xml=raw_msg,
                    is_rpc=False,
                    is_reply=False,
                    error=str(e)
                )
                messages.append(error_msg)

        return NetconfSession(
            messages=messages,
            capabilities=list(set(capabilities)),
            session_id=session_id,
            protocol_version=version
        )

    def parse_netconf_message(self, xml_data: str) -> NetconfMessage:
        """Parse individual NETCONF message"""

        try:
            # Clean up XML data
            xml_data = self._clean_xml_data(xml_data)

            # Parse XML
            root = ET.fromstring(xml_data)

            # Extract message information
            message_id = root.get('message-id')
            is_rpc = root.tag.endswith('rpc')
            is_reply = root.tag.endswith('rpc-reply')

            # Determine operation
            operation = None
            if is_rpc:
                operation = self._extract_operation(root)

            return NetconfMessage(
                message_id=message_id,
                operation=operation,
                content=root,
                raw_xml=xml_data,
                is_rpc=is_rpc,
                is_reply=is_reply
            )

        except ET.ParseError as e:
            return NetconfMessage(
                message_id=None,
                operation=None,
                content=None,
                raw_xml=xml_data,
                is_rpc=False,
                is_reply=False,
                error=f"XML Parse Error: {e}"
            )

    def create_netconf_rpc(self, operation: NetconfOperation, message_id: str,
                          **kwargs) -> str:
        """Create NETCONF RPC message"""

        # Create RPC root element
        rpc = ET.Element('rpc')
        rpc.set('xmlns', self.netconf_namespace)
        rpc.set('message-id', message_id)

        # Create operation element
        op_element = ET.SubElement(rpc, operation.value)

        # Add operation-specific content
        if operation == NetconfOperation.GET_CONFIG:
            self._add_get_config_content(op_element, **kwargs)
        elif operation == NetconfOperation.EDIT_CONFIG:
            self._add_edit_config_content(op_element, **kwargs)
        elif operation == NetconfOperation.GET:
            self._add_get_content(op_element, **kwargs)
        elif operation in [NetconfOperation.LOCK, NetconfOperation.UNLOCK]:
            self._add_lock_content(op_element, **kwargs)

        return ET.tostring(rpc, encoding='unicode', xml_declaration=True)

    def create_netconf_reply(self, message_id: str, content: Optional[ET.Element] = None,
                           error: Optional[str] = None) -> str:
        """Create NETCONF RPC reply message"""

        reply = ET.Element('rpc-reply')
        reply.set('xmlns', self.netconf_namespace)
        reply.set('message-id', message_id)

        if error:
            # Create error reply
            rpc_error = ET.SubElement(reply, 'rpc-error')
            error_type = ET.SubElement(rpc_error, 'error-type')
            error_type.text = 'application'
            error_message = ET.SubElement(rpc_error, 'error-message')
            error_message.text = error
        elif content is not None:
            # Add content to reply
            reply.append(content)
        else:
            # Create OK reply
            ok = ET.SubElement(reply, 'ok')

        return ET.tostring(reply, encoding='unicode', xml_declaration=True)

    def extract_data_from_reply(self, reply_message: NetconfMessage) -> Optional[Dict[str, Any]]:
        """Extract data content from NETCONF reply"""

        if not reply_message.is_reply or reply_message.content is None:
            return None

        # Look for data element
        data_element = reply_message.content.find('.//{*}data')
        if data_element is not None:
            return self._xml_to_dict(data_element)

        # Look for config element
        config_element = reply_message.content.find('.//{*}config')
        if config_element is not None:
            return self._xml_to_dict(config_element)

        # Return entire content if no specific data element found
        return self._xml_to_dict(reply_message.content)

    def validate_netconf_message(self, message: NetconfMessage) -> List[str]:
        """Validate NETCONF message structure"""
        issues = []

        if message.error:
            issues.append(f"Parse error: {message.error}")
            return issues

        if message.content is None:
            issues.append("No XML content")
            return issues

        # Check namespace
        if not message.content.get('xmlns') == self.netconf_namespace:
            issues.append("Missing or incorrect NETCONF namespace")

        # Check message ID for RPC messages
        if message.is_rpc and not message.message_id:
            issues.append("RPC message missing message-id")

        # Validate operation-specific content
        if message.operation:
            op_issues = self._validate_operation_content(message)
            issues.extend(op_issues)

        return issues

    def format_netconf_session(self, session: NetconfSession, version: str = "1.0") -> str:
        """Format NETCONF session for transmission"""

        delimiter = self.netconf_delimiters.get(version, self.netconf_delimiters["1.0"])
        formatted_messages = []

        for message in session.messages:
            if message.raw_xml:
                formatted_messages.append(message.raw_xml + delimiter)

        return ''.join(formatted_messages)

    def _clean_xml_data(self, xml_data: str) -> str:
        """Clean XML data for parsing"""
        # Remove NETCONF delimiters
        for delimiter in self.netconf_delimiters.values():
            xml_data = xml_data.replace(delimiter, '')

        # Remove extra whitespace
        xml_data = xml_data.strip()

        # Ensure XML declaration if missing
        if not xml_data.startswith('<?xml'):
            xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data

        return xml_data

    def _extract_operation(self, rpc_element: ET.Element) -> Optional[NetconfOperation]:
        """Extract operation from RPC element"""
        for child in rpc_element:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag_name in self.operation_mapping:
                return self.operation_mapping[tag_name]
        return None

    def _is_hello_message(self, element: ET.Element) -> bool:
        """Check if message is a NETCONF hello message"""
        tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        return tag_name == 'hello'

    def _extract_capabilities(self, hello_element: ET.Element) -> List[str]:
        """Extract capabilities from hello message"""
        capabilities = []
        caps_element = hello_element.find('.//{*}capabilities')
        if caps_element is not None:
            for cap in caps_element.findall('.//{*}capability'):
                if cap.text:
                    capabilities.append(cap.text.strip())
        return capabilities

    def _extract_session_id(self, hello_element: ET.Element) -> Optional[str]:
        """Extract session ID from hello message"""
        session_id_element = hello_element.find('.//{*}session-id')
        return session_id_element.text if session_id_element is not None else None

    def _add_get_config_content(self, op_element: ET.Element, **kwargs):
        """Add get-config specific content"""
        source = kwargs.get('source', 'running')
        filter_content = kwargs.get('filter')

        # Add source
        source_elem = ET.SubElement(op_element, 'source')
        ET.SubElement(source_elem, source)

        # Add filter if provided
        if filter_content:
            filter_elem = ET.SubElement(op_element, 'filter')
            if isinstance(filter_content, str):
                filter_elem.text = filter_content
            elif isinstance(filter_content, ET.Element):
                filter_elem.append(filter_content)

    def _add_edit_config_content(self, op_element: ET.Element, **kwargs):
        """Add edit-config specific content"""
        target = kwargs.get('target', 'candidate')
        config = kwargs.get('config')
        default_operation = kwargs.get('default_operation')

        # Add target
        target_elem = ET.SubElement(op_element, 'target')
        ET.SubElement(target_elem, target)

        # Add default operation if specified
        if default_operation:
            default_op_elem = ET.SubElement(op_element, 'default-operation')
            default_op_elem.text = default_operation

        # Add config
        if config:
            config_elem = ET.SubElement(op_element, 'config')
            if isinstance(config, str):
                config_elem.text = config
            elif isinstance(config, ET.Element):
                config_elem.append(config)

    def _add_get_content(self, op_element: ET.Element, **kwargs):
        """Add get specific content"""
        filter_content = kwargs.get('filter')

        # Add filter if provided
        if filter_content:
            filter_elem = ET.SubElement(op_element, 'filter')
            if isinstance(filter_content, str):
                filter_elem.text = filter_content
            elif isinstance(filter_content, ET.Element):
                filter_elem.append(filter_content)

    def _add_lock_content(self, op_element: ET.Element, **kwargs):
        """Add lock/unlock specific content"""
        target = kwargs.get('target', 'candidate')

        # Add target
        target_elem = ET.SubElement(op_element, 'target')
        ET.SubElement(target_elem, target)

    def _validate_operation_content(self, message: NetconfMessage) -> List[str]:
        """Validate operation-specific content"""
        issues = []

        if message.operation == NetconfOperation.GET_CONFIG:
            source = message.content.find('.//{*}source')
            if source is None:
                issues.append("get-config missing source element")

        elif message.operation == NetconfOperation.EDIT_CONFIG:
            target = message.content.find('.//{*}target')
            config = message.content.find('.//{*}config')
            if target is None:
                issues.append("edit-config missing target element")
            if config is None:
                issues.append("edit-config missing config element")

        return issues

    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {}

        # Add attributes
        if element.attrib:
            result['@attributes'] = element.attrib

        # Add text content
        if element.text and element.text.strip():
            result['text'] = element.text.strip()

        # Add child elements
        for child in element:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            child_dict = self._xml_to_dict(child)

            if tag_name in result:
                # Convert to list if multiple elements with same tag
                if not isinstance(result[tag_name], list):
                    result[tag_name] = [result[tag_name]]
                result[tag_name].append(child_dict)
            else:
                result[tag_name] = child_dict

        return result