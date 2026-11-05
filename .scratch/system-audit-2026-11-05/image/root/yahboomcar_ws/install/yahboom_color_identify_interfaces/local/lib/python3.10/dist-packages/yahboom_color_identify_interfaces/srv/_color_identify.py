# generated from rosidl_generator_py/resource/_idl.py.em
# with input from yahboom_color_identify_interfaces:srv/ColorIdentify.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_ColorIdentify_Request(type):
    """Metaclass of message 'ColorIdentify_Request'."""

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
            module = import_type_support('yahboom_color_identify_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'yahboom_color_identify_interfaces.srv.ColorIdentify_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__color_identify__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__color_identify__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__color_identify__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__color_identify__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__color_identify__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class ColorIdentify_Request(metaclass=Metaclass_ColorIdentify_Request):
    """Message class 'ColorIdentify_Request'."""

    __slots__ = [
        '_if_identify',
    ]

    _fields_and_field_types = {
        'if_identify': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.if_identify = kwargs.get('if_identify', str())

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
        if self.if_identify != other.if_identify:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def if_identify(self):
        """Message field 'if_identify'."""
        return self._if_identify

    @if_identify.setter
    def if_identify(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'if_identify' field must be of type 'str'"
        self._if_identify = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_ColorIdentify_Response(type):
    """Metaclass of message 'ColorIdentify_Response'."""

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
            module = import_type_support('yahboom_color_identify_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'yahboom_color_identify_interfaces.srv.ColorIdentify_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__color_identify__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__color_identify__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__color_identify__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__color_identify__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__color_identify__response

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class ColorIdentify_Response(metaclass=Metaclass_ColorIdentify_Response):
    """Message class 'ColorIdentify_Response'."""

    __slots__ = [
        '_response',
    ]

    _fields_and_field_types = {
        'response': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.response = kwargs.get('response', str())

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
        if self.response != other.response:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def response(self):
        """Message field 'response'."""
        return self._response

    @response.setter
    def response(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'response' field must be of type 'str'"
        self._response = value


class Metaclass_ColorIdentify(type):
    """Metaclass of service 'ColorIdentify'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('yahboom_color_identify_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'yahboom_color_identify_interfaces.srv.ColorIdentify')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__color_identify

            from yahboom_color_identify_interfaces.srv import _color_identify
            if _color_identify.Metaclass_ColorIdentify_Request._TYPE_SUPPORT is None:
                _color_identify.Metaclass_ColorIdentify_Request.__import_type_support__()
            if _color_identify.Metaclass_ColorIdentify_Response._TYPE_SUPPORT is None:
                _color_identify.Metaclass_ColorIdentify_Response.__import_type_support__()


class ColorIdentify(metaclass=Metaclass_ColorIdentify):
    from yahboom_color_identify_interfaces.srv._color_identify import ColorIdentify_Request as Request
    from yahboom_color_identify_interfaces.srv._color_identify import ColorIdentify_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
