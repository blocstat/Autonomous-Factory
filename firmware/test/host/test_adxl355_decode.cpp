// Host-side known-answer tests for the ADXL355 decoding helpers.
// Build and run from the repository root:
//   c++ -std=c++17 -Wall -Wextra -I firmware/main firmware/test/host/test_adxl355_decode.cpp -o /tmp/test_adxl355_decode && /tmp/test_adxl355_decode
// No hardware is involved; the inputs are hand-made byte patterns.
#include <cmath>
#include <cstdio>

#include "adxl355_decode.hpp"

namespace {

int failures = 0;

void expect_int(const char *name, long long got, long long want) {
    if (got != want) {
        std::printf("FAIL %s: got %lld, want %lld\n", name, got, want);
        ++failures;
    } else {
        std::printf("ok   %s\n", name);
    }
}

void expect_near(const char *name, double got, double want, double tol) {
    if (std::fabs(got - want) > tol) {
        std::printf("FAIL %s: got %.4f, want %.4f\n", name, got, want);
        ++failures;
    } else {
        std::printf("ok   %s\n", name);
    }
}

}  // namespace

int main() {
    using adxl355::decode_axis;
    expect_int("zero", decode_axis(0x00, 0x00, 0x00), 0);
    expect_int("max positive", decode_axis(0x7F, 0xFF, 0xF0), 524287);
    expect_int("most negative", decode_axis(0x80, 0x00, 0x00), -524288);
    expect_int("minus one", decode_axis(0xFF, 0xFF, 0xF0), -1);
    expect_int("low nibble of DATA1 ignored", decode_axis(0x00, 0x00, 0x1F), 1);
    // +1 g at +/-2 g range = 256,000 LSB = 0x3E800 -> bytes 0x3E 0x80 0x00.
    expect_int("plus one g", decode_axis(0x3E, 0x80, 0x00), 256000);
    // -1 g = -256,000 -> 0x100000 - 256000 = 0xC1800 -> bytes 0xC1 0x80 0x00.
    expect_int("minus one g", decode_axis(0xC1, 0x80, 0x00), -256000);
    expect_near("temp at 1885 LSB", adxl355::temp_c(1885), 25.0, 1e-9);
    expect_near("temp at 1795 LSB", adxl355::temp_c(1795), 34.945, 0.01);
    std::printf(failures ? "%d FAILED\n" : "all passed\n", failures);
    return failures ? 1 : 0;
}
