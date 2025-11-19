###### Imports ######
import pandas as pd
import requests
import urllib3
import sys
import urllib3
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
pd.options.mode.chained_assignment = None
from datetime import datetime, timedelta
import re
import math
import webbrowser
import matplotlib as mpl
from timezonefinder import TimezoneFinder
import pytz
from suntime import Sun

tab10 = plt.get_cmap('tab10')

##################### Functions #####################

aspect_dict = {'N':0,
     'NNE':22.5,
     'NE':45,
     'ENE':67.5,
     'E':90,
     'ESE':112.5,
     'SE':135,
     'SSE':157.5,
     'S':180,
     'SSW':202.5,
     'SW':225,
     'WSW':247.5,
     'W':270,
     'WNW':292.5,
     'NW':315,
     'NNW':337.5}

def human_aspect(deg):
    for aspect,aspect_deg in aspect_dict.items():
        if abs(deg-aspect_deg) < 22.5:
            final_aspect = aspect
            return final_aspect

def parse_time_period(time_string):
    time_list = time_string.split('/')
    start_time = pd.to_datetime(time_list[0]) - pd.Timedelta(time_list[1])
    end_time = pd.to_datetime(time_list[0])
    return start_time,end_time

def parse_time_period2(time_string):
    time_list = time_string.split('/')
    end_time = pd.to_datetime(time_list[0]) + pd.Timedelta(time_list[1])
    start_time = pd.to_datetime(time_list[0])
    return start_time,end_time

def get_snotel_df(SiteName, years = 'recent'):
    SiteID = site_df.loc[SiteName]['snotel_sitenumber']
    snotel_site_name = site_df.loc[SiteName]['snotel_sitename']
    StateAbb = site_df.loc[SiteName]['state']
    ############## Snotel
    today_string = datetime.today().date().strftime('%Y-%m-%d')
    threedaysago_string = (datetime.today() - timedelta(days = 8)).date().strftime('%Y-%m-%d')
    if years == 'recent':
        StartDate = threedaysago_string
        EndDate = today_string
    else:
        yearsago_string = (datetime.today() - timedelta(days = years*365)).date().strftime('%Y-%m-%d')
        StartDate = yearsago_string
        EndDate = today_string
        

    # Example URL for Hourly snow report for bear lake
    #     https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customMultiTimeSeriesGroupByStationReport/hourly/start_of_period/322:CO:SNTL%257Cid=%2522%2522%257Cname/2025-01-07,2025-01-09/SNWD::value,WTEQ::value,TAVG::value,WDIRV::value,WSPDV::value?fitToScreen=false
    #     Basically all the column options:
    #     https://wcc.sc.egov.usda.gov/reportGenerator/view/customMultiTimeSeriesGroupByStationReport/hourly/start_of_period/322:CO:SNTL%257Cid=%2522%2522%257Cname/2025-02-14,2025-02-18/
    column_list = ['WTEQ','SNWD','PREC','TOBS','WDIRV','WSPDV','WSPDX']
    url1 = 'https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customMultiTimeSeriesGroupByStationReport/hourly/start_of_period/'
    url2 = f'{SiteID}:{StateAbb}:SNTL%257Cid=%2522%2522%257Cname/'
    url3 = f'{StartDate},{EndDate}/'
    column_list = ['WTEQ','SNWD','PREC','TOBS','WDIRV','WSPDV','WSPDX']
    url4 = ','.join([col + '::value' for col in column_list])
    url5 = '?fitToScreen=false'
    url = url1+url2+url3+url4+url5
    print('Snotel URL:',url)
    human_snotel_url = f'https://wcc.sc.egov.usda.gov/nwcc/site?sitenum={SiteID}'
    print(f'  (for humans): {human_snotel_url}')

    print(f'Start retrieving SNOTEL data for {snotel_site_name}, {SiteID}')

    http = urllib3.PoolManager()
    response = http.request('GET', url)
    data = response.data.decode('utf-8')
    print('     Received SNOTEL data')

    i=0
    for line in data.split("\n"):
        if line.startswith("#"):
            i=i+1
    data = data.split("\n")[i:]

    snotel_df = pd.DataFrame.from_dict(data)
    print('     Made dataframe')

    snotel_df = snotel_df[0].str.split(',', expand=True)
    
    snotel_df.rename(columns={0:snotel_df[0][0], 
                        1:snotel_df[1][0], 
                        2:snotel_df[2][0],
                        3:snotel_df[3][0],
                        4:snotel_df[4][0],
                        5:snotel_df[5][0],
                        6:snotel_df[6][0],
                        7:snotel_df[7][0]}, inplace=True)

    snotel_df.rename(columns = {f'{snotel_site_name} ({SiteID}) Snow Depth (in)':'snow_depth_in',
                                f'{snotel_site_name} ({SiteID}) Snow Water Equivalent (in)':'swe_in',
                                f'{snotel_site_name} ({SiteID}) Air Temperature Average (degF)':'temperature_f',
                                f'{snotel_site_name} ({SiteID}) Wind Direction Average (degree)':'wind_dir',
                                f'{snotel_site_name} ({SiteID}) Wind Speed Average (mph)':'wind_speed',
                                f'{snotel_site_name} ({SiteID}) Precipitation Accumulation (in)':'precipitation_accumulation',
                                f'{snotel_site_name} ({SiteID}) Air Temperature Observed (degF)':'temperature_observed',
                                f'{snotel_site_name} ({SiteID}) Wind Speed Maximum (mph)':'wind_speed_max'}, inplace = True)
    snotel_df.drop(0, inplace=True)
    snotel_df.dropna(inplace=True)
    snotel_df.reset_index(inplace=True, drop=True)
    snotel_df["Date"] = pd.to_datetime(snotel_df["Date"])

    for col in snotel_df.columns:
        if col != 'Date':
            snotel_df[col] = pd.to_numeric(snotel_df[col])

    print('     Getting new snow totals')
    # snotel_df['snow_depth_in'] = snotel_df['snow_depth_in'].rolling(window=3).mean()
    snotel_df['new_snow'] = snotel_df['snow_depth_in'].diff()
    snotel_df['new_swe'] = snotel_df['swe_in'].diff()
    snotel_df['day'] = snotel_df['Date'].dt.dayofweek
    snotel_df['color'] = snotel_df['day'].apply(lambda x:tab10(x))

    
    print('     rolling average')
    # print(new_snow_24h)
    # snotel_df_24h.plot.bar(x = 'Date', y = 'snow_depth_in', ylim = (35,45))
    return snotel_df


def split_name_num(text):
    result = list(re.findall('(.+) \((\d+)\)',text)[0])
    return result





def get_nearest_snotel_site(name, lat, lon):
    # if name not in site_df.index:
    #     raise ValueError(f'Could not find {name} in sites.csv. Please add it to the file.')
    # lat = site_df.loc[name]['lat']
    # lon = site_df.loc[name]['lon']
    # print(name, lat, lon)


    snotel_sites_df['lat_dist'] = lat - snotel_sites_df['lat']
    snotel_sites_df['lon_dist'] = lon - snotel_sites_df['lon']
    def get_dist(row):
        return math.sqrt(row['lat_dist']**2 + row['lon_dist']**2)


    snotel_sites_df['dist'] = snotel_sites_df.apply(get_dist, axis=1)
    # display(snotel_sites_df[snotel_sites_df['dist'] == snotel_sites_df['dist'].min()])
    closest_snotel_site_df = snotel_sites_df[snotel_sites_df['dist'] == snotel_sites_df['dist'].min()]
    closest_snotel_site = closest_snotel_site_df.reset_index().loc[0]['name']
    sitenumber = closest_snotel_site_df.reset_index().loc[0]['number']
    state = closest_snotel_site_df.reset_index().loc[0]['state']
    # return closest_snotel_site
    return pd.Series({'snotel_sitename':closest_snotel_site,
                      'snotel_sitenumber':sitenumber,
                      'state':state})

def get_new_snow(snotel_df):
    yesterday_string = (datetime.today() - timedelta(days = 1)).date().strftime('%Y-%m-%d')
    snotel_df_24h = snotel_df[snotel_df['Date'] > yesterday_string]

    new_snow_24h = snotel_df_24h[snotel_df_24h['new_snow'] >= 0]['new_snow'].sum()
    return new_snow_24h

def get_new_snow_and_df(SiteName):
    snotel_df = get_snotel_df(SiteName)
    new_snow_24h = get_new_snow(snotel_df)
    return new_snow_24h

############## Import Sites ##############

snotel_sites_df = pd.read_csv('snotel_sites.csv') # From https://wcc.sc.egov.usda.gov/nwcc/yearcount?network=sntl&state=&counttype=statelist
snotel_sites_df[['name','number']] = snotel_sites_df['site_name'].apply(lambda x: pd.Series(split_name_num(x)))
snotel_sites_df.set_index('name', inplace= True)

site_df = pd.read_csv('sites.csv')
site_df[['snotel_sitename','snotel_sitenumber','state']] = site_df.apply(lambda x: get_nearest_snotel_site(x['name'],x['lat'],x['lon']), axis = 1)
site_df.set_index('name', inplace = True)
if int(site_df.index.value_counts().max()) > 1:
    raise ValueError('Duplicate Entries in sites.csv file. All names must be unique')

########### Get Snotel Data and Plot ##############
for SiteName in ['Bear Lake', 'Longmont']:
    SiteID = site_df.loc[SiteName]['snotel_sitenumber']
    human_snotel_url = f'https://wcc.sc.egov.usda.gov/nwcc/site?sitenum={SiteID}'
    lat = site_df.loc[SiteName]['lat']
    lon = site_df.loc[SiteName]['lon']

    co_sites_df = snotel_sites_df[snotel_sites_df['state'] == 'CO']

    snotel_df = get_snotel_df(SiteName)
    new_snow_24h = get_new_snow(snotel_df)


    ################ NOAA Forecast
    forecast_url = f'https://api.weather.gov/points/{lat},{lon}'
    print('Checking NOAA forecast landing page')
    print(f'    {forecast_url}')
    forecast_landing_data = requests.get(forecast_url)
    # print(f'     converting to JSON')
    forecast_landing_json = forecast_landing_data.json()
    hourly_forecast_url = forecast_landing_json['properties']['forecastHourly']
    print(f'Retrieving NOAA Forecast for {lat}, {lon}')
    print(f'      {hourly_forecast_url}')
    human_noaa_url = f'https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}'
    print(f'      For Humans: {human_noaa_url}')
    hourly_forecast_data = requests.get(hourly_forecast_url)
    # print(f'     converting to json')
    hourly_forecast_json = hourly_forecast_data.json()
    # print('     Received NOAA data')
    hourly_forecast_df = pd.json_normalize(hourly_forecast_json['properties']['periods'])
    # hourly_forecast_df['startTime'] = pd.to_datetime(hourly_forecast_df['startTime']) # This just quit working
    hourly_forecast_df['startTime'] = pd.to_datetime(hourly_forecast_df['startTime'], utc = True)
    hourly_forecast_df['startTime'] = hourly_forecast_df['startTime'].dt.tz_localize(None) # Remove time zone since snowfall data doesn't have a timezone
    hourly_forecast_df['endTime'] = pd.to_datetime(hourly_forecast_df['endTime'])




    grid_data_url = forecast_landing_json['properties']['forecastGridData']
    print(f'Retrieving NOAA snowfall data')
    print(f'      {grid_data_url}')
    grid_data_data = requests.get(grid_data_url)
    print('     converting to json')
    grid_data_json = grid_data_data.json()
    print('     Received snowfall and skycover data')
    snowfall_df = pd.json_normalize(grid_data_json['properties']['snowfallAmount']['values'])
    skycover_df = pd.json_normalize(grid_data_json['properties']['skyCover']['values'])
    precip_prob_df = pd.json_normalize(grid_data_json['properties']['probabilityOfPrecipitation']['values'])

    print('     Parsing snowfall data')
    snowfall_df['startTime'] = snowfall_df['validTime'].apply(lambda x: parse_time_period2(x)[0])
    snowfall_df['endTime'] = snowfall_df['validTime'].apply(lambda x: parse_time_period2(x)[1])

    print('     Parsing skycover data')
    skycover_df['startTime'] = skycover_df['validTime'].apply(lambda x: parse_time_period2(x)[0])
    skycover_df['endTime'] = skycover_df['validTime'].apply(lambda x: parse_time_period2(x)[1])

    print('     Parsing precip prob data')
    precip_prob_df['startTime'] = precip_prob_df['validTime'].apply(lambda x: parse_time_period2(x)[0])
    precip_prob_df['endTime'] = precip_prob_df['validTime'].apply(lambda x: parse_time_period2(x)[1])



    # Getting hourly snowfall and merging with main df
    print("     Generating hourly snowfal data")
    hourly_snowfall_df = pd.DataFrame(columns = ['startTime','snowfall_mm'])
    for line in snowfall_df.iterrows():
        snowfall = line[1]['value']
        start_time = line[1]['startTime']
        end_time = line[1]['endTime']
        duration_hours = (end_time-start_time).total_seconds()/(60*60)
        snowfall_per_hour = snowfall/duration_hours
        for i in range(int(duration_hours)):
            hourly_snowfall_df.loc[len(hourly_snowfall_df)] = [start_time + timedelta(hours = i), snowfall_per_hour]

    hourly_snowfall_df['startTime'] = pd.to_datetime(hourly_snowfall_df['startTime'])
    hourly_snowfall_df['startTime'] = hourly_snowfall_df['startTime'].dt.tz_localize(None) # Remove time zone since snowfall data doesn't have a timezone

    noaa_df = hourly_snowfall_df.merge(hourly_forecast_df, on = 'startTime', how = 'inner')

    noaa_df['snowfall_in'] = noaa_df['snowfall_mm'] / 25.4
    noaa_df['total_snowfall_in'] = noaa_df['snowfall_in'].cumsum() # Sums all previous snowfall amounts to give total snowfall
    noaa_df['windSpeed_mph'] = noaa_df['windSpeed'].apply(lambda x: float(x.split(' ')[0]))

    print('Calculating Wind Direction')
    dir_list = ['N','NNW','NW','WNW','W','WSW','SW','SSW','S','SSE','SE','ESE','E','ENE','NE','NNE']
    direction_dict = {}

    noaa_df = noaa_df[noaa_df['windDirection'].isin(dir_list)]
    for i, dir in enumerate(dir_list):
        angle = 22.5*i
        scale = 0.1
        direction_dict[dir] = (scale*math.sin(angle*math.pi/180),-scale*math.cos(angle*math.pi/180))

    noaa_df['wind_x'] = noaa_df['windDirection'].apply(lambda x: direction_dict[x][0])
    noaa_df['wind_y'] = noaa_df['windDirection'].apply(lambda x: direction_dict[x][1])
    noaa_df['total_hours'] = (noaa_df['startTime']-noaa_df['startTime'].min()).dt.total_seconds()/(60*60)

    # Change timezones


    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lon)
    timezone = pytz.timezone(timezone_str)
    dt = datetime.now()
    timezone_diff = timezone.utcoffset(dt)

    # timezone_diff = timedelta(hours = 6)
    for df in [noaa_df,skycover_df, precip_prob_df]:
        df['startTime_utc'] = df['startTime']
        df['endTime_utc'] = df['endTime']
        df['startTime_local'] = df['startTime_utc'] + timezone_diff
        df['endTime_local'] = df['endTime_utc'] + timezone_diff

    #Interpolating precip prob df
    precip_prob_df_simple = pd.DataFrame(columns = ['time_local','value'])
    for index, line in precip_prob_df.iterrows():
        current_time = line['startTime_local']
        end_time = line['endTime_local']
        while current_time <= end_time:
            precip_prob_df_simple.loc[len(precip_prob_df_simple)] = [current_time, line['value']]
            current_time += timedelta(hours = 1)

    ### Sunrise and Sunset ####
    sun_df = pd.DataFrame(columns = ['date','sunrise','sunset','next_sunrise'])
    for date in noaa_df.startTime_local.dt.date.unique():
        sun = Sun(lat, lon)
        
        sunrise_time = (sun.get_local_sunrise_time(date) + timezone_diff).time()
        sunrise = datetime.combine(date,sunrise_time)
        sunset_time = (sun.get_local_sunset_time(date) + timezone_diff).time()
        sunset = datetime.combine(date,sunset_time)
        next_sunrise = sun.get_local_sunrise_time(date + timedelta(days = 1)) + timezone_diff
        sun_df.loc[len(sun_df)] = [date, sunrise, sunset, next_sunrise]

    ########### Plotting ##################
    print("plotting")
    fig, ax = plt.subplots(4, sharex=True)
    fig.set_figwidth(10)
    fig.set_figheight(7)

    min_time = noaa_df['startTime_local'].min()
    max_time = noaa_df['startTime_local'].max()

    temp_norm = plt.Normalize(22, 42)

    temp_plot = noaa_df.plot.scatter(x = 'startTime_local', y = 'temperature', ax = ax[0], xlim = (min_time, max_time), c = 'temperature', cmap = 'coolwarm', norm = temp_norm)
    ax[0].collections[0].colorbar.remove()
    ax[0].set_ylabel('Temperature (F)')
    ax[0].scatter(x = sun_df.sunrise, y = [noaa_df['temperature'].min()-5 for n in range(len(sun_df))], marker='$\u263C$', c = 'gold')
    ax[0].scatter(x = sun_df.sunset, y = [noaa_df['temperature'].min()-5 for n in range(len(sun_df))], marker='$\u263E$')



    snowfall_norm = plt.Normalize(0,0.5)
    noaa_df.plot.scatter(x = 'startTime_local', y = 'total_snowfall_in', ax = ax[1], xlim = (min_time, max_time), c = 'snowfall_in', norm = snowfall_norm, cmap = 'viridis')
    ax[1].collections[0].colorbar.remove()
    ax[1].set_ylabel('Snowfall (in)')

    ax11 = ax[1].twinx()
    noaa_df.plot(x = 'startTime_local', y = 'snowfall_in', ax = ax11, xlim = (min_time, max_time), c = tab10(1), x_compat=True, alpha = 0.3, legend = False, label = 'Snowfall Rate')
    ax11.set_ylabel('Snowfall Rate (in/hour)')
    ax11.fill_between(noaa_df['startTime_local'], noaa_df['snowfall_in'], 0, color=tab10(1), alpha=0.3)
    from labellines import labelLine, labelLines
    labelLines(ax11.get_lines(), zorder=2.5, align = True, xvals = [0.5], yoffsets=[0.15])

    for axis in ax:
        plt.grid(True)
        axis.grid(which='major', color='#DDDDDD', linewidth=0.8)
        axis.grid(which='minor', color='#EEEEEE', linestyle=':', linewidth=0.5)

    skycover_df.plot(x = 'startTime_local', y = 'value', ax = ax[2], label = 'Skycover', c = '#a3a3a3', x_compat = True, legend = False)
    ax[2].fill_between(skycover_df['startTime_local'], skycover_df['value'], 0, color='#a3a3a3', alpha=0.3)
    ax[2].fill_between(skycover_df['startTime_local'], skycover_df['value'], 100, color='#6bc9ff', alpha=0.3)
    ax[2].set_ylabel('Skycover (%)')

    wind_norm = plt.Normalize(0,30)
    idx = mpl.dates.date2num(noaa_df['startTime_local'])
    ax[3].quiver(idx, noaa_df['windSpeed_mph'],noaa_df['wind_x'],noaa_df['wind_y'],noaa_df['windSpeed_mph'], norm = wind_norm)
    ax[3].set_ylabel('Wind Speed (mph)')
    ax[3].set_ylim(0,noaa_df['windSpeed_mph'].max()+ 5)

    date_format = mdates.DateFormatter("%a, %m-%d")
    ax[3].xaxis.set_major_formatter(date_format)

    ax22 = ax[2].twinx()
    # precip_prob_df_simple.plot(x = 'time_local', y = 'value', ax = ax[4], label = 'probabilityOfPrecipitation', c = '#a3a3a3', x_compat = True, legend = False)
    ax22.fill_between(precip_prob_df_simple['time_local'], precip_prob_df_simple['value'], 0, color='none', alpha=0.3, hatch = 'OO', edgecolor='#005791')
    # ax[4].fill_between(precip_prob_df_simple['time_local'], precip_prob_df_simple['value'], 100, color='#6bc9ff', alpha=0.3)
    ax22.set_ylabel('Precip (%)')
    ax22.set_ylim(0,100)
    labelLines(ax22.get_lines(), zorder=2.5, align = True, xvals = [0.5], yoffsets=[0.15])

    for index, row in sun_df.iterrows():
        sunset = row['sunset']
        next_sunrise = row['next_sunrise']
        for axis in ax:
            axis.axvspan(sunset, next_sunrise, facecolor='gray', alpha=0.07)

    fig2, ax2 = plt.subplots()
    fig2.suptitle(f'Snotel Report for {SiteName}')
    fig2.set_figwidth(15)
    snotel_df.plot.bar(x = 'Date', y = 'snow_depth_in', 
                    ylim = (snotel_df['snow_depth_in'].min()-1,snotel_df['snow_depth_in'].max()+1),
                    ax = ax2,
                    color = list(snotel_df['color']), legend = False)
    ax2.set_ylabel('Snow Depth (in)')
    fig2.tight_layout()


    today = datetime.today()
    tomorrow = datetime.today() + timedelta(days = 1)
    two_days = datetime.today() + timedelta(days = 2)
    noaa_df_24h = noaa_df[noaa_df['startTime_local'].between(today,tomorrow)]
    high_temp = noaa_df_24h['temperature'].max()
    low_temp = noaa_df_24h['temperature'].min()
    average_windspeed = round(noaa_df_24h['windSpeed_mph'].mean())
    wind_direction = noaa_df_24h['windDirection'].mode()[0]
    total_snowfall = round(noaa_df_24h['total_snowfall_in'].max(),1)

    print('CAIC:',f'https://avalanche.state.co.us/?lat={lat}&lng={lon}')
    print('High:',high_temp, 'F')
    print('Low:',low_temp, 'F')
    print('Wind:',average_windspeed, 'mph',wind_direction)
    print('Predicted Snowfall:',total_snowfall,'inches')
    print('New Snow:',new_snow_24h, 'inches')

    fig.suptitle(f'Weather for {SiteName}')
    fig.set_tight_layout('tight')
    fig.subplots_adjust(hspace=0)
    plt.grid(True)
    date_format = mdates.DateFormatter('%Y-%m-%d')  # Specify the desired format

    caic_url = f'https://avalanche.state.co.us/?lat={lat}&lng={lon}'


    ########### Unique to Snotel_Simple.py ###########
    fig.savefig('daily_forecast.png',dpi = 300)
    fig2.savefig('daily_snotel_report.png',dpi = 300)

    # plt.show()
    # sys.exit()

    from email.message import EmailMessage
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
    import smtplib
    import ssl
    import os

    
    email_sender = 'snowbanks.weather@gmail.com'
    # Password is stored in environment variable for security
    # To set the environment variable, in CmdPrompt use:
    # set snowbanks_password=yourpasswordhere
    # In the google account, this seems to need to be an App Password, not the regular account password
    # I couldn't navigate to this, but if I went to myaccount.google.com, I searched for "App Passwords" and it took me to the right place
    email_password = os.getenv('snowbanks_password')
    email_receiver = 'jon.banks.87@gmail.com'

    def send_emails(email_list):
        for person in email_list:
            body = f'''
                NOAA Forecast: {human_noaa_url}
                Snotel: {human_snotel_url}
                High: {high_temp} F
                Low: {low_temp} F
                Wind: {average_windspeed} mph {wind_direction}
                Predicted Snowfall: {total_snowfall} inches
                New Snow: {new_snow_24h} inches
                '''
            msg = MIMEMultipart()
            msg['From'] = email_sender
            msg['To'] = person
            date = datetime.today().strftime('%Y-%m-%d')
            msg['Subject'] = f'{SiteName} Daily Snow Report for {date}'
            msg.attach(MIMEText(body, 'plain'))

            for filename in ['daily_forecast.png', 'daily_snotel_report.png']:
                # filename = 'daily_forecast.png'
                attachment = open(filename, 'rb')
                attachment_package = MIMEBase('application', 'octed-stream')
                attachment_package.set_payload((attachment).read())
                encoders.encode_base64(attachment_package)
                attachment_package.add_header('Content-Disposition', 'attachment; filename= ' + filename)
                msg.attach(attachment_package)
            
            text = msg.as_string()

            print('Connecting to server...')
            TIE_server = smtplib.SMTP('smtp.gmail.com', 587)
            TIE_server.starttls()
            TIE_server.login(email_sender, email_password)
            print("Successfully connected to server")
            print()

            print(f"Sending email to: {person}")
            TIE_server.sendmail(email_sender, person, text)
            print(f'Email sent to: {person}')
            print()
        
        TIE_server.quit()

    send_emails([email_receiver])
    # plt.show()