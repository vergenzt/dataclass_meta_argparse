import re
from dataclasses import dataclass
from typing import Callable, Optional, Union


def default_envize_string(s: str, keep_case: Union[bool, Callable[[str], bool]] = lambda s: len(s) == 1) -> str:
    subbed = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_')
    return subbed if (keep_case is True or callable(keep_case) and keep_case(subbed)) else subbed.upper()


@dataclass
class EnvArgExtractor:
    include_env: bool = False
    env_prefix: Optional[str] = None
    envize_str_fn: Callable[[str], str] = default_envize_string

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



    .... from_args:
                if include_env:
                    argv = cls._extra_args_from_env() + argv
