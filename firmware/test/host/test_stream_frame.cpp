// Host-side known-answer tests for the stream frame builder and FIFO parser.
// Build and run from the repository root:
//   c++ -std=c++17 -Wall -Wextra -I firmware/main firmware/test/host/test_stream_frame.cpp -o /tmp/test_stream_frame && /tmp/test_stream_frame
// No hardware is involved. The expected frame bytes were computed separately
// with Python's binascii.crc_hqx (CRC-16/CCITT-FALSE), and the same vector is
// checked by python/tests/test_adxl355_stream.py.
#include <cstdio>
#include <cstring>

#include "stream_frame.hpp"

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

void expect_bytes(const char *name, const uint8_t *got, const uint8_t *want, size_t n) {
    if (std::memcmp(got, want, n) != 0) {
        std::printf("FAIL %s: bytes differ\n", name);
        ++failures;
    } else {
        std::printf("ok   %s\n", name);
    }
}

// x word (bit 0 of byte 3 set), y word, z word.
constexpr uint8_t SET_A[9] = {0x12, 0x34, 0x51, 0xFE, 0xDC, 0xB0, 0x00, 0x01, 0x00};
constexpr uint8_t SET_B[9] = {0x00, 0x00, 0x11, 0x00, 0x00, 0x20, 0x00, 0x00, 0x30};

}  // namespace

int main() {
    const uint8_t check[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    expect_int("crc16 check value", stream::crc16_ccitt(check, sizeof(check)), 0x29B1);

    // One set, sequence 0x1234, first index 16, both flags set.
    const uint8_t want_frame[] = {0xA5, 0x5A, 0x01, 0x34, 0x12, 0x10, 0x00, 0x00, 0x00, 0x01, 0x03,
                                  0x12, 0x34, 0x51, 0xFE, 0xDC, 0xB0, 0x00, 0x01, 0x00, 0x96, 0x71};
    uint8_t frame[stream::MAX_FRAME_SIZE] = {};
    const size_t length = stream::build_frame(frame, 0x1234, 16, SET_A, 1, 0x03);
    expect_int("frame length", static_cast<long long>(length), sizeof(want_frame));
    expect_bytes("frame bytes", frame, want_frame, sizeof(want_frame));
    expect_int("0 sets rejected", static_cast<long long>(stream::build_frame(frame, 0, 0, SET_A, 0, 0)), 0);
    expect_int("33 sets rejected", static_cast<long long>(stream::build_frame(frame, 0, 0, SET_A, 33, 0)), 0);

    // Normal stream: two complete sets.
    {
        stream::FifoParser parser;
        uint8_t words[18];
        std::memcpy(words, SET_A, 9);
        std::memcpy(words + 9, SET_B, 9);
        uint8_t out[9 * 8] = {};
        expect_int("two sets parsed", static_cast<long long>(parser.feed(words, 6, out)), 2);
        expect_bytes("first set kept", out, SET_A, 9);
        expect_bytes("second set kept", out + 9, SET_B, 9);
        expect_int("nothing dropped", parser.dropped_words(), 0);
    }

    // A set split across two reads is completed by the second read.
    {
        stream::FifoParser parser;
        uint8_t out[9 * 8] = {};
        expect_int("split: first part", static_cast<long long>(parser.feed(SET_A, 2, out)), 0);
        expect_int("split: second part", static_cast<long long>(parser.feed(SET_A + 6, 1, out)), 1);
        expect_bytes("split: set intact", out, SET_A, 9);
    }

    // Orphan y/z words before the first x, and an empty-FIFO word, are dropped.
    {
        stream::FifoParser parser;
        const uint8_t empty[3] = {0x00, 0x00, 0x02};
        uint8_t words[3 * 6];
        std::memcpy(words, SET_A + 3, 6);  // y, z without x
        std::memcpy(words + 6, empty, 3);
        std::memcpy(words + 9, SET_B, 9);
        uint8_t out[9 * 8] = {};
        expect_int("orphans: one set", static_cast<long long>(parser.feed(words, 6, out)), 1);
        expect_bytes("orphans: set is B", out, SET_B, 9);
        expect_int("orphans: 3 dropped", parser.dropped_words(), 3);
    }

    // An x word that arrives before the previous set is complete restarts the set.
    {
        stream::FifoParser parser;
        uint8_t words[3 * 4];
        std::memcpy(words, SET_A, 3);       // x
        std::memcpy(words + 3, SET_B, 9);   // x, y, z
        uint8_t out[9 * 8] = {};
        expect_int("restart: one set", static_cast<long long>(parser.feed(words, 4, out)), 1);
        expect_bytes("restart: set is B", out, SET_B, 9);
        expect_int("restart: 1 dropped", parser.dropped_words(), 1);
    }

    std::printf("%s (%d failure%s)\n", failures == 0 ? "PASS" : "FAIL", failures,
                failures == 1 ? "" : "s");
    return failures == 0 ? 0 : 1;
}
