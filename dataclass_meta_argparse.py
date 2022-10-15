r'''
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

>>> @argument_parser_from_dataclass_meta(prog='my-cli')
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
'''

import argparse
import os
import re
import sys
from argparse import Action, ArgumentParser, Namespace
from dataclasses import asdict, dataclass, field, fields
from functools import partial, partialmethod, wraps
from logging import debug
from typing import (
    Any,
    Callable,
    ClassVar,
    Concatenate,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    ParamSpec,
    Type,
    TypeAlias,
    TypeVar,
    Union
)
from wsgiref import validate


Self = TypeVar('Self', bound=ArgumentParser)
P = ParamSpec('P')
R = TypeVar('R', ArgumentParser, Action)


def _partial_instance_method(source_fn: Callable[Concatenate[Self, P], R]) -> Callable[P, Callable[[Self], R]]:
    def outer(*outer_args: P.args, **outer_kwargs: P.kwargs) -> Callable[[Self], R]:
        def inner(self: Self, **kwargs) -> R:
            return source_fn(self, *outer_args, **outer_kwargs, **kwargs)
        return inner
    return outer


argparse_argument: Callable[..., Callable[[ArgumentParser], Action]]
argparse_argument = _partial_instance_method(ArgumentParser.add_argument)
argparse_argument.__doc__ = '''
    An `argparse_argument` is a saved set of arguments to `ArgumentParser.add_argument`, for
    later application to a specific `ArgumentParser` instance.

    Instantiate one by calling `argparse_argument(...)` with the same arguments you would
    give to the `add_argument` method of an `ArgumentParser` instance.

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


def default_envize_string(s: str, keep_case: Union[bool, Callable[[str], bool]] = lambda s: len(s) == 1) -> str:
    subbed = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_')
    return subbed if (keep_case is True or callable(keep_case) and keep_case(subbed)) else subbed.upper()


ArgumentParserT = TypeVar('ArgumentParserT', bound=ArgumentParser)
ArgumentParserP = ParamSpec('ArgumentParserP')
T = TypeVar('T')

def _param_spec_scope_container(ArgumentParser: Callable[ArgumentParserP, ArgumentParserT]):

    def argument_parser_from_dataclass_meta(
        include_env: bool = True,
        env_prefix: Optional[str] = None,
        envize_str_fn: Callable[[str], str] = default_envize_string,
        validate_field_types: bool = False,
        *args: ArgumentParserP.args,
        **kwargs: ArgumentParserP.kwargs,
    ):
        class _argument_parser_from_dataclass_meta_base:
            argument_parser: ArgumentParserT = ArgumentParser(*args, **kwargs)

            def __init_subclass__(cls):

                for field in fields(cls):
                    for add_arg_fn in field.metadata[ARGS]:
                        add_arg_fn(cls.argument_parser, dest=field.name)

                if validate_field_types:
                    old_post_init = getattr(cls, '__post_init__', None)

                    def new_post_init(self, *args, **kwargs):
                        self._validate_types(self)
                        if old_post_init:
                            old_post_init(self, *args, **kwargs)

                    setattr(cls, '__post_init__', new_post_init)

            @classmethod
            def _validate_types(cls, self):
                from trycast import isassignable
                for field in fields(self):
                    field_val = getattr(self, field.name)
                    assert isassignable(field_val, field.type), f'{field.name} {field_val} should be a {field.type}!'

            @classmethod
            def _extra_args_from_env(cls, env: Mapping[str, str] = os.environ) -> List[str]:
                parser = cls.argument_parser
                prefix: str = env_prefix or envize_str_fn(parser.prog)

                envized_opts: Dict[str, str] = {
                    envize_str_fn(opt): opt
                    for opt in parser._option_string_actions.keys()
                }

                extra_args: List[str] = []
                for envvar, envvar_val in env.items():
                    if not envvar.startswith(prefix + '_') or not envvar_val:
                        continue

                    envized_opt = envvar[len(prefix)+1:]
                    if envized_opt not in envized_opts:
                        raise ValueError(
                            f'Envvar {envvar}: Unrecognized option {repr(envized_opt)}. Must be one of {set(envized_opts.keys())}.')

                    opt = envized_opts[envized_opt]
                    action = parser._option_string_actions[opt]

                    extra_arg = [
                        opt] + ([envvar_val] if action.nargs is None or action.nargs else [])
                    extra_args = extra_arg + extra_args  # prepend

                    debug(f'Extra arg from env var {envvar}: {extra_arg}')

                return extra_args

            @classmethod
            def from_args(cls, argv: Optional[List[str]] = None) -> '_argument_parser_from_dataclass_meta_base':
                if argv is None:
                    argv = (cls._extra_args_from_env() if include_env else []) + sys.argv[1:]

                parser = cls.argument_parser
                args_ns: Namespace = parser.parse_args(argv)
                args = cls(**args_ns.__dict__)
                return args

        def wrapper_generator(cls: Type[T]) -> Type[T]:
            @wraps(cls, updated=[])
            class wrapper(cls, _argument_parser_from_dataclass_meta_base): # type:ignore
                pass
            return wrapper

        return wrapper_generator

    return argument_parser_from_dataclass_meta

argument_parser_from_dataclass_meta = _param_spec_scope_container(ArgumentParser)
