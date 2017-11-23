from argparse import ArgumentParser
import unicodecsv as csv
import os
import StringIO

from utility.pytskutil import TSKUtil
import olefile

REPORT_COLS = ['note_id', 'created', 'modified', 'note_text', 'note_file']


def main(evidence, image_type, report_folder):
    tsk_util = TSKUtil(evidence, image_type)
    note_files = tsk_util.recurse_files('StickyNotes.snt', '/Users',
                                        'equals')

    report_details = []
    for note_file in note_files:
        user_dir = note_file[1].split("/")[1]
        file_like_obj = create_file_like_obj(note_file[2])
        note_data = parse_snt_file(file_like_obj)
        if note_data is None:
            continue
        write_note_rtf(note_data, os.path.join(report_folder, user_dir))
        report_details += prep_note_report(note_data, REPORT_COLS,
                            "/Users" + note_file[1])
    write_csv(os.path.join(report_folder, 'sticky_notes.csv'), REPORT_COLS,
              report_details)


def create_file_like_obj(note_file):
    file_size = note_file.info.meta.size
    file_content = note_file.read_random(0, file_size)
    return StringIO.StringIO(file_content)

def parse_snt_file(snt_file):
    if not olefile.isOleFile(snt_file):
        print "This is not an OLE file"
        return None
    ole = olefile.OleFileIO(snt_file)
    note = {}
    for stream in ole.listdir():
        if stream[0].count("-") == 3:
            if stream[0] not in note:
                note[stream[0]] = {
                    # Read timestamps
                    "created": ole.getctime(stream[0]),
                    "modified": ole.getmtime(stream[0])
                }

            content = None
            if stream[1] == '0':
                # Parse RTF text
                content = ole.openstream(stream).read()
            elif stream[1] == '3':
                # Parse UTF text
                content = ole.openstream(stream).read().decode("utf-16")

            if content:
                note[stream[0]][stream[1]] = content

    return note

def write_note_rtf(note_data, report_folder):
    if not os.path.exists(report_folder):
        os.makedirs(report_folder)
    for note_id, stream_data in note_data.items():
        fname = os.path.join(report_folder, note_id+".rtf")
        with open(fname, 'w') as open_file:
            open_file.write(stream_data['0'])

def prep_note_report(note_data, report_cols, note_file):
    report_details = []
    for note_id, stream_data in note_data.items():
        report_details.append({
            "note_id": note_id,
            "created": stream_data['created'],
            "modified": stream_data['modified'],
            "note_text": stream_data['3'].strip("\x00"),
            "note_file": note_file
        })
    return report_details

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
    parser.add_argument('REPORT_FOLDER', help="Path to report folder")
    args = parser.parse_args()
    main(args.EVIDENCE_FILE, args.IMAGE_TYPE, args.REPORT_FOLDER)
