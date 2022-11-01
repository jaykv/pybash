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
            # execed--
            # >ls -la
            parsed_line = shlex.split(token.line)
            command = get_bash_command(parsed_line)
            token.string = build_subprocess_list_cmd("run", command) + '\n'         
            new_tokens.append(token)        
        elif '= >' in token.line:
            # variabilized--
            # a = >cat test.txt
            parsed_line = shlex.split(token.line)
            start_index = get_start_index(parsed_line)
            command = get_bash_command(parsed_line, start_index=start_index)
            token.string = ' '.join(parsed_line[:start_index])
            token.string += build_subprocess_list_cmd("check_output", command) + '\n'
            new_tokens.append(token)
        elif '(>' in token.line:
            # wrapped--
            # print(>cat test.txt)
            parsed_line = shlex.split(token.line)
            start_index = get_start_index(parsed_line)
            command = get_bash_command(parsed_line, start_index=start_index, wrapped=True)
            par_count = parsed_line[start_index].count('(')
            token.string = ' '.join(parsed_line[:start_index]) + parsed_line[start_index][:parsed_line[start_index].index('>')]
            token.string += build_subprocess_list_cmd("check_output", command) + (')' * par_count) + '\n'
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

def get_bash_command(parsed_line: list, start_index: int=None, wrapped: bool=None) -> list:
    """Parses line to bash command

    Args:
        parsed_line (list): line to parse
        start_index (int, optional): index to start parsing command from. Defaults to None.
        wrapped (bool, optional): input is surrounded by parentheses
        
    Returns:
        list: parsed command list
    """
    # find which arg index the > is at
    if not start_index:
        start_index = get_start_index(parsed_line)
        
    # strip everything before that index-- not part of the command
    command = parsed_line[start_index:]
    
    # > may be at the beginning or somewhere in the middle of this arg
    # examples: >ls, print(>cat => strip up to and including >
    command[0] = command[0][command[0].index('>')+1:]
    
    # pop all consecutive end parentheses if wrapped-- not part of the command
    if wrapped:
        while command[-1][-1] == ')':
            command[-1] = command[-1][:-1]
        
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
    command += ")"
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
    command += ")"
    return command
