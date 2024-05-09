import csv

# attempt to convert the log to CSV


def parse_log_file(log_file):
    parsed_data = []
    with open(log_file, 'r') as f:
        for line in f:
            # Split the line into fields (assuming fields are separated by commas or spaces)
            fields = line.strip().split(',')

            # Check if the line has enough fields
            if len(fields) < 7:
                # Skip this line if it doesn't have enough fields
                continue

            # Extract relevant information from the fields
            gps_time = fields[0]
            sat_prn = fields[1]
            sat_x = fields[2]
            sat_y = fields[3]
            sat_z = fields[4]
            pseudo_range = fields[5]
            cn0 = fields[6]

            # Convert Sat.X, Sat.Y, Sat.Z to ECEF coordinates if necessary

            # Create a tuple or dictionary containing the parsed data
            parsed_line = (gps_time, sat_prn, sat_x, sat_y, sat_z, pseudo_range, cn0)

            # Append the parsed data to the list
            parsed_data.append(parsed_line)
    return parsed_data

def write_to_csv(parsed_data, output_file):
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        # Write header row
        writer.writerow(['GPS time', 'SatPRN', 'Sat.X', 'Sat.Y', 'Sat.Z', 'Pseudo-Range', 'CN0'])
        # Write parsed data to CSV
        writer.writerows(parsed_data)

if __name__ == "__main__":
    log_file = "gnss_log_2024_04_13_19_53_33.txt"
    output_file = "output.csv"
    parsed_data = parse_log_file(log_file)
    write_to_csv(parsed_data, output_file)
