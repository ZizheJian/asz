// 先固定stencil pattern和traversal order，遍历t，计算BR和PSNR
// 再固定stencil pattern，遍历traversal order，计算BR和PSNR
// 再用相同的斜率比较不同stencil pattern并打分

#include <string>
#include <vector>
#include <functional>
#include <cmath>
#include "../third_party/csv_tools/c_codes/csv.hpp"

using namespace std;

inline void hash_combine(uint64_t &v1,uint64_t v2) //v2应该是std::hash产生的uint64_t
{
    v1^=v2+0x9e3779b97f4a7c15ULL+(v1<<6)+(v1>>2);
}

namespace std
{
    template<>
    struct hash<vector<double>>
    {
        size_t operator()(const vector<double> &v) const
        {
            uint64_t h=0;
            for (auto &x:v)
                hash_combine(h,hash<double>{}(x));
            return h;
        }
    };
}

int main()
{
    string repository_path="/home/x-zjian1/asz";
    string data_name="Pf01";
    // string data_name="CLDICE";
    vector<string> predictor_name_vec={"1d4r0","1d4r1","1d4r2"};
    vector<string> traversal_order_vec={"xx0","xx1","xx2"};
    vector<string> csv_path_vec;
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
        csv_path_vec.push_back(repository_path+"/csv/"+data_name+"_"+predictor_name+"_"+traversal_order+".csv");
    vector<double> rel_eb_vec;
    vector<vector<double>> t_vec_vec;
    {
        vector<vector<string>> data=read_csv(csv_path_vec[0]);
        for (int row_id=1;(uint64_t)row_id<data.size();row_id++)
        {
            rel_eb_vec.push_back(stod(data[row_id][0]));
            if ((predictor_name_vec[0].compare(0,4,"1d4r")==0) || (predictor_name_vec[0].compare(0,4,"2d4r")==0))
                t_vec_vec.push_back({stod(data[row_id][1])});
            else
                t_vec_vec.push_back({stod(data[row_id][1]),stod(data[row_id][2])});
        }
        sort(rel_eb_vec.begin(),rel_eb_vec.end(),greater<double>());
        rel_eb_vec.erase(unique(rel_eb_vec.begin(),rel_eb_vec.end()),rel_eb_vec.end());
        sort(t_vec_vec.begin(),t_vec_vec.end(),greater<vector<double>>());
        t_vec_vec.erase(unique(t_vec_vec.begin(),t_vec_vec.end()),t_vec_vec.end());
    }

    printf("读取原始数据。。。。。。\n");
    // 访问方式是data[csv_path][rel_eb][t_vec][value_name]
    unordered_map<string,unordered_map<double,unordered_map<vector<double>,unordered_map<string,double>>>> data;
    for (auto &csv_path:csv_path_vec)
    {
        vector<vector<string>> temp_data=read_csv(csv_path);
        for (int row_id=1;(uint64_t)row_id<temp_data.size();row_id++)
        for (int column_id=t_vec_vec[0].size()+1;(uint64_t)column_id<temp_data[row_id].size();column_id++)
        {
            double rel_eb=stod(temp_data[row_id][0]);
            vector<double> t_vec;
            for (int i=0;i<(int)t_vec_vec[0].size();i++)
                t_vec.push_back(stod(temp_data[row_id][i+1]));
            string value_name=temp_data[0][column_id];
            double value=stod(temp_data[row_id][column_id]);
            data[csv_path][rel_eb][t_vec][value_name]=value;
        }
    }

    printf("第一轮 对每个stencil pattern和traversal order计算平均BR和PSNR。。。。。。\n");
    // 访问方式是xxx[rel_eb][predictor_name][traversal_order]
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> avg_br_1,avg_psnr_1;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
        for (auto &predictor_name:predictor_name_vec)
        for (auto &traversal_order:traversal_order_vec)
        {
            if ((csv_path.find(predictor_name)==string::npos) || (csv_path.find(traversal_order)==string::npos))
                continue;
            avg_br_1[rel_eb][predictor_name][traversal_order]+=data[csv_path][rel_eb][t_vec]["BR"];
            avg_psnr_1[rel_eb][predictor_name][traversal_order]+=data[csv_path][rel_eb][t_vec]["PSNR"];
        }
    for (auto &rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        avg_br_1[rel_eb][predictor_name][traversal_order]/=(t_vec_vec.size());
        avg_psnr_1[rel_eb][predictor_name][traversal_order]/=(t_vec_vec.size());
    }

    printf("第一轮 计算平均斜率。。。。。。\n");
    // 访问方式是slope_1[rel_eb][predictor_name][traversal_order]
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> slope_1;
    for (auto &rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        double left_rel_eb,right_rel_eb;
        if (rel_eb==rel_eb_vec[0])
            left_rel_eb=rel_eb;
        else
            left_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)-1);
        if (rel_eb==rel_eb_vec.back())
            right_rel_eb=rel_eb;
        else
            right_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)+1);
        double delta_br=avg_br_1[right_rel_eb][predictor_name][traversal_order]-avg_br_1[left_rel_eb][predictor_name][traversal_order];
        double delta_psnr=avg_psnr_1[right_rel_eb][predictor_name][traversal_order]-avg_psnr_1[left_rel_eb][predictor_name][traversal_order];
        slope_1[rel_eb][predictor_name][traversal_order]=delta_psnr/delta_br;
    }

    printf("第一轮 计算每个点的分数。。。。。。\n");
    // 访问方式是score_1[rel_eb][predictor_name][traversal_order][t_vec]
    unordered_map<double,unordered_map<string,unordered_map<string,unordered_map<vector<double>,double>>>> score_1;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
        for (auto &predictor_name:predictor_name_vec)
        for (auto &traversal_order:traversal_order_vec)    
        {
            if ((csv_path.find(predictor_name)==string::npos) || (csv_path.find(traversal_order)==string::npos))
                continue;
            double temp_slope=slope_1[rel_eb][predictor_name][traversal_order];
            double &temp_score=score_1[rel_eb][predictor_name][traversal_order][t_vec];
            double temp_br=data[csv_path][rel_eb][t_vec]["BR"];
            double temp_psnr=data[csv_path][rel_eb][t_vec]["PSNR"];
            temp_score=(-temp_slope*temp_br+temp_psnr)/sqrt(temp_slope*temp_slope+1);
        }

    printf("第一轮 寻找每个rel_eb、traversal order、stencil pattern下的最好情况。。。。。。\n");
    // 访问方式是xxx[rel_eb][predictor_name][traversal_order]
    unordered_map<double,unordered_map<string,unordered_map<string,vector<double>>>> best_t_vec;
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> best_score_1;
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> best_br_1;
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> best_psnr_1;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
        best_score_1[rel_eb][predictor_name][traversal_order]=-1e10;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
        for (auto &predictor_name:predictor_name_vec)
        for (auto &traversal_order:traversal_order_vec)
        {
            if ((csv_path.find(predictor_name)==string::npos) || (csv_path.find(traversal_order)==string::npos))
                continue;
            if (best_score_1[rel_eb][predictor_name][traversal_order]<score_1[rel_eb][predictor_name][traversal_order][t_vec])
            {
                best_score_1[rel_eb][predictor_name][traversal_order]=score_1[rel_eb][predictor_name][traversal_order][t_vec];
                best_t_vec[rel_eb][predictor_name][traversal_order]=t_vec;
                best_br_1[rel_eb][predictor_name][traversal_order]=data[csv_path][rel_eb][t_vec]["BR"];
                best_psnr_1[rel_eb][predictor_name][traversal_order]=data[csv_path][rel_eb][t_vec]["PSNR"];
            }
        }
    
    printf("第二轮 对每个stencil pattern计算平均BR和PSNR。。。。。。\n");
    // 访问方式是xxx[rel_eb][predictor_name]
    unordered_map<double,unordered_map<string,double>> avg_br_2,avg_psnr_2;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        avg_br_2[rel_eb][predictor_name]+=best_br_1[rel_eb][predictor_name][traversal_order];
        avg_psnr_2[rel_eb][predictor_name]+=best_psnr_1[rel_eb][predictor_name][traversal_order];
    }
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    {
        avg_br_2[rel_eb][predictor_name]/=(traversal_order_vec.size());
        avg_psnr_2[rel_eb][predictor_name]/=(traversal_order_vec.size());
    }

    printf("第二轮 计算平均斜率。。。。。。\n");
    // 访问方式是slope_2[rel_eb][predictor_name]
    unordered_map<double,unordered_map<string,double>> slope_2;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    {
        double left_rel_eb,right_rel_eb;
        if (rel_eb==rel_eb_vec[0])
            left_rel_eb=rel_eb;
        else
            left_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)-1);
        if (rel_eb==rel_eb_vec.back())
            right_rel_eb=rel_eb;
        else
            right_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)+1);
        double delta_br=avg_br_2[right_rel_eb][predictor_name]-avg_br_2[left_rel_eb][predictor_name];
        double delta_psnr=avg_psnr_2[right_rel_eb][predictor_name]-avg_psnr_2[left_rel_eb][predictor_name];
        slope_2[rel_eb][predictor_name]=delta_psnr/delta_br;
    }

    printf("第二轮 计算每个点的分数。。。。。。\n");
    // 访问方式是score_2[rel_eb][predictor_name][traversal_order]
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> score_2;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        double temp_slope=slope_2[rel_eb][predictor_name];
        double &temp_score=score_2[rel_eb][predictor_name][traversal_order];
        double temp_br=best_br_1[rel_eb][predictor_name][traversal_order];
        double temp_psnr=best_psnr_1[rel_eb][predictor_name][traversal_order];
        temp_score=(-temp_slope*temp_br+temp_psnr)/sqrt(temp_slope*temp_slope+1);
    }

    printf("第二轮 寻找每个rel_eb、stencil pattern下的最好情况。。。。。。\n");
    // 访问方式是xxx[rel_eb][predictor_name]
    unordered_map<double,unordered_map<string,string>> best_traversal_order;
    unordered_map<double,unordered_map<string,double>> best_score_2;
    unordered_map<double,unordered_map<string,double>> best_br_2;
    unordered_map<double,unordered_map<string,double>> best_psnr_2;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
        best_score_2[rel_eb][predictor_name]=-1e10;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        if (best_score_2[rel_eb][predictor_name]<score_2[rel_eb][predictor_name][traversal_order])
        {
            best_score_2[rel_eb][predictor_name]=score_2[rel_eb][predictor_name][traversal_order];
            best_traversal_order[rel_eb][predictor_name]=traversal_order;
            best_br_2[rel_eb][predictor_name]=best_br_1[rel_eb][predictor_name][traversal_order];
            best_psnr_2[rel_eb][predictor_name]=best_psnr_1[rel_eb][predictor_name][traversal_order];
        }
    }

    printf("第三轮 计算平均BR和PSNR。。。。。。\n");
    // 访问方式是xxx[rel_eb]
    unordered_map<double,double> avg_br_3,avg_psnr_3;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    {
        avg_br_3[rel_eb]+=best_br_2[rel_eb][predictor_name];
        avg_psnr_3[rel_eb]+=best_psnr_2[rel_eb][predictor_name];
    }
    for (auto rel_eb:rel_eb_vec)
    {
        avg_br_3[rel_eb]/=(predictor_name_vec.size());
        avg_psnr_3[rel_eb]/=(predictor_name_vec.size());
    }

    printf("第三轮 计算平均斜率。。。。。。\n");
    // 访问方式是slope_3[rel_eb]
    unordered_map<double,double> slope_3;
    for (auto rel_eb:rel_eb_vec)
    {
        double left_rel_eb,right_rel_eb;
        if (rel_eb==rel_eb_vec[0])
            left_rel_eb=rel_eb;
        else
            left_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)-1);
        if (rel_eb==rel_eb_vec.back())
            right_rel_eb=rel_eb;
        else
            right_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)+1);
        double delta_br=avg_br_3[right_rel_eb]-avg_br_3[left_rel_eb];
        double delta_psnr=avg_psnr_3[right_rel_eb]-avg_psnr_3[left_rel_eb];
        slope_3[rel_eb]=delta_psnr/delta_br;
    }

    printf("第三轮 计算每个点的分数。。。。。。\n");
    // 访问方式是score_3[rel_eb][predictor_name]
    unordered_map<double,unordered_map<string,double>> score_3;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    {
        double temp_slope=slope_3[rel_eb];
        double &temp_score=score_3[rel_eb][predictor_name];
        double temp_br=best_br_2[rel_eb][predictor_name];
        double temp_psnr=best_psnr_2[rel_eb][predictor_name];
        temp_score=(-temp_slope*temp_br+temp_psnr)/sqrt(temp_slope*temp_slope+1);
    }

    printf("输出结果。。。。。。\n");
    string output_csv_path_score=repository_path+"/csv/"+data_name+"_each_sp_best_score.csv";
    string output_csv_path_rmse=repository_path+"/csv/"+data_name+"_each_sp_best_rmse.csv";
    string output_csv_path_mae=repository_path+"/csv/"+data_name+"_each_sp_best_mae.csv";
    create_csv_header(output_csv_path_score,"rel_eb");
    create_csv_header(output_csv_path_rmse,"rel_eb");
    create_csv_header(output_csv_path_mae,"rel_eb");
    for (auto &rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    {
        write_csv_item(output_csv_path_score,rel_eb,predictor_name,score_3[rel_eb][predictor_name]);
        string traversal_order=best_traversal_order[rel_eb][predictor_name];
        vector<double> t_vec=best_t_vec[rel_eb][predictor_name][traversal_order];
        for (auto csv_path:csv_path_vec)
        {
            if ((csv_path.find(predictor_name)==string::npos) || (csv_path.find(traversal_order)==string::npos))
                continue;
            write_csv_item(output_csv_path_rmse,rel_eb,predictor_name,data[csv_path][rel_eb][t_vec]["RMSE"]);
            write_csv_item(output_csv_path_mae,rel_eb,predictor_name,data[csv_path][rel_eb][t_vec]["MAE"]);
        }
    }
}