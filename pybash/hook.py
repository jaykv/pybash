from ideas import import_hook

from pybash.transformer import transform


def source_init():
    """Adds subprocess import"""
    return "import subprocess"


def add_hook():
    """Creates and automatically adds the import hook in sys.meta_path"""
    return import_hook.create_hook(
        hook_name=__name__,
        transform_source=transform_source,
        source_init=source_init,
    )


def transform_source(source, **_kwargs):
    """Convert >bash commands to subprocess calls"""
    return transform(source, **_kwargs)
