from dataclasses import dataclass, fields

from trycast import isassignable

from .. import DataclassMetaArgumentParserPlugin


@dataclass
class ArgTypeValidation(DataclassMetaArgumentParserPlugin):
    def __post_init__(self):
        self.validate_types()

    def validate_types(self):
        for field in fields(self):
            field_val = getattr(self, field.name)
            assert isassignable(field_val, field.type), f'{field.name} {field_val} should be a {field.type}!'
