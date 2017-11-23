from argparse import ArgumentParser
import datetime
import StringIO
import struct

from utility.pytskutil import TSKUtil
from Registry import Registry


def parse_windows_filetime(date_value):
    microseconds = float(date_value) / 10
    ts = datetime.datetime(1601,1,1) + datetime.timedelta(
        microseconds=microseconds)
    return ts.strftime('%Y-%m-%d %H:%M:%S.%f')


def parse_unix_epoch(date_value):
    ts = datetime.datetime.fromtimestamp(date_value)
    return ts.strftime('%Y-%m-%d %H:%M:%S.%f')


def process_system_hive(hive):
    root = hive.root()
    current_control_set = root.find_key("Select").value("Current").value()
    control_set = root.find_key("ControlSet{:03d}".format(
        current_control_set))

    # Parse shutdown time
    raw_shutdown_time = struct.unpack('<Q',
        control_set.find_key("Control").find_key("Windows").value(
            "ShutdownTime").value())
    shutdown_time = parse_windows_filetime(raw_shutdown_time[0])
    print "Last Shutdown Time: {}".format(shutdown_time)

    # Parse timezone
    time_zone = control_set.find_key("Control").find_key(
        "TimeZoneInformation").value("TimeZoneKeyName").value()
    print "Machine Time Zone: {}".format(time_zone)

    # Parse computer name
    computer_name = control_set.find_key("Control").find_key(
            "ComputerName").find_key("ComputerName").value(
            "ComputerName").value()
    print "Machine Name: {}".format(computer_name)

    # Parse Last Access Timestamp Default
    last_access = control_set.find_key("Control").find_key(
        "FileSystem").value("NtfsDisableLastAccessUpdate").value()
    last_access = "Disabled" if last_access == 1 else "enabled"
    print "Last Access Updates: {}".format(last_access)


def process_software_hive(hive):
    root = hive.root()
    nt_curr_ver = root.find_key("Microsoft").find_key(
        "Windows NT").find_key("CurrentVersion")

    print "Product name: {}".format(nt_curr_ver.value(
        "ProductName").value())
    print "CSD Version: {}".format(nt_curr_ver.value(
        "CSDVersion").value())
    print "Current Build: {}".format(nt_curr_ver.value(
        "CurrentBuild").value())
    print "Registered Owner: {}".format(nt_curr_ver.value(
        "RegisteredOwner").value())
    print "Registered Org: {}".format(nt_curr_ver.value(
        "RegisteredOrganization").value())

    raw_install_date = nt_curr_ver.value("InstallDate").value()
    install_date = parse_unix_epoch(raw_install_date)
    print "Installation Date: {}".format(install_date)

def open_file_as_reg(reg_file):
    file_size = reg_file.info.meta.size
    file_content = reg_file.read_random(0, file_size)
    file_like_obj = StringIO.StringIO(file_content)
    return Registry.Registry(file_like_obj)

def main(evidence, image_type):
    tsk_util = TSKUtil(evidence, image_type)
    tsk_system_hive = tsk_util.recurse_files(
        'system', '/Windows/system32/config', 'equals')
    tsk_software_hive = tsk_util.recurse_files(
        'software', '/Windows/system32/config', 'equals')

    system_hive = open_file_as_reg(tsk_system_hive[0][2])
    software_hive = open_file_as_reg(tsk_software_hive[0][2])

    process_system_hive(system_hive)
    process_software_hive(software_hive)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('EVIDENCE_FILE', help="Path to evidence file")
    parser.add_argument('IMAGE_TYPE', help="Evidence file format",
        choices=('ewf', 'raw'))
    args = parser.parse_args()
    main(args.EVIDENCE_FILE, args.IMAGE_TYPE)
