The component use Flower Care&trade; Smart Monitor to retrieve flower information (http://www.huahuacaocao.com/product).
HuaHuaCaoCao, in Chinese which means flowers & Plants.

Need to register to Flower Care&trade; Smart Monitor App 
<a href="https://play.google.com/store/apps/details?id=com.huahuacaocao.flowercare&hl=it" target="_blank">on Google Android devices</a> or 
<a href="https://apps.apple.com/it/app/flower-care/id1095274672" target="_blank">on Apple iOS devices</a> to use the component.

## Features

* Xiaomi mi flora sensor and Flower Care&trade; Smart Monitor integration
* Sensor optimal range applied using plant ID
* Retrieve general plant information
* Retrieve information to plant maintenance
* Retrieve plant image

## Configuration

1. Install your preferred Flower Care&trade; Smart Monitor App
2. Register your credentials in App, the same credentials will be used to configure the `huahuacaocao` integration component

### Component variables

**username**
>(string)(Required)<br>The username to use with your Flower Care&trade; Smart Monitor App.

**password**
>(string)(Required)<br>The corresponding password in yourFlower Care&trade; Smart Monitor App.

**region**
>(string)(Optional)<br>Your country code (two-letter)

#### Examples

```yaml
huahuacaocao:
  username: !secret huahuacaocao_user
  password: !secret huahuacaocao_password
  region: EU
```

### Sensor variables

**plant_id**
>(string)(Required)<br>Plant alias. You can find it in the Plant Archive panel of the Flower Care&trade; Smart Monitor App

**Name**
>(string)(Required)<br>Name to use in the frontend.

**sensors**
>(list)(Required)<br>List of sensor measure entities.

>**moisture**
>>(string)(Optional)<br>Moisture of the plant. Measured in %. Can have a min and max value set optionally.

>**battery**
>>(string)(Optional)<br>Battery level of the plant sensor. Measured in %. Can only have a min level set optionally.

>**temperature**
>>(string)(Optional)<br>Temperature of the plant. Measured in degrees Celsius. Can have a min and max value set optionally.

>**conductivity**
>>(string)(Optional)<br>Conductivity of the plant. Measured in µS/cm. Can have a min and max value set optionally.

>**brightness**
>>(string)(Optional)<br>Light exposure of the plant. Measured in Lux. Can have a min and max value set optionally.


#### Examples

```yaml
  - platform: huahuacaocao
    plant_id: "zamioculcas zamiifolia"
    name: "Plant Zamioculcas Zamiifolia"
    sensors:
      moisture: sensor.zamioculcas_zamiifolia_moisture
      battery: sensor.zamioculcas_zamiifolia_battery
      temperature: sensor.zamioculcas_zamiifolia_temperature
      conductivity: sensor.zamioculcas_zamiifolia_conductivity
      brightness: sensor.zamioculcas_zamiifolia_light_intensity
```

## Integration Examples

```yaml
huahuacaocao:
  username: !secret huahuacaocao_user
  password: !secret huahuacaocao_password
  region: EU
  
sensor:
  - platform: miflora
    mac: 'XX:XX:XX:XX:XX:XX'
    name: Zamioculcas Zamiifolia
    force_update: true
    median: 3
    monitored_conditions:
      - moisture
      - light
      - temperature
      - conductivity
      - battery

  - platform: huahuacaocao
    plant_id: "zamioculcas zamiifolia"
    name: "Plant Zamioculcas Zamiifolia"
    sensors:
      moisture: sensor.zamioculcas_zamiifolia_moisture
      battery: sensor.zamioculcas_zamiifolia_battery
      temperature: sensor.zamioculcas_zamiifolia_temperature
      conductivity: sensor.zamioculcas_zamiifolia_conductivity
      brightness: sensor.zamioculcas_zamiifolia_light_intensity
```

Home Assistant Flora Panel 

<img src="/.md.images/ha-plant-panel.png"  width="40%" height="40%" alt="Home Assistant plant panel">