#include "asz_core/asz_param.hpp"

using namespace std;

int main()
{
    auto param=asz::param_c();
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    param.original_data_path="/lcrc/project/SDR/zjian-in-SDR/Pf01.bin";
    param.data_shape={100,500,500};
    param.rel_eb=1e-5;

    param.data.resize(param.data_shape[0]*param.data_shape[1]*param.data_shape[2]);
    ifstream data_file(param.original_data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(param.data.data()),param.data.size()*sizeof(float));
    data_file.close();
    param.min_val=*min_element(param.data.begin(),param.data.end());
    param.max_val=*max_element(param.data.begin(),param.data.end());
    param.abs_eb=param.rel_eb*(param.max_val-param.min_val);

    //////// 获得基准斜率 ////////
    param.get_default_slope();
    printf("default_slope=%f\n",param.default_slope);

    while (true)
    {
        param.generate_config_enumerate();
        param.compress();
        exit(0);
    }
}