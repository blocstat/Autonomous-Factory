#include "adxl355.hpp"

#include <cstring>

#include "esp_heap_caps.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace adxl355 {

namespace {
// Address byte (1) + up to 11 data bytes (TEMP2 through ZDATA1).
constexpr size_t MAX_TRANSFER = 12;
}  // namespace

esp_err_t Device::attach(spi_host_device_t host, int cs_gpio, int clock_hz) {
    spi_device_interface_config_t config = {};
    config.mode = 0;  // CPOL = 0, CPHA = 0
    config.clock_speed_hz = clock_hz;
    config.spics_io_num = cs_gpio;
    config.queue_size = 1;
    // DMA-capable buffers for FIFO reads (up to 1 + 96 * 3 bytes).
    const size_t fifo_bytes = 1 + 3 * FIFO_WORDS;
    dma_tx_ = static_cast<uint8_t *>(heap_caps_calloc(1, fifo_bytes, MALLOC_CAP_DMA));
    dma_rx_ = static_cast<uint8_t *>(heap_caps_calloc(1, fifo_bytes, MALLOC_CAP_DMA));
    if (dma_tx_ == nullptr || dma_rx_ == nullptr) {
        return ESP_ERR_NO_MEM;
    }
    return spi_bus_add_device(host, &config, &handle_);
}

esp_err_t Device::read(uint8_t address, uint8_t *data, size_t length) {
    if (length == 0 || length + 1 > MAX_TRANSFER) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t tx[MAX_TRANSFER] = {};
    uint8_t rx[MAX_TRANSFER] = {};
    tx[0] = static_cast<uint8_t>((address << 1) | 0x01);

    spi_transaction_t transaction = {};
    transaction.length = (length + 1) * 8;
    transaction.tx_buffer = tx;
    transaction.rx_buffer = rx;
    const esp_err_t err = spi_device_polling_transmit(handle_, &transaction);
    if (err == ESP_OK) {
        std::memcpy(data, rx + 1, length);
    }
    return err;
}

esp_err_t Device::write(uint8_t address, uint8_t value) {
    uint8_t tx[2] = {static_cast<uint8_t>(address << 1), value};
    spi_transaction_t transaction = {};
    transaction.length = 16;
    transaction.tx_buffer = tx;
    return spi_device_polling_transmit(handle_, &transaction);
}

esp_err_t Device::read_ids(Ids &ids) {
    uint8_t buffer[4] = {};
    const esp_err_t err = read(reg::DEVID_AD, buffer, sizeof(buffer));
    ids = {buffer[0], buffer[1], buffer[2], buffer[3]};
    return err;
}

esp_err_t Device::soft_reset() {
    const esp_err_t err = write(reg::RESET, RESET_CODE);
    vTaskDelay(pdMS_TO_TICKS(20));
    return err;
}

esp_err_t Device::start_measurement() {
    // Reset values are kept: +/-2 g, 4000 Hz ODR, 1000 Hz low-pass.
    // Only the standby bit is cleared.
    return write(reg::POWER_CTL, 0x00);
}

esp_err_t Device::read_sample(RawSample &sample) {
    // TEMP2, TEMP1, then X, Y, Z (3 bytes each), read in one burst so the
    // axes come from the same output sample.
    uint8_t b[11] = {};
    const esp_err_t err = read(reg::TEMP2, b, sizeof(b));
    if (err != ESP_OK) {
        return err;
    }
    sample.temp = static_cast<uint16_t>(((b[0] & 0x0F) << 8) | b[1]);
    sample.x = decode_axis(b[2], b[3], b[4]);
    sample.y = decode_axis(b[5], b[6], b[7]);
    sample.z = decode_axis(b[8], b[9], b[10]);
    return ESP_OK;
}

esp_err_t Device::read_status_and_entries(uint8_t &status, uint8_t &entries) {
    uint8_t b[2] = {};
    const esp_err_t err = read(reg::STATUS, b, sizeof(b));
    status = b[0];
    entries = static_cast<uint8_t>(b[1] & 0x7F);
    return err;
}

esp_err_t Device::read_fifo(uint8_t *out, size_t n_words) {
    if (n_words == 0 || n_words > FIFO_WORDS) {
        return ESP_ERR_INVALID_ARG;
    }
    const size_t length = 1 + 3 * n_words;
    std::memset(dma_tx_, 0, length);
    dma_tx_[0] = static_cast<uint8_t>((reg::FIFO_DATA << 1) | 0x01);
    spi_transaction_t transaction = {};
    transaction.length = length * 8;
    transaction.tx_buffer = dma_tx_;
    transaction.rx_buffer = dma_rx_;
    const esp_err_t err = spi_device_polling_transmit(handle_, &transaction);
    if (err == ESP_OK) {
        std::memcpy(out, dma_rx_ + 1, 3 * n_words);
    }
    return err;
}

esp_err_t Device::read_temperature(uint16_t &raw) {
    uint8_t b[2] = {};
    const esp_err_t err = read(reg::TEMP2, b, sizeof(b));
    raw = static_cast<uint16_t>(((b[0] & 0x0F) << 8) | b[1]);
    return err;
}

}  // namespace adxl355
