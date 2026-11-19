#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace {

constexpr const char *TAG = "af_monitor";
constexpr int HEARTBEAT_PERIOD_MS = 5000;

}  // namespace

// Skeleton only. No GPIO, ADC, I2C, SPI, Wi-Fi, MQTT, or actuator outputs.
// A heartbeat log is not evidence that a board is attached or that a sensor
// measured anything.
extern "C" void app_main(void) {
    ESP_LOGI(TAG, "af_monitor skeleton started");
    ESP_LOGI(TAG, "sensor sampling, radio, and actuator outputs are not enabled");
    ESP_LOGI(TAG, "do not treat this log as a hardware measurement");

    while (true) {
        ESP_LOGI(TAG, "heartbeat");
        vTaskDelay(pdMS_TO_TICKS(HEARTBEAT_PERIOD_MS));
    }
}
