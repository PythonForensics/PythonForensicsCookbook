# Internal libs
from argparse import ArgumentParser
import datetime
import os
import struct

# Third-party and custom libs
from utility.pytskutil import TSKUtil
import unicodecsv as csv

def parse_windows_filetime(date_value):
    microseconds = float(date_value) / 10
    ts = datetime.datetime(1601,1,1) + datetime.timedelta(
        microseconds=microseconds)
    return ts.strftime('%Y-%m-%d %H:%M:%S.%f')

def sizeof_fmt(num, suffix='B'):
    # From https://stackoverflow.com/a/1094933/3194812
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def read_dollar_i(file_obj):
    if file_obj.read_random(0,8) != '\x01\x00\x00\x00\x00\x00\x00\x00':
        return None  # Invalid file
    raw_file_size = struct.unpack('<q', file_obj.read_random(8,8))
    raw_deleted_time = struct.unpack('<q', file_obj.read_random(16,8))
    raw_file_path = file_obj.read_random(24,520)

    file_size = sizeof_fmt(raw_file_size[0])
    deleted_time = parse_windows_filetime(raw_deleted_time[0])
    file_path = raw_file_path.decode("utf16").strip("\x00")
    return {'file_size': file_size, 'file_path': file_path,
        'deleted_time': deleted_time}

def process_dollar_i(tsk_util, dollar_i_files):
    processed_files = []
    for dollar_i in dollar_i_files:
        # Interpret file metadata
        file_attribs = read_dollar_i(dollar_i[2])
        if file_attribs is None:
            continue  # Invalid $I file
        file_attribs['dollar_i_file'] = os.path.join(
            '/$Recycle.bin', dollar_i[1][1:])

        # Get the $R file
        recycle_file_path = os.path.join('/$Recycle.bin',
            dollar_i[1].rsplit("/", 1)[0][1:])
        dollar_r_files = tsk_util.recurse_files("$R"+dollar_i[0][2:],
            path=recycle_file_path, logic="startswith")

        if dollar_r_files is None:
            dollar_r_dir = os.path.join(recycle_file_path,
                                        "$R"+dollar_i[0][2:])
            dollar_r_dirs = tsk_util.query_directory(dollar_r_dir)
            if dollar_r_dirs is None:
                file_attribs['dollar_r_file'] = "Not Found"
                file_attribs['is_directory'] = 'Unknown'
            else:
                file_attribs['dollar_r_file'] = dollar_r_dir
                file_attribs['is_directory'] = True
        else :
            dollar_r = [os.path.join(recycle_file_path, r[1][1:]) \
                        for r in dollar_r_files]
            file_attribs['dollar_r_file'] = ";".join(dollar_r)
            file_attribs['is_directory'] = False

        # Store entry attributes
        processed_files.append(file_attribs)
    return processed_files

def main(evidence, image_type, report_file):
    tsk_util = TSKUtil(evidence, image_type)

    dollar_i_files = tsk_util.recurse_files("$I", path='/$Recycle.bin',
        logic="startswith")

    if dollar_i_files is not None:
        processed_files = process_dollar_i(tsk_util, dollar_i_files)

        write_csv(report_file,
                  ['file_path', 'file_size', 'deleted_time',
                   'dollar_i_file', 'dollar_r_file', 'is_directory'],
                  processed_files)
    else:
        print "No $I files found"

def write_csv(outfile, fieldnames, data):
    with open(outfile, 'wb') as open_outfile:
        csvfile = csv.DictWriter(open_outfile, fieldnames)
        csvfile.writeheader()
        csvfile.writerows(data)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('EVIDENCE_FILE', help="Path to evidence file")
    parser.add_argument('IMAGE_TYPE', help="Evidence file format",
        choices=('ewf', 'raw'))
    parser.add_argument('CSV_REPORT', help="Path to CSV report")
    args = parser.parse_args()
    main(args.EVIDENCE_FILE, args.IMAGE_TYPE, args.CSV_REPORT)
