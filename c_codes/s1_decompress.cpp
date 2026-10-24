#include "asz_core/asz_param.hpp"

using namespace std;

int main(int argc,char* argv[]) try
{
    if(argc==2&&string(argv[1])=="--help")
    {
        printf("usage: s1_decompress -i INPUT -z COMPRESSED -o RECONSTRUCTED -3 DIM0 DIM1 DIM2 -M REL REL_EB [options]\n");
        return 0;
    }
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
        else if (arg=="--max-layer-num")
        {
            param.max_layer_num=stoull(argv[++i]);
            continue;
        }
        else if (arg=="--full-predictor-search-layer-num")
        {
            param.full_predictor_search_layer_num=stoull(argv[++i]);
            continue;
        }
        else if (arg=="--t-precision")
        {
            param.t_precision=stoi(argv[++i]);
            continue;
        }
        else if (arg=="--t-policy")
        {
            param.set_t_policy(argv[++i]);
            continue;
        }
        else
            throw invalid_argument("unknown argument: "+arg);
    }

    if(param.compressed_data_path.empty()||param.decompressed_data_path.empty())
        throw invalid_argument("compressed-input and decompressed-output paths are required");
    if(param.data_shape.size()!=3||any_of(param.data_shape.begin(),param.data_shape.end(),[](uint64_t size){return size<7;}))
        throw invalid_argument("all three dimensions must be at least 7");
    if(!(param.rel_eb>0&&isfinite(param.rel_eb)))
        throw invalid_argument("relative error bound must be positive and finite");
    uint64_t data_size=1;
    for(uint64_t size:param.data_shape)
    {
        if(data_size>numeric_limits<uint64_t>::max()/size)
            throw invalid_argument("data dimensions overflow the element count");
        data_size*=size;
    }
    if(data_size>numeric_limits<size_t>::max()/sizeof(float))
        throw invalid_argument("data dimensions exceed the addressable output size");
    if (!(param.pivot_eb_ratio>0&&param.pivot_eb_ratio<=1))
        throw invalid_argument("pivot_eb_ratio must be in (0,1]");
    if (!(param.eb_ratio>0&&param.eb_ratio<=1))
        throw invalid_argument("eb_ratio must be in (0,1]");
    if (!(param.slope_ratio>0&&param.slope_ratio<=1))
        throw invalid_argument("slope_ratio must be in (0,1]");
    if (param.block_pivot_ratio==0)
        throw invalid_argument("block_pivot_ratio must be positive");
    if (param.max_layer_num==0||param.max_layer_num>63)
        throw invalid_argument("max_layer_num must be in [1,63]");
    if (param.full_predictor_search_layer_num==0||param.full_predictor_search_layer_num>63)
        throw invalid_argument("full_predictor_search_layer_num must be in [1,63]");
    if (param.t_precision<16||param.t_precision%16!=0)
        throw invalid_argument("t_precision must be a positive multiple of 16");

    ifstream compressed_data_file(param.compressed_data_path,ios::binary);
    if (!compressed_data_file)
        throw runtime_error("cannot open compressed input: "+param.compressed_data_path);
    uint64_t compressed_data_file_size=compressed_data_file.seekg(0,ios::end).tellg();
    if(compressed_data_file_size==0)
        throw runtime_error("compressed input is empty: "+param.compressed_data_path);
    compressed_data_file.seekg(0,ios::beg);
    param.zstd_bs_vec.resize(compressed_data_file_size);
    compressed_data_file.read(reinterpret_cast<char*>(param.zstd_bs_vec.data()),compressed_data_file_size);
    if(!compressed_data_file)
        throw runtime_error("cannot read complete compressed input: "+param.compressed_data_path);
    compressed_data_file.close();

    param.generate_config("decompress");
    param.decompress();
    ofstream decompressed_data_file(param.decompressed_data_path,ios::binary);
    if (!decompressed_data_file)
        throw runtime_error("cannot open decompressed output: "+param.decompressed_data_path);
    decompressed_data_file.write(reinterpret_cast<const char*>(param.compressed_data.data()),param.compressed_data.size()*sizeof(float));
    if (!decompressed_data_file)
        throw runtime_error("cannot write decompressed output: "+param.decompressed_data_path);
    decompressed_data_file.close();
}
catch(const exception &error)
{
    fprintf(stderr,"error: %s\n",error.what());
    return 1;
}
