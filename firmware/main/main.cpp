// Phase 1, step 2: ADXL355 bring-up on an ESP32-S3-DevKitC-1.
//
// What it does: reads the ADXL355 ID registers over SPI and prints PASS or
// FAIL, then prints one reading per second (x, y, z in g, temperature).
// What it does not do: stream at full rate, store data, use Wi-Fi, or drive
// any output. Power the board from USB only.
//
// Every line meant for a program starts with "AF," so a script can pick it
// out of the log.

#include <cinttypes>

#include "adxl355.hpp"
#include "driver/spi_master.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace {

constexpr const char *TAG = "af_monitor";

// ESP32-S3 SPI2 IO_MUX pins (ESP-IDF SPI Master docs), on header J1 of the
// ESP32-S3-DevKitC-1. GPIO35-37 are avoided: octal-PSRAM modules use them.
constexpr int PIN_CS = 10;    // J1 pin 16 -> ADXL355 Pmod P1 pin 1 (CS)
constexpr int PIN_MOSI = 11;  // J1 pin 17 -> P1 pin 2 (MOSI)
constexpr int PIN_SCLK = 12;  // J1 pin 18 -> P1 pin 4 (SCLK)
constexpr int PIN_MISO = 13;  // J1 pin 19 -> P1 pin 3 (MISO)

// 1 MHz for bring-up: slow enough to tolerate jumper wires.
constexpr int SPI_CLOCK_HZ = 1 * 1000 * 1000;
constexpr int SAMPLE_PERIOD_MS = 1000;

bool check_ids(adxl355::Device &sensor) {
    adxl355::Ids ids = {};
    const esp_err_t err = sensor.read_ids(ids);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "SPI read failed: %s", esp_err_to_name(err));
        printf("AF,id,result=FAIL,reason=spi_error\n");
        return false;
    }
    printf("AF,id,devid_ad=0x%02X,devid_mst=0x%02X,partid=0x%02X,revid=0x%02X,result=%s\n",
           ids.devid_ad, ids.devid_mst, ids.partid, ids.revid, ids.ok() ? "PASS" : "FAIL");
    if (!ids.ok()) {
        ESP_LOGE(TAG, "expected 0xAD 0x1D 0xED. All 0x00 or all 0xFF usually means a "
                      "wiring or power problem; check 3V3, GND, MISO and CS.");
    }
    return ids.ok();
}

}  // namespace

extern "C" void app_main(void) {
    ESP_LOGI(TAG, "ADXL355 bring-up: ID check, then 1 reading per second");
    ESP_LOGI(TAG, "readings are from the ADXL355, uncalibrated (+/-8%% scale tolerance)");

    spi_bus_config_t bus = {};
    bus.mosi_io_num = PIN_MOSI;
    bus.miso_io_num = PIN_MISO;
    bus.sclk_io_num = PIN_SCLK;
    bus.quadwp_io_num = -1;
    bus.quadhd_io_num = -1;
    bus.max_transfer_sz = 32;
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_DISABLED));

    adxl355::Device sensor;
    ESP_ERROR_CHECK(sensor.attach(SPI2_HOST, PIN_CS, SPI_CLOCK_HZ));

    sensor.soft_reset();
    if (!check_ids(sensor)) {
        // Keep retrying so a loose wire can be fixed without reflashing.
        while (!check_ids(sensor)) {
            vTaskDelay(pdMS_TO_TICKS(2000));
        }
    }

    ESP_ERROR_CHECK(sensor.start_measurement());
    vTaskDelay(pdMS_TO_TICKS(50));
    printf("AF,columns,uptime_ms,x_g,y_g,z_g,temp_c\n");

    while (true) {
        adxl355::RawSample s = {};
        if (sensor.read_sample(s) == ESP_OK) {
            const double k = adxl355::LSB_PER_G_2G;
            printf("AF,sample,%" PRIu32 ",%.4f,%.4f,%.4f,%.1f\n",
                   static_cast<uint32_t>(xTaskGetTickCount() * portTICK_PERIOD_MS),
                   s.x / k, s.y / k, s.z / k, adxl355::temp_c(s.temp));
        } else {
            printf("AF,sample,error\n");
        }
        vTaskDelay(pdMS_TO_TICKS(SAMPLE_PERIOD_MS));
    }
}
