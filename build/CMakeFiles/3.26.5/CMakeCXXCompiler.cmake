set(CMAKE_CXX_COMPILER "/apps/spack/anvil/apps/openmpi/4.0.6-gcc-11.2.0-3navcwb/bin/mpiCC")
set(CMAKE_CXX_COMPILER_ARG1 "")
set(CMAKE_CXX_COMPILER_ID "GNU")
set(CMAKE_CXX_COMPILER_VERSION "11.2.0")
set(CMAKE_CXX_COMPILER_VERSION_INTERNAL "")
set(CMAKE_CXX_COMPILER_WRAPPER "")
set(CMAKE_CXX_STANDARD_COMPUTED_DEFAULT "17")
set(CMAKE_CXX_EXTENSIONS_COMPUTED_DEFAULT "ON")
set(CMAKE_CXX_COMPILE_FEATURES "cxx_std_98;cxx_template_template_parameters;cxx_std_11;cxx_alias_templates;cxx_alignas;cxx_alignof;cxx_attributes;cxx_auto_type;cxx_constexpr;cxx_decltype;cxx_decltype_incomplete_return_types;cxx_default_function_template_args;cxx_defaulted_functions;cxx_defaulted_move_initializers;cxx_delegating_constructors;cxx_deleted_functions;cxx_enum_forward_declarations;cxx_explicit_conversions;cxx_extended_friend_declarations;cxx_extern_templates;cxx_final;cxx_func_identifier;cxx_generalized_initializers;cxx_inheriting_constructors;cxx_inline_namespaces;cxx_lambdas;cxx_local_type_template_args;cxx_long_long_type;cxx_noexcept;cxx_nonstatic_member_init;cxx_nullptr;cxx_override;cxx_range_for;cxx_raw_string_literals;cxx_reference_qualified_functions;cxx_right_angle_brackets;cxx_rvalue_references;cxx_sizeof_member;cxx_static_assert;cxx_strong_enums;cxx_thread_local;cxx_trailing_return_types;cxx_unicode_literals;cxx_uniform_initialization;cxx_unrestricted_unions;cxx_user_literals;cxx_variadic_macros;cxx_variadic_templates;cxx_std_14;cxx_aggregate_default_initializers;cxx_attribute_deprecated;cxx_binary_literals;cxx_contextual_conversions;cxx_decltype_auto;cxx_digit_separators;cxx_generic_lambdas;cxx_lambda_init_captures;cxx_relaxed_constexpr;cxx_return_type_deduction;cxx_variable_templates;cxx_std_17;cxx_std_20;cxx_std_23")
set(CMAKE_CXX98_COMPILE_FEATURES "cxx_std_98;cxx_template_template_parameters")
set(CMAKE_CXX11_COMPILE_FEATURES "cxx_std_11;cxx_alias_templates;cxx_alignas;cxx_alignof;cxx_attributes;cxx_auto_type;cxx_constexpr;cxx_decltype;cxx_decltype_incomplete_return_types;cxx_default_function_template_args;cxx_defaulted_functions;cxx_defaulted_move_initializers;cxx_delegating_constructors;cxx_deleted_functions;cxx_enum_forward_declarations;cxx_explicit_conversions;cxx_extended_friend_declarations;cxx_extern_templates;cxx_final;cxx_func_identifier;cxx_generalized_initializers;cxx_inheriting_constructors;cxx_inline_namespaces;cxx_lambdas;cxx_local_type_template_args;cxx_long_long_type;cxx_noexcept;cxx_nonstatic_member_init;cxx_nullptr;cxx_override;cxx_range_for;cxx_raw_string_literals;cxx_reference_qualified_functions;cxx_right_angle_brackets;cxx_rvalue_references;cxx_sizeof_member;cxx_static_assert;cxx_strong_enums;cxx_thread_local;cxx_trailing_return_types;cxx_unicode_literals;cxx_uniform_initialization;cxx_unrestricted_unions;cxx_user_literals;cxx_variadic_macros;cxx_variadic_templates")
set(CMAKE_CXX14_COMPILE_FEATURES "cxx_std_14;cxx_aggregate_default_initializers;cxx_attribute_deprecated;cxx_binary_literals;cxx_contextual_conversions;cxx_decltype_auto;cxx_digit_separators;cxx_generic_lambdas;cxx_lambda_init_captures;cxx_relaxed_constexpr;cxx_return_type_deduction;cxx_variable_templates")
set(CMAKE_CXX17_COMPILE_FEATURES "cxx_std_17")
set(CMAKE_CXX20_COMPILE_FEATURES "cxx_std_20")
set(CMAKE_CXX23_COMPILE_FEATURES "cxx_std_23")

set(CMAKE_CXX_PLATFORM_ID "Linux")
set(CMAKE_CXX_SIMULATE_ID "")
set(CMAKE_CXX_COMPILER_FRONTEND_VARIANT "GNU")
set(CMAKE_CXX_SIMULATE_VERSION "")




set(CMAKE_AR "/usr/bin/ar")
set(CMAKE_CXX_COMPILER_AR "/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/bin/gcc-ar")
set(CMAKE_RANLIB "/usr/bin/ranlib")
set(CMAKE_CXX_COMPILER_RANLIB "/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/bin/gcc-ranlib")
set(CMAKE_LINKER "/apps/anvil/external/apps/xalt2/xalt/xalt/bin/ld")
set(CMAKE_MT "")
set(CMAKE_COMPILER_IS_GNUCXX 1)
set(CMAKE_CXX_COMPILER_LOADED 1)
set(CMAKE_CXX_COMPILER_WORKS TRUE)
set(CMAKE_CXX_ABI_COMPILED TRUE)

set(CMAKE_CXX_COMPILER_ENV_VAR "CXX")

set(CMAKE_CXX_COMPILER_ID_RUN 1)
set(CMAKE_CXX_SOURCE_FILE_EXTENSIONS C;M;c++;cc;cpp;cxx;m;mm;mpp;CPP;ixx;cppm)
set(CMAKE_CXX_IGNORE_EXTENSIONS inl;h;hpp;HPP;H;o;O;obj;OBJ;def;DEF;rc;RC)

foreach (lang C OBJC OBJCXX)
  if (CMAKE_${lang}_COMPILER_ID_RUN)
    foreach(extension IN LISTS CMAKE_${lang}_SOURCE_FILE_EXTENSIONS)
      list(REMOVE_ITEM CMAKE_CXX_SOURCE_FILE_EXTENSIONS ${extension})
    endforeach()
  endif()
endforeach()

set(CMAKE_CXX_LINKER_PREFERENCE 30)
set(CMAKE_CXX_LINKER_PREFERENCE_PROPAGATES 1)

# Save compiler ABI information.
set(CMAKE_CXX_SIZEOF_DATA_PTR "8")
set(CMAKE_CXX_COMPILER_ABI "ELF")
set(CMAKE_CXX_BYTE_ORDER "LITTLE_ENDIAN")
set(CMAKE_CXX_LIBRARY_ARCHITECTURE "")

if(CMAKE_CXX_SIZEOF_DATA_PTR)
  set(CMAKE_SIZEOF_VOID_P "${CMAKE_CXX_SIZEOF_DATA_PTR}")
endif()

if(CMAKE_CXX_COMPILER_ABI)
  set(CMAKE_INTERNAL_PLATFORM_ABI "${CMAKE_CXX_COMPILER_ABI}")
endif()

if(CMAKE_CXX_LIBRARY_ARCHITECTURE)
  set(CMAKE_LIBRARY_ARCHITECTURE "")
endif()

set(CMAKE_CXX_CL_SHOWINCLUDES_PREFIX "")
if(CMAKE_CXX_CL_SHOWINCLUDES_PREFIX)
  set(CMAKE_CL_SHOWINCLUDES_PREFIX "${CMAKE_CXX_CL_SHOWINCLUDES_PREFIX}")
endif()





set(CMAKE_CXX_IMPLICIT_INCLUDE_DIRECTORIES "/apps/spack/anvil/apps/openmpi/4.0.6-gcc-11.2.0-3navcwb/include;/apps/spack/anvil/apps/numactl/2.0.14-gcc-11.2.0-wrjotmv/include;/apps/spack/anvil/apps/libfabric/1.12.0-gcc-8.4.1-xj6lmd4/include;/apps/spack/anvil/apps/zlib/1.2.11-gcc-11.2.0-g2guo73/include;/apps/spack/anvil/apps/mpc/1.1.0-gcc-8.4.1-dh4xij5/include;/apps/spack/anvil/apps/mpfr/4.0.2-gcc-11.2.0-ke4ellj/include;/apps/spack/anvil/apps/gmp/6.2.1-gcc-11.2.0-trpptvt/include;/home/x-zjian1/hdf5/hdf5-1.14.6/install/include;/home/x-zjian1/jpeg-9f/install/include;/home/x-zjian1/netcdf-c/netcdf-c-4.9.3/install/include;/home/x-zjian1/GKlib/install/include;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/include/c++/11.2.0;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/include/c++/11.2.0/x86_64-pc-linux-gnu;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/include/c++/11.2.0/backward;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib/gcc/x86_64-pc-linux-gnu/11.2.0/include;/usr/local/include;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/include;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib/gcc/x86_64-pc-linux-gnu/11.2.0/include-fixed;/usr/include")
set(CMAKE_CXX_IMPLICIT_LINK_LIBRARIES "mpi_cxx;mpi;stdc++;m;gcc_s;gcc;pthread;c;gcc_s;gcc")
set(CMAKE_CXX_IMPLICIT_LINK_DIRECTORIES "/apps/spack/anvil/apps/openmpi/4.0.6-gcc-11.2.0-3navcwb/lib;/apps/spack/anvil/apps/hwloc/2.5.0-gcc-11.2.0-zzxt6un/lib;/apps/spack/anvil/apps/libevent/2.1.12-gcc-11.2.0-loxxg45/lib;/apps/spack/anvil/apps/zlib/1.2.11-gcc-11.2.0-g2guo73/lib;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib64;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib/gcc/x86_64-pc-linux-gnu/11.2.0;/lib64;/usr/lib64;/apps/spack/anvil/apps/numactl/2.0.14-gcc-11.2.0-wrjotmv/lib;/apps/spack/anvil/apps/libfabric/1.12.0-gcc-8.4.1-xj6lmd4/lib;/apps/spack/anvil/apps/gcc/11.2.0-gcc-8.4.1-qjtdkvs/lib;/apps/spack/anvil/apps/mpc/1.1.0-gcc-8.4.1-dh4xij5/lib;/apps/spack/anvil/apps/mpfr/4.0.2-gcc-11.2.0-ke4ellj/lib;/apps/spack/anvil/apps/gmp/6.2.1-gcc-11.2.0-trpptvt/lib;/home/x-zjian1/hdf5/hdf5-1.14.6/install/lib;/home/x-zjian1/jpeg-9f/install/lib;/home/x-zjian1/netcdf-c/netcdf-c-4.9.3/install/lib;/home/x-zjian1/GKlib/install/lib")
set(CMAKE_CXX_IMPLICIT_LINK_FRAMEWORK_DIRECTORIES "")
