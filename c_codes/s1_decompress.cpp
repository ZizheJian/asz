#include "asz_core/asz_param.hpp"

using namespace std;

int main(int argc,char* argv[])
{
    auto param=asz::param_c<float>();
    for (int i=1;i<argc;i++)
    {
        string arg=argv[i];
        if (arg=="-f")
            continue;
        else if (arg=="-i")
        {
            param.original_data_path=argv[++i];
            param.compressed_data_path=param.original_data_path+".asz";
            param.decompressed_data_path=param.original_data_path+".bin";
            continue;
        }
        else if (arg=="-z")
        {
            param.compressed_data_path=argv[++i];
            param.decompressed_data_path=param.compressed_data_path+".bin";
            continue;
        }
        else if (arg=="-o")
        {
            param.decompressed_data_path=argv[++i];
            continue;
        }
        else if (arg=="-3")
        {
            param.data_shape={stoul(argv[++i]),stoul(argv[++i]),stoul(argv[++i])};
            continue;
        }
        else if (arg=="-M")
        {
            i++;
            param.rel_eb=stof(argv[++i]);
            continue;
        }
    }

    ifstream compressed_data_file(param.compressed_data_path,ios::binary);
    uint64_t compressed_data_file_size=compressed_data_file.seekg(0,ios::end).tellg();
    compressed_data_file.seekg(0,ios::beg);
    param.zstd_bs_vec.resize(compressed_data_file_size);
    compressed_data_file.read(reinterpret_cast<char*>(param.zstd_bs_vec.data()),compressed_data_file_size);
    compressed_data_file.close();

    auto param_double=asz::param_c<double>();
    if (param.rel_eb<1e-5)
    {
        param_double.copy_from(param);
        param_double.generate_config("decompress");
        param_double.decompress();
        param.copy_from(param_double);
    }
    else
    {
        param.generate_config("decompress");
        param.decompress();
    }
}