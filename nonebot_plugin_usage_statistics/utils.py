from typing import Type


def get_cls_fullname(cls: Type) -> str:
    module = cls.__module__
    if module == 'builtins':
        return cls.__qualname__  # avoid outputs like 'builtins.str'
    return module + '.' + cls.__qualname__
