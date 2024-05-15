import sys, os, csv
import simplekml
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import navpy
from gnssutils import EphemerisManager
pd.options.mode.chained_assignment = None  # Suppress SettingWithCopyWarning

# files path (adjust as needed) !!!!
parent_directory = os.path.split(os.getcwd())[0]
data_directory = os.path.join(parent_directory,'pythonProject1', 'data') # change to you project name ass needed !!
output_directory = os.path.join(parent_directory,'pythonProject1', 'output')# change to you project name ass needed !!
sys.path.insert(0, parent_directory)
data_log_name = 'gnss_log_2024_05_13_23_35_14_mylog.txt'
# data_log_name = 'gnss_log_2024_04_13_19_51_17.txt'

# Consents
WEEKSEC = 604800
LIGHTSPEED = 2.99792458e8
manager = EphemerisManager(data_directory)

# Satellite Position Determination
def calculate_satellite_position(ephemeris, transmit_time):
    mu = 3.986005e14
    OmegaDot_e = 7.2921151467e-5
    F = -4.442807633e-10
    sv_position = pd.DataFrame()
    sv_position['GPS time'] = transmit_time - ephemeris['t_oe']

    sv_position['SatPRN'] = ephemeris.index
    # sv_position.set_index('SatPRN', inplace=True)

    A = ephemeris['sqrtA'].pow(2)
    n_0 = np.sqrt(mu / A.pow(3))
    n = n_0 + ephemeris['deltaN']
    M_k = ephemeris['M_0'] + n * sv_position['GPS time']
    E_k = M_k
    err = pd.Series(data=[1] * len(sv_position.index))
    i = 0
    while err.abs().min() > 1e-8 and i < 10:
        new_vals = M_k + ephemeris['e'] * np.sin(E_k)
        err = new_vals - E_k
        E_k = new_vals
        i += 1

    sinE_k = np.sin(E_k)
    cosE_k = np.cos(E_k)
    delT_r = F * ephemeris['e'].pow(ephemeris['sqrtA']) * sinE_k
    delT_oc = transmit_time - ephemeris['t_oc']
    sv_position['delT_sv'] = ephemeris['SVclockBias'] + ephemeris['SVclockDrift'] * delT_oc + ephemeris[
        'SVclockDriftRate'] * delT_oc.pow(2)

    v_k = np.arctan2(np.sqrt(1 - ephemeris['e'].pow(2)) * sinE_k, (cosE_k - ephemeris['e']))

    Phi_k = v_k + ephemeris['omega']

    sin2Phi_k = np.sin(2 * Phi_k)
    cos2Phi_k = np.cos(2 * Phi_k)

    du_k = ephemeris['C_us'] * sin2Phi_k + ephemeris['C_uc'] * cos2Phi_k
    dr_k = ephemeris['C_rs'] * sin2Phi_k + ephemeris['C_rc'] * cos2Phi_k
    di_k = ephemeris['C_is'] * sin2Phi_k + ephemeris['C_ic'] * cos2Phi_k

    u_k = Phi_k + du_k

    r_k = A * (1 - ephemeris['e'] * np.cos(E_k)) + dr_k

    i_k = ephemeris['i_0'] + di_k + ephemeris['IDOT'] * sv_position['GPS time']

    x_k_prime = r_k * np.cos(u_k)
    y_k_prime = r_k * np.sin(u_k)

    Omega_k = ephemeris['Omega_0'] + (ephemeris['OmegaDot'] - OmegaDot_e) * sv_position['GPS time'] - OmegaDot_e * ephemeris[
        't_oe']

    sv_position['Sat_x'] = x_k_prime * np.cos(Omega_k) - y_k_prime * np.cos(i_k) * np.sin(Omega_k)
    sv_position['Sat_y'] = x_k_prime * np.sin(Omega_k) + y_k_prime * np.cos(i_k) * np.cos(Omega_k)
    sv_position['Sat_z'] = y_k_prime * np.sin(i_k)

    return sv_position

def final_sat_pos(ephemeris, transmit_time , one_epoch):
    sv_position = calculate_satellite_position(ephemeris, transmit_time)

    # Initial guesses of receiver clock bias and position
    # Apply satellite clock bias to correct the measured pseudorange values
    sv_position["Pr"] = one_epoch['PrM'] + LIGHTSPEED * sv_position['delT_sv']

    # Include CN0 values
    sv_position['cn0'] = one_epoch['Cn0DbHz']

    # Doppler shift calculation
    try:
        one_epoch['CarrierFrequencyHz'] = pd.to_numeric(one_epoch['CarrierFrequencyHz'])
        sv_position['DopplerShiftHz'] = -(one_epoch['PseudorangeRateMetersPerSecond'] / LIGHTSPEED) * one_epoch[
            'CarrierFrequencyHz']
    except Exception:
        sv_position['DopplerShiftHz'] = np.nan
    return sv_position

# Least Squares Position Solution
def least_squares(xs, measured_pseudorange, x0, b0):
    dx = 100*np.ones(3)
    b = b0
    # set up the G matrix with the right dimensions. We will later replace the first 3 columns
    # note that b here is the clock bias in meters equivalent, so the actual clock bias is b/LIGHTSPEED
    G = np.ones((measured_pseudorange.size, 4))
    iterations = 0
    while np.linalg.norm(dx) > 1e-3:
        # Eq. (2):
        r = np.linalg.norm(xs - x0, axis=1)
        # Eq. (1):
        phat = r + b0
        # Eq. (3):
        deltaP = measured_pseudorange - phat
        G[:, 0:3] = -(xs - x0) / r[:, None]
        # Eq. (4):
        sol = np.linalg.inv(np.transpose(G) @ G) @ np.transpose(G) @ deltaP
        # Eq. (5):
        dx = sol[0:3]
        db = sol[3]
        x0 = x0 + dx
        b0 = b0 + db
    norm_dp = np.linalg.norm(deltaP)
    return x0, b0, norm_dp

def read_data():
    # Data Aquisition
    input_filepath = os.path.join(data_directory, data_log_name)
    with open(input_filepath) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[0][0] == '#':
                if 'Fix' in row[0]:
                    android_fixes = [row[1:]]
                elif 'Raw' in row[0]:
                    measurements = [row[1:]]
            else:
                if row[0] == 'Fix':
                    android_fixes.append(row[1:])
                elif row[0] == 'Raw':
                    measurements.append(row[1:])

    android_fixes = pd.DataFrame(android_fixes[1:], columns=android_fixes[0])
    measurements = pd.DataFrame(measurements[1:], columns=measurements[0])
    return measurements , android_fixes

def analyse_data(measurements):
    # Format satellite IDs
    measurements.loc[measurements['Svid'].str.len() == 1, 'Svid'] = '0' + measurements['Svid']
    measurements.loc[measurements['ConstellationType'] == '1', 'Constellation'] = 'G'
    measurements.loc[measurements['ConstellationType'] == '3', 'Constellation'] = 'R'
    measurements['SvName'] = measurements['Constellation'] + measurements['Svid']

    # Remove all non-GPS measurements
    measurements = measurements.loc[measurements['Constellation'] == 'G']

    # Convert columns to numeric representation
    measurements['Cn0DbHz'] = pd.to_numeric(measurements['Cn0DbHz'])
    measurements['TimeNanos'] = pd.to_numeric(measurements['TimeNanos'])
    measurements['FullBiasNanos'] = pd.to_numeric(measurements['FullBiasNanos'])
    measurements['ReceivedSvTimeNanos'] = pd.to_numeric(measurements['ReceivedSvTimeNanos'])
    measurements['PseudorangeRateMetersPerSecond'] = pd.to_numeric(measurements['PseudorangeRateMetersPerSecond'])
    measurements['ReceivedSvTimeUncertaintyNanos'] = pd.to_numeric(measurements['ReceivedSvTimeUncertaintyNanos'])

    # A few measurement values are not provided by all phones
    # We'll check for them and initialize them with zeros if missing
    if 'BiasNanos' in measurements.columns:
        measurements['BiasNanos'] = pd.to_numeric(measurements['BiasNanos'])
    else:
        measurements['BiasNanos'] = 0
    if 'TimeOffsetNanos' in measurements.columns:
        measurements['TimeOffsetNanos'] = pd.to_numeric(measurements['TimeOffsetNanos'])
    else:
        measurements['TimeOffsetNanos'] = 0

    return measurements

def pre_provessing(measurements):
    # Pre-processing
    # Timestamp Generation
    measurements['GpsTimeNanos'] = measurements['TimeNanos'] - (
                measurements['FullBiasNanos'] - measurements['BiasNanos'])
    gpsepoch = datetime(1980, 1, 6, 0, 0, 0)
    measurements['UnixTime'] = pd.to_datetime(measurements['GpsTimeNanos'], utc=True, origin=gpsepoch)
    measurements['UnixTime'] = measurements['UnixTime']

    # Split data into measurement epochs
    measurements['Epoch'] = 0
    measurements.loc[
        measurements['UnixTime'] - measurements['UnixTime'].shift() > timedelta(milliseconds=200), 'Epoch'] = 1
    measurements['Epoch'] = measurements['Epoch'].cumsum()

    # This should account for rollovers since it uses a week number specific to each measurement
    measurements['tRxGnssNanos'] = measurements['TimeNanos'] + measurements['TimeOffsetNanos'] - (
                measurements['FullBiasNanos'].iloc[0] + measurements['BiasNanos'].iloc[0])
    measurements['GpsWeekNumber'] = np.floor(1e-9 * measurements['tRxGnssNanos'] / WEEKSEC)
    measurements['tRxSeconds'] = 1e-9 * measurements['tRxGnssNanos'] - WEEKSEC * measurements['GpsWeekNumber']
    measurements['tTxSeconds'] = 1e-9 * (measurements['ReceivedSvTimeNanos'] + measurements['TimeOffsetNanos'])
    # Calculate pseudorange in seconds
    measurements['prSeconds'] = measurements['tRxSeconds'] - measurements['tTxSeconds']

    # Conver to meters
    measurements['PrM'] = LIGHTSPEED * measurements['prSeconds']
    measurements['PrSigmaM'] = LIGHTSPEED * 1e-9 * measurements['ReceivedSvTimeUncertaintyNanos']
    return measurements

# Reads GNSS measurements data, analyzes and formats it, and retrieves ephemeris data.
#
# Returns:
# - DataFrame: Preprocessed GNSS measurements data.
# - DataFrame: Satellite positions data.
def qustion2():
    measurements, android_fixes = read_data()
    measurements = analyse_data(measurements)
    measurements = pre_provessing(measurements)

    # Retrieving Ephemeris Data
    epoch = 0
    all_sv_positions = pd.DataFrame()
    while epoch != measurements['Epoch'].max()+1:
        one_epoch = measurements.loc[(measurements['Epoch'] == epoch) & (measurements['prSeconds'] < 0.1)].drop_duplicates(subset='SvName')
        num_sats = len(one_epoch.index)

        if num_sats >= 5:
            timestamp = one_epoch.iloc[0]['UnixTime'].to_pydatetime(warn=False)
            one_epoch.set_index('SvName', inplace=True)
            sats = one_epoch.index.unique().tolist()
            ephemeris = manager.get_ephemeris(timestamp, sats)
            sv_position = final_sat_pos(ephemeris,one_epoch['tTxSeconds'],one_epoch)

            all_sv_positions = pd.concat([all_sv_positions, sv_position])
        epoch += 1

    # Remove the 'delT_sv' column
    all_sv_positions = all_sv_positions.drop('delT_sv', axis=1)
    all_sv_positions.to_csv(os.path.join(output_directory, 'OutPut_Q2.csv'),index=False)
    return measurements, all_sv_positions

# Calculates the location of the receiver using satellite measurements.
#
# Args:
# - measurements (DataFrame): Preprocessed GNSS measurements data.
#
# Returns:
# - list: List of tuples containing receiver locations and corresponding GPS times.
def qustion3(measurements):
    b0 = 0
    x0 = np.array([0, 0, 0])

    # ecef_list = []
    ecef_list_time = []
    for epoch in measurements['Epoch'].unique():
        one_epoch = measurements.loc[(measurements['Epoch'] == epoch) & (measurements['prSeconds'] < 0.1)]
        one_epoch = one_epoch.drop_duplicates(subset='SvName').set_index('SvName')
        if len(one_epoch.index) > 4:
            timestamp = one_epoch.iloc[0]['UnixTime'].to_pydatetime(warn=False)
            sats = one_epoch.index.unique().tolist()
            ephemeris = manager.get_ephemeris(timestamp, sats)
            sv_position = final_sat_pos(ephemeris, one_epoch['tTxSeconds'],measurements)

            xs = sv_position[['Sat_x', 'Sat_y', 'Sat_z']].to_numpy()
            pr = one_epoch['PrM'] + LIGHTSPEED * sv_position['delT_sv']
            pr = pr.to_numpy()

            x, b, dp = least_squares(xs, pr, x0, b0)
            # ecef_list.append(x)
            ecef_list_time.append((x,sv_position['GPS time'].min()))

    return ecef_list_time

#  Generates a KML file with points and writes satellite data to a CSV file.
#
# Args:
# - ecef_list (list of tuples): List of tuples containing ECEF coordinates and GPS times.
# - lat_lon_alt (list of tuples): List of tuples containing latitude, longitude, and altitude.
# - q2_output (DataFrame): DataFrame containing satellite data.

def qustion5(ecef_list, lat_lon_alt, q2_output):
    kml(lat_lon_alt)

    file_path = os.path.join(output_directory, 'combined.csv')
    with open(file_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['GPS time','SatPRN','Sat_x','Sat_y','Sat_z','Pr','cn0','DopplerShiftHz','Pos.X', 'Pos.Y', 'Pos.Z', 'Lat', 'Lon', 'Alt'])

        for index, row in q2_output.iterrows():
            GPS_time = row['GPS time']
            SatPRN = row['SatPRN'] if 'SatPRN' in row else ''
            Sat_x = row['Sat_x'] if 'Sat_x' in row else ''
            Sat_y = row['Sat_y'] if 'Sat_y' in row else ''
            Sat_z = row['Sat_z'] if 'Sat_z' in row else ''
            Pr = row['Pr'] if 'Pr' in row else ''
            cn0 = row['cn0'] if 'cn0' in row else ''
            DopplerShiftHz = row['DopplerShiftHz'] if 'DopplerShiftHz' in row else ''

            found = False
            for (coord, time) in ecef_list:
                if GPS_time == time:
                    lla = navpy.ecef2lla(coord)
                    csv_writer.writerow([GPS_time, SatPRN, Sat_x, Sat_y, Sat_z, Pr, cn0, DopplerShiftHz, coord[0], coord[1], coord[2], lla[0], lla[1], lla[2]])
                    found = True
                    break
            if not found:
                lla = navpy.ecef2lla(coord)
                csv_writer.writerow([GPS_time, SatPRN, Sat_x, Sat_y, Sat_z, Pr, cn0, DopplerShiftHz, '', '', '', '', '', ''])
def kml(coordinates):
    file_name = os.path.join(output_directory ,"KML.kml")
    kml = simplekml.Kml()
    for coordinate in coordinates:
        lat, lon, alt = coordinate
        kml.newpoint(name="", coords=[(lon, lat, alt)])
    kml.save(file_name)
def delete_files_in_folder(folder_path):
    """
    Deletes all files in the specified folder.

    Args:
    - folder_path (str): The path to the folder containing the files to be deleted.
    """
    try:
        # List all files in the folder
        files = os.listdir(folder_path)
        # Iterate over each file and delete it
        for file in files:
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):  # Check if it's a file
                os.remove(file_path)
        print("All files deleted successfully from:", folder_path)
    except Exception as e:
        print("An error occurred:", str(e))

def main():
    # deleat previos out put files
    delete_files_in_folder(output_directory)

    # qustion 2
    measurements, sv_position = qustion2()

    # qustion 3
    ecef_list = qustion3(measurements) #my location in x y z coords

    # this is a given function that converting method from X,Y,Z to Lat, Lon, Alt
    # qustion 4
    lat_lon_alt = [navpy.ecef2lla(coord) for (coord, time) in ecef_list] # my location in LLA for the KML file !

    # qustion 5
    qustion5(ecef_list, lat_lon_alt,sv_position)
    print("end")

if __name__ == "__main__":
    main()