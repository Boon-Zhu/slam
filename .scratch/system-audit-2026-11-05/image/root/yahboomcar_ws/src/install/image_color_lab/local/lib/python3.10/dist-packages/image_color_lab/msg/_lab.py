# generated from rosidl_generator_py/resource/_idl.py.em
# with input from image_color_lab:msg/Lab.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_Lab(type):
    """Metaclass of message 'Lab'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('image_color_lab')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'image_color_lab.msg.Lab')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__lab
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__lab
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__lab
            cls._TYPE_SUPPORT = module.type_support_msg__msg__lab
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__lab

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class Lab(metaclass=Metaclass_Lab):
    """Message class 'Lab'."""

    __slots__ = [
        '_l_min',
        '_a_min',
        '_b_min',
        '_l_max',
        '_a_max',
        '_b_max',
    ]

    _fields_and_field_types = {
        'l_min': 'int64',
        'a_min': 'int64',
        'b_min': 'int64',
        'l_max': 'int64',
        'a_max': 'int64',
        'b_max': 'int64',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int64'),  # noqa: E501
        rosidl_parser.definition.BasicType('int64'),  # noqa: E501
        rosidl_parser.definition.BasicType('int64'),  # noqa: E501
        rosidl_parser.definition.BasicType('int64'),  # noqa: E501
        rosidl_parser.definition.BasicType('int64'),  # noqa: E501
        rosidl_parser.definition.BasicType('int64'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.l_min = kwargs.get('l_min', int())
        self.a_min = kwargs.get('a_min', int())
        self.b_min = kwargs.get('b_min', int())
        self.l_max = kwargs.get('l_max', int())
        self.a_max = kwargs.get('a_max', int())
        self.b_max = kwargs.get('b_max', int())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.l_min != other.l_min:
            return False
        if self.a_min != other.a_min:
            return False
        if self.b_min != other.b_min:
            return False
        if self.l_max != other.l_max:
            return False
        if self.a_max != other.a_max:
            return False
        if self.b_max != other.b_max:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def l_min(self):
        """Message field 'l_min'."""
        return self._l_min

    @l_min.setter
    def l_min(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'l_min' field must be of type 'int'"
            assert value >= -9223372036854775808 and value < 9223372036854775808, \
                "The 'l_min' field must be an integer in [-9223372036854775808, 9223372036854775807]"
        self._l_min = value

    @builtins.property
    def a_min(self):
        """Message field 'a_min'."""
        return self._a_min

    @a_min.setter
    def a_min(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'a_min' field must be of type 'int'"
            assert value >= -9223372036854775808 and value < 9223372036854775808, \
                "The 'a_min' field must be an integer in [-9223372036854775808, 9223372036854775807]"
        self._a_min = value

    @builtins.property
    def b_min(self):
        """Message field 'b_min'."""
        return self._b_min

    @b_min.setter
    def b_min(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'b_min' field must be of type 'int'"
            assert value >= -9223372036854775808 and value < 9223372036854775808, \
                "The 'b_min' field must be an integer in [-9223372036854775808, 9223372036854775807]"
        self._b_min = value

    @builtins.property
    def l_max(self):
        """Message field 'l_max'."""
        return self._l_max

    @l_max.setter
    def l_max(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'l_max' field must be of type 'int'"
            assert value >= -9223372036854775808 and value < 9223372036854775808, \
                "The 'l_max' field must be an integer in [-9223372036854775808, 9223372036854775807]"
        self._l_max = value

    @builtins.property
    def a_max(self):
        """Message field 'a_max'."""
        return self._a_max

    @a_max.setter
    def a_max(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'a_max' field must be of type 'int'"
            assert value >= -9223372036854775808 and value < 9223372036854775808, \
                "The 'a_max' field must be an integer in [-9223372036854775808, 9223372036854775807]"
        self._a_max = value

    @builtins.property
    def b_max(self):
        """Message field 'b_max'."""
        return self._b_max

    @b_max.setter
    def b_max(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'b_max' field must be of type 'int'"
            assert value >= -9223372036854775808 and value < 9223372036854775808, \
                "The 'b_max' field must be an integer in [-9223372036854775808, 9223372036854775807]"
        self._b_max = value
