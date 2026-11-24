// Phase 1, step 3: stream every ADXL355 sample to the host over USB.
//
// What it does: checks the ADXL355 ID, then reads the sensor's FIFO every
// millisecond at the reset settings (4000 Hz output rate, 1000 Hz low-pass,
// +/-2 g) and sends every x/y/z set to the host in CRC-checked binary frames
// (format in stream_frame.hpp) on UART0, the USB-to-UART port, at 921600 baud.
// Once per second it also sends a text status line.
// What it does not do: store data, use Wi-Fi, or drive any output. Power the
// board from USB only.
//
// Text lines meant for scripts start with "AF,". Read the stream with
// python/scripts/capture_adxl355.py, not with idf.py monitor (binary data
// shows as garbage there).

#include <cinttypes>
#include <cstdio>
#include <cstring>

#include "adxl355.hpp"
#include "driver/spi_master.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "stream_frame.hpp"

// The FIFO holds 8 ms of data at 4000 Hz and the stream task reads it once
// per tick, so the tick must be 1 ms. An sdkconfig made before step 3 keeps
// the default 100 Hz: delete firmware/sdkconfig and build again.
static_assert(CONFIG_FREERTOS_HZ == 1000,
              "CONFIG_FREERTOS_HZ must be 1000: delete firmware/sdkconfig and rebuild");

namespace {

constexpr const char *TAG = "af_monitor";

// ESP32-S3 SPI2 IO_MUX pins (ESP-IDF SPI Master docs), on header J1 of the
// ESP32-S3-DevKitC-1. GPIO35-37 are avoided: octal-PSRAM modules use them.
constexpr int PIN_CS = 10;    // J1 pin 16 -> ADXL355 Pmod P1 pin 1 (CS)
constexpr int PIN_MOSI = 11;  // J1 pin 17 -> P1 pin 2 (MOSI)
constexpr int PIN_SCLK = 12;  // J1 pin 18 -> P1 pin 4 (SCLK)
constexpr int PIN_MISO = 13;  // J1 pin 19 -> P1 pin 3 (MISO)

// 8 MHz is under the ADXL355's 10 MHz limit. A full FIFO read (289 bytes)
// then takes about 0.3 ms.
constexpr int SPI_CLOCK_HZ = 8 * 1000 * 1000;

constexpr uart_port_t STREAM_UART = UART_NUM_0;
constexpr uint32_t STREAM_BAUD = 921600;  // ~92 kB/s; the stream needs ~40 kB/s
constexpr int STREAM_UART_TX_BUFFER = 16 * 1024;
constexpr size_t SETS_PER_FRAME = 16;  // one frame about every 4 ms
constexpr int64_t STATUS_PERIOD_US = 1000 * 1000;

adxl355::Device sensor;

void send(const void *data, size_t length) {
    uart_write_bytes(STREAM_UART, data, length);
}

void send_text(const char *text) { send(text, std::strlen(text)); }

bool check_ids() {
    adxl355::Ids ids = {};
    const esp_err_t err = sensor.read_ids(ids);
    char line[128];
    if (err != ESP_OK) {
        std::snprintf(line, sizeof(line), "AF,id,result=FAIL,reason=spi_error\n");
    } else {
        std::snprintf(line, sizeof(line),
                      "AF,id,devid_ad=0x%02X,devid_mst=0x%02X,partid=0x%02X,revid=0x%02X,"
                      "result=%s\n",
                      ids.devid_ad, ids.devid_mst, ids.partid, ids.revid,
                      ids.ok() ? "PASS" : "FAIL");
    }
    send_text(line);
    return err == ESP_OK && ids.ok();
}

void stream_task(void *) {
    static uint8_t fifo[3 * adxl355::FIFO_WORDS];
    static uint8_t sets[stream::SET_SIZE * (stream::MAX_SETS_PER_FRAME + adxl355::FIFO_WORDS / 3)];
    static uint8_t frame[stream::MAX_FRAME_SIZE];
    stream::FifoParser parser;

    size_t pending_sets = 0;
    uint32_t sets_sent = 0;
    uint16_t sequence = 0;
    uint8_t flags = 0;
    uint32_t overruns = 0;
    uint32_t spi_errors = 0;
    uint32_t last_dropped = 0;
    int64_t next_status_us = esp_timer_get_time() + STATUS_PERIOD_US;

    sensor.start_measurement();
    const int64_t start_us = esp_timer_get_time();
    {
        char line[160];
        std::snprintf(line, sizeof(line),
                      "AF,stream,version=%u,odr_hz=4000,lpf_hz=1000,range_g=2,"
                      "lsb_per_g=256000,sets_per_frame=%u,start_us=%" PRId64 "\n",
                      stream::VERSION, static_cast<unsigned>(SETS_PER_FRAME), start_us);
        send_text(line);
    }

    while (true) {
        uint8_t status = 0;
        uint8_t entries = 0;
        if (sensor.read_status_and_entries(status, entries) != ESP_OK) {
            ++spi_errors;
        } else {
            if (status & adxl355::STATUS_FIFO_OVR) {
                ++overruns;
                flags |= stream::FLAG_FIFO_OVERRUN;
            }
            const size_t words = (entries / 3) * 3;
            if (words > 0) {
                if (sensor.read_fifo(fifo, words) == ESP_OK) {
                    pending_sets += parser.feed(fifo, words, sets + stream::SET_SIZE * pending_sets);
                } else {
                    ++spi_errors;
                }
            }
        }
        if (parser.dropped_words() != last_dropped) {
            last_dropped = parser.dropped_words();
            flags |= stream::FLAG_WORD_DROPPED;
        }

        size_t offset = 0;
        while (pending_sets - offset >= SETS_PER_FRAME) {
            const size_t length = stream::build_frame(frame, sequence++, sets_sent,
                                                      sets + stream::SET_SIZE * offset,
                                                      SETS_PER_FRAME, flags);
            send(frame, length);
            flags = 0;
            sets_sent += SETS_PER_FRAME;
            offset += SETS_PER_FRAME;
        }
        if (offset > 0) {
            std::memmove(sets, sets + stream::SET_SIZE * offset,
                         stream::SET_SIZE * (pending_sets - offset));
            pending_sets -= offset;
        }

        const int64_t now_us = esp_timer_get_time();
        if (now_us >= next_status_us) {
            next_status_us += STATUS_PERIOD_US;
            uint16_t temp_raw = 0;
            sensor.read_temperature(temp_raw);
            char line[192];
            std::snprintf(line, sizeof(line),
                          "AF,status,uptime_us=%" PRId64 ",sets=%" PRIu32 ",fifo_overruns=%" PRIu32
                          ",dropped_words=%" PRIu32 ",spi_errors=%" PRIu32 ",temp_c=%.2f\n",
                          now_us - start_us, sets_sent + static_cast<uint32_t>(pending_sets),
                          overruns, parser.dropped_words(), spi_errors,
                          adxl355::temp_c(temp_raw));
            send_text(line);
        }
        vTaskDelay(1);  // 1 ms with CONFIG_FREERTOS_HZ=1000
    }
}

}  // namespace

extern "C" void app_main(void) {
    ESP_LOGI(TAG, "ADXL355 streaming firmware; switching this port to 921600 baud for binary frames");

    // Take over UART0 for the stream. From here on, only this program writes
    // to it, so text lines and frames never interleave.
    fflush(stdout);
    ESP_ERROR_CHECK(uart_driver_install(STREAM_UART, 256, STREAM_UART_TX_BUFFER, 0, nullptr, 0));
    // The boot messages above go out at 115200; everything from here on at
    // STREAM_BAUD. The capture script skips the boot text.
    uart_wait_tx_done(STREAM_UART, pdMS_TO_TICKS(100));
    ESP_ERROR_CHECK(uart_set_baudrate(STREAM_UART, STREAM_BAUD));
    esp_log_level_set("*", ESP_LOG_NONE);

    spi_bus_config_t bus = {};
    bus.mosi_io_num = PIN_MOSI;
    bus.miso_io_num = PIN_MISO;
    bus.sclk_io_num = PIN_SCLK;
    bus.quadwp_io_num = -1;
    bus.quadhd_io_num = -1;
    bus.max_transfer_sz = 1 + 3 * adxl355::FIFO_WORDS;
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO));
    ESP_ERROR_CHECK(sensor.attach(SPI2_HOST, PIN_CS, SPI_CLOCK_HZ));

    sensor.soft_reset();
    while (!check_ids()) {
        send_text("AF,hint,check 3V3 GND MISO CS wiring; retrying in 2 s\n");
        vTaskDelay(pdMS_TO_TICKS(2000));
    }

    // Core 1, above normal priority: the FIFO holds 8 ms of data at 4000 Hz.
    xTaskCreatePinnedToCore(stream_task, "stream", 8192, nullptr, 10, nullptr, 1);
}
