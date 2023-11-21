from argparse import ArgumentParser

from .type_utils import partial_instance_method


argparse_argument = partial_instance_method(ArgumentParser.add_argument)
argparse_argument.__doc__ = '''
    Specification for an `ArgumentParser` argument, detached from any specific `ArgumentParser` instance.

    Instantiate one by calling `argparse_argument(...)` with the same arguments you would
    pass to `ArgumentParser.add_argument`.

    Exception: You should not specify a `dest`; this will be supplied to `add_argument`
    later with the name of the dataclass field whose metadata the `argparse_argument` is a
    member of.

    >>> my_arg_fn = argparse_argument('-f', '--foo', action='store_true', help='bar')
    >>> parser = ArgumentParser(prog='baz')
    >>> action = my_arg_fn(parser)
    >>> parser.print_help()
    usage: baz [-h] [-f]
    <BLANKLINE>
    options:
      -h, --help  show this help message and exit
      -f, --foo   bar
'''


ARGS = object()
ARGS.__doc__ = 'Sentinal object for use as dataclass field `metadata` key.'
