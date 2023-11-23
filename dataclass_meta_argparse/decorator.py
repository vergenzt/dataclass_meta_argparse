import os
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import Field, dataclass, fields
from functools import update_wrapper
from logging import debug
from typing import Any, Callable, ClassVar, Dict, List, Mapping, Optional, ParamSpec, Protocol, Type, TypeVar

from .metadata import ARGS
from .str_utils import default_envize_string


# based on typeshed: https://github.com/python/typeshed/pull/9362
class _DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


ArgumentParserParams = ParamSpec('ArgumentParserParams')
DataclassType = TypeVar('DataclassType', bound=Type[_DataclassProtocol])


# AFAIK Python does not have a way to directly assign a ParamSpec to the parameter spec
# of a *specific* method, only a generic method passed into a function call. So this
# function definition & the following invocation lets us work around that.
def _param_spec_scope_container(ArgumentParserCallable: Callable[ArgumentParserParams, ArgumentParser]):
    def argument_parser_from_dataclass_meta(
        include_env: bool = True,
        env_prefix: Optional[str] = None,
        envize_str_fn: Callable[[str], str] = default_envize_string,
        validate_field_types: bool = False,
        *args: ArgumentParserParams.args,
        **kwargs: ArgumentParserParams.kwargs,
    ):
        """
        Wraps a `dataclass` definition to add convenience methods for populating from command line arguments.
        """

        def wrapper_generator(cls: DataclassType) -> DataclassType:
            @dataclass
            class wrapper(cls):
                argument_parser: ClassVar[ArgumentParser] = ArgumentParser(*args, **kwargs)

                # populate argument_parser at class definition time
                for field in fields(cls):
                    for add_arg_fn in field.metadata[ARGS]:
                        add_arg_fn(argument_parser, dest=field.name)

                def __post_init__(self):
                    if validate_field_types:
                        self._validate_types()

                def _validate_types(self):
                    from trycast import isassignable

                    for field in fields(self):
                        field_val = getattr(self, field.name)
                        assert isassignable(
                            field_val, field.type
                        ), f'{field.name} {field_val} should be a {field.type}!'

                @classmethod
                def _extra_args_from_env(cls, env: Mapping[str, str] = os.environ) -> List[str]:
                    parser = cls.argument_parser
                    prefix: str = env_prefix or envize_str_fn(parser.prog)

                    envized_opts: Dict[str, str] = {
                        envize_str_fn(opt): opt for opt in parser._option_string_actions.keys()
                    }

                    extra_args: List[str] = []
                    for envvar, envvar_val in env.items():
                        if not envvar.startswith(prefix + '_') or not envvar_val:
                            continue

                        envized_opt = envvar[len(prefix) + 1 :]
                        if envized_opt not in envized_opts:
                            raise ValueError(
                                f'Envvar {envvar}: Unrecognized option {repr(envized_opt)}. Must be one of {set(envized_opts.keys())}.'
                            )

                        opt = envized_opts[envized_opt]
                        action = parser._option_string_actions[opt]

                        extra_arg = [opt] + ([envvar_val] if action.nargs is None or action.nargs else [])
                        extra_args = extra_arg + extra_args  # prepend

                        debug(f'Extra arg from env var {envvar}: {extra_arg}')

                    return extra_args

                @classmethod
                def from_args(cls, argv: Optional[List[str]] = None) -> 'wrapper':
                    """
                    Returns an instance of the wrapped dataclass from the parsed arguments.
                    """

                    if argv is None:
                        argv = (cls._extra_args_from_env() if include_env else []) + sys.argv[1:]

                    parser = cls.argument_parser
                    args_ns: Namespace = parser.parse_args(argv)
                    args = cls(**args_ns.__dict__)
                    return args

            update_wrapper(wrapper, cls, updated=[])
            return wrapper

        return wrapper_generator

    return argument_parser_from_dataclass_meta


argument_parser_from_dataclass_meta = _param_spec_scope_container(ArgumentParser)
