from argparse import ArgumentParser
import os
import StringIO
import struct

from utility.pytskutil import TSKUtil
from Registry import Registry
import jinja2


def open_file_as_reg(reg_file):
    file_size = reg_file.info.meta.size
    file_content = reg_file.read_random(0, file_size)
    file_like_obj = StringIO.StringIO(file_content)
    return Registry.Registry(file_like_obj)

def parse_wordwheel(explorer_key, username):
    try:
        wwq = explorer_key.find_key("WordWheelQuery")
    except Registry.RegistryKeyNotFoundException:
        return []

    mru_list = wwq.value("MRUListEx").value()
    mru_order = []
    for i in xrange(0, len(mru_list), 2):
        order_val = struct.unpack('h', mru_list[i:i+2])[0]
        if order_val in mru_order and \
            order_val in (0, -1):
            break
        else:
            mru_order.append(order_val)

    search_list = []
    for count, val in enumerate(mru_order):
        ts = "N/A"
        if count == 0:
            ts = wwq.timestamp()
        search_list.append({
            'timestamp': ts,
            'username': username,
            'order': count,
            'value_name': str(val),
            'search': wwq.value(str(val)).value(
                ).decode("UTF-16").strip("\x00")
        })
    return search_list

def parse_typed_paths(explorer_key, username):
    try:
        typed_paths = explorer_key.find_key("TypedPaths")
    except Registry.RegistryKeyNotFoundException:
        return []

    typed_path_details = []
    for val in typed_paths.values():
        typed_path_details.append({
            "username": username,
            "value_name": val.name(),
            "path": val.value()
        })
    return typed_path_details

def parse_run_mru(explorer_key, username):
    try:
        run_mru = explorer_key.find_key("RunMRU")
    except Registry.RegistryKeyNotFoundException:
        return []

    if len(run_mru.values()) == 0:
        return []

    mru_list = run_mru.value("MRUList").value()
    mru_order = []
    for i in mru_list:
        mru_order.append(i)

    mru_details = []
    for count, val in enumerate(mru_order):
        ts = "N/A"
        if count == 0:
            ts = run_mru.timestamp()
        mru_details.append({
            "username": username,
            "timestamp": ts,
            "order": count,
            "value_name": val,
            "run_statement": run_mru.value(val).value()
        })

    return mru_details


def main(evidence, image_type, report):
    tsk_util = TSKUtil(evidence, image_type)
    tsk_ntuser_hives = tsk_util.recurse_files('ntuser.dat',
                                             '/Users', 'equals')

    nt_rec = {
        'wordwheel': {'data': [], 'title': 'WordWheel Query'},
        'typed_path': {'data': [], 'title': 'Typed Paths'},
        'run_mru': {'data': [], 'title': 'Run MRU'}
    }
    for ntuser in tsk_ntuser_hives:
        uname = ntuser[1].split("/")[1]

        open_ntuser = open_file_as_reg(ntuser[2])
        try:
            explorer_key = open_ntuser.root().find_key("Software"
               ).find_key("Microsoft").find_key("Windows"
               ).find_key("CurrentVersion").find_key("Explorer"
               )
        except Registry.RegistryKeyNotFoundException:
            continue  # Required registry key not found for user

        nt_rec['wordwheel']['data'] += parse_wordwheel(
            explorer_key, uname)
        nt_rec['typed_path']['data'] += parse_typed_paths(
            explorer_key, uname)
        nt_rec['run_mru']['data'] += parse_run_mru(
            explorer_key,uname)

    nt_rec['wordwheel']['headers'] = \
        nt_rec['wordwheel']['data'][0].keys()

    nt_rec['typed_path']['headers'] = \
        nt_rec['typed_path']['data'][0].keys()

    nt_rec['run_mru']['headers'] = \
        nt_rec['run_mru']['data'][0].keys()

    write_html(report, nt_rec)


def write_html(outfile, data_dict):
    cwd = os.path.dirname(os.path.abspath(__file__))
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(cwd))
    template = env.get_template("user_activity.html")
    rendering = template.render(nt_data=data_dict)
    with open(outfile, 'w') as open_outfile:
        open_outfile.write(rendering)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('EVIDENCE_FILE',
                        help="Path to evidence file")
    parser.add_argument('IMAGE_TYPE',
                        help="Evidence file format",
                        choices=('ewf', 'raw'))
    parser.add_argument('REPORT',
                        help="Path to report file")
    args = parser.parse_args()
    main(args.EVIDENCE_FILE, args.IMAGE_TYPE, args.REPORT)
