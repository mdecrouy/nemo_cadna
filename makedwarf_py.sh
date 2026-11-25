rm -rf tests/DWARF

./makenemo -n DWARF -a TEST_ORCA_SINGLE --del_key "key_si3 key_top key_xios key_mpi_off" -j 0 #--add_key "key_mpi_off"

dirdummy=tests/DWARF/MY_SRC_DUMMY_PY

[ ! -d $dirdummy ] && mkdir -p $dirdummy

for ff in src/OCE/ASM/*90 \
	      src/OCE/BDY/*90 \
	      src/OCE/C1D/*90 \
	      src/OCE/DIU/*90 \
	      src/OCE/ICB/*90 \
	      src/OCE/ISF/*90 \
	      src/OCE/OBS/*90 \
	      src/OCE/STO/*90 \
	      src/OCE/TSL/*90 \
	      src/OCE/TRD/*90 \
	      src/OCE/SBC/sbccpl.F90
	      #src/OCE/SBC/*90
	      #src/OCE/DIA/*90 \
do
	echo $ff
    python3.11 ./makedummy.py $ff $dirdummy
done

./makenemo -n DWARF --my_srcpath "MY_SRC MY_SRC_DUMMY_PY" -j 0

# delete unused variables declaration

for ff in $dirdummy/*90; do
	echo $ff

	vars=$(sed -e "/^ *TYPE *[^(]/,/^ *[eE][nN][dD] *[tT][yY][pP][eE]/d" $ff | 
		grep -i -E "^ *(integer|real|logical|character|type *\().*::" | 
		grep -iv intent | 
		sed -e "s/.*:: *//" -e "s/ *= *[^,]* */ /g" -e "s/ *, */ /g" -e "s/(.*)//g" |
		grep -Eo '\b[A-Za-z][A-Za-z0-9_]*\b') 

	vars_to_clean=

	nn=mskisf_cav
	for nn in $vars; do
		nb=$(grep -c -m2 $nn $ff) # search first in file where variable is declared
		if [ $nb -eq 1 ]; then

			nb=$(cat tests/DWARF/WORK/*90 | grep -m2 -c $nn)
			if [ $nb -eq 1 ]; then
				vars_to_clean="${vars_to_clean} $nn"
			fi
		fi
	done

	if [ -n "${vars_to_clean// }" ]; then
		echo $vars_to_clean
		python3.11 ./clean_var.py $ff $dirdummy $vars_to_clean
	fi

	sed -e "/:: *$/d" $ff > tmp
	mv tmp $ff
done
	
./makenemo -m marthe_sp_ifort -n DWARF --my_srcpath "MY_SRC MY_SRC_DUMMY_PY" -j 8 --debug

