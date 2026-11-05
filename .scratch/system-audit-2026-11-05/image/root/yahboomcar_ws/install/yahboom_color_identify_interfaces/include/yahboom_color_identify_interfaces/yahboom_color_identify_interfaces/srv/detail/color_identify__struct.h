// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from yahboom_color_identify_interfaces:srv/ColorIdentify.idl
// generated code does not contain a copyright notice

#ifndef YAHBOOM_COLOR_IDENTIFY_INTERFACES__SRV__DETAIL__COLOR_IDENTIFY__STRUCT_H_
#define YAHBOOM_COLOR_IDENTIFY_INTERFACES__SRV__DETAIL__COLOR_IDENTIFY__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'if_identify'
#include "rosidl_runtime_c/string.h"

/// Struct defined in srv/ColorIdentify in the package yahboom_color_identify_interfaces.
typedef struct yahboom_color_identify_interfaces__srv__ColorIdentify_Request
{
  rosidl_runtime_c__String if_identify;
} yahboom_color_identify_interfaces__srv__ColorIdentify_Request;

// Struct for a sequence of yahboom_color_identify_interfaces__srv__ColorIdentify_Request.
typedef struct yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence
{
  yahboom_color_identify_interfaces__srv__ColorIdentify_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'response'
// already included above
// #include "rosidl_runtime_c/string.h"

/// Struct defined in srv/ColorIdentify in the package yahboom_color_identify_interfaces.
typedef struct yahboom_color_identify_interfaces__srv__ColorIdentify_Response
{
  rosidl_runtime_c__String response;
} yahboom_color_identify_interfaces__srv__ColorIdentify_Response;

// Struct for a sequence of yahboom_color_identify_interfaces__srv__ColorIdentify_Response.
typedef struct yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence
{
  yahboom_color_identify_interfaces__srv__ColorIdentify_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // YAHBOOM_COLOR_IDENTIFY_INTERFACES__SRV__DETAIL__COLOR_IDENTIFY__STRUCT_H_
