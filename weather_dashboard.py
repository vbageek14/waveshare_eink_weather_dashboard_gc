import os
import sys
import csv
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import requests
import xml.etree.ElementTree as ET

# Automatically add the 'lib' directory relative to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(os.path.dirname(__file__), 'e-Paper/RaspberryPi_JetsonNano/python/lib')
sys.path.append(lib_path)
from waveshare_epd import epd7in5_V2
epd = epd7in5_V2.EPD()

# User defined configuration
try:
    from config_private import LOCATION, BASE_URL
except ImportError:
    LOCATION = "XXXXX" # Add your location (e.g., Toronto) for it to be displayed in top right corner of dashboard
    BASE_URL = "https://dd.weather.gc.ca/citypage_weather/xml/XX/XXXXXXXXXX.xml" # Add the XML file link with your city code and province

FONT_DIR = os.path.join(os.path.dirname(__file__), 'font')
ICON_DIR = os.path.join(os.path.dirname(__file__), 'icons')
CSV_OPTION = True # if csv_option == True, a weather data will be appended to 'record.cs

# Initialize display
epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()

# Logging configuration for both file and console
LOG_FILE = os.path.join(os.path.dirname(__file__), 'weather_dashboard_activity.log')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use RotatingFileHandler for log rotation
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)  # 1MB file size, 3 backups
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(file_handler)

# Stream handler for logging to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(console_handler)

logger.info("Weather display script started.")

# Set fonts with specific sizes to match the old behavior
FONT_PATH = os.path.join(FONT_DIR, 'Font.ttc')
FONTS = {size: ImageFont.truetype(FONT_PATH, size) for size in [18, 20, 22, 30, 80]}
COLORS = {'black': 'rgb(0,0,0)', 'white': 'rgb(255,255,255)', 'grey': 'rgb(235,235,235)'}

# Fetch weather data
def fetch_weather_data():
    url = BASE_URL
    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        logging.info("Weather data fetched successfully.")
        return root
    except requests.RequestException as e:
        logging.error(f"Failed to fetch weather data: {e}")
        raise

# Process weather data
def process_weather_data(root):
    try:
        current_data = {}
	
	# Find 'warnings' element and extract descriptions
        warnings = root.find('warnings')  # Find the 'warnings' element
        if warnings is not None:
            warnings_list = []
            for event in warnings.findall('event'): 
                description = event.get('description')
                priority = event.get('priority')
                if description:
                    warnings_list.append(f"{description}")
        
            # Join multiple warnings with commas
            if warnings_list:
                current_data["alerts"] = ", ".join(warnings_list)
            else:
                current_data["alerts"] = None
        else:
            current_data["alerts"] = None

        # Locate current weather conditions in XML file
        current_conditions = root.find('currentConditions')

        # Loop through dateTime elements for observation in EDT zone
        for date_time in current_conditions.findall('dateTime'):
            if date_time.get('name') == 'observation' and date_time.get('zone') == 'EDT':
                # Extract date and time in 'month/day/year hour:minute'
                year = date_time.find('year').text
                month = date_time.find('month').text
                day = date_time.find('day').text
                hour = date_time.find('hour').text
                minute = date_time.find('minute').text

                full_date = f"{month}/{day}/{year} {hour}:{minute}"
                current_data["full_date"] = full_date
            

        # Extract current weather  conditions
        current_data["temperature"] = current_conditions.find('temperature').text if current_conditions.find('temperature') is not None else None
        current_data["wind_chill"] = current_conditions.find('windChill').text if current_conditions.find('windChill') is not None else None
        current_data["pressure"] = current_conditions.find('pressure').text if current_conditions.find('pressure') is not None else None
        current_data["humidity"] = current_conditions.find('relativeHumidity').text if current_conditions.find('relativeHumidity') is not None else None
        current_data["wind_speed"] = current_conditions.find('wind/speed').text if current_conditions.find('wind/speed') is not None else None
        current_data["wind_direction"] = current_conditions.find('wind/direction').text if current_conditions.find('wind/direction') is not None else None
        current_data["condition"] = current_conditions.find('condition').text if current_conditions.find('condition') is not None else None
        current_data["icon_code"] = current_conditions.find('iconCode').text if current_conditions.find('iconCode') is not None else None
    
        # Extract sunset and sunrise data
        sunrise_sunset_group = root.find('riseSet')
    
        if sunrise_sunset_group is not None:
            # Loop through dateTime elements for 'sunrise' and 'sunset' in EDT zone
            for date_time in sunrise_sunset_group.findall('dateTime'):
                if date_time.get('name') == 'sunrise' and date_time.get('zone') == 'EDT':
                    # Extract sunrise time
                    sunrise_time = date_time.find('textSummary').text if date_time.find('textSummary') is not None else None
                    if sunrise_time:
                        sunrise_time = sunrise_time.split(' at ')[-1].replace('EDT', '').strip()
                        sunrise_time = datetime.strptime(sunrise_time, '%H:%M')
                        sunrise_time = sunrise_time.strftime('%I:%M %p').lower()
                    current_data["sunrise_time"] = sunrise_time
                elif date_time.get('name') == 'sunset' and date_time.get('zone') == 'EDT':
                    # Extract sunset time
                    sunset_time = date_time.find('textSummary').text if date_time.find('textSummary') is not None else None
                    if sunset_time:
                        sunset_time = sunset_time.split(' at ')[-1].replace('EDT', '').strip()
                        sunset_time = datetime.strptime(sunset_time, '%H:%M')
                        sunset_time = sunset_time.strftime('%I:%M %p').lower()
                        current_data["sunset_time"] = sunset_time
    
        # Process forecast data for upcoming weather
        forecast_data = []
        forecast_group = root.find('forecastGroup')
        if forecast_group is not None:
            # Loop through each forecast period
            for forecast in forecast_group.findall('forecast'): 
                # Extract forecast details
                period = forecast.find('period').text if forecast.find('period') is not None else None
                text_summary = forecast.find('cloudPrecip/textSummary').text if forecast.find('cloudPrecip/textSummary') is not None else None
                temperature = forecast.find('temperatures/temperature').text if forecast.find('temperatures/temperature') is not None else None
                winds = forecast.find('winds')
                precipitation_type = forecast.find('precipitation/precipType').text if forecast.find('precipitation/precipType') is not None else None
                accumulation = forecast.find('precipitation/accumulation/amount')
                accumulation = accumulation.text if accumulation is not None else None
                accumulation_percentage = forecast.find('abbreviatedForecast/pop')
                accumulation_percentage = accumulation_percentage.text if accumulation_percentage is not None else None
                icon_code = forecast.find('abbreviatedForecast/iconCode')
                icon_code = icon_code.text if icon_code is not None else None
                wind_chill = forecast.find('windChill/calculated')
                wind_chill = wind_chill.text if wind_chill is not None else None

                # Append extracted forecast data to list
                forecast_data.append({
                    "period": period,
                    "text_summary": text_summary,
                    "temperature": temperature,
                    "precipitation_type": precipitation_type,
                    "accumulation": accumulation,
                    "accumulation_percentage": accumulation_percentage,
                    "icon_code": icon_code,
                    "wind_chill": wind_chill
                    })
        
        # Process hourly forecast data
        hourly_forecast_data = []
        hourly_forecast_group = root.find('hourlyForecastGroup')
        if hourly_forecast_group is not None:
            # Loop through each hourly forecast
            for hourly_forecast in hourly_forecast_group.findall('hourlyForecast'): 
                time = hourly_forecast.get("dateTimeUTC")

                edt_time = convert_utc_to_edt(time)
                
                # Extract hourly forecast data
                temperature = hourly_forecast.find('temperature')
                temperature = temperature.text if temperature is not None else None
                lop = hourly_forecast.find('lop')
                lop = lop.text if lop is not None else None
                icon_code = hourly_forecast.find('iconCode')
                icon_code = icon_code.text if icon_code is not None else None
                wind_chill = hourly_forecast.find('windChill')
                wind_chill = wind_chill.text if wind_chill is not None else None
                uv_index = hourly_forecast.find('uv')
                uv_index_value = uv_index.find('index').text if uv_index is not None else None

                # Append hourly forecast data to list
                hourly_forecast_data.append({
                    "time": edt_time,
                    "temperature": temperature,
                    "lop": lop,
                    "icon_code": icon_code,
                    "wind_chill": wind_chill,
                    "uv_index": uv_index_value
                    })     
                
        logging.info("Weather data processed successfully.")
        return current_data, forecast_data, hourly_forecast_data

    except KeyError as e:
        logging.error(f"Error processing weather data: {e}")
        raise

def is_daylight_saving_time(date):
    """Returns True if the given date is in Daylight Saving Time (DST) in Ottawa (Eastern Time)."""
    year = date.year
    # Find the second Sunday in March
    march_start = datetime(year, 3, 1)
    second_sunday_march = march_start + timedelta(days=(6 - march_start.weekday() + 7) % 7)
    # Find the first Sunday in November
    november_start = datetime(year, 11, 1)
    first_sunday_november = november_start + timedelta(days=(6 - november_start.weekday()) % 7)
    return second_sunday_march <= date < first_sunday_november

def convert_utc_to_edt(utc_string):
    """Converts a UTC dateTime string (YYYYMMDDHHMM) to EDT/EST."""
    # Parse the dateTimeUTC string
    utc_time = datetime.strptime(utc_string, "%Y%m%d%H%M")
    
    # Determine offset (-4 for EDT, -5 for EST)
    offset = -4 if is_daylight_saving_time(utc_time) else -5
    
    # Convert to Eastern Time
    edt_time = utc_time + timedelta(hours=offset)
    
    # Return formatted time
    return edt_time.strftime("%m/%d/%Y %I:%M %p")

def save_to_csv(current_data, hourly_forecast_data):
    """Saves weather records to CSV file."""        
    if not CSV_OPTION:
        return
    try:
	    # Append current weather conditions to the CSV file
        with open(os.path.join(os.path.dirname(__file__), 'current_conditions_records.csv'), 'a', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                current_data["full_date"],
                LOCATION,
                current_data["temperature"],
                current_data["wind_chill"],
                current_data["humidity"],
                current_data["wind_speed"],
                current_data["wind_direction"],
                current_data["sunrise_time"],
                current_data["sunset_time"],
                current_data["pressure"]
                ])
        logging.info("Current data appended to CSV.")

        # Append hourly forecast data to a separate CSV file
        with open(os.path.join(os.path.dirname(__file__),'hourly_forecast_records.csv'), 'a' , newline='') as csv_file:
            writer = csv.writer(csv_file)
            for hourly_forecast in hourly_forecast_data:
                writer.writerow([
                    hourly_forecast["time"],
                    hourly_forecast["temperature"],
                    hourly_forecast["lop"],
                    hourly_forecast["wind_chill"],
                    hourly_forecast["uv_index"]
                ])

        logging.info("Hourly forecast data appeneded to CSV.")
        
        # Remove duplicate entries based on "time" column from the current conditions CSV
        unique_records = {}
        with open(os.path.join(os.path.dirname(__file__),'current_conditions_records.csv'), 'r', newline='') as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                if row:  # Ensure the row is not empty
                    time_value = row[0]  # Assuming "time" is the first column
                    unique_records[time_value] = row  # Store only the latest entry for each time
        
        # Write back the unique records to the CSV file
        with open(os.path.join(os.path.dirname(__file__), 'current_conditions_records.csv'), 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(unique_records.values())
        logging.info("Duplicate entries removed based on time.")

    except IOError as e:
        logging.error(f"Failed to save data to CSV: {e}")

def generate_display_image(current_data, forecast_data, hourly_forecast_data):
    try:
        # Create a blank canvas (7.5-inch screen size is 800x480 pixels for this model)
        template = Image.new('1', (epd.width, epd.height), 255)
        draw = ImageDraw.Draw(template)

        # Set icon size
        icon_size = (35, 35)

        # Extract and format the last update time
        date_time_str = current_data['full_date']
        date_time_obj = datetime.strptime(date_time_str, "%m/%d/%Y %H:%M")
        formatted_date_time = date_time_obj.strftime("%m/%d/%Y %I:%M %p").lower()

        # Get text width to right-align elements
        date_time_bbox = draw.textbbox((0, 0), formatted_date_time, font=FONTS[30])
        date_time_width = date_time_bbox[2] - date_time_bbox[0]
        x_position = epd.width  - 25  # 25px padding from the right edge

        # Draw the last update time and location
        draw.text((x_position - date_time_width, 25), formatted_date_time, font=FONTS[30], fill=COLORS['black'])
        location_bbox = draw.textbbox((0, 0), LOCATION, font=FONTS[30])
        location_width = location_bbox[2] - location_bbox[0]
        draw.text((x_position - location_width, 60), LOCATION, font=FONTS[30], fill=COLORS['black'])

        # Display weather alerts
        alert_text = f"Alert(s): {current_data['alerts']}" if current_data['alerts'] else "No active alerts"
        draw.text((45, 210), alert_text, font=FONTS[18], fill=COLORS['black'])        

        # Load and display current weather icon
        icon_path = os.path.join(ICON_DIR, f"{current_data['icon_code']}.png")
        if os.path.exists(icon_path):
            icon_image = Image.open(icon_path).resize((150, 150))
            template.paste(icon_image, (40, 10))

        # Display current temperature
        if current_data['temperature'] is not None:
            draw.text((240, 20), f"{float(current_data['temperature']):.0f}°C", font=FONTS[80], fill=COLORS['black'])
        # Display wind chill
        wind_chill = current_data['wind_chill'] if current_data['wind_chill'] is not None else current_data['temperature']
        if wind_chill is not None:
            draw.text((240, 110), f"Wind chill: {float(wind_chill):.0f}°C", font=FONTS[30], fill=COLORS['black'])

        # Display weather condition description
        if current_data['condition'] is not None:
            draw.text((240, 155), f"{current_data['condition']}", font=FONTS[22], fill=COLORS['black'])

        # Display wind and humidity icons and values
        for icon_file, pos, key, unit in [
            ("wind_icon.png", (40, 420), 'wind_speed', " km/h"),
            ("humidity_icon.png", (40, 270), 'humidity', "%")
        ]:
            icon = Image.open(os.path.join(ICON_DIR, icon_file)).resize(icon_size)
            template.paste(icon, pos)

            if current_data[key] is not None:
                draw.text((pos[0] + 40, pos[1]), f"{float(current_data[key]):.1f}{unit}", font=FONTS[22], fill=COLORS['black'])

        # Display sunrise and sunset times
        for icon_file, pos, key in [
            ("sunrise_icon.png", (40, 320), 'sunrise_time'),
            ("sunset_icon.png", (40, 370), 'sunset_time')
        ]:
            icon = Image.open(os.path.join(ICON_DIR, icon_file)).resize(icon_size)
            template.paste(icon, pos)
    
            if current_data[key] is not None:
                draw.text((pos[0] + 40, pos[1]), current_data[key], font=FONTS[22], fill=COLORS['black'])

        # Display forecast for next 4 periods (arranged in two columns)
        y_offset_start = 270  # Starting y-position for the first forecast item
        x_offset_start = 220  # Fixed x-position for all items
        x_offset_shift = 190 # Shift for the second column
        y_spacing = 100  # Space between each forecast item

        for i, day in enumerate(forecast_data[1:5]):
            icon_path = os.path.join(ICON_DIR, f"{day['icon_code']}.png")
            icon_image = Image.open(icon_path) if os.path.exists(icon_path) else None
    
            row = i // 2  # Determine which column (0 for left, 1 for right)
            column = i % 2  # Determine position in the column
    
            x_offset = x_offset_start + (column * x_offset_shift)
            y_offset = y_offset_start + (row * y_spacing)

            icon_path = os.path.join(ICON_DIR, f"{day['icon_code']}.png")
            icon_image = Image.open(icon_path) if os.path.exists(icon_path) else None
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path).resize((40, 40))
                template.paste(icon_image, (x_offset, y_offset))
 
            if day.get('period'):
                period = day['period']
                parts = period.split()
                day_abbr = parts[0][:3]  # Take the first three letters of the first word
                display_period = f"{day_abbr} night" if "night" in period.lower() else day_abbr
                draw.text((x_offset + 50, y_offset + 5), display_period, font=FONTS[22], fill=COLORS['black'])
    
            if day['temperature'] is not None:
                draw.text((x_offset + 50, y_offset + 30), f"Temp: {float(day['temperature']):.0f}°C", font=FONTS[20], fill=COLORS['black'])
    
            if day['wind_chill'] is not None:
                draw.text((x_offset + 50, y_offset + 50), f"W. Chill: {float(day['wind_chill']):.0f}°C", font=FONTS[20], fill=COLORS['black'])
                y_offset += 20  # Shift accumulation if wind chill exists
            if day['accumulation_percentage'] is not None:
                draw.text((x_offset + 50, y_offset + 50), f"{float(day['accumulation_percentage']):.0f}%", font=FONTS[20], fill=COLORS['black'])

        # Display hourly forecast (next 8 hours) in the right section
        hourly_x_offset = 605 
        hourly_y_offset = 130
        y_spacing = 42
        for i, hour in enumerate(hourly_forecast_data[:8]):
            icon_path = os.path.join(ICON_DIR, f"{hour['icon_code']}.png")

            y_position = hourly_y_offset + (i * y_spacing)
            
            # Display time first
            if hour['time'] is not None:
                time_obj = datetime.strptime(hour["time"], ("%m/%d/%Y %I:%M %p"))
                time_str = time_obj.strftime("%I:%M %p")
                draw.text((hourly_x_offset, y_position), time_str, font=FONTS[20], fill=COLORS['black'])
            
            # Display corresponding icon
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path).resize((40, 40))
                template.paste(icon_image, (hourly_x_offset + 90, y_position - 5))
            
            # Display temperature
            if hour['temperature'] is not None:
                draw.text((hourly_x_offset + 135, y_position), f"{float(hour['temperature']):.0f}°C", font=FONTS[20], fill=COLORS['black'])
        
        logging.info("Display image generated successfully.")
        return template

    except Exception as e:
        logging.error(f"Error generating display image: {e}")
        raise


# Display image on screen
def display_image(image):
    try:
        h_image = Image.new('1', (epd.width, epd.height), 255)
        h_image.paste(image, (0, 0))
        epd.display(epd.getbuffer(h_image))
        logging.info("Image displayed on e-paper successfully.")
    except Exception as e:
        logging.error(f"Failed to display image: {e}")
        raise


# Main function
def main():
    try:
        data = fetch_weather_data()
        current_data, forecast_data, hourly_forecast_data  = process_weather_data(data)
        save_to_csv(current_data, hourly_forecast_data)
        image = generate_display_image(current_data, forecast_data, hourly_forecast_data)
        display_image(image)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
