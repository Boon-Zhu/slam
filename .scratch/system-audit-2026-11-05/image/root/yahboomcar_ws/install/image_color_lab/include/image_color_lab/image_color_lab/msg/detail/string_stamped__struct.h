// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from image_color_lab:msg/StringStamped.idl
// generated code does not contain a copyright notice

#ifndef IMAGE_COLOR_LAB__MSG__DETAIL__STRING_STAMPED__STRUCT_H_
#define IMAGE_COLOR_LAB__MSG__DETAIL__STRING_STAMPED__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.h"
// Member 'data'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/StringStamped in the package image_color_lab.
typedef struct image_color_lab__msg__StringStamped
{
  std_msgs__msg__Header header;
  rosidl_runtime_c__String data;
} image_color_lab__msg__StringStamped;

// Struct for a sequence of image_color_lab__msg__StringStamped.
typedef struct image_color_lab__msg__StringStamped__Sequence
{
  image_color_lab__msg__StringStamped * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} image_color_lab__msg__StringStamped__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // IMAGE_COLOR_LAB__MSG__DETAIL__STRING_STAMPED__STRUCT_H_
