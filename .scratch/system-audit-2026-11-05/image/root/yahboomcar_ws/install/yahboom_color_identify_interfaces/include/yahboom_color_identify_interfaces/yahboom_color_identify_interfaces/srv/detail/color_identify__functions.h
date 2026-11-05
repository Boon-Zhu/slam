// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from yahboom_color_identify_interfaces:srv/ColorIdentify.idl
// generated code does not contain a copyright notice

#ifndef YAHBOOM_COLOR_IDENTIFY_INTERFACES__SRV__DETAIL__COLOR_IDENTIFY__FUNCTIONS_H_
#define YAHBOOM_COLOR_IDENTIFY_INTERFACES__SRV__DETAIL__COLOR_IDENTIFY__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "yahboom_color_identify_interfaces/msg/rosidl_generator_c__visibility_control.h"

#include "yahboom_color_identify_interfaces/srv/detail/color_identify__struct.h"

/// Initialize srv/ColorIdentify message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Request
 * )) before or use
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Request__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__init(yahboom_color_identify_interfaces__srv__ColorIdentify_Request * msg);

/// Finalize srv/ColorIdentify message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
void
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__fini(yahboom_color_identify_interfaces__srv__ColorIdentify_Request * msg);

/// Create srv/ColorIdentify message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Request__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
yahboom_color_identify_interfaces__srv__ColorIdentify_Request *
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__create();

/// Destroy srv/ColorIdentify message.
/**
 * It calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Request__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
void
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__destroy(yahboom_color_identify_interfaces__srv__ColorIdentify_Request * msg);

/// Check for srv/ColorIdentify message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__are_equal(const yahboom_color_identify_interfaces__srv__ColorIdentify_Request * lhs, const yahboom_color_identify_interfaces__srv__ColorIdentify_Request * rhs);

/// Copy a srv/ColorIdentify message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__copy(
  const yahboom_color_identify_interfaces__srv__ColorIdentify_Request * input,
  yahboom_color_identify_interfaces__srv__ColorIdentify_Request * output);

/// Initialize array of srv/ColorIdentify messages.
/**
 * It allocates the memory for the number of elements and calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Request__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence__init(yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence * array, size_t size);

/// Finalize array of srv/ColorIdentify messages.
/**
 * It calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Request__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
void
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence__fini(yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence * array);

/// Create array of srv/ColorIdentify messages.
/**
 * It allocates the memory for the array and calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence *
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence__create(size_t size);

/// Destroy array of srv/ColorIdentify messages.
/**
 * It calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
void
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence__destroy(yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence * array);

/// Check for srv/ColorIdentify message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence__are_equal(const yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence * lhs, const yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence * rhs);

/// Copy an array of srv/ColorIdentify messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence__copy(
  const yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence * input,
  yahboom_color_identify_interfaces__srv__ColorIdentify_Request__Sequence * output);

/// Initialize srv/ColorIdentify message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Response
 * )) before or use
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Response__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__init(yahboom_color_identify_interfaces__srv__ColorIdentify_Response * msg);

/// Finalize srv/ColorIdentify message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
void
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__fini(yahboom_color_identify_interfaces__srv__ColorIdentify_Response * msg);

/// Create srv/ColorIdentify message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Response__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
yahboom_color_identify_interfaces__srv__ColorIdentify_Response *
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__create();

/// Destroy srv/ColorIdentify message.
/**
 * It calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Response__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
void
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__destroy(yahboom_color_identify_interfaces__srv__ColorIdentify_Response * msg);

/// Check for srv/ColorIdentify message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__are_equal(const yahboom_color_identify_interfaces__srv__ColorIdentify_Response * lhs, const yahboom_color_identify_interfaces__srv__ColorIdentify_Response * rhs);

/// Copy a srv/ColorIdentify message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__copy(
  const yahboom_color_identify_interfaces__srv__ColorIdentify_Response * input,
  yahboom_color_identify_interfaces__srv__ColorIdentify_Response * output);

/// Initialize array of srv/ColorIdentify messages.
/**
 * It allocates the memory for the number of elements and calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Response__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence__init(yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence * array, size_t size);

/// Finalize array of srv/ColorIdentify messages.
/**
 * It calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Response__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
void
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence__fini(yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence * array);

/// Create array of srv/ColorIdentify messages.
/**
 * It allocates the memory for the array and calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence *
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence__create(size_t size);

/// Destroy array of srv/ColorIdentify messages.
/**
 * It calls
 * yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
void
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence__destroy(yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence * array);

/// Check for srv/ColorIdentify message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence__are_equal(const yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence * lhs, const yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence * rhs);

/// Copy an array of srv/ColorIdentify messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_yahboom_color_identify_interfaces
bool
yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence__copy(
  const yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence * input,
  yahboom_color_identify_interfaces__srv__ColorIdentify_Response__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // YAHBOOM_COLOR_IDENTIFY_INTERFACES__SRV__DETAIL__COLOR_IDENTIFY__FUNCTIONS_H_
