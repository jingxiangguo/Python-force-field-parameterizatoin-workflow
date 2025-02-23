!----------------------------------------------- Program Descriptions --------------------------------------------- 

! This modules provide subroutines to read a dcd file  

! The subroutine/function names with "call_xxx" can be called from Python or C 

! Date composed by Jingxiang Guo : 04/15/2020 

module DCD_reader_mod
	use system
	implicit none 
	! all variables and subroutines/functions are private  
	private 

	! Export these subroutines/functions as public ( other subroutines/functions are still private):
	public :: readdcdheader, & 
             & call_read_dcd_header,& 
             & call_read_dcd_traj,& 
             & call_read_dcd_traj_in_chunk,& 
			 & read_xyz_box,& 
			 & read_xyz_box_in_chunk

	! Global varialbes: 
	
contains

!----------------------------------------------------------------------------------------------------------------- 
!                                               Interfacing with C                                                 
!----------------------------------------------------------------------------------------------------------------- 
	
    subroutine call_read_dcd_header(dcdfile,& 
                                  & strleng,&
                                  & total_atoms,&
                                  & total_frames)&
                                  & bind(c,name="call_dcd_header")
        implicit none 

        ! Passed:  
        integer(c_int),intent(in) :: strleng 
        character(kind=c_char,len=1),intent(in),dimension(1:strleng) :: dcdfile 

        ! Local: 
        character(len=:),allocatable :: filename 

        ! Output: 
        integer(c_int),intent(out) :: total_atoms, total_frames  
        integer :: i 

        call convert_c_string_f_string(dcdfile,strleng,filename)  

        call readdcdheader(filename,total_atoms,total_frames)  

        end subroutine 

    subroutine call_read_dcd_traj(dcdfile,&
                                & strleng,& 
                                & total_atoms,& 
                                & current_frame,&
                                & box,&
                                & xyz)&
                                & bind(c,name="call_dcd_traj")
        implicit none 
    
        ! Passed: 
        integer(c_int),intent(in) :: strleng,total_atoms,current_frame
        character(kind=c_char,len=1),intent(in),dimension(1:strleng) :: dcdfile  
   
        ! Local: 
        character(len=:),allocatable :: filename 

        ! Output: 
        real(c_float), intent(out),dimension(1:3,1:total_atoms) :: xyz  
        real(c_double),intent(out),dimension(1:3) :: box 

        
        call convert_c_string_f_string(dcdfile,strleng,filename) 
        
        call read_xyz_box(filename,total_atoms,current_frame,xyz,box) 

        end subroutine 

    subroutine call_read_dcd_traj_in_chunk(dcdfile,&
                                         & strleng,&
                                         & start_at,&
                                         & num_configs,&
                                         & total_atoms,&
                                         & box,&
                                         & xyz) bind(c,name="call_dcd_traj_chunk")
        implicit none 

        ! Passed: 
        integer(c_int),intent(in) :: start_at,strleng,total_atoms,num_configs 
        character(kind=c_char,len=1),intent(in),dimension(1:strleng) :: dcdfile  

        ! Local: 
        character(len=:),allocatable :: filename

        ! Output: 
        real(c_float), intent(out),dimension(1:3,1:total_atoms,1:num_configs) :: xyz  
        real(c_double),intent(out),dimension(1:3,1:num_configs) :: box 

        call convert_c_string_f_string(dcdfile,strleng,filename) 
        
        call read_xyz_box_in_chunk(filename,start_at,num_configs,total_atoms,xyz,box) 

        end subroutine 
!----------------------------------------------------------------------------------------------------------------- 
!                                               Fortran Dcd Reader                                                 
!----------------------------------------------------------------------------------------------------------------- 

	subroutine readdcdheader(dcdfile,total_atoms,total_frames) 
		implicit none 
		character(len=*),intent(in) :: dcdfile
		integer,dimension(20) :: ICNTRL
		character(len=3) :: fext
		character(len=4) :: HDR
		real(sp) :: delta
		integer :: i,unitnum
		integer,intent(out) :: total_atoms,total_frames 

		unitnum = 1234 
        

		open(unit=unitnum,file=trim(dcdfile),form='unformatted',status='old')
            
			read(unitnum) HDR, (ICNTRL(i),i=1,9),delta,(ICNTRL(i),i=11,20)
			read(unitnum)
			read(unitnum) total_atoms 
            
			total_frames =  ICNTRL(1)

		close(unitnum)

		end subroutine 

	subroutine read_xyz_box(dcdfile,total_atoms,current_frame,xyz,box) 
		implicit none 
		character(len=*),intent(in)  :: dcdfile 
		integer,intent(in) :: current_frame
        integer,intent(in),value :: total_atoms 
		integer ::i,iframe,imol,counter,unitnum 
		real(dp),dimension(6) :: XTLABC 
		real(dp),intent(out),dimension(1:3) :: box 
		real(sp),intent(out),dimension(1:3,1:total_atoms) :: xyz  

		unitnum = 123 

		open(unit=unitnum,file=trim(dcdfile),form='unformatted',status='old') 

			read(unitnum)
			read(unitnum)
			read(unitnum)

			do i = 1, current_frame - 1  

				read(unitnum)
				read(unitnum)
				read(unitnum)
				read(unitnum)

			end do 

			read(unitnum) (XTLABC(i),i=1,6) 
        
			read(unitnum) (xyz(1,imol),imol=1,total_atoms) 
			read(unitnum) (xyz(2,imol),imol=1,total_atoms) 
			read(unitnum) (xyz(3,imol),imol=1,total_atoms) 

			box =  [ XTLABC(1),XTLABC(3),XTLABC(6) ] 

		close(unitnum) 

		end subroutine 

	subroutine read_xyz_box_in_chunk(dcdfile,start_at,num_configs,total_atoms,xyz,box) 
		implicit none 
		character(len=*),intent(in)  :: dcdfile 
		integer,intent(in) :: start_at,total_atoms,num_configs
		integer ::i,iframe,imol,counter,unitnum 
		real(dp),dimension(6) :: XTLABC 
		real(dp),intent(out),dimension(1:3,1:num_configs):: box 	
		real(sp),intent(out),dimension(1:3,1:total_atoms,1:num_configs) :: xyz 	

		unitnum = 10000 

		counter = 0 

		open(unit=unitnum,file=trim(dcdfile),form='unformatted',status='old') 
		
			! DCD Header 

			read(unitnum)
			read(unitnum)
			read(unitnum)

			! Skip these frames 

			do i = 1, start_at - 1 		

				read(unitnum)
				read(unitnum)
				read(unitnum)
				read(unitnum) 

			end do 
		
			! Read these frames 	
			
			do iframe = 1,num_configs

				read(unitnum) (XTLABC(i),i=1,6)
				read(unitnum) xyz(1,:,iframe)  
				read(unitnum) xyz(2,:,iframe) 
				read(unitnum) xyz(3,:,iframe)

				box(1:3,iframe) =  [ XTLABC(1),XTLABC(3),XTLABC(6) ] 

			end do 

		close(unitnum) 	

		end subroutine   

end module 
