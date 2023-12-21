import sys
from argparse import Action, ArgumentParser, Namespace
from dataclasses import Field, dataclass, fields
from functools import update_wrapper
from typing import Any, Callable, ClassVar, List, Optional, ParamSpec, Protocol, Tuple, Type, TypeVar

from .metadata import ARGS


# based on typeshed: https://github.com/python/typeshed/pull/9362
class DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


APInitParams = ParamSpec('APInitParams')
DataclassT = TypeVar('DataclassT', bound=DataclassProtocol)


def _with_param_spec_of(_ArgumentParser: Callable[APInitParams, ArgumentParser]):
    """
    AFAIK Python does not have a way to directly assign a ParamSpec to the parameter spec
    of a *specific* method, only a generic method passed into a function call. So this
    function definition & the following invocation lets us work around that.
    """

    class Mixin(DataclassProtocol, Protocol):
        argument_parser: ClassVar[ArgumentParser]

        @classmethod
        def init_argument_parser(cls, *args: APInitParams.args, **kwargs: APInitParams.kwargs) -> ArgumentParser:
            cls.argument_parser = cls.init_argument_parser(*args, **kwargs)
            for field in fields(cls):
                cls.init_field(cls.argument_parser, field)
            return cls.argument_parser

        @classmethod
        def init_field(cls, parser: ArgumentParser, field: Field[Any]) -> List[Action]:
            return [cls.init_argument(parser, field, add_arg_fn) for add_arg_fn in field.metadata[ARGS]]

        @classmethod
        def init_argument(
            cls, parser: ArgumentParser, field: Field[Any], add_arg_fn: Callable[[ArgumentParser], Action]
        ) -> Action:
            return add_arg_fn(parser, dest=field.name)  # type: ignore

        @classmethod
        def parse_args(cls, args_str: List[str]):
            parser = cls.argument_parser
            args_ns: Namespace = parser.parse_args(args_str)
            args = cls(**args_ns.__dict__)
            return args

        @classmethod
        def from_args(cls, argv: Optional[List[str]] = None):
            """
            Returns an instance of the wrapped dataclass from the parsed arguments.
            """
            return cls.parse_args(argv if argv is not None else sys.argv[1:])

        def __init_subclass__(
            cls,
            plugins: Tuple[Type["Plugin"], ...],
            *a: APInitParams.args,
            **kw: APInitParams.kwargs,
        ) -> None:
            cls.init_argument_parser

    class Plugin(Protocol):
        argument_parser: ClassVar[ArgumentParser]

        @classmethod
        def init_argument_parser(cls: Mixin, *args: APInitParams.args, **kwargs: APInitParams.kwargs) -> ArgumentParser:
            return super().init_argument_parser(*args, **kwargs)

        @classmethod
        def init_field(cls, parser: ArgumentParser, field: Field[Any]) -> List[Action]:
            return [cls.init_argument(parser, field, add_arg_fn) for add_arg_fn in field.metadata[ARGS]]

        @classmethod
        def init_argument(
            cls, parser: ArgumentParser, field: Field[Any], add_arg_fn: Callable[[ArgumentParser], Action]
        ) -> Action:
            return add_arg_fn(parser, dest=field.name)  # type: ignore

        @classmethod
        def parse_args(cls, args_str: List[str]):
            parser = cls.argument_parser
            args_ns: Namespace = parser.parse_args(args_str)
            args = cls(**args_ns.__dict__)
            return args

    def argument_parser_from_dataclass_meta(
        plugins: Tuple[Type[Plugin], ...] = (),
        *args: APInitParams.args,
        **kwargs: APInitParams.kwargs,
    ):
        """
        Wraps a `dataclass` definition to add convenience methods for populating from command line arguments.
        """

        def wrapper_generator(cls: Type[DataclassT]) -> Type[DataclassT]:
            if '__dataclass_fields__' not in cls.__dict__:
                raise ValueError(f'Class is not a dataclass: {cls}')

            wrapper_bases: Tuple[type, ...] = (cls, Mixin)
            wrapper = type('DataclassMetaArgparseWrapper', wrapper_bases, {}, plugins=plugins)

            update_wrapper(wrapper, cls, updated=[])
            return wrapper  # type: ignore

        return wrapper_generator

    return (
        Plugin,
        Mixin,
        argument_parser_from_dataclass_meta,
    )


(
    Plugin,
    DataclassMetaArgparseMixin,
    argument_parser_from_dataclass_meta,
) = _with_param_spec_of(ArgumentParser)
