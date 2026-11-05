// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from yahboom_msgs:msg/Position.idl
// generated code does not contain a copyright notice

#ifndef YAHBOOM_MSGS__MSG__DETAIL__POSITION__STRUCT_H_
#define YAHBOOM_MSGS__MSG__DETAIL__POSITION__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/Position in the package yahboom_msgs.
typedef struct yahboom_msgs__msg__Position
{
  float anglex;
  float angley;
  float distance;
} yahboom_msgs__msg__Position;

// Struct for a sequence of yahboom_msgs__msg__Position.
typedef struct yahboom_msgs__msg__Position__Sequence
{
  yahboom_msgs__msg__Position * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} yahboom_msgs__msg__Position__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // YAHBOOM_MSGS__MSG__DETAIL__POSITION__STRUCT_H_
