##############################################################################

# Python-force-field-parameterization-workflow:
# A Python Library for performing force-field optimization

#

# Authors: Jingxiang Guo, Jeremy Palmer

#

# Python-force-field-parameterization-workflow is free software;
# you can redistribute it and/or modify it under the terms of the
# MIT License

# You should have received a copy of the MIT License along with the package.

##############################################################################


"""
This module contains a class defining how to invoke a MD simulators
to compute predicted properties once a new set of optimized
force-field parameter is generated.

The major task of this class is:
1. Taking the shell command from the input files
processing it, and determine the number of cores for each job
2. Generate and store a list of folders where predicted properties are computed 
3. Loop over each folder and invoke the shell command to run simulations 

"""

# Python standard library:
import subprocess
import sys
import time
import logging
import os

# customized library:
from sampling.potential_LAMMPS import choose_lammps_potential,\
                                      propagate_force_field
# Third-party library 
import gmso 
# Launch and Terminate sampling jobs


class run_as_subprocess:

    """Invoke external sampling softwares of choice to compute predicted properties
       using the optimzied force-field parameters in every iterations:

    -Parameters:
    ------------

    matching_type:
    e.g."rdf", "force" ....

    wk_folder: which folders simulations should be run
    e.g. job_1234/predicted/rdf/

    cores: number of cores used in simulation
    e.g. srun -n 4  or mpirun -np 4

    -Return:
    --------

    finish: True if all jobs run successfully and False otherwise
    """

    # Class variables visible for all objects

    command_list_cls = []

    wk_folder_list_cls = []

    @classmethod
    def __init__(cls,
                 packagename,
                 matching_type,
                 wk_folder_tple,
                 num_jobs,
                 command,
                 total_cores_assigned,
                 HOME):

        cls.packagename = packagename

        cls.matching_type = matching_type

        cls.sampling_cores_assignment(matching_type,
                                      num_jobs,
                                      total_cores_assigned)
        cls.num_jobs = num_jobs

        command_modified = command % (cls.cores_per_job, matching_type)

        cls.command = command_modified

        # For every matching type,
        # save its command and working folders into list

        cls.update_matching(command_modified, wk_folder_tple)

        # Print the Initialization information:

        cls.print_initialization()

        cls.HOME = HOME

        return None

    @classmethod
    def sampling_cores_assignment(cls,
                                  matching_type,
                                  num_jobs,
                                  total_cores_assigned):

        cores_logger = logging.getLogger(__name__)

        cls.cores_per_job = int(total_cores_assigned/num_jobs)

        if (cls.cores_per_job == 0):

            cores_logger.error("ERROR: " + matching_type + " : " +
                               "The total number of cores requested ( %d )"
                               " through input file " % total_cores_assigned +
                               "is less than the number jobs (%d)"
                               " ...\n" % (num_jobs) +
                               "Watch out performance degration!")

            sys.exit("Check errors in the log file")

        return None

    @classmethod
    def print_initialization(cls):

        logger = logging.getLogger(__name__)

        logger.info("------------------------- Initialize sampling method: "
                    "%s -------------------------\n\n" % (cls.packagename))

        logger.info("Number of jobs: %d \n" % cls.num_jobs)

        logger.info("Number of cores used per job:  %d \n"
                    % (cls.cores_per_job))

        logger.info("Command:  %s \n" % cls.command)

        return None

    @classmethod
    def Launch_Jobs(cls, cmd, joblist):

        out = open("output", "w")

        error = open("error", "w")

        joblist.append(subprocess.Popen(cmd,
                       stdout=out, stderr=error, shell=True))

        return joblist

    @classmethod
    def update_matching(cls, command, working_folders):

        cls.command_list_cls.append(command)

        cls.wk_folder_list_cls.append(working_folders)

        return None

    @classmethod
    def useGMSO(cls, content_dict, force_field_parameters):
        logger = logging.getLogger(__name__)
        all_keys = list(content_dict.keys()) 
        if (content_dict[all_keys[0]][0] == "TurnOnGMSO"):
            top = content_dict[all_keys[0]][2]
            write_lammpsdata = content_dict[all_keys[0]][1] 
            set_params = content_dict[all_keys[0]][4]
            top = set_params(top, force_field_parameters) 
            write_lammpsdata(top, all_keys[0], content_dict[all_keys[0]][3])

    @classmethod
    def run(cls, type_name, force_field_parameters):

        """
        Iteratively change into each working folder to run
        simulations from commandline.

        -Parameters:
        ------------

        Working folders list ( wk_folder_list_cls):
        change to target folders corresponding to properties

        Command list ( command_list_cls):
        apply command corresponding to proeprties

        -Return:
        --------

        exit_code for each subprocess after they finish

        """

        run_logger = logging.getLogger(__name__)

        run_logger.debug("Ready to Run jobs ... ")

        output_content_dict = choose_lammps_potential(type_name,
                                                      force_field_parameters)

        propagate_force_field(cls.wk_folder_list_cls, output_content_dict)

        All_jobs = []

        # iterate each type of properties in the list

        for indx, cmd in enumerate(cls.command_list_cls):

            each_matching_type = []

            for folder in cls.wk_folder_list_cls[indx]:

                os.chdir(folder)
                cls.useGMSO(output_content_dict, force_field_parameters)

                each_matching_type = cls.Launch_Jobs(cmd, each_matching_type)

                time.sleep(0.02)

            All_jobs.append(each_matching_type)

        cls.exit_codes = [[job.wait() for job in matching_type]
                          for matching_type in All_jobs]

        os.chdir(cls.HOME)

        run_logger.debug("All LAMMPS jobs are launched ... ")

        return None

    @classmethod
    def exit(cls):

        """
        Check if LAMMPS jobs ran successfully:


        -Parameters:
        ------------
        exit_code "0" means job is sumbitted and run successfully
        error file size = 0 means no error messages written

        -Return:
        --------

        finish = True if all jobs exit successful.

        """

        exit_logger = logging.getLogger(__name__)

        for type_index, matching in enumerate(cls.wk_folder_list_cls):

            for sub_index, fd in enumerate(matching):

                if (os.stat(fd + "/error").st_size == 0 and
                   cls.exit_codes[type_index][sub_index] == 0):

                    continue

                else:

                    error_command = cls.command_list_cls[type_index]

                    at_folder = cls.wk_folder_list_cls[type_index][sub_index]

                    exit_logger.error("ERROR: Command: %s, Folders: %s "
                                      % (error_command, at_folder))

                    return False

        exit_logger.debug("LAMMPS exits successfully")

        return True
