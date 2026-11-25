wp_st="double_st"
use_mpi=true
fortran_compiler=ifort
case=TEST_ORCA_SINGLE

echo "---------------------------"
echo "Precision :" $wp_st 
echo "Use MPI :" $use_mpi
echo "Test case :" $case
echo "Compiling with :" $fortran_compiler
echo "---------------------------"

set -u

./makenemo -n DWARF clean

dircadna=tests/DWARF/MY_SRC_CADNA

[ -d $dircadna ] && rm -rf $dircadna
mkdir -p $dircadna

if [ -d tests/DWARF/WORK_dwarf_org ]
then
    rm -rf tests/DWARF/WORK/
    rsync -a tests/DWARF/WORK_dwarf_org/ tests/DWARF/WORK/
else
    rsync -a tests/DWARF/WORK/ tests/DWARF/WORK_dwarf_org/
fi

ff='tests/'$case'/EXP00/namelist_cfg'
ff_ice='tests/'$case'/EXP00/namelist_ice_cfg'
cfg_vars=$( (sed -nE 's/^ *(rn_[A-Za-z0-9_]*) *=.*$/\1/p' "$ff"; sed -nE 's/^ *(rn_[A-Za-z0-9_]*) *=.*$/\1/p' "$ff_ice") | xargs )

ff='tests/'$case'/EXP00/namelist_ref'
ff_ice='tests/'$case'/EXP00/namelist_ice_ref'
ref_vars=$( (sed -nE 's/^ *(rn_[A-Za-z0-9_]*) *=.*$/\1/p' "$ff"; sed -nE 's/^ *(rn_[A-Za-z0-9_]*) *=.*$/\1/p' "$ff_ice") | xargs )

echo $cfg_vars 
echo $ref_vars
for ff in $( find tests/DWARF/WORK -name "*90" )
do
    echo $ff
    python3 cadna_var.py $ff $dircadna $wp_st $cfg_vars $ref_vars
    #cp $ff $dircadna
done

for ff in  $( find tests/$case/MY_SRC/*90 -name "*90" )
do
    echo $ff
    python3 cadna_var.py $ff $dircadna $wp_st $cfg_vars $ref_vars
done

for ff in  $( find src/ICE/*90 -name "*90" )
do
    echo $ff
    python3 cadna_var.py $ff $dircadna $wp_st $cfg_vars $ref_vars
done

for ff in par_oce.F90 module_example.F90 solfrac_mod.F90 timing.F90 abl.F90 icedyn_rhg_eap.F90 par_ice.F90 par_icedyn.F90
do
    sed -e "/^ *[uU][sS][eE] * par_kind/a\ \ \ USE cadna, cadna_sign => sign\n   USE cadna_mpi, cadna_sign => sign" $dircadna/$ff > tmp
    mv tmp $dircadna/$ff
done

for ff in lbclnk.F90 lbcnfd.F90 mpp_loc_generic.h90
do
    sed -e "/ *# *define * PRECISION * sp/a#define REAL_PRECISION single_st" \
	-e "/ *# *define * PRECISION * dp/a#define REAL_PRECISION double_st" \
	-e "/#undef PRECISION/a#undef REAL_PRECISION" $dircadna/$ff > tmp
    mv tmp $dircadna/$ff
done

ff=nemogcm.F90
if [ "$use_mpi" = true ] ; then
    sed -e "/CALL nemo_closefile/a\      CALL cadna_mpi_end" $dircadna/$ff > tmp
else
    sed -e "/INTEGER ::   istp/a\      CALL cadna_init(-1)" \
        -e "/CALL nemo_closefile/a\      CALL cadna_end()" $dircadna/$ff > tmp
fi
 
mv tmp $dircadna/$ff

#--- Special cases ---

# quick fix to avoid overflow when comparing stochastic variable with HUGE
for ff in mppini.F90 lib_fortran_generic.h90 stpctl.F90 traadv_fct.F90 ldfeke.F90 mpp_nfd_generic.h90 daymod.F90 lib_mpp.F90
do
    sed -E 's/(HUGE *\([^()]+\))/\1\/16/g' $dircadna/$ff > tmp
    mv tmp $dircadna/$( basename $ff )
done

ff=iom.F90
sed -e "/CALL iom_rstput.*DELAY_/d" $dircadna/$ff > tmp
mv tmp $dircadna/$ff

for ff in zdfmxl.F90 
do
    sed -e "/ prt_ctl *(/d" $dircadna/$ff > tmp
    mv tmp $dircadna/$ff
done

ff=domwri.F90
sed -e "/'[uvft]mask'/d" $dircadna/$ff >tmp
mv tmp $dircadna/$ff

ff=diamlr.F90
sed -e "/^ *USE tsltde   ! Tides/a\ \ \ USE cadna, cadna_sign => sign  \nUSE cadna_mpi, cadna_sign => sign" $dircadna/$ff > tmp
mv tmp $dircadna/$ff

# to write number of significant digits
ff=diawri.F90
sed -e "/'misfk/d" \
    -e "/msk/d" \
    -e "/DIMENSION(T2D(   0  ),jpk) ::   z3d/a \      type($wp_st), DIMENSION(T2D(   nn_hls  ),jpk) :: nbdig3d"\
    -e "/DIMENSION(T2D(   0  )    ) ::   z2d/a \      type($wp_st), DIMENSION(T2D(   nn_hls  )    ) :: nbdig2d"\
    -e "/DIMENSION(jpi,jpj,jpk) :: z3d/a \      real(wp), DIMENSION(jpi,jpj,jpk) :: nbdig3d"\
    -e "/DIMENSION(jpi,jpj    ) :: z2d/a \      real(wp), DIMENSION(jpi,jpj) :: nbdig2d" $dircadna/$ff > tmp
mv tmp $dircadna/$ff

# pbs due to cmplx
ff=prtctl.F90
sed -e "/, *clfmt *) *[RA][EI][AM][LA]/d" $dircadna/$ff > tmp
mv tmp $dircadna/$ff

# initialize logicals
ff=sbc_oce.F90
sed 's/::   ln_icebergs/::   ln_icebergs = .false./' "$dircadna/$ff" > tmp
mv tmp "$dircadna/$ff"

#--- MPI variables and operations ---

if [ "$use_mpi" = true ] ; then

ff=lib_mpp.F90
sed -e "/CALL mpi_comm_size( mpi_comm_oce, mppsize, ierr )/a \      call cadna_mpi_init(mpprank, -1)" $dircadna/$ff > tmp
mv tmp $dircadna/$ff

for ff in lbclnk.F90 lbcnfd.F90 timing.F90 lib_mpp.F90 mpp_allreduce_generic.h90 
do
    sed -e "s/mpi_real/mpif_single_st/ig" \
        -e "s/mpi_double_precision/mpif_double_st/ig"\
        -e "s/mpi_complex/mpif_complex_st/ig" \
        -e "s/mpi_double_complex/mpif_double_complex_st/ig" $dircadna/$ff > tmp
    mv tmp $dircadna/$ff
done

ff=mpp_loc_generic.h90
sed -E \
    -e 's/mpi_2real/mpif_2single_st/ig'\
    -e 's/mpi_2double_precision/mpif_2double_st/ig'\
    -e 's/(OPERATION_(MINLOC|MAXLOC))/\1\
#      if defined REALDP_TYPE\n#         define MPI_OPERATION mpif_cadna_\2_dp\
#      elif defined REALSP_TYPE\n#         define MPI_OPERATION mpif_cadna_\2_sp\n#      else/' \
    -e 's/#      (define MPI_OPERATION MPI_(MINLOC|MAXLOC))/#         \1\n#      endif/' $dircadna/$ff > tmp
mv tmp "$dircadna/$ff"

ff=mpp_allreduce_generic.h90
sed -E \
    -e 's/(OPERATION_(MIN|MAX))/\1\
#      if defined REALDP_TYPE\n#         define MPI_OPERATION mpif_cadna_\2_dp\
#      elif defined REALSP_TYPE\n#         define MPI_OPERATION mpif_cadna_\2_sp\n#      else/' \
    -e 's/#      (define MPI_OPERATION MPI_(MIN|MAX))/#         \1\n#      endif/' $dircadna/$ff > tmp
mv tmp "$dircadna/$ff"

fi

#--- Compilation and execution ---

if [ "$use_mpi" = true ] ; then
    if [[ $wp_st == "double_st" ]]
    then 
        ./makenemo -n DWARF --my_srcpath "MY_SRC MY_SRC_DUMMY_PY MY_SRC_CADNA" -j 8 -m marthe_$fortran_compiler  --del_key key_mpi_off --del_key key_single --add_key key_xios --add_key key_qco --add_key key_vco_1d3d --add_key key_si3 --debug
    else
        ./makenemo -n DWARF --my_srcpath "MY_SRC MY_SRC_DUMMY_PY MY_SRC_CADNA" -j 8 -m marthe_sp_$fortran_compiler  --del_key key_mpi_off --add_key key_xios --add_key key_qco --add_key key_vco_1d3d --add_key key_si3 --debug
    fi
else
    if [[ $wp_st == "double_st" ]]
    then
        ./makenemo -n DWARF --my_srcpath "MY_SRC MY_SRC_DUMMY_PY MY_SRC_CADNA" -j 8 -m marthe_$fortran_compiler --add_key key_mpi_off --del_key key_xios
    else
	./makenemo -n DWARF --my_srcpath "MY_SRC MY_SRC_DUMMY_PY MY_SRC_CADNA" -j 8 -m marthe_sp_$fortran_compiler --add_key key_mpi_off --del_key key_xios
    fi
fi

#cd tests/DWARF/EXP00/
#if [ "$use_mpi" = true ] ; then
#    mpirun -np 8 ./nemo
#else
#    ./nemo
#fi
#
#cat time.step
#cd -
