# generated from rosidl_generator_py/resource/_idl.py.em
# with input from yahboom_attitude_record_interfaces:srv/AttuitudeRecord.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_AttuitudeRecord_Request(type):
    """Metaclass of message 'AttuitudeRecord_Request'."""

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
            module = import_type_support('yahboom_attitude_record_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'yahboom_attitude_record_interfaces.srv.AttuitudeRecord_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__attuitude_record__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__attuitude_record__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__attuitude_record__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__attuitude_record__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__attuitude_record__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class AttuitudeRecord_Request(metaclass=Metaclass_AttuitudeRecord_Request):
    """Message class 'AttuitudeRecord_Request'."""

    __slots__ = [
        '_pitch',
        '_yaw',
    ]

    _fields_and_field_types = {
        'pitch': 'int64',
        'yaw': 'int64',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int64'),  # noqa: E501
        rosidl_parser.definition.BasicType('int64'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.pitch = kwargs.get('pitch', int())
        self.yaw = kwargs.get('yaw', int())

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
        if self.pitch != other.pitch:
            return False
        if self.yaw != other.yaw:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def pitch(self):
        """Message field 'pitch'."""
        return self._pitch

    @pitch.setter
    def pitch(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'pitch' field must be of type 'int'"
            assert value >= -9223372036854775808 and value < 9223372036854775808, \
                "The 'pitch' field must be an integer in [-9223372036854775808, 9223372036854775807]"
        self._pitch = value

    @builtins.property
    def yaw(self):
        """Message field 'yaw'."""
        return self._yaw

    @yaw.setter
    def yaw(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'yaw' field must be of type 'int'"
            assert value >= -9223372036854775808 and value < 9223372036854775808, \
                "The 'yaw' field must be an integer in [-9223372036854775808, 9223372036854775807]"
        self._yaw = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_AttuitudeRecord_Response(type):
    """Metaclass of message 'AttuitudeRecord_Response'."""

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
            module = import_type_support('yahboom_attitude_record_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'yahboom_attitude_record_interfaces.srv.AttuitudeRecord_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__attuitude_record__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__attuitude_record__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__attuitude_record__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__attuitude_record__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__attuitude_record__response

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class AttuitudeRecord_Response(metaclass=Metaclass_AttuitudeRecord_Response):
    """Message class 'AttuitudeRecord_Response'."""

    __slots__ = [
        '_res',
    ]

    _fields_and_field_types = {
        'res': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.res = kwargs.get('res', str())

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
        if self.res != other.res:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def res(self):
        """Message field 'res'."""
        return self._res

    @res.setter
    def res(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'res' field must be of type 'str'"
        self._res = value


class Metaclass_AttuitudeRecord(type):
    """Metaclass of service 'AttuitudeRecord'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('yahboom_attitude_record_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'yahboom_attitude_record_interfaces.srv.AttuitudeRecord')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__attuitude_record

            from yahboom_attitude_record_interfaces.srv import _attuitude_record
            if _attuitude_record.Metaclass_AttuitudeRecord_Request._TYPE_SUPPORT is None:
                _attuitude_record.Metaclass_AttuitudeRecord_Request.__import_type_support__()
            if _attuitude_record.Metaclass_AttuitudeRecord_Response._TYPE_SUPPORT is None:
                _attuitude_record.Metaclass_AttuitudeRecord_Response.__import_type_support__()


class AttuitudeRecord(metaclass=Metaclass_AttuitudeRecord):
    from yahboom_attitude_record_interfaces.srv._attuitude_record import AttuitudeRecord_Request as Request
    from yahboom_attitude_record_interfaces.srv._attuitude_record import AttuitudeRecord_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
