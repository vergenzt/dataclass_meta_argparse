# """
# Basic CLI demo.


# """
# import argparse
# from dataclasses import dataclass, field

# from dataclass_meta_argparse import argument_parser_from_dataclass_meta, argparse_argument, ARGS


# @argument_parser_from_dataclass_meta(prog='basic')
# @dataclass
# class BasicCli:
#   verbosity: int = field(metadata={
#     ARGS: [
#       argparse_argument('-v', '--verbose', action=argparse.)
#     ]
#   })
#   foo: str = field(metadata={
#     ARGS: [argparse_argument('foo')]
#   })
#   bar: str = field(metadata={
#     ARGS: [argparse_argument('foo')]
#   })
