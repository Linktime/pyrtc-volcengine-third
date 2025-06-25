from enum import Enum

class BaseEnum(Enum):
    def __new__(cls, value, name_zh=None, desc=None):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.name_zh = name_zh
        obj.desc = desc
        return obj
    
    @classmethod
    def all(cls):
        return list(cls._value2member_map_.keys())
    
    @classmethod
    def contains(cls, value):
        return value in cls._value2member_map_.keys()
    
    @classmethod
    def get_enums(cls):
        return cls.__members__.values()
    
    @classmethod
    def get_name_zh(cls, value):
        for member in cls.__members__.values():
            if member.value == value:
                return member.name_zh
        return None  # 如果没有找到匹配的值，返回None
    
    @classmethod
    def get_value_by_name_zh(cls, name_zh):
        for member in cls.__members__.values():
            if member.name_zh == name_zh:
                return member.value
        return None  # 如果没有找到匹配的描述，返回None