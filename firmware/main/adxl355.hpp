// Minimal ADXL355 SPI driver for Phase 1 bring-up.
//
// Facts used here come from the ADXL354/ADXL355 data sheet (Rev. D) and
// Analog Devices' no-OS driver:
//   - SPI mode 0 (CPOL = 0, CPHA = 0), 0.1 to 10 MHz.
//   - First byte = (register address << 1) | R/W, with R/W = 1 for a read.
//   - ID registers: DEVID_AD 0x00 = 0xAD, DEVID_MST 0x01 = 0x1D,
//     PARTID 0x02 = 0xED.
//   - Data: 20-bit, left-justified across three bytes, two's complement.
//   - Scale: 256,000 LSB/g typical in the +/-2 g range (the reset range).
//   - Temperature: 12-bit, 1885 LSB at 25 degC, -9.05 LSB/degC.
//   - POWER_CTL bit 0 = standby; the part powers up in standby.
#pragma once

#include <cstdint>

#include "adxl355_decode.hpp"
#include "driver/spi_master.h"
#include "esp_err.h"

namespace adxl355 {

namespace reg {
constexpr uint8_t DEVID_AD = 0x00;
constexpr uint8_t DEVID_MST = 0x01;
constexpr uint8_t PARTID = 0x02;
constexpr uint8_t REVID = 0x03;
constexpr uint8_t STATUS = 0x04;
constexpr uint8_t FIFO_ENTRIES = 0x05;
constexpr uint8_t TEMP2 = 0x06;
constexpr uint8_t XDATA3 = 0x08;
constexpr uint8_t FIFO_DATA = 0x11;
constexpr uint8_t FILTER = 0x28;
constexpr uint8_t RANGE = 0x2C;
constexpr uint8_t POWER_CTL = 0x2D;
constexpr uint8_t RESET = 0x2F;
}  // namespace reg

constexpr uint8_t EXPECTED_DEVID_AD = 0xAD;
constexpr uint8_t EXPECTED_DEVID_MST = 0x1D;
constexpr uint8_t EXPECTED_PARTID = 0xED;
constexpr uint8_t RESET_CODE = 0x52;

// STATUS bits (data sheet, Table 20). Reading STATUS clears FIFO_OVR.
constexpr uint8_t STATUS_DATA_RDY = 0x01;
constexpr uint8_t STATUS_FIFO_FULL = 0x02;
constexpr uint8_t STATUS_FIFO_OVR = 0x04;

// The FIFO holds 96 single-axis words (32 x/y/z sets).
constexpr size_t FIFO_WORDS = 96;

// Typical sensitivity in the +/-2 g range. The data sheet allows
// 235,520 to 276,480 LSB/g, so readings in g are good to about +/-8 %
// until the unit is calibrated.
constexpr double LSB_PER_G_2G = 256000.0;

struct Ids {
    uint8_t devid_ad;
    uint8_t devid_mst;
    uint8_t partid;
    uint8_t revid;
    bool ok() const {
        return devid_ad == EXPECTED_DEVID_AD && devid_mst == EXPECTED_DEVID_MST &&
               partid == EXPECTED_PARTID;
    }
};

struct RawSample {
    int32_t x;
    int32_t y;
    int32_t z;
    uint16_t temp;
};

class Device {
public:
    // Adds the sensor to an SPI bus that is already initialised.
    esp_err_t attach(spi_host_device_t host, int cs_gpio, int clock_hz);

    esp_err_t read(uint8_t address, uint8_t *data, size_t length);
    esp_err_t write(uint8_t address, uint8_t value);

    esp_err_t read_ids(Ids &ids);
    esp_err_t soft_reset();
    esp_err_t start_measurement();
    esp_err_t read_sample(RawSample &sample);

    // Reads STATUS and FIFO_ENTRIES in one transfer.
    esp_err_t read_status_and_entries(uint8_t &status, uint8_t &entries);

    // Reads `n_words` 3-byte words from FIFO_DATA in one transfer (the
    // address does not auto-increment on FIFO_DATA, so a multi-byte read
    // keeps popping the FIFO). `out` gets 3 * n_words bytes.
    esp_err_t read_fifo(uint8_t *out, size_t n_words);

    // Reads the 12-bit temperature code.
    esp_err_t read_temperature(uint16_t &raw);

private:
    spi_device_handle_t handle_ = nullptr;
    uint8_t *dma_tx_ = nullptr;
    uint8_t *dma_rx_ = nullptr;
};

}  // namespace adxl355
