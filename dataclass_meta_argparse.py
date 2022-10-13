from functools import partial, partialmethod
import os
import re
import sys
from abc import ABC, abstractmethod
from argparse import Action, ArgumentParser, HelpFormatter
from dataclasses import dataclass, field, fields
from logging import debug
from typing import Callable, ClassVar, Dict, Iterator, List, Tuple, Type, Union

from trycast import isassignable


ARGSPEC_KEY: object = object()


class ArgSpec(partial):
  '''
  An ArgSpec is a saved set of arguments to `ArgumentParser.add_argument`, for later
  application to a specific ArgumentParser instance.

  Instantiate one by calling `ArgSpec(...)` with the same arguments you would use
  on `ArgumentParser.add_argument`.
  
  Exception: You should not specify a `dest`; this will be supplied to `add_argument` as
  a `kwarg` with the name of the dataclass field the argument is assigned to.
  '''
  func = partial(partialmethod, ArgumentParser.add_argument)


class _DataclassArgumentParserMeta(type['DataclassArgumentParser']):
  def __new__(cls, clsname, bases, dct, **parser_init_kws):
    self = super().__new__(cls, clsname, bases, dct)
    self._argumentparser_kwargs = parser_init_kws


@dataclass
class DataclassArgumentParser(metaclass=_DataclassArgumentParserMeta):
  """
  Base class to help build ArgumentParsers out of dataclass metadata.

  To use:

   1. Create a dataclass that inherits this class whose fields you'd like to populate
      from `argparse.ArgumentParser` arguments. Declare those fields using
      `dataclasses.field`. 

   2. Configure command line arguments to populate a dataclass field by setting
      `ARGSPEC_KEY` on its `metadata` dict to a list of `ArgSpec`s -- which are essentially
      `functools.partial`'s on `ArgumentParser.add_argument`.

      Note: You should not use the `dest` keyword arg in your `ArgSpec`s, as this class
      specifies the name of the dataclass field as the argument destination via an
      additional `dest` kwarg.

  Example:

    >>> @dataclass
    ... class MyCliArgs(metaclass=CliArgsBase, prog='my_cli.py'):
    ...   'My CLI app that does a thing'
    ...
    ...   my_arg: int = field(metadata={
    ...     ARGSPEC_KEY: [ArgSpec(
    ...       '--myarg', '-m',
    ...       metavar='INT',
    ...       type=int,
    ...       default=5,
    ...       help='my integer argument',
    ...     )],
    ...   })
    ...
    ...   remainder: List[str] = field(metadata={
    ...     ARGSPEC_KEY: [ArgSpec(
    ...       nargs=argparse.ZERO_OR_MORE,
    ...       metavar='STR',
    ...       help='remaining string arguments',
    ...     )],
    ...   })
    
    >>> MyCliArgs.parse('foo', 'bar', '--myarg', '7', 'baz')
    MyCliArgs(my_arg=7, remainder=['foo', 'bar', 'baz'])

    >>> MyCliArgs._get_argument_parser().format_help()
    'usage: myprogram.py [-h] [--foo FOO]

    options:
    -h, --help  show this help message and exit
    --foo FOO   foo help
  """

  _argumentparser_kwargs: ClassVar[Dict] = field(default_factory=dict, kw_only=True)

  @classmethod
  def parser(cls) -> ArgumentParser:
    parser = ArgumentParser(description=cls.__doc__, **cls._argumentparser_kwargs)
    [
      add_arg_fn(parser, dest=field.name)
      for field in fields(cls) 
      for add_arg_fn in field.metadata[ARGSPEC_KEY]
    ]
    return parser

  @staticmethod
  def _envize_string(s: str, keep_case: Union[bool, Callable[[str],bool]] = False) -> str:
    subbed = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_')
    return subbed if (keep_case is True or callable(keep_case) and keep_case(subbed)) else subbed.upper()

  @classmethod
  def _arguments_from_env(cls, parser: ArgumentParser) -> Iterator[str]:

    envized_opts: Dict[str, str] = {
      cls._envize_string(opt, keep_case=lambda s: len(s) == 1): opt
      for opt in parser._option_string_actions.keys()
    }

    for envvar, envvar_val in sorted(os.environ.items()):
      if not envvar.startswith(cls._ENVVAR_PREFIX) or not envvar_val:
        continue

      if not (match := re.match(cls._ENVVAR_RE, envvar)):
        raise ValueError(f'Envvar {envvar}: Could not parse. Should match {repr(cls._ENVVAR_RE)}.')

      if (_envized_opt := match['envized_opt']) not in envized_opts:
        raise ValueError(f'Envvar {envvar}: Unrecognized option {repr(_envized_opt)}. Must be one of {envized_opts.keys()}.')

      opt = envized_opts[_envized_opt]
      action = parser._option_string_actions[opt]

      extra_args = [opt] + ([envvar_val] if action.nargs is None or action.nargs else [])
      debug(f'Extra args from env var {envvar}: {extra_args}')
      yield from extra_args

  @classmethod
  def parse(cls: Type['DataclassArgumentParser'], argv: List[str] = sys.argv[1:]) -> Tuple['DataclassArgumentParser', ArgumentParser]:
    parser = cls.parser()
    cmd = cls._get_command(argv)
    argv = list(cls._arguments_from_env(parser, cmd)) + argv
    args_namespace = parser.parse_args(argv)
    args = cls(**args_namespace.__dict__)
    return args, parser

  def __post_init__(self):
    for field in fields(self):
      assert isassignable(val := getattr(self, field.name), field.type), f'{field.name} {val} should be a {field.type}!'
