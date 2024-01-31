import sys
from argparse import Action, ArgumentParser, Namespace
from dataclasses import Field, fields, is_dataclass
from functools import cached_property, update_wrapper
from typing import TYPE_CHECKING, Any, Callable, Dict, List, ParamSpec, Tuple, Type, TypeVar

from .metadata import ARGS

Argument = Callable[[ArgumentParser], Action]


Params = ParamSpec('Params')
T = TypeVar('T')


def _execute_with_param_spec(_ArgumentParser: Callable[Params, ArgumentParser]):
    """
    AFAIK Python does not have a way to directly assign a ParamSpec to the parameter spec
    of a *specific* method, only a generic method passed into a function call. So this
    function definition & the following invocation lets us work around that.
    """

    class DataclassMetaArgumentParser(type):
        def __new__(
            cls,
            name: str,
            bases: Tuple[type, ...],
            namespace: Dict[str, Any],
            *_args: Params.args,
            **_kwargs: Params.kwargs,
        ):
            return super().__new__(cls, name, bases, namespace)

        def __init__(
            cls,
            name: str,
            bases: Tuple[type, ...],
            namespace: Dict[str, Any],
            *args: Params.args,
            **kwargs: Params.kwargs,
        ):
            cls._args = args
            cls._kwargs = kwargs
            super().__init__(name, bases, namespace)

        @cached_property
        def argument_parser(cls) -> ArgumentParser:
            if not (TYPE_CHECKING or is_dataclass(cls)):
                raise ValueError('dataclass_meta_argparse should only be used with dataclasses!')
            return cls.init_argument_parser(cls, *cls._args, *cls._kwargs)

        def init_argument_parser(cls, *args: Params.args, **kwargs: Params.kwargs) -> ArgumentParser:
            cls.argument_parser = cls.init_argument_parser(*args, **kwargs)
            for field in fields(cls):  # type: ignore[arg-type]
                cls.init_field(cls.argument_parser, field)
            return cls.argument_parser

        def init_field(cls, parser: ArgumentParser, field: Field[Any]) -> List[Action]:
            return [cls.init_argument(parser, field, arg) for arg in field.metadata[ARGS]]

        def init_argument(cls, parser: ArgumentParser, field: Field[Any], arg: Argument) -> Action:
            return arg(parser, dest=field.name)  # type: ignore

        def from_sys_args(cls):
            """
            Returns an instance of the wrapped dataclass from parsed system arguments.
            """
            return cls.from_args(sys.argv[1:])

        def from_args(cls, argv: List[str]):
            """
            Returns an instance of the wrapped dataclass from the parsed arguments.
            """
            parser = cls.argument_parser
            args_ns: Namespace = parser.parse_args(argv)
            args = cls(**args_ns.__dict__)
            return args

    class DataclassMetaArgumentParserPlugin(metaclass=DataclassMetaArgumentParser):
        def __new__(cls, *a, **kw) -> None:  # type: ignore
            if cls is DataclassMetaArgumentParserPlugin:
                raise ValueError(f'{cls.__name__}s should not be instantiated!')
            object.__new__(cls, *a, **kw)

    def dataclass_meta_argument_parser(
        plugins: Tuple[Type[DataclassMetaArgumentParserPlugin], ...] = (),
        *args: Params.args,
        **kwargs: Params.kwargs,
    ) -> DataclassMetaArgumentParser:
        """
        Wraps a `dataclass` definition to add convenience methods for populating from command line arguments.
        """

        def wrapper_generator(cls: Type[T]) -> Type[T]:
            if not is_dataclass(cls):
                raise ValueError(f'Class is not a dataclass: {cls}')

            wrapper = DataclassMetaArgumentParser(cls.__name__, (cls, *plugins), {}, *args, **kwargs)

            update_wrapper(wrapper, cls, updated=[])
            return wrapper  # type: ignore

        return wrapper_generator

    return (
        DataclassMetaArgumentParser,
        DataclassMetaArgumentParserPlugin,
        dataclass_meta_argument_parser,
    )


(
    DataclassMetaArgumentParser,
    DataclassMetaArgumentParserPlugin,
    dataclass_meta_argument_parser,
) = _execute_with_param_spec(ArgumentParser)
