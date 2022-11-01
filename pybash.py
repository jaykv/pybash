from ideas import import_hook
import token_utils

def transform_source(source, **_kwargs):
    """Convert >bash commands to subprocess calls"""
    new_tokens = []
    for tokens in token_utils.get_lines(source):
        token = token_utils.get_first(tokens)
        
        if token == ">":
            command = [tok for tok in token.line.split(' ') if tok]
            command[0] = command[0][1:]
            command[-1] = command[-1][:-1]
            
            token.string = 'subprocess.run(['
            for cmd in command:
                token.string += '\"' + cmd + '\",'
            token.string += '])\n'
            
            new_tokens.append(token)
        else:
            new_tokens.extend(tokens)
            
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

