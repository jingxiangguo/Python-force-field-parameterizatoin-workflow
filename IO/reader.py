##############################################################################

# Python-force-field-parameterization-workflow: 
# A Python Library for reading trajectory from MD or MC simulations of
# various file formats: dcd, xyz, and txt

#

# Authors: Jingxiang Guo, Jeremy Palmer

#

# Python-force-field-parameterization-workflow is free software:
# you can redistribute it and/or modify it under the terms of the
# MIT License

# You should have received a copy of the MIT License along with the package.

##############################################################################



"""
A module for reading a trajectory from a MD or MC simulation.
Supported trajectory file format: 
1. *.txt 
2. *.dcd
3. *.lammpstraj

Many trajectory file formats are supported including: dcd, xyz, and txt.
The module allows a user to extract box and coordinates information from
a trajectory in parallel by using the multiprocessing library

The module also allows a user to read chunks of trajectory satisfying the
limit set by buffer size. This can efficient if appropriate buffer size is
set.

Finally, the specific file extension can be used to identify either xyz or dcd
trajectory and invoke its corresponding reader to parse a arbitrary trajectory 


"""
# Python standard library
import numpy as np
import multiprocessing as mp
import os
import sys
import itertools
import logging
from ctypes import CDLL, c_int, c_double, c_long, c_float, byref

# Local library:
import fortranAPI.IO
from IO.type_conversion import string_to_ctypes_string,\
                               int_to_ctypes_int,\
                               np_to_ctypes_array

import IO.check_file

# Third-party library:

# get the dynamic library path from the fortranAPI IO module:
fortranlib_address = os.path.join(os.path.dirname(fortranAPI.IO.__file__),
                                  "lib")

# Load the dynamic library of dcd trajectory reader:
dcd_lib = CDLL(os.path.join(fortranlib_address, "libdcd_reader.so"))

# Load the dynamic library of txt file reader:
txt_lib = CDLL(os.path.join(fortranlib_address, "libtxt_reader.so"))

# Load the dynamic library of xyz trajectory reader:
xyz_lib = CDLL(os.path.join(fortranlib_address, "libxyz_reader.so"))

# -------------------------------------------------------------------------
#                         Parallel workload manager
# -------------------------------------------------------------------------


def job_assignment(first, last, buffer_size):
    """Determine the workload (number of configuraitons)
       assigned for each core
    
    Parameters  

    ----------

    first: int

        which configuration to start with in a trajectory  

    last: int 

        which configuration to end with in a trajectory 
   
    buffer_size: int

        how many configurations to be read into memory per core at a time  
 
    Returns

    ----------

    pointer_ary: np.ndarray  

        pointer_ary tells which core should start reading which configuration

    
    work_load_ary: np.ndarray 

        Total configurations that should be read  

    Notes

    ----------

    This is used to initialize parallel processing of a large trajectory in
    xyz, dcd, and txt file format

    
    Examples

    ----------


    """

    total_workload = last - first + 1

    load_times = int(total_workload/buffer_size) + 1

    work_load_ary = np.zeros(load_times, dtype=int)

    # every core used no more than buffersize of frames

    work_load_ary[:] = int(buffer_size)

    # the left-over (remainder) workload will be sent to the last core:
    # So, the last core may have workload < buffersize

    work_load_ary[-1] = total_workload % buffer_size

    work_load_ary = work_load_ary[work_load_ary != 0]

    pointer_ary = np.zeros(np.count_nonzero(work_load_ary), dtype=np.int)

    pointer_ary[0] = first

    for i in range(pointer_ary.size-1):

        pointer_ary[i+1] = work_load_ary[i] + pointer_ary[i]

    return pointer_ary, work_load_ary


def parallel_assignment(start_at, work_load, num_cores, buffer_size):

    work_load_jobs = np.zeros(num_cores, dtype=np.int)

    start_ary = np.zeros(num_cores, dtype=np.int)

    work_load_per_core = int(work_load/num_cores)

    work_load_jobs[:] = work_load_per_core

    work_load_jobs[-1] += work_load % num_cores

    start_ary[0] = start_at

    job_assembly_lines = []

    for i in range(num_cores):

        end = start_ary[i] + work_load_jobs[i]

        if (i < num_cores - 1):

            start_ary[i+1] = end

        pointer_ary, work_load_ary = job_assignment(start_ary[i],
                                                    end-1,
                                                    buffer_size)

        # job_assembly_lines.append()
        job_assembly_lines.append((tuple(zip(pointer_ary, work_load_ary))))

    return job_assembly_lines

# -------------------------------------------------------------------------
#                          Python Read LAMMPS traj
# -------------------------------------------------------------------------


def get_num_configs_LAMMPS_traj(total_atoms, total_lines):

    # LAMMPS format: The header contains 9 lines
    lammps_traj_header_length = 9

    return int(total_lines/(total_atoms + lammps_traj_header_length))


def get_num_lines_LAMMPS_traj(keyword, total_atoms, num_configs):

    # LAMMPS format: The header contains 9 lines
    lammps_traj_header_length = 9

    if (num_configs == 1):

        return 0

    elif(keyword == "start"):

        return int((num_configs-1)*(total_atoms + lammps_traj_header_length))

    elif (keyword == "end"):

        return int(num_configs*(total_atoms + lammps_traj_header_length))


def read_LAMMPS_traj_num_atoms(file_address):

    with open(file_address, "r") as content:
        """ LAMMPS Format:
            ITEM: TIMESTEP
            1
            ITEM: NUMBER OF ATOMS
        """
        # skip first 3 lines:

        content.readline()
        content.readline()
        content.readline()
        natoms = int(content.readline())

    return natoms


def read_LAMMPS_traj_as_iterator(fileaddress,
                                 start,
                                 end,
                                 n_col_selected,
                                 col_start,
                                 col_end):

    with open(fileaddress, "r") as file_content:

        content = itertools.islice(file_content, start, end)

        for each_line in content:

            linedata = each_line.split()

            # use the length of the columns to determine which line to be read

            if (len(linedata) == n_col_selected):

                # return iterator rather than actual data
                # need to convert this iterator into an array to use it

                yield linedata[col_start:col_end]


def read_LAMMPS_traj(dtype,
                     fileaddress,
                     start,
                     end,
                     n_col_selected,
                     col_start,
                     col_end):

    read_LAMMPS = logging.getLogger(__name__)

    data_itera = read_LAMMPS_traj_as_iterator(fileaddress,
                                              start,
                                              end,
                                              n_col_selected,
                                              col_start,
                                              col_end)

    if (dtype == "double"):

        return np.fromiter(itertools.chain.from_iterable(data_itera),
                           dtype=np.float64)

    elif (dtype == "single"):

        return np.fromiter(itertools.chain.from_iterable(data_itera),
                           dtype=np.float32)

    else:

        read_LAMMPS.info("dtype should be either 'single' or 'double' ")

        sys.exit("Check errors in the log file!")

        return None


def read_LAMMPS_traj_in_parallel(file_address,
                                 num_cores,
                                 total_atoms,
                                 num_configs,
                                 first,
                                 buffer_size,
                                 workers=None):

    work_flow = parallel_assignment(first,
                                    num_configs,
                                    num_cores,
                                    buffer_size)

    if (workers is None):

        workers = mp.Pool(num_cores)

    # set up and launch the job:

    job_list = []

    # the row with exactly 5 columns of data will be parsed
    n_col_selected = 5

    # the column index start reading fx,fy,fz
    col_start = 2

    col_end = 5

    for each_core in work_flow:

        for start_at, num_configs in each_core:

            end = start_at + num_configs - 1

            lines_start = get_num_lines_LAMMPS_traj("start",
                                                    total_atoms,
                                                    start_at)

            lines_end = get_num_lines_LAMMPS_traj("end", total_atoms, end)

            job_list.append(workers.apply_async(read_LAMMPS_traj,
                                                args=("double",
                                                      file_address,
                                                      lines_start,
                                                      lines_end,
                                                      n_col_selected,
                                                      col_start,
                                                      col_end)))

    return job_list

# -------------------------------------------------------------------------
#                          Fortran dcd reader
# -------------------------------------------------------------------------


def call_read_dcd_header(dcdfile):

    if (not IO.check_file.status_is_ok(dcdfile)):

        sys.exit("Errors in reading file: %s; The file " 
                 "does not exist or is empty " % dcdfile)

    # declare c types varibles:

    dcdfile, strlength = string_to_ctypes_string(dcdfile)

    total_atoms = c_int()

    total_frames = c_int()

    dcd_lib.call_dcd_header(dcdfile,
                            byref(strlength),
                            byref(total_atoms),
                            byref(total_frames))

    return total_atoms.value, total_frames.value


def call_read_dcd_xyz_box(dcdfile, current_frame, total_atoms, return_numpy):

    # declare variables:

    dcdfile, strlength = string_to_ctypes_string(dcdfile)

    current_frame = int_to_ctypes_int(current_frame)

    total_atoms = int_to_ctypes_int(total_atoms)

    # box = (c_double*3)()
    box = np.ctypeslib.as_ctypes(np.zeros(3, dtype=np.float64))

    # xyz = ((c_float*total_atoms.value)*3)()

    xyz = np.ctypeslib.as_ctypes(np.zeros(total_atoms.value*3,
                                          dtype=np.float32))

    # current_frame = c_int(current_frame)

    dcd_lib.call_dcd_traj(dcdfile,
                          byref(strlength),
                          byref(total_atoms),
                          byref(current_frame),
                          box,
                          xyz)

    if (return_numpy):

        xyz = np.ctypeslib.as_array(xyz).reshape((total_atoms.value, 3))

        box = np.ctypeslib.as_array(box)

        return xyz, box

    else:

        # convert to double precision
        xyz = np.ctypeslib.as_ctypes(np.ctypeslib.as_array(xyz)
                                     .astype(np.float64))

        return xyz, box


def call_read_dcd_xyz_box_in_chunk(dcdfile,
                                   start_at,
                                   num_configs,
                                   total_atoms,
                                   return_numpy):

    # declare variables:

    dcdfile, strlength = string_to_ctypes_string(dcdfile)

    num_configs = int_to_ctypes_int(num_configs)

    start_at = int_to_ctypes_int(start_at)

    total_atoms = int_to_ctypes_int(total_atoms)

    # box = ((c_double*3)*num_configs)()
    box = np.ctypeslib.as_ctypes(np.zeros(3*num_configs.value,
                                 dtype=np.float64))

    # xyz = (((c_float*total_atoms.value)*3)*num_configs.value)()
    xyz = np.ctypeslib.as_ctypes(np.zeros(
                                 3*num_configs.value*total_atoms.value,
                                 dtype=np.float32))

    dcd_lib.call_dcd_traj_chunk(dcdfile,
                                byref(strlength),
                                byref(start_at),
                                byref(num_configs),
                                byref(total_atoms),
                                box,
                                xyz)

    if (return_numpy):

        xyz = np.ctypeslib.as_array(xyz).reshape((num_configs.value,
                                                  total_atoms.value,
                                                  3))

        box = np.ctypeslib.as_array(box).reshape((num_configs.value, 3))

        return xyz, box

    else:

        # convert to double precision
        xyz = np.ctypeslib.as_ctypes(np.ctypeslib.as_array(xyz)
                                       .astype(np.float64))

        return xyz, box

# -------------------------------------------------------------------------
#                          Fortran txt reader
# -------------------------------------------------------------------------


def get_lines_columns(txtfile):

    if (not IO.check_file.status_is_ok(txtfile)):

        sys.exit("Errors in reading file: %s; The file " 
                 "does not exist or is empty " % txtfile)

    txtfile, strlength = string_to_ctypes_string(txtfile)

    num_lines = c_int()

    num_columns = c_int()

    txt_lib.get_txt_lines_columns(txtfile,
                                  byref(strlength),
                                  byref(num_lines),
                                  byref(num_columns))

    return num_lines.value, num_columns.value

# used together with "get_lines_columns" to get num_lines, num_cols
def loadtxt(txtfile, num_lines, num_cols, skiprows, return_numpy):

    txtfile, strlength = string_to_ctypes_string(txtfile)

    num_selected = num_lines-skiprows

    loaded_data = np.ctypeslib.as_ctypes(np.zeros(
                                         num_selected*num_cols,
                                         dtype=np.float64))

    num_lines = int_to_ctypes_int(num_lines)

    num_cols = int_to_ctypes_int(num_cols)

    skiprows = int_to_ctypes_int(skiprows)

    txt_lib.load_txt(txtfile,
                     byref(strlength),
                     byref(num_lines),
                     byref(num_cols),
                     byref(skiprows),
                     loaded_data)

    if (return_numpy):

        return np.ctypeslib.as_array(loaded_data).reshape((num_cols.value,
                                                           num_lines.value -
                                                           skiprows.value)).T

    else:

        return loaded_data


def np_loadtxt(txtfile, skiprows=0):

    num_lines, num_cols = get_lines_columns(txtfile)

    if (skiprows >= num_lines): 

        sys.exit("Errors in reading the file: '%s' !. The rows skipped is %d, "
                 "which is more than or equal to the %d rows available in "
                 "this file " % (txtfile, skiprows, num_lines)) 

    return loadtxt(txtfile, num_lines, num_cols, skiprows, return_numpy=True)

# -------------------------------------------------------------------------
#                          Fortran xyz reader
# -------------------------------------------------------------------------


def call_read_xyz_header(xyzfile):

    if (not IO.check_file.status_is_ok(xyzfile)):

        sys.exit("Errors in reading file: %s; The file " 
                 "does not exist or is empty " % xyzfile)

    xyzfile, strlength = string_to_ctypes_string(xyzfile)

    total_atoms = c_int()

    total_frames = c_int()

    xyz_lib.call_read_xyz_header(xyzfile,
                                 byref(strlength),
                                 byref(total_atoms),
                                 byref(total_frames))

    return total_atoms.value, total_frames.value


def call_read_xyz_xyz_box(xyzfile,
                          current_frame,
                          total_atoms,
                          read_box=True,
                          return_numpy=True):

    # declare variables:

    xyzfile, strlength = string_to_ctypes_string(xyzfile)

    total_atoms = int_to_ctypes_int(total_atoms)

    current_frame = int_to_ctypes_int(current_frame)

    # xyz = ((c_float*total_atoms.value)*3)()

    xyz = np.ctypeslib.as_ctypes(np.zeros(
                                          total_atoms.value*3,
                                          dtype=np.float64))

    # current_frame = c_int(current_frame)

    # if the box is read from the xyz
    if (read_box):

        box = np.ctypeslib.as_ctypes(np.zeros(3, dtype=np.float64))

        xyz_lib.call_read_xyz_with_box(xyzfile,
                                       byref(strlength),
                                       byref(current_frame),
                                       byref(total_atoms),
                                       box,
                                       xyz)

        # if the xyz, box has to be returned as numpy data type
        if (return_numpy):

            xyz = np.ctypeslib.as_array(xyz).reshape((total_atoms.value, 3))

            box = np.ctypeslib.as_array(box)

            # return numpy array format of xyz,box
            return xyz, box

        else:

            # return ctypes format of xyz,box
            return xyz, box

    # if the box is not read from the xyz
    else:

        xyz_lib.call_read_xyz_no_box(xyzfile,
                                     byref(strlength),
                                     byref(current_frame),
                                     byref(total_atoms),
                                     xyz)
        # if the xyz has to be returned as numpy data type
        if (return_numpy):

            return np.ctypeslib.as_array(xyz).reshape((total_atoms.value, 3))

        else:

            return xyz


def call_read_xyz_xyz_box_chunk(xyzfile,
                                total_atoms,
                                start,
                                num_configs,
                                read_box=True,
                                return_numpy=True):

    # declare variables:

    xyzfile, strlength = string_to_ctypes_string(xyzfile)

    total_atoms = int_to_ctypes_int(total_atoms)

    start = int_to_ctypes_int(start)

    num_configs = int_to_ctypes_int(num_configs)

    # xyz = ((c_float*total_atoms.value)*3)()

    xyz = np.ctypeslib.as_ctypes(np.zeros(
                                 total_atoms.value*3*num_configs.value,
                                 dtype=np.float64))

    # if the box is read from the xyz
    if (read_box):

        box = np.ctypeslib.as_ctypes(np.zeros(
                                     3*num_configs.value,
                                     dtype=np.float64))

        xyz_lib.call_read_xyz_with_box_chunk(xyzfile,
                                             byref(strlength),
                                             byref(total_atoms),
                                             byref(start),
                                             byref(num_configs),
                                             box,
                                             xyz)

        # if the xyz, box has to be returned as numpy data type
        if (return_numpy):

            xyz = np.ctypeslib.as_array(xyz).reshape((
                                                      num_configs.value,
                                                      total_atoms.value,
                                                      3))

            box = np.ctypeslib.as_array(box).reshape((num_configs.value, 3))

            # return numpy array format of xyz,box
            return xyz, box

        else:

            # return ctypes format of xyz,box
            return xyz, box

    # if the box is not read from the xyz
    else:

        xyz_lib.call_read_xyz_no_box_chunk(xyzfile,
                                           byref(strlength),
                                           byref(total_atoms),
                                           byref(start),
                                           byref(num_configs),
                                           xyz)

        # if the xyz has to be returned as numpy data type
        if (return_numpy):

            return np.ctypeslib.as_array(xyz).reshape((
                                                       num_configs.value,
                                                       total_atoms.value,
                                                       3))

        else:

            return xyz


# -------------------------------------------------------------------------
#                          traj reader
# -------------------------------------------------------------------------


def call_read_header(filename):

    extension = os.path.splitext(filename)

    if (extension[-1] == ".xyz"):

        return call_read_xyz_header(filename)

    elif(extension[-1] == ".dcd"):

        return call_read_dcd_header(filename)


def call_read_traj(filename,
                   current_frame,
                   total_atoms,
                   return_numpy=True,
                   xyz_keyword={"read_box": True}):

    extension = os.path.splitext(filename)

    if (extension[-1] == ".xyz"):

        read_box = xyz_keyword.get("read_box", False)

        return call_read_xyz_xyz_box(filename,
                                     current_frame,
                                     total_atoms,
                                     read_box,
                                     return_numpy)

    elif (extension[-1] == ".dcd"):

        return call_read_dcd_xyz_box(filename,
                                     current_frame,
                                     total_atoms,
                                     return_numpy)


def call_read_chunk_traj(filename,
                         start,
                         num_configs,
                         total_atoms,
                         return_numpy=True,
                         xyz_keyword={"read_box": True}):

    extension = os.path.splitext(filename)

    if (extension[-1] == ".xyz"):

        read_box = xyz_keyword.get("read_box", False)

        return call_read_xyz_xyz_box_chunk(filename,
                                           total_atoms,
                                           start,
                                           num_configs,
                                           read_box,
                                           return_numpy)

    elif (extension[-1] == ".dcd"):

        return call_read_dcd_xyz_box_in_chunk(filename,
                                              start,
                                              num_configs,
                                              total_atoms,
                                              return_numpy)
