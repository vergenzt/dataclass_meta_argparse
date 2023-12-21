from dataclasses import fields

from trycast import isassignable

from ..decorator import DataclassProtocol


def validate_types(dataclass_inst: DataclassProtocol):
  for field in fields(dataclass_inst):
      field_val = getattr(dataclass_inst, field.name)
      assert isassignable(
          field_val, field.type
      ), f'{field.name} {field_val} should be a {field.type}!'
