from dataclasses import dataclass, field

from dataclass_meta_argparse import dataclass_meta_argument_parser, argparse_argument, ARGS
from dataclass_meta_argparse.plugins.args_from_env import ArgsFromEnv
from ..dataclass_meta_argparse.plugins.type_validation import ValidateTypes


@dataclass_meta_argument_parser(
  plugins=(ArgsFromEnv, ValidateTypes),
  prog='basic-cli',
)
@dataclass
class BasicCli:
  pass
  verbosity: int = field(metadata={
    ARGS: [
      argparse_argument('-v', '--verbose', action=argparse.)
    ]
  })
  foo: str = field(metadata={
    ARGS: [argparse_argument('foo')]
  })
  bar: str = field(metadata={
    ARGS: [argparse_argument('foo')]
  })
