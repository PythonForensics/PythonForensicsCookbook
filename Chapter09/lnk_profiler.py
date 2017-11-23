from argparse import ArgumentParser
import csv
import StringIO

from utility.pytskutil import TSKUtil
import pylnk


def open_file_as_lnk(lnk_file):
    file_size = lnk_file.info.meta.size
    file_content = lnk_file.read_random(0, file_size)
    file_like_obj = StringIO.StringIO(file_content)
    lnk = pylnk.file()
    lnk.open_file_object(file_like_obj)
    return lnk


def main(evidence, image_type, report):
    tsk_util = TSKUtil(evidence, image_type)
    lnk_files = tsk_util.recurse_files("lnk", path="/", logic="endswith")
    if lnk_files is None:
        print "No lnk files found"
        exit(0)

    columns = [
        'command_line_arguments', 'description', 'drive_serial_number',
        'drive_type', 'file_access_time', 'file_attribute_flags',
        'file_creation_time', 'file_modification_time', 'file_size',
        'environmental_variables_location', 'volume_label',
        'machine_identifier', 'local_path', 'network_path',
        'relative_path', 'working_directory'
     ]

    parsed_lnks = []
    for entry in lnk_files:
        lnk = open_file_as_lnk(entry[2])
        lnk_data = {'lnk_path': entry[1], 'lnk_name': entry[0]}
        for col in columns:
            lnk_data[col] = getattr(lnk, col, "N/A")
        lnk.close()
        parsed_lnks.append(lnk_data)

    write_csv(report, columns+['lnk_path', 'lnk_name'], parsed_lnks)


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
