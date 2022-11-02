import shlex

import token_utils
from ideas import import_hook


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
            pipeline_command = Pipeline(command).parse_command()
            if pipeline_command != command:
                token.string = pipeline_command + '\n'
            else:
                # no pipers
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
            raw_line = [tok for tok in token.line.split(' ') if tok]
            start_index = get_start_index(parsed_line)
            command = get_bash_command(parsed_line, start_index=start_index, wrapped=True)

            # shlex strips out single quotes and double quotes-- use raw_line for the code around the wrapped command
            token.string = ' '.join(raw_line[:start_index]) + raw_line[start_index][: raw_line[start_index].index('>')]
            token.string += (
                build_subprocess_list_cmd("check_output", command) + raw_line[-1][raw_line[-1].index(')') :] + '\n'
            )
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
    hook = import_hook.create_hook(hook_name=__name__, transform_source=transform_source, source_init=source_init)
    return hook


## UTILS ##


class Pipers:
    PIPES = ['|', '>', '>>']

    @classmethod
    def get_piper(cls, pipe: str):
        if pipe == '|':
            return cls.chain_pipe_command
        elif pipe == '>':
            return cls.chain_sredirect_command
        elif pipe == '>>':
            return cls.chain_dredirect_command
        return None

    @classmethod
    def chain_pipe_command(cls, command: list, pipeline: list, start_index: int = 0, **kwargs):
        first_idx, _ = pipeline.pop(0)
        pre_command = command[start_index:first_idx]
        cmd1 = build_subprocess_list_cmd('Popen', pre_command, stdout='subprocess.PIPE', **kwargs)

        if len(pipeline) == 0:
            ## No other pipes
            post_command = command[first_idx + 1 :]
            cmd2 = build_subprocess_list_cmd('run', post_command, stdin='cmd1.stdout')
            return f"cmd1 = {cmd1}; cmd2 = {cmd2}"

        out = f"cmd1 = {cmd1};"
        while len(pipeline) > 0:
            idx, piper = pipeline[0]
            cmd = cls.get_piper(piper)(command, pipeline, start_index=first_idx + 1, stdin="cmd1.stdout")
            out += cmd
            first_idx = idx

        return out

    @classmethod
    def chain_redirect(
        cls,
        command: list,
        pipeline: list,
        start_index: int = 0,
        fvar: str = "fout",
        fmode: str = "wb",
        chained: bool = False,
        **kwargs,
    ):
        first_idx, _ = pipeline.pop(0)
        pre_command = command[start_index:first_idx]
        filename = command[first_idx + 1 : first_idx + 2][0]

        if chained:
            # file-to-file redirection so cat from source file
            pre_command.insert(0, 'cat')

        # out to file
        fout = f'open("{filename}", "{fmode}")'
        cmd1 = build_subprocess_list_cmd("run", pre_command, stdout=fvar, **kwargs)

        if len(pipeline) == 0:
            return f"{fvar} = {fout}; cmd1 = {cmd1}"

        out = f"{fvar} = {fout}; cmd1 = {cmd1};"
        while len(pipeline) > 0:
            idx, piper = pipeline[0]
            fvar = f"fout{idx}"
            if piper in ['>', '>>']:
                cmd = cls.get_piper(piper)(command, pipeline, start_index=first_idx + 1, fvar=fvar, chained=True)
            else:
                cmd = cls.get_piper(piper)(command, pipeline, start_index=first_idx + 1, stdin=fvar)
            out += cmd
            first_idx = idx

        return out

    @classmethod
    def chain_sredirect_command(
        cls, command: list, pipeline: list, start_index: int = 0, fvar: str = "fout", chained: bool = False, **kwargs
    ):
        return cls.chain_redirect(command, pipeline, start_index, fmode="wb", fvar=fvar, chained=chained, **kwargs)

    @classmethod
    def chain_dredirect_command(
        cls, command: list, pipeline: list, start_index: int = 0, fvar: str = "fout", chained: bool = False, **kwargs
    ):
        return cls.chain_redirect(command, pipeline, start_index, fmode="ab", fvar=fvar, chained=chained, **kwargs)


class Pipeline:
    __slots__ = ['command', 'pipeline']

    def __init__(self, command: list):
        self.command = command
        self.pipeline = [(i, arg) for i, arg in enumerate(self.command) if arg in Pipers.PIPES]

    def parse_command(self):
        if not self.pipeline:
            return self.command

        _, first_piper = self.pipeline[0]
        return Pipers.get_piper(first_piper)(self.command, self.pipeline)


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


def get_bash_command(parsed_line: list, start_index: int = None, wrapped: bool = None) -> list:
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
    command[0] = command[0][command[0].index('>') + 1 :].strip()

    # remove everything after and including first )- not part of the command
    if wrapped:
        if ')' not in command[-1]:
            raise SyntaxError("Missing end parentheses")

        command[-1] = command[-1][: command[-1].index(')')]

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
    command = command[:-1]
    command += ']'
    if kwargs:
        for k, v in kwargs.items():
            command += f", {k}={v}"
    command += ")"
    return command
