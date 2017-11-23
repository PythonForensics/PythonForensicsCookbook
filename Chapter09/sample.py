import argparse
import os
import pytsk3
import pyewf
import sys
from utility.pytskutil import TSKUtil


def main(evidence, image_type):

    # Case-insensitive test -- print files in dir (if dir exists)
    tsk_util = TSKUtil(evidence, image_type)
    dir_obj_test4 = tsk_util.query_directory("/WINDOWS/SYSTEM32/CoNfIg")
    if dir_obj_test4 is not None:
        for dir_tuple in dir_obj_test4:
            for fs_object in dir_tuple[1]:
                # Skip ".", ".." or directory entries without a name.
                if not hasattr(fs_object, "info") or not hasattr(fs_object.info, "name") or not hasattr(fs_object.info.name, "name") or fs_object.info.name.name in [".", ".."]:
                    continue

                file_name = fs_object.info.name.name
                file_path = "PARTITION {}{}/{}".format(dir_tuple[0], "/WINDOWS/SYSTEM32/CONFIG", fs_object.info.name.name)
                print "Found File in Dir: {}".format(file_path)

    # This will scan from the specified dir (root in this case) and is equal to the word "SAM" and is case sensitive

    file_obj_test2 = tsk_util.recurse_files("SAM", path="/", equal=True, case=True)
    if file_obj_test2 is not None:
        for part in file_obj_test2:
            for hit_tuple in part:
                print "Found Hit: {}, {}".format(hit_tuple[0], hit_tuple[1])




if __name__ == "__main__":
    # Command-line Argument Parser
    parser = argparse.ArgumentParser()
    parser.add_argument("EVIDENCE_FILE", help="Evidence file path")
    parser.add_argument("TYPE", help="Type of Evidence", choices=("raw", "ewf"))
    args = parser.parse_args()

    if os.path.exists(args.EVIDENCE_FILE) and os.path.isfile(args.EVIDENCE_FILE):
        main(args.EVIDENCE_FILE, args.TYPE)
    else:
        print("[-] Supplied input file {} does not exist or is not a file".format(args.EVIDENCE_FILE))
        sys.exit(1)
