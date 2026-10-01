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
        else if (arg=="--predictor-family")
        {
            string family=argv[++i];
            if (family=="cubic")
                param.force_quintic=false;
            else if (family=="quintic")
                param.force_quintic=true;
            else
                throw invalid_argument("predictor_family must be cubic or quintic");
            continue;
        }
        else if (arg=="--pivot-eb-ratio")
        {
            param.pivot_eb_ratio=stof(argv[++i]);
            continue;
        }
        else if (arg=="--eb-ratio")
        {
            param.eb_ratio=stof(argv[++i]);
            continue;
        }
        else if (arg=="--slope-ratio")
        {
            param.slope_ratio=stof(argv[++i]);
            continue;
        }
        else if (arg=="--block-pivot-ratio")
        {
            param.block_pivot_ratio=stoull(argv[++i]);
            continue;
        }
    }

    if (!(param.pivot_eb_ratio>0&&param.pivot_eb_ratio<=1))
        throw invalid_argument("pivot_eb_ratio must be in (0,1]");
    if (!(param.eb_ratio>0&&param.eb_ratio<=1))
        throw invalid_argument("eb_ratio must be in (0,1]");
    if (!(param.slope_ratio>0&&param.slope_ratio<=1))
        throw invalid_argument("slope_ratio must be in (0,1]");
    if (param.block_pivot_ratio==0)
        throw invalid_argument("block_pivot_ratio must be positive");

    ifstream compressed_data_file(param.compressed_data_path,ios::binary);
    if (!compressed_data_file)
        throw runtime_error("cannot open compressed input: "+param.compressed_data_path);
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
    ofstream decompressed_data_file(param.decompressed_data_path,ios::binary);
    if (!decompressed_data_file)
        throw runtime_error("cannot open decompressed output: "+param.decompressed_data_path);
    decompressed_data_file.write(reinterpret_cast<const char*>(param.compressed_data.data()),param.compressed_data.size()*sizeof(float));
    if (!decompressed_data_file)
        throw runtime_error("cannot write decompressed output: "+param.decompressed_data_path);
    decompressed_data_file.close();
}
