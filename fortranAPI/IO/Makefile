SHELL = /bin/sh

# fortran compiler 
FC = ifort #

FFLAGS_D = -fPIC -shared

FFLAGS_S = -c 

INC_DIR = include/

LIB_DIR = lib/

link_to_system = -L../general/lib/ 

libfile = -lforsys

sys_include = -I ../general/include

local_include = -module include/

system_file= ../general/src/system_mod.f90

all: lib/libdcd_reader.so lib/libtxt_reader.so lib/libxyz_reader.so lib/libforIO.a 

# compile all source codes into dynamic library 
$(LIB_DIR)libdcd_reader.so: src/dcd_reader_mod.f90

	@ mkdir -p $(LIB_DIR)
	@ mkdir -p $(INC_DIR)

	$(FC) $(FFLAGS_D) $(system_file) src/dcd_reader_mod.f90  -o $(LIB_DIR)libdcd_reader.so
	
	@ mv *.mod $(INC_DIR) 
 
$(LIB_DIR)libtxt_reader.so: src/txt_reader_mod.f90

	@ mkdir -p $(LIB_DIR)
	@ mkdir -p $(INC_DIR)

	$(FC) $(FFLAGS_D) $(system_file) src/txt_reader_mod.f90  -o $(LIB_DIR)libtxt_reader.so 

	@ mv *.mod $(INC_DIR) 

$(LIB_DIR)libxyz_reader.so: src/xyz_reader_mod.f90

	@ mkdir -p $(LIB_DIR)
	@ mkdir -p $(INC_DIR)

	$(FC) $(FFLAGS_D) $(system_file) src/xyz_reader_mod.f90  -o $(LIB_DIR)libxyz_reader.so 

	@ mv *.mod $(INC_DIR) 

# compile all source codes into static library 

xyz_reader_mod.o: src/xyz_reader_mod.f90

	@ mkdir -p $(LIB_DIR)
	@ mkdir -p $(INC_DIR)

	$(FC) $(FFLAGS_S) $(link_to_system) $(libfile) src/xyz_reader_mod.f90  $(sys_include) 

	@ mv *.mod $(INC_DIR) 

txt_reader_mod.o: src/txt_reader_mod.f90

	@ mkdir -p $(LIB_DIR)
	@ mkdir -p $(INC_DIR)

	$(FC) $(FFLAGS_S) $(link_to_system) $(libfile) src/txt_reader_mod.f90  $(sys_include)  

	@ mv *.mod $(INC_DIR) 

dcd_reader_mod.o: src/dcd_reader_mod.f90

	@ mkdir -p $(LIB_DIR)
	@ mkdir -p $(INC_DIR)

	$(FC) $(FFLAGS_S) $(link_to_system) $(libfile) src/dcd_reader_mod.f90 $(sys_include)  

	@ mv *.mod $(INC_DIR) 

$(LIB_DIR)libforIO.a: dcd_reader_mod.o xyz_reader_mod.o txt_reader_mod.o  

	@ mkdir -p $(LIB_DIR)
	
	ar -cvq $(LIB_DIR)libforIOlib.a dcd_reader_mod.o xyz_reader_mod.o txt_reader_mod.o  

.PHONY: all clean count

clean:

	rm *.o 

