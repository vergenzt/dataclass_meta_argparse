from typing import Callable, Concatenate, ParamSpec, TypeVar


Self = TypeVar('Self')
Params = ParamSpec('Params')
Return = TypeVar('Return')

InstanceMethod = Callable[Concatenate[Self, Params], Return]
DelayedInstanceMethod = Callable[Params, Callable[Concatenate[Self, Params], Return]]


def partial_instance_method(
    source_fn: InstanceMethod[Self, Params, Return],
) -> DelayedInstanceMethod[Params, Self, Return]:
    def outer(*outer_args: Params.args, **outer_kwargs: Params.kwargs) -> Callable[Concatenate[Self, Params], Return]:
        def inner(self: Self, *_args: Params.args, **kwargs: Params.kwargs) -> Return:
            assert not _args, 'Only kwargs can be supplied to results of _partial_instance_method'
            return source_fn(self, *outer_args, *_args, **outer_kwargs, **kwargs)

        return inner

    return outer
