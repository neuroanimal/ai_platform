import re

def calculate_indent(line):
    # Liczymy spacje PRZED pierwszym znakiem (nawet jesli to #)
    return len(line) - len(line.lstrip(' '))

def simulate_stack_logic(yaml_lines):
    stack = []
    print(f"{'IND':<4} | {'LINE':<30} | {'BUILT PATH'}")
    print("-" * 60)

    for raw_line in yaml_lines:
        if not raw_line.strip(): continue

        indent = calculate_indent(raw_line)
        content = raw_line.lstrip().lstrip('#').strip()

        # Wyciaganie klucza
        key_match = re.search(r'^([a-zA-Z0-9_\-\.]+)\s*:', content.lstrip('- '))
        current_key = key_match.group(1) if key_match else ("[N]" if content.startswith('-') else None)

        if not current_key:
            continue

        # Zarzadzanie stosem
        while stack and stack[-1]['indent'] >= indent:
            stack.pop()

        parent_path = stack[-1]['path'] if stack else ""

        # Budowanie sciezki (uproszczone dla testu)
        if content.startswith('-') and current_key != "[N]":
            full_path = f"{parent_path}.[N].{current_key}" if parent_path else f"[N].{current_key}"
        else:
            full_path = f"{parent_path}.{current_key}" if parent_path else current_key

        full_path = full_path.strip('.')

        print(f"{indent:<4} | {raw_line.strip()[:30]:<30} | {full_path}")

        stack.append({'indent': indent, 'path': full_path})

# TWOJE DANE TESTOWE
test_yaml = [
    "global:",
    "  #fsGroup:",
    "  #  manual: 10000",
    "  #  namespace: false",
    "",
    "  cire_frn:",
    "    enabled: true",
    "    PREFIX-ports:",
    "    geode-locators:",
    "      port: 8091",
    "      protocol: TCP",
    "      targetPort: 8091",
    "      tcpkeepalive:",
    "        interval: 10",
    "        probes: 6",
    "        time: 500",
    "  annotations: {}",
    "  # proxy.istio.io/config: '{\"gatewayTopology\" : { \"numTrustedProxies\": 0 } }'",
    "",
]

simulate_stack_logic(test_yaml)

