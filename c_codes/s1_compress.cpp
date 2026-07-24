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
            param.decompressed_data_path=param.compressed_data_path+".bin";
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

    param.data.resize(param.data_shape[0]*param.data_shape[1]*param.data_shape[2]);
    ifstream data_file(param.original_data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(param.data.data()),param.data.size()*sizeof(float));
    data_file.close();
    param.min_val=*min_element(param.data.begin(),param.data.end());
    param.max_val=*max_element(param.data.begin(),param.data.end());
    if (param.min_val==param.max_val)
        throw runtime_error("max_val==min_val");
    
    auto param_double=asz::param_c<double>();
    if (param.rel_eb<1e-5)
    {
        param_double.copy_from(param);
        param_double.abs_eb=param_double.rel_eb*(param_double.max_val-param_double.min_val);
        param_double.get_default_slope();
        printf("default_slope=%f\n",param_double.default_slope);
        param_double.generate_config("compress");
        param_double.print_config();
        param_double.compress();
        param.copy_from(param_double);
    }
    else
    {
        param.abs_eb=param.rel_eb*(param.max_val-param.min_val);
        param.get_default_slope();
        printf("default_slope=%f\n",param.default_slope);
        param.generate_config("compress");
        param.print_config();
        param.compress();
    }
    ofstream compressed_data_file(param.compressed_data_path,ios::binary);
    compressed_data_file.write(reinterpret_cast<const char*>(param.zstd_bs_vec.data()),param.zstd_bs_vec.size());
    compressed_data_file.close();
    exit(0);

    //////// 搜索配置 ////////
    // float best_dist=-1e8;
    // for (int attempt=0;attempt<100;attempt++)
    // {
    //     printf("Attempt %d\n",attempt);
    //     asz::param_c backup_param;
    //     backup_param.copy_from(param);
    //     param.generate_config_enumerate();
    //     float dist=param.compress();
    //     if (dist<best_dist)
    //         param.copy_from(backup_param);
    //     else
    //     {
    //         printf("\033[32mFound better configuration\n\033[0m");
    //         best_dist=dist;
    //     }
    //     printf("\n");
    // }
    // param.print_config();
}