r"""
Tools to help build ArgumentParsers out of dataclass metadata.

To use:

 1. Create a dataclass whose fields you'd like to populate from `argparse` arguments,
    set its metaclass to `DataclassMetaArgumentParser`, and pass any additional `ArgumentParser`
    keyword args to the metaclass.

 2. Associate command line arguments with dataclass fields by adding lists of `argparse_arguments`
    to fields' `metadata` dicts under the `ARGS` key. (An `argparse_argument` is essentially a
    `functools.partial` on `ArgumentParser.add_argument`, but where the actual parser instance
    is added last.)

 3. Apply any additional customizations to the ArgumentParser after the class is declared through
    the class's `argument_parser` attribute.

 4. Get an instance of your dataclass from parsed command line arguments via the class's
    new `from_args` method.

Example:

>>> @dataclass_meta_argument_parser(prog='my-cli')
... @dataclass
... class MyCliArgs:
...   'My CLI app that does a thing'
...   my_arg: int = field(metadata={
...     ARGS: [argparse_argument(
...       '--myarg', '-m',
...       metavar='INT',
...       type=int,
...       default=5,
...       help='my integer argument',
...     )],
...   })
...   remainder: List[str] = field(metadata={
...     ARGS: [argparse_argument(
...       nargs=argparse.ZERO_OR_MORE,
...       metavar='STR',
...       help='remaining string arguments',
...     )],
...   })
>>> MyCliArgs.from_args(['--myarg', '7', 'foo', 'bar', 'baz'])
MyCliArgs(my_arg=7, remainder=['foo', 'bar', 'baz'])
>>> MyCliArgs.argument_parser.print_help()
usage: my-cli [-h] [--myarg INT] [STR ...]
<BLANKLINE>
positional arguments:
  STR                  remaining string arguments
<BLANKLINE>
options:
  -h, --help           show this help message and exit
  --myarg INT, -m INT  my integer argument
"""

from .decorator import dataclass_meta_argument_parser, DataclassMetaArgumentParserPlugin
from .metadata import ARGS, argparse_argument

__all__ = [
  'dataclass_meta_argument_parser',
  'DataclassMetaArgumentParserPlugin',
  'ARGS',
  'argparse_argument',
]
