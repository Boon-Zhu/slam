// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from yahboom_msgs:msg/Target.idl
// generated code does not contain a copyright notice

#ifndef YAHBOOM_MSGS__MSG__DETAIL__TARGET__STRUCT_H_
#define YAHBOOM_MSGS__MSG__DETAIL__TARGET__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'frame_id'
#include "rosidl_runtime_c/string.h"
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.h"

/// Struct defined in msg/Target in the package yahboom_msgs.
typedef struct yahboom_msgs__msg__Target
{
  rosidl_runtime_c__String frame_id;
  builtin_interfaces__msg__Time stamp;
  float scores;
  float ptx;
  float pty;
  float distw;
  float disth;
  float centerx;
  float centery;
} yahboom_msgs__msg__Target;

// Struct for a sequence of yahboom_msgs__msg__Target.
typedef struct yahboom_msgs__msg__Target__Sequence
{
  yahboom_msgs__msg__Target * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} yahboom_msgs__msg__Target__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // YAHBOOM_MSGS__MSG__DETAIL__TARGET__STRUCT_H_
