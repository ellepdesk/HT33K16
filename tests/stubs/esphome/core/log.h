#pragma once
// Host-side stub of esphome/core/log.h.
//
// The macros still expand to a real variadic call so that format strings and
// their arguments are type-checked by the compiler, but output is discarded
// unless HT33K16_TEST_VERBOSE_LOG is defined.

#include <cstdarg>
#include <cstdio>

namespace esphome {

inline void test_log_(const char *tag, const char *format, ...) __attribute__((format(printf, 2, 3)));

inline void test_log_(const char *tag, const char *format, ...) {
#ifdef HT33K16_TEST_VERBOSE_LOG
  va_list arg;
  va_start(arg, format);
  fprintf(stderr, "[%s] ", tag);
  vfprintf(stderr, format, arg);
  fprintf(stderr, "\n");
  va_end(arg);
#else
  (void) tag;
  (void) format;
#endif
}

}  // namespace esphome

#define ESP_LOGV(tag, ...) ::esphome::test_log_(tag, __VA_ARGS__)
#define ESP_LOGD(tag, ...) ::esphome::test_log_(tag, __VA_ARGS__)
#define ESP_LOGI(tag, ...) ::esphome::test_log_(tag, __VA_ARGS__)
#define ESP_LOGW(tag, ...) ::esphome::test_log_(tag, __VA_ARGS__)
#define ESP_LOGE(tag, ...) ::esphome::test_log_(tag, __VA_ARGS__)
#define ESP_LOGCONFIG(tag, ...) ::esphome::test_log_(tag, __VA_ARGS__)
