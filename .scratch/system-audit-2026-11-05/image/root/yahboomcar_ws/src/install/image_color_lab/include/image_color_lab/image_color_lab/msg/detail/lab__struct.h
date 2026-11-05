// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from image_color_lab:msg/Lab.idl
// generated code does not contain a copyright notice

#ifndef IMAGE_COLOR_LAB__MSG__DETAIL__LAB__STRUCT_H_
#define IMAGE_COLOR_LAB__MSG__DETAIL__LAB__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/Lab in the package image_color_lab.
typedef struct image_color_lab__msg__Lab
{
  int64_t l_min;
  int64_t a_min;
  int64_t b_min;
  int64_t l_max;
  int64_t a_max;
  int64_t b_max;
} image_color_lab__msg__Lab;

// Struct for a sequence of image_color_lab__msg__Lab.
typedef struct image_color_lab__msg__Lab__Sequence
{
  image_color_lab__msg__Lab * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} image_color_lab__msg__Lab__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // IMAGE_COLOR_LAB__MSG__DETAIL__LAB__STRUCT_H_
