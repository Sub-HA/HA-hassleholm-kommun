"""Constants for the Hässleholm Miljö integration."""

DOMAIN = "hassleholm_miljo"

BASE_URL = "https://hassleholmmiljo.se/privat/sophamtning/tomningskalender"

DEFAULT_SCAN_INTERVAL = 12  # hours

ALIAS_PREFIX = "hmab"

CONF_ALIAS = "alias"
CONF_SCAN_INTERVAL = "scan_interval"

ATTR_NEXT_PICKUP = "next_pickup"
ATTR_PICKUP_TYPE = "pickup_type"
ATTR_UPCOMING = "upcoming_pickups"
ATTR_ADDRESS = "address"

SWEDISH_MONTHS = {
    "Januari": 1, "Februari": 2, "Mars": 3, "April": 4,
    "Maj": 5, "Juni": 6, "Juli": 7, "Augusti": 8,
    "September": 9, "Oktober": 10, "November": 11, "December": 12,
}
