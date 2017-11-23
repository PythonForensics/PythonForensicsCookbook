from argparse import ArgumentParser
import unicodecsv as csv
import datetime
import StringIO
import struct

from utility.pytskutil import TSKUtil
import pyesedb
COL_TYPES = pyesedb.column_types


def parse_windows_filetime(date_value):
    microseconds = float(date_value) / 10
    ts = datetime.datetime(1601,1,1) + datetime.timedelta(
        microseconds=microseconds)
    return ts.strftime('%Y-%m-%d %H:%M:%S.%f')

def open_file_as_esedb(esedb):
    file_size = esedb.info.meta.size
    file_content = esedb.read_random(0, file_size)
    file_like_obj = StringIO.StringIO(file_content)
    esedb = pyesedb.file()
    try:
        esedb.open_file_object(file_like_obj)
    except IOError:
        return None
    return esedb

def process_windows_search(ese):
    report_cols = [
        (0, "DocID"), (286, "System_KindText"),
        (35, "System_ItemUrl"), (5, "System_DateModified"),
        (6, "System_DateCreated"), (7, "System_DateAccessed"),
        (3, "System_Size"), (19, "System_IsFolder"),
        (2, "System_Search_GatherTime"), (22, "System_IsDeleted"),
        (61, "System_FileOwner"), (31, "System_ItemPathDisplay"),
        (150, "System_Link_TargetParsingPath"),
        (265, "System_FileExtension"), (348, "System_ComputerName"),
        (34, "System_Communication_AccountName"),
        (44, "System_Message_FromName"),
        (43, "System_Message_FromAddress"), (49, "System_Message_ToName"),
        (47, "System_Message_ToAddress"),
        (62, "System_Message_SenderName"),
        (189, "System_Message_SenderAddress"),
        (52, "System_Message_DateSent"),
        (54, "System_Message_DateReceived")
    ]

    table = ese.get_table_by_name("SystemIndex_0A")
    table_data = []
    for record in table.records:
        record_info = {}
        for col_id, col_name in report_cols:
            rec_val = record.get_value_data(col_id)
            col_type = record.get_column_type(col_id)

            if col_type in (COL_TYPES.DATE_TIME, COL_TYPES.BINARY_DATA):
                try:
                    raw_val = struct.unpack('>q', rec_val)[0]
                    rec_val = parse_windows_filetime(raw_val)
                except:
                    if rec_val is not None:
                        rec_val = rec_val.encode('hex')

            elif col_type in (COL_TYPES.TEXT, COL_TYPES.LARGE_TEXT):
                try:
                    rec_val = record.get_value_data_as_string(col_id)
                except:
                    rec_val = rec_val.decode("utf-16-be", "replace")

            elif col_type == COL_TYPES.INTEGER_32BIT_SIGNED:
                rec_val = record.get_value_data_as_integer(col_id)

            elif col_type == COL_TYPES.BOOLEAN:
                rec_val = rec_val == '\x01'

            else:
                if rec_val is not None:
                    rec_val = rec_val.encode('hex')

            record_info[col_name] = rec_val
        table_data.append(record_info)

    return [x[1] for x in report_cols], table_data

def main(evidence, image_type, report):
    tsk_util = TSKUtil(evidence, image_type)
    esedb_files = tsk_util.recurse_files("Windows.edb",
        path="/ProgramData/Microsoft/Search/Data/Applications/Windows",
        logic="equals")
    if esedb_files is None:
        print "No Windows.edb file found"
        exit(0)

    for entry in esedb_files:
        ese = open_file_as_esedb(entry[2])
        if ese is None:
            continue  # Invalid ESEDB
        report_cols, ese_data = process_windows_search(ese)

    write_csv(report, report_cols, ese_data)

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
