from ideas import import_hook
import token_utils
import shlex

def transform_source(source, **_kwargs):
    """Convert >bash commands to subprocess calls"""
    new_tokens = []
    for line in token_utils.get_lines(source):
        token = token_utils.get_first(line)
        if not token:
            new_tokens.extend(line)
            continue
        
        if token == ">":
            # >ls -la
            parsed_line = shlex.split(token.line)
            command = parse_bash_command(parsed_line)
            token.string = build_subprocess_list_cmd("run", command)            
            new_tokens.append(token)        
        elif '= >' in token.line:
            # a = >cat test.txt
            parsed_line = shlex.split(token.line)
            start_index = get_start_index(parsed_line)
            command = parse_bash_command(parsed_line, start_index=start_index)
            token.string = ' '.join(parsed_line[:start_index])
            token.string += build_subprocess_list_cmd("check_output", command)
            new_tokens.append(token)
        else:
            new_tokens.extend(line)
            
    return token_utils.untokenize(new_tokens)

def source_init():
    """Adds subprocess import"""
    import_subprocess = "import subprocess"
    return import_subprocess

def add_hook(**_kwargs):
    """Creates and automatically adds the import hook in sys.meta_path"""
    hook = import_hook.create_hook(
        hook_name=__name__,
        transform_source=transform_source,
        source_init=source_init
    )
    return hook


## UTILS ##
def get_start_index(parsed_line: list) -> int:
    """Get the start index of first matching >

    Args:
        parsed_line (list): line to parse

    Returns:
        int: starting index
    """
    for i, val in enumerate(parsed_line):
        if '>' in val:
            return i

def parse_bash_command(parsed_line: list, start_index: int=None) -> list:
    """Parses line to bash command

    Args:
        parsed_line (list): line to parse
        start_index (int, optional): index to start parsing command from. Defaults to None.

    Returns:
        list: parsed command list
    """
    if not start_index:
        start_index = get_start_index(parsed_line)
        
    command = parsed_line[start_index:]
    command[0] = command[0][1:]
    return command

def build_subprocess_str_cmd(method: str, arg: str, **kwargs) -> str:
    """Builds subprocess command with string arg

    Args:
        method (str): subprocess method name
        arg (str): string arg

    Returns:
        str: subprocess command
    """
    command = f'subprocess.{method}({arg}'
    if kwargs:
        for k, v in kwargs.items():
            command += f", {k}={v}"
    command += ")\n"
    return command

def build_subprocess_list_cmd(method: str, args: list, **kwargs) -> str:
    """Builds subprocess command with list args

    Args:
        method (str): subprocess method name
        args (list): list of args

    Returns:
        str: subprocess command
    """
    command = f'subprocess.{method}(['
    for arg in args:
        command += '\"' + arg + '\",'
    command += ']'
    if kwargs:
        for k, v in kwargs.items():
            command += f", {k}={v}"
    command += ")\n"
    return command
