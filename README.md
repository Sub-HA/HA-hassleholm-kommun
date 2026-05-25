# Hässleholm Miljö – Home Assistant Integration

A custom Home Assistant integration that fetches your garbage collection schedule from [hassleholmmiljo.se](https://hassleholmmiljo.se) and exposes it as sensors and a calendar entity.

---

## What you get

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.next_pickup` | Sensor | ISO date of the next collection |
| `sensor.days_until_pickup` | Sensor | Number of days until next collection |
| `calendar.tomningskalender` | Calendar | All upcoming pickups shown in the HA calendar |

The **Next Pickup** sensor also has attributes:
- `address` – your address as shown on the site
- `pickup_type` – e.g. `Kärl1`, `Kärl1, Kärl2`, `Budad hämtning`
- `upcoming_pickups` – list of the next 10 pickups with date, types, and days_until

---

## Installation

### Via HACS (recommended)

1. In HACS → Integrations → ⋮ → Custom repositories
2. Add this repo URL, category: **Integration**
3. Install **Hässleholm Miljö Tömningskalender**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/hassleholm_miljo/` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Hässleholm Miljö**
3. Enter your **address alias** — find it in the URL when you look up your address on the website:
   ```
   https://hassleholmmiljo.se/...?alias=hmab-ekstigen-11-vittsjoe
                                         ^^^^^^^^^^^^^^^^^^^^^^^^
                                         paste this part
   ```
   You can also paste the full URL — it will be parsed automatically.
4. Set the update interval (default: 12 hours).

---

## Example automations

### Notification the evening before pickup

```yaml
automation:
  - alias: "Påminnelse sophämtning"
    trigger:
      - platform: time
        at: "19:00:00"
    condition:
      - condition: template
        value_template: "{{ states('sensor.days_until_pickup') | int == 1 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🗑️ Sophämtning imorgon!"
          message: >
            Kom ihåg att ställa ut kärlet.
            Typ: {{ state_attr('sensor.next_pickup', 'pickup_type') }}
```

### Morning of pickup

```yaml
automation:
  - alias: "Sopdag idag"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: template
        value_template: "{{ states('sensor.days_until_pickup') | int == 0 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🗑️ Sophämtning idag!"
          message: "{{ state_attr('sensor.next_pickup', 'pickup_type') }}"
```

---

## Dashboard card example

```yaml
type: entities
title: Sophämtning
entities:
  - entity: sensor.next_pickup
    name: Nästa hämtning
  - entity: sensor.days_until_pickup
    name: Dagar kvar
```

Or with a Markdown card:

```yaml
type: markdown
content: >
  ## 🗑️ Sophämtning
  
  **Nästa:** {{ states('sensor.next_pickup') }}  
  **Om:** {{ states('sensor.days_until_pickup') }} dagar  
  **Typ:** {{ state_attr('sensor.next_pickup', 'pickup_type') }}
```

---

## Troubleshooting

- **"invalid_alias"** – make sure you copy just the alias value after `?alias=` in the URL
- **"cannot_connect"** – check your internet connection or if the site is down
- The calendar only shows what's currently published on the site (typically a few months ahead)
