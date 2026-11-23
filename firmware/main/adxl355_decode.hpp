// Pure data-decoding helpers for the ADXL355, kept free of ESP-IDF headers
// so they can be tested on the host (see firmware/test/host/).
#pragma once

#include <cstdint>

namespace adxl355 {

// Sign-extends a 20-bit two's-complement value held in the low bits.
inline int32_t sign_extend_20(uint32_t value) {
    value &= 0xFFFFF;
    if (value & 0x80000) {
        return static_cast<int32_t>(value) - (1 << 20);
    }
    return static_cast<int32_t>(value);
}

// Builds one axis from its three data bytes. The data is left-justified:
// DATA3 holds bits 19..12, DATA2 bits 11..4, DATA1 bits 3..0 in its upper
// nibble.
inline int32_t decode_axis(uint8_t data3, uint8_t data2, uint8_t data1) {
    const uint32_t raw = (static_cast<uint32_t>(data3) << 12) |
                         (static_cast<uint32_t>(data2) << 4) |
                         (static_cast<uint32_t>(data1) >> 4);
    return sign_extend_20(raw);
}

// 12-bit temperature: 1885 LSB at 25 degC, -9.05 LSB/degC (typical,
// uncalibrated).
inline double temp_c(uint16_t raw) {
    return 25.0 + (static_cast<double>(raw) - 1885.0) / -9.05;
}

}  // namespace adxl355
