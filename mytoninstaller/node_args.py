

def get_validator_service():
    path = '/etc/systemd/system/validator.service'
    with open(path, 'r') as f:
        return f.read()
#end define


def get_node_start_command():
    service = get_validator_service()
    for line in service.split('\n'):
        if line.startswith('ExecStart'):
            return line.split('=')[1].strip()
#end define


"""
def get_node_args(command: str = None):
    if command is None:
        command = get_node_start_command()
    result = []
    key = ''
    for c in command.split(' ')[1:]:
        if c.startswith('--') or c.startswith('-'):
            if key:
                result.append([key, ''])
            key = c
        elif key:
            result.append([key, c])
            key = ''
    if key:
        result.append([key, ''])
    return result
#end define
"""


def get_node_args(command: str = None):
    if command is None:
        command = get_node_start_command()
    result = {}  # {key: [value1, value2]}
    key = ''
    for c in command.split(' ')[1:]:
        if c.startswith('--') or c.startswith('-'):
            if key:
                result[key] = result.get(key, []) + ['']
            key = c
        elif key:
            result[key] = result.get(key, []) + [c]
            key = ''
    if key:
        result[key] = result.get(key, []) + ['']
    return result
#end define

