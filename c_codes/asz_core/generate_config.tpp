#pragma once

namespace asz
{
    void param_c::generate_config_enumerate()
    {
        //////// 用于搜索一个合适的config ////////
        if (!config_generated)
        {
            //////// 这里写初始配置 ////////
            // block_shape={48,48,48};
            block_shape={100,500,500};
            pivot_stride={4,4,4};
            pivot_eb_ratio=0.2;
            
            for (int dim=0;dim<3;dim++)
                block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
            for (int i=0;i<block_num[0]*block_num[1]*block_num[2];i++)
            {
                predictor_vec.push_back({"cubic1","cubic2","cubic3","cubic1","cubic2","cubic3"});
                eb_ratio_vec.push_back({1,1,1,1,1,1});
            }
            config_generated=true;
        }
        else
        {
            //////// 这里写搜索策略 ////////
        }
    }
}