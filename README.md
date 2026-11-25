# CADNA Integration for NEMO

This repository contains scripts to modify NEMO source files in order to enable numerical stochastic analysis using **CADNA**.

The .sh and .py scripts must be placed in the root NEMO directory (alongside the main NEMO files and directories) before execution.

The process consists of two main steps:
1. Cleaning up unused source files to simplify the modification process.
2. Generating modified NEMO sources compatible with CADNA.

## Prerequisites

Before running the scripts, make sure the following software is installed and properly configured:

- **NEMO** – the NEMO source code.
- **CADNA** – the CADNA library (Control of Accuracy and Debugging for Numerical Applications). See the [official CADNA website](https://cadna.lip6.fr/) for installation instructions and documentation. **Make sure to enable Fortran support when configuring and installing CADNA.**

### NEMO Configuration

Before running the scripts, edit `mk/bld.cfg` in the root NEMO directory and add the following lines:

```text
bld::excl_dep        use::cadna
bld::excl_dep        use::cadna_mpi
```

These exclusions are required for NEMO to compile correctly with the modified CADNA sources.

## Usage

The workflow consists of running the following two scripts in order.

### 1. Empty unused source files

```bash
./makedummy.sh
```

This script calls two Python scripts:

- `makedummy.py`: empties source files that are not required for the current configuration.
- `clean_var.py`: removes unused variables from the remaining source files.

This step reduces the amount of source code that needs to be processed during the subsequent CADNA modifications, while preserving the original file structure.

The modified sources can be found in:

`nemo/tests/DWARF/MY_SRC_DUMMY_PY`

After running the script, the modified sources can be found in:

`nemo/tests/DWARF/MY_SRC_DUMMY_PY`

### 2. Generate CADNA-compatible NEMO sources

```bash
./makecadna.sh
```

This script uses the Python script `cadna_var.py` to generate modified NEMO source files compatible with CADNA-based stochastic arithmetic.

The script takes the following configuration options into account:

- **Precision:** Selects between single and double precision.
- **Compiler:** Specifies the Fortran compiler to be used.
- **MPI:** Determines whether the generated sources should use MPI (parallel execution) or run in sequential mode.

The script modifies the NEMO source code, replacing standard floating-point variables and operations with their corresponding CADNA stochastic arithmetic equivalents where required. 

After running the script, the modified sources can be found in:

`nemo/tests/DWARF/MY_SRC_CADNA`

The script automatically then compiles the modified NEMO sources with CADNA, using custom architecture files:

`arch-marthe[_sp]_[compiler].fcm`

where:
- `_sp` is included when using single precision.
- `[compiler]` specifies the selected compiler.

**Important:** These files contain library paths pointing to the original development environment. Before compilation, make sure to update these paths to match your local installations of **XIOS** and **CADNA**.

## MPI Support and Warnings

**MPI support may be compiler-dependent and is not guaranteed to work in all configurations.**

In particular:
- MPI compatibility may vary depending on the compiler and its configuration.
- Some combinations of compiler and MPI settings may produce errors.
- In certain cases, MPI execution may work with a specific number of processes but fail with others.

**Recommendation:** Start by testing the generated sources in sequential mode (without MPI). Once the sequential configuration is working correctly, proceed with MPI.

If MPI-related issues occur, try different numbers of processes and check the compatibility of your compiler and MPI implementation.

## Workflow Summary

```bash
# Step 1: Empty unused source files
./makedummy.sh

# Step 2: Generate CADNA-compatible NEMO sources
./makecadna.sh
```
