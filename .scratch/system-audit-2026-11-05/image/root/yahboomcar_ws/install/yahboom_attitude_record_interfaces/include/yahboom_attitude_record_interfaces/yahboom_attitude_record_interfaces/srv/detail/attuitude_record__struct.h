// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from yahboom_attitude_record_interfaces:srv/AttuitudeRecord.idl
// generated code does not contain a copyright notice

#ifndef YAHBOOM_ATTITUDE_RECORD_INTERFACES__SRV__DETAIL__ATTUITUDE_RECORD__STRUCT_H_
#define YAHBOOM_ATTITUDE_RECORD_INTERFACES__SRV__DETAIL__ATTUITUDE_RECORD__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in srv/AttuitudeRecord in the package yahboom_attitude_record_interfaces.
typedef struct yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Request
{
  int64_t pitch;
  int64_t yaw;
} yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Request;

// Struct for a sequence of yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Request.
typedef struct yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Request__Sequence
{
  yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'res'
#include "rosidl_runtime_c/string.h"

/// Struct defined in srv/AttuitudeRecord in the package yahboom_attitude_record_interfaces.
typedef struct yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Response
{
  rosidl_runtime_c__String res;
} yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Response;

// Struct for a sequence of yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Response.
typedef struct yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Response__Sequence
{
  yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} yahboom_attitude_record_interfaces__srv__AttuitudeRecord_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // YAHBOOM_ATTITUDE_RECORD_INTERFACES__SRV__DETAIL__ATTUITUDE_RECORD__STRUCT_H_
