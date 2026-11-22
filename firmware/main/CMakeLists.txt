idf_component_register(
    SRCS "main.cpp" "adxl355.cpp"
    INCLUDE_DIRS "."
    PRIV_REQUIRES freertos log esp_driver_spi
)
