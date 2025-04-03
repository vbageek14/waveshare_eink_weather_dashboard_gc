

# Waveshare-RPI Weather Display - Canada Only

This project uses a Rapsberry Pi along with an 7.5 inch e-paper display by Waveshare to provide weather data in form of a dashboard that includes current weather conditions, daily and hourly forecast as well as any active alerts in the selected area. 

This project was inspired by a similar [project](https://github.com/AbnormalDistributions/e_paper_weather_display) that used OpenWeatherMap API. Unfortunately, after updating the code to suit my needs (you can find the fork of the original project [here](https://github.com/vbageek14/waveshare_eink_weather_dashboard), I wasn't getting accurate weather datafrom OpenWeatherMap API in my region. Thus, I decided to look for another API and landed on the Government of Canada public API that offers weather data in XML format. It is provided by Environment and Climate Change Canada (ECCC) as part of their Meteorological Service of Canada (MSC) branch. For more information about this API, please consult this [website](https://eccc-msc.github.io/open-data/msc-datamart/readme_en/).

![Front](https://github.com/vbageek14/waveshare_eink_weather_dashboard_gc/blob/main/photos/RaspberryPi_ePaper_Weather_Display_Front.jpeg)
![Back](https://github.com/vbageek14/waveshare_eink_weather_dashboard_gc/blob/main/photos/RaspberryPi_ePaper_Weather_Display_Back.jpeg)

---

## Table of Contents
- [Components](#components)
- [Setup Instructions](#setup-instructions)
  - [Installation](#installation)
  - [Setup Guide](#setup-guide)
- [Running the Script](#running-the-script)
- [Setting up Automatic Updates (Cron)](#setting-up-automatic-updates-optional)
- [Repository Structure](#files-in-this-repository)
- [Credit and License](#credit-and-license)

### Components
- **Waveshare 7.5-inch e-Paper HAT**: [Purchased on Amazon](https://a.co/d/cKgyf4m). 
- **Raspberry Pi** (set up on a Pi 4 2GB RAM; any model should work except the Pi Zero without soldered headers).
- **SD card** (at least 8 GB).
- **Power supply** for the Raspberry Pi.
- **Ethernet connection (optional)** Mine is running on WiFi without noticeable issues but if your connection isn't stable or the device is located far from router, an Ethernet connection would be recommended.
- **5 x 7 inch photo frame**: The one in the image was purchased at Wal-Mart.

## Setup Instructions

### Installation
1. **Clone the Project**:
   Open a terminal and run:
   ```bash
   git clone https://github.com/vbageek14/waveshare_eink_weather_dashboard.git
   cd waveshare_eink_weather_dashboard
   ```
2. **Clone the e-Paper library**:
   This project requires the Waveshare e-Paper library. Clone it into the project library by running:
   ```bash
   git clone https://github.com/waveshare/e-Paper.git
   ```

3. **Install Python Libraries**:
   ```bash
   pip install pillow requests
   ```

### Setup Guide
1. **Customize the Government of Canada's Meteorological Service of Canada API URL**:
    Go to the [documentation directory](https://dd.weather.gc.ca/citypage_weather/docs/) of the MSC City Page Weather XML feed to find the city code for your location (e.g., s0000458 for Toronto). It should be available in the site_list_en.csv file. Then, plug the 2 letter province abbreviation (e.g., ON for Ontario) followed by the city code into the XML weather data file: (https://dd.weather.gc.ca/citypage_weather/xml/XX/XXXXXXXX.xml)     

2. **Customize Your Settings**:
   Edit the following user-defined settings at the top of `weather_dashboard.py`:
   - `BASE_URL`: the XML weather data file link from the above step
   - `LOCATION`: Name of the location to display (e.g., `Toronto``).
   - `CSV_OPTION`: Set this to `True` if you’d like to save a daily log of weather data in `records.csv`.

> **Note**: If you are not using a 7.5 inch Version 2 display, you will want to replace 'epd7in5_V2.py' in the 'lib' folder with the appropriate version from [Waveshare's e-Paper library](https://github.com/waveshare/e-Paper/tree/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd). Adjustments will be required for other screen sizes.

## Running the Script
1. **To Run Manually**:
   From the `e_paper_weather_display` directory, run:
   ```bash
   python weather_dashboard.py
   ```
   This will fetch the weather data and update the display immediately.

## Setting up Automatic Updates (Optional)
You can set up a scheduled update every 15 minutes using `crontab`. This will make sure your display updates automatically.

In the terminal, type:
```bash
crontab -e
```
Then, add the following line at the end of the file:
```bash
*/15 * * * * /usr/bin/python /home/pi/waveshare_eink_weather_dashboard_gc/weather_dashboard.py >> /home/pi/waveshare_eink_weather_dashboard/weather_display_gc.log 2>&1
```
- This command updates the display every 15 minutes.
- Be sure to replace `/home/pi/waveshare/eink_weather_dashboard_gc/` with the path where the project is stored, if different.

If you would like to set restrictions for when to run the update, you can do the following:
```bash
*/15 6-23 * * * /usr/bin/python /home/pi/waveshare_eink_weather_dashboard_gc/weather_dashboard.py >> /home/pi/waveshare_eink_weather_dashboarda_gc/weather_display.log 2>&1
```
- This command stops the updates from 12am until 7am.
## Files in This Repository
- **weather_dashboard.py**: Main script file that fetches weather data and updates the display.
- **lib/**: Contains display drivers for the Waveshare e-paper display.
- **font/** and **icons/**: Folders with fonts and icons used by the display.
- **photos/**: Sample images of the display.
- **current_conditions_records.csv** and **hourly_forecast_records.csv**: Optional log files for weather data if `CSV_OPTION` is enabled.
- **weather_dashboard_activity**: Records log messages generated by the program for troubleshooting

## Credit and License
- **Weather Icons**: All icons were obtained from [Flaticon](https://www.flaticon.com/free-icons/).
- **Code**: Licensed under [MIT License](http://opensource.org/licenses/mit-license.html).
- **Documentation**: Licensed under [CC BY 3.0](http://creativecommons.org/licenses/by/3.0).
