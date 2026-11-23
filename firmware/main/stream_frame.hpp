// Binary frame format for streaming ADXL355 samples to the host, and the
// FIFO word parser. Free of ESP-IDF headers so both can be tested on the
// host (firmware/test/host/). The Python reader is
// python/af_signal/adxl355_stream.py; the two must stay in step.
//
// Frame, all multi-byte header fields little-endian:
//   0  2  sync 0xA5 0x5A
//   2  1  version (1)
//   3  2  frame sequence number (wraps at 65536)
//   5  4  index of the first sample set in this frame, counted from the
//         start of streaming
//   9  1  number of sample sets N (1..MAX_SETS_PER_FRAME)
//  10  1  flags: bit 0 FIFO overrun seen since the previous frame,
//                bit 1 an empty or out-of-order FIFO word was dropped
//  11  9N sample sets: x, y, z, each the 3 raw FIFO bytes, most
//         significant byte first, exactly as read from FIFO_DATA
//  11+9N 2  CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over bytes
//         2 .. 10+9N, little-endian
#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace stream {

constexpr uint8_t SYNC0 = 0xA5;
constexpr uint8_t SYNC1 = 0x5A;
constexpr uint8_t VERSION = 1;
constexpr size_t HEADER_SIZE = 11;
constexpr size_t SET_SIZE = 9;
constexpr size_t CRC_SIZE = 2;
constexpr size_t MAX_SETS_PER_FRAME = 32;
constexpr size_t MAX_FRAME_SIZE = HEADER_SIZE + SET_SIZE * MAX_SETS_PER_FRAME + CRC_SIZE;

constexpr uint8_t FLAG_FIFO_OVERRUN = 0x01;
constexpr uint8_t FLAG_WORD_DROPPED = 0x02;

inline uint16_t crc16_ccitt(const uint8_t *data, size_t length) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; ++i) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;
        for (int bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                                 : static_cast<uint16_t>(crc << 1);
        }
    }
    return crc;
}

// Writes one frame into `out` (at least MAX_FRAME_SIZE bytes) and returns
// its length, or 0 if `n_sets` is out of range.
inline size_t build_frame(uint8_t *out, uint16_t sequence, uint32_t first_index,
                          const uint8_t *sets, size_t n_sets, uint8_t flags) {
    if (n_sets == 0 || n_sets > MAX_SETS_PER_FRAME) {
        return 0;
    }
    out[0] = SYNC0;
    out[1] = SYNC1;
    out[2] = VERSION;
    out[3] = static_cast<uint8_t>(sequence & 0xFF);
    out[4] = static_cast<uint8_t>(sequence >> 8);
    for (int i = 0; i < 4; ++i) {
        out[5 + i] = static_cast<uint8_t>((first_index >> (8 * i)) & 0xFF);
    }
    out[9] = static_cast<uint8_t>(n_sets);
    out[10] = flags;
    std::memcpy(out + HEADER_SIZE, sets, n_sets * SET_SIZE);
    const size_t body_end = HEADER_SIZE + n_sets * SET_SIZE;
    const uint16_t crc = crc16_ccitt(out + 2, body_end - 2);
    out[body_end] = static_cast<uint8_t>(crc & 0xFF);
    out[body_end + 1] = static_cast<uint8_t>(crc >> 8);
    return body_end + CRC_SIZE;
}

// Groups 3-byte FIFO words into x/y/z sets. Per the data sheet, bit 0 of the
// third byte marks an x-axis word and bit 1 marks a read of an empty FIFO.
// A set starts at an x word; words that are empty, or y/z words without a
// preceding x, are dropped and counted.
class FifoParser {
public:
    // Feeds `n_words` words. Complete sets are written to `sets_out`
    // (9 bytes each, room for at least n_words / 3 + 1 sets). Returns the
    // number of complete sets written.
    size_t feed(const uint8_t *words, size_t n_words, uint8_t *sets_out) {
        size_t written = 0;
        for (size_t i = 0; i < n_words; ++i) {
            const uint8_t *word = words + 3 * i;
            if (word[2] & 0x02) {
                ++dropped_;
                continue;
            }
            if (word[2] & 0x01) {
                if (pending_ != 0) {
                    dropped_ += pending_;
                }
                std::memcpy(set_, word, 3);
                pending_ = 1;
                continue;
            }
            if (pending_ == 0) {
                ++dropped_;
                continue;
            }
            std::memcpy(set_ + 3 * pending_, word, 3);
            if (++pending_ == 3) {
                std::memcpy(sets_out + SET_SIZE * written, set_, SET_SIZE);
                ++written;
                pending_ = 0;
            }
        }
        return written;
    }

    uint32_t dropped_words() const { return dropped_; }

private:
    uint8_t set_[SET_SIZE] = {};
    size_t pending_ = 0;
    uint32_t dropped_ = 0;
};

}  // namespace stream
