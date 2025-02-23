!--------------------------------- Program Descriptions -----------------------------

! This module contains routines to perform radial distribution function calculations

! Date composed by Jingxiang Guo : 7/2/2020 

module RDF
    use system
    use constants, only: pi
    implicit none 
    private 

    public :: build_homo_pair_distance_histogram, & 
            & build_homo_pair_distance_histogram_in_chunk,& 
            & normalize_histogram 

contains

    subroutine build_homo_pair_distance_histogram(total_atoms,&
                                                 & cutoff,&
                                                 & num_bins,&
                                                 & XYZ,&
                                                 & L_xyz,&
                                                 & rdf_histogram) &
                                                 & bind(c,name="homo_pair_distance_histogram") 
        implicit none
        
        ! Passed 
        integer(c_int),intent(in) :: total_atoms,num_bins 
        real(c_double),intent(in) :: cutoff
        real(c_float),intent(in),dimension(1:3,1:total_atoms) :: XYZ
        real(c_double),intent(in),dimension(1:3) :: L_xyz

        ! Local 
        real(dp),dimension(1:size(L_xyz)) :: xyz_temp,xyz_separate
        integer :: i,j,bin_index
        real(dp) :: distance_sqr,distance,cutoff_sqr,r_interval 

        ! Output 
        real(c_double),intent(out),dimension(1:num_bins) :: rdf_histogram

        r_interval = cutoff/num_bins 

        cutoff_sqr = cutoff*cutoff

        rdf_histogram = 0.0d0 

        do i = 1, total_atoms-1

            xyz_temp = xyz(1:3,i)

            do j = i + 1,total_atoms

                ! compute the separation vector between i,j  

                xyz_separate = xyz_temp - xyz(1:3,j)

                ! apply minimum image convention 

                xyz_separate = xyz_separate - L_xyz*dnint(xyz_separate/L_xyz)

                ! sum of squared separation vector  

                distance_sqr = xyz_separate(1)*xyz_separate(1) & 
                           & + xyz_separate(2)*xyz_separate(2) & 
                           & + xyz_separate(3)*xyz_separate(3)

                if (distance_sqr < cutoff_sqr ) then 
                    
                    bin_index = int(dsqrt(distance_sqr)/r_interval) + 1
                    
                    rdf_histogram(bin_index)  =  rdf_histogram(bin_index) + 2

                end if

            end do 

        end do

        end subroutine 

    subroutine build_homo_pair_distance_histogram_in_chunk(total_atoms,&
                                                 & num_configs,& 
                                                 & cutoff,&
                                                 & num_bins,&
                                                 & XYZ,&
                                                 & L_xyz,&
                                                 & rdf_histogram, &
                                                 & sum_volume)&
                                                 & bind(c,name="call_homo_pair_distance_histogram_in_chunk") 
        implicit none

        ! Passed 
        integer(c_int),intent(in) :: total_atoms,num_bins,num_configs 
        real(c_double),intent(in) :: cutoff
        real(c_double),intent(in),dimension(1:3,1:total_atoms,1:num_configs) :: XYZ
        real(c_double),intent(in),dimension(1:3,1:num_configs) :: L_xyz

        ! Local 
        real(dp),dimension(1:size(L_xyz)) :: xyz_temp,xyz_separate
        integer :: i,j,bin_index,iconfig
        real(dp) :: distance_sqr,distance,cutoff_sqr,r_interval 
        real(dp),dimension(1:3) :: box  

        ! Output 
        real(c_double),intent(out),dimension(1:num_bins) :: rdf_histogram
        real(c_double),intent(out) :: sum_volume
        
        r_interval = cutoff/num_bins 

        cutoff_sqr = cutoff*cutoff

        rdf_histogram = 0.0d0 

        sum_volume = 0.0

        do iconfig = 1, num_configs 
    
            box = L_xyz(:,iconfig) 

            sum_volume = sum_volume + product(box)

            do i = 1, total_atoms-1

                xyz_temp = xyz(1:3,i,iconfig)

                do j = i + 1,total_atoms

                    ! compute the separation vector between i,j  

                    xyz_separate = xyz_temp - xyz(1:3,j,iconfig)

                    ! apply minimum image convention 

                    xyz_separate = xyz_separate - box*dnint(xyz_separate/box)

                    ! sum of squared separation vector  

                    distance_sqr = xyz_separate(1)*xyz_separate(1) & 
                               & + xyz_separate(2)*xyz_separate(2) & 
                               & + xyz_separate(3)*xyz_separate(3)

                    if (distance_sqr < cutoff_sqr ) then 
                        
                        bin_index = int(dsqrt(distance_sqr)/r_interval) + 1
                        
                        rdf_histogram(bin_index)  =  rdf_histogram(bin_index) + 2

                    end if

                end do 

            end do

        end do 
        
        end subroutine 

    subroutine normalize_histogram(rdf_histogram, &
                                 & num_bins,&
                                 & cutoff,&
                                 & natoms,&
                                 & num_configs,&
                                 & bulk_density,&
                                 & gr) bind(c,name="call_normalize_histogram")
        implicit none  

        ! Passed 
        integer(c_int),intent(in) :: num_bins,natoms,num_configs
        real(c_double),intent(in),dimension(1:num_bins) :: rdf_histogram 
        real(c_double),intent(in) :: cutoff,bulk_density  

        ! Local
        real(dp) :: preconst,vshell_i,half_interval,upper_r,lower_r,center_r,r_interval  
        integer :: i 

        ! Output
        real(c_double),dimension(1:num_bins),intent(out) :: gr  

        preconst = 4.0d0/3.0d0*pi

        half_interval = r_interval/2.0d0*natoms 

        r_interval = cutoff/num_bins

        do i = 1,num_bins 

            upper_r = i*r_interval 

            lower_r = (i-1)*r_interval

            center_r = half_interval + r_interval*(i-1)

            vshell_i = preconst*( ( upper_r*upper_r*upper_r ) - (lower_r*lower_r*lower_r) )  

            gr(i) = rdf_histogram(i)/( vshell_i*bulk_density*natoms*num_configs)

        end do 				

        end subroutine 

end module 
