import os
import pytsk3
import sys
import pyewf

class EWFImgInfo(pytsk3.Img_Info):
    """EWF Image Format helper class"""
    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        super(EWFImgInfo, self).__init__(url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def close(self):
        self._ewf_handle.close()

    def read(self, offset, size):
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self):
        return self._ewf_handle.get_media_size()


class TSKUtil(object):
    def __init__(self, evidence, image_type):
        self.evidence = evidence
        self.image_type = image_type

        # Assigned parameters
        self.vol = None
        self.image_handle = None
        self.fs = []

        # Prep volume and fs objects
        self.run()

    def run(self):
        self.open_vol()
        self.open_FS()

    def open_vol(self):
        sys.stderr.write("[+] Opening {}\n".format(self.evidence))
        # Handle EWF/Raw Images
        if self.image_type == "ewf":
            try:
                filenames = pyewf.glob(self.evidence)
            except IOError, e:
                sys.stderr.write("[-] Invalid EWF format:\n {}\n".format(e))
                raise IOError

            ewf_handle = pyewf.handle()
            ewf_handle.open(filenames)

            # Open PYTSK3 handle on EWF Image
            self.image_handle = EWFImgInfo(ewf_handle)
        else:
            self.image_handle = pytsk3.Img_Info(self.evidence)

        # Open volume from image
        try:
            self.vol = pytsk3.Volume_Info(self.image_handle)
        except IOError, e:
            sys.stderr.write("[-] Unable to read partition table. Possible logical image:\n {}\n".format(e))

    def open_FS(self):
        # Open FS and Recurse
        if self.vol is not None:
            for partition in self.vol:
                if partition.len > 2048 and "Unallocated" not in partition.desc and "Extended" not in partition.desc and "Primary Table" not in partition.desc:
                    try:
                        self.fs.append(pytsk3.FS_Info(self.image_handle,
                            offset=partition.start*self.vol.info.block_size))
                    except IOError, e:
                        sys.stderr.write("[-] Unable to open FS:\n {}\n".format(e))
        else:
            try:
                self.fs.append(pytsk3.FS_Info(self.image_handle))
            except IOError, e:
                sys.stderr.write("[-] Unable to open FS:\n {}\n".format(e))

    def recurse_files(self, substring, path="/", logic="contains", case=False):
        files = []
        for i, fs in enumerate(self.fs):
            try:
                root_dir = fs.open_dir(path)
            except IOError:
                continue
            files += self.recurse_dirs(i, fs, root_dir, [], [], [""], substring, logic, case)

        if files == []:
            return None
        else:
            return files

    def query_directory(self, path):
        dirs = []
        for i, fs in enumerate(self.fs):
            try:
                dirs.append((i, fs.open_dir(path)))
            except IOError:
                continue

        if dirs == []:
            return None
        else:
            return dirs

    def recurse_dirs(self, part, fs, root_dir, dirs, data, parent, substring, logic, case):
        dirs.append(root_dir.info.fs_file.meta.addr)
        for fs_object in root_dir:
            # Skip ".", ".." or directory entries without a name.
            if not hasattr(fs_object, "info") or not hasattr(fs_object.info, "name") or not hasattr(fs_object.info.name, "name") or fs_object.info.name.name in [".", ".."]:
                continue
            try:
                file_name = fs_object.info.name.name
                file_path = "{}/{}".format("/".join(parent), fs_object.info.name.name)
                try:
                    if fs_object.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
                        f_type = "DIR"
                        file_ext = ""
                    else:
                        f_type = "FILE"

                except AttributeError:
                    continue  # Which object has the AttributeError?

                if f_type == "FILE":
                    if logic.lower() == 'contains':
                        if case == False:
                            if substring.lower() in file_name.lower():
                                data.append((file_name, file_path, fs_object, part))
                        else:
                            if substring in file_name:
                                data.append((file_name, file_path, fs_object, part))
                    elif logic.lower() == 'startswith':
                        if case == False:
                            if file_name.lower().startswith(substring.lower()):
                                data.append((file_name, file_path, fs_object, part))
                        else:
                            if file_name.startswith(substring):
                                data.append((file_name, file_path, fs_object, part))
                    elif logic.lower() == 'endswith':
                        if case == False:
                            if file_name.lower().endswith(substring.lower()):
                                data.append((file_name, file_path, fs_object, part))
                        else:
                            if file_name.endswith(substring):
                                data.append((file_name, file_path, fs_object, part))
                    elif logic.lower() in ('equal', 'equals'):
                        if case == False:
                            if substring.lower() == file_name.lower():
                                data.append((file_name, file_path, fs_object, part))
                        else:
                            if substring == file_name:
                                data.append((file_name, file_path, fs_object, part))
                    else:
                        sys.stderr.write("[-] Warning invalid logic {} provided\n".format(logic))
                        sys.exit()

                elif f_type == "DIR":
                    parent.append(fs_object.info.name.name)
                    sub_directory = fs_object.as_directory()
                    inode = fs_object.info.meta.addr

                    # This ensures that we don't recurse into a directory
                    # above the current level and thus avoid circular loops.
                    if inode not in dirs:
                        self.recurse_dirs(part, fs, sub_directory, dirs, data, parent, substring, logic, case)
                    parent.pop(-1)

            except IOError:
                pass  # What causes this error?
        dirs.pop(-1)
        return data
