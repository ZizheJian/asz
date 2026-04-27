#include "asz_core/asz_param.hpp"

using namespace std;

int main()
{
    srand(time(NULL));
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

    //////// 直接生成配置 ////////
    param.generate_config();
    printf("pivot_eb_ratio=%f\n",param.pivot_eb_ratio);
    printf("eb_ratio=%f\n",param.eb_ratio);
    for (auto predictor:param.predictor_vec[0])
        printf("\"%s\",",predictor.c_str());
    printf("\n");
    param.compress();
    exit(0);

    //////// 搜索配置 ////////
    float best_dist=0;
    for (int attempt=0;attempt<50;attempt++)
    {
        asz::param_c backup_param;
        backup_param.copy_from(param);
        param.generate_config_enumerate();
        float dist=param.compress();
        if (dist<best_dist)
            param.copy_from(backup_param);
        else
        {
            printf("Found better configuration\n");
            best_dist=dist;
        }
        printf("\n");
    }
    printf("pivot_eb_ratio=%f\n",param.pivot_eb_ratio);
    printf("eb_ratio=%f\n",param.eb_ratio);
    for (auto predictor:param.predictor_vec[0])
        printf("\"%s\",",predictor.c_str());
    printf("\n");
}