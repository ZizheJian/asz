set(CMAKE_C_COMPILER "/apps/spack/anvil/apps/openmpi/4.0.6-gcc-11.2.0-3navcwb/bin/mpicc")
set(CMAKE_C_COMPILER_ARG1 "")
set(CMAKE_C_COMPILER_ID "GNU")
set(CMAKE_C_COMPILER_VERSION "11.2.0")
set(CMAKE_C_COMPILER_VERSION_INTERNAL "")
set(CMAKE_C_COMPILER_WRAPPER "")
set(CMAKE_C_STANDARD_COMPUTED_DEFAULT "17")
set(CMAKE_C_EXTENSIONS_COMPUTED_DEFAULT "ON")
set(CMAKE_C_COMPILE_FEATURES "c_std_90;c_function_prototypes;c_std_99;c_restrict;c_variadic_macros;c_std_11;c_static_assert;c_std_17;c_std_23")
set(CMAKE_C90_COMPILE_FEATURES "c_std_90;c_function_prototypes")
set(CMAKE_C99_COMPILE_FEATURES "c_std_99;c_restrict;c_variadic_macros")
set(CMAKE_C11_COMPILE_FEATURES "c_std_11;c_static_assert")
set(CMAKE_C17_COMPILE_FEATURES "c_std_17")
set(CMAKE_C23_COMPILE_FEATURES "c_std_23")

set(CMAKE_C_PLATFORM_ID "Linux")
set(CMAKE_C_SIMULATE_ID "")
set(CMAKE_C_COMPILER_FRONTEND_VARIANT "GNU")
set(CMAKE_C_SIMULATE_VERSION "")




set(CMAKE_AR "/usr/bin/ar")
set(CMAKE_C_COMPILER_AR "/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/bin/gcc-ar")
set(CMAKE_RANLIB "/usr/bin/ranlib")
set(CMAKE_C_COMPILER_RANLIB "/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/bin/gcc-ranlib")
set(CMAKE_LINKER "/apps/anvil/external/apps/xalt2/xalt/xalt/bin/ld")
set(CMAKE_MT "")
set(CMAKE_COMPILER_IS_GNUCC 1)
set(CMAKE_C_COMPILER_LOADED 1)
set(CMAKE_C_COMPILER_WORKS TRUE)
set(CMAKE_C_ABI_COMPILED TRUE)

set(CMAKE_C_COMPILER_ENV_VAR "CC")

set(CMAKE_C_COMPILER_ID_RUN 1)
set(CMAKE_C_SOURCE_FILE_EXTENSIONS c;m)
set(CMAKE_C_IGNORE_EXTENSIONS h;H;o;O;obj;OBJ;def;DEF;rc;RC)
set(CMAKE_C_LINKER_PREFERENCE 10)

# Save compiler ABI information.
set(CMAKE_C_SIZEOF_DATA_PTR "8")
set(CMAKE_C_COMPILER_ABI "ELF")
set(CMAKE_C_BYTE_ORDER "LITTLE_ENDIAN")
set(CMAKE_C_LIBRARY_ARCHITECTURE "")

if(CMAKE_C_SIZEOF_DATA_PTR)
  set(CMAKE_SIZEOF_VOID_P "${CMAKE_C_SIZEOF_DATA_PTR}")
endif()

if(CMAKE_C_COMPILER_ABI)
  set(CMAKE_INTERNAL_PLATFORM_ABI "${CMAKE_C_COMPILER_ABI}")
endif()

if(CMAKE_C_LIBRARY_ARCHITECTURE)
  set(CMAKE_LIBRARY_ARCHITECTURE "")
endif()

set(CMAKE_C_CL_SHOWINCLUDES_PREFIX "")
if(CMAKE_C_CL_SHOWINCLUDES_PREFIX)
  set(CMAKE_CL_SHOWINCLUDES_PREFIX "${CMAKE_C_CL_SHOWINCLUDES_PREFIX}")
endif()





set(CMAKE_C_IMPLICIT_INCLUDE_DIRECTORIES "/apps/spack/anvil/apps/openmpi/4.0.6-gcc-11.2.0-3navcwb/include;/apps/spack/anvil/apps/numactl/2.0.14-gcc-11.2.0-wrjotmv/include;/apps/spack/anvil/apps/libfabric/1.12.0-gcc-8.4.1-xj6lmd4/include;/apps/spack/anvil/apps/zlib/1.2.11-gcc-11.2.0-g2guo73/include;/apps/spack/anvil/apps/mpc/1.1.0-gcc-8.4.1-dh4xij5/include;/apps/spack/anvil/apps/mpfr/4.0.2-gcc-11.2.0-ke4ellj/include;/apps/spack/anvil/apps/gmp/6.2.1-gcc-11.2.0-trpptvt/include;/home/x-zjian1/hdf5/hdf5-1.14.6/install/include;/home/x-zjian1/jpeg-9f/install/include;/home/x-zjian1/netcdf-c/netcdf-c-4.9.3/install/include;/home/x-zjian1/GKlib/install/include;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib/gcc/x86_64-pc-linux-gnu/11.2.0/include;/usr/local/include;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/include;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib/gcc/x86_64-pc-linux-gnu/11.2.0/include-fixed;/usr/include")
set(CMAKE_C_IMPLICIT_LINK_LIBRARIES "mpi;gcc;gcc_s;pthread;c;gcc;gcc_s")
set(CMAKE_C_IMPLICIT_LINK_DIRECTORIES "/apps/spack/anvil/apps/openmpi/4.0.6-gcc-11.2.0-3navcwb/lib;/apps/spack/anvil/apps/hwloc/2.5.0-gcc-11.2.0-zzxt6un/lib;/apps/spack/anvil/apps/libevent/2.1.12-gcc-11.2.0-loxxg45/lib;/apps/spack/anvil/apps/zlib/1.2.11-gcc-11.2.0-g2guo73/lib;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib64;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib/gcc/x86_64-pc-linux-gnu/11.2.0;/lib64;/usr/lib64;/apps/spack/anvil/apps/numactl/2.0.14-gcc-11.2.0-wrjotmv/lib;/apps/spack/anvil/apps/libfabric/1.12.0-gcc-8.4.1-xj6lmd4/lib;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib;/apps/spack/anvil/apps/mpc/1.1.0-gcc-8.4.1-dh4xij5/lib;/apps/spack/anvil/apps/mpfr/4.0.2-gcc-11.2.0-ke4ellj/lib;/apps/spack/anvil/apps/gmp/6.2.1-gcc-11.2.0-trpptvt/lib;/home/x-zjian1/hdf5/hdf5-1.14.6/install/lib;/home/x-zjian1/jpeg-9f/install/lib;/home/x-zjian1/netcdf-c/netcdf-c-4.9.3/install/lib;/home/x-zjian1/GKlib/install/lib")
set(CMAKE_C_IMPLICIT_LINK_FRAMEWORK_DIRECTORIES "")
