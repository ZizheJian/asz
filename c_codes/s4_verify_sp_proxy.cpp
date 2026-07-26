// 给定stencil pattern和eb，根据BR和PSNR，选择最好的t和遍历顺序
// 用于比较不同stencil pattern的区别

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
    string repository_path="/home/x-zjian1/ASTZ_tests";
    // string data_name="Pf01";
    string data_name="CLDICE";
    vector<string> predictor_name_vec={"1d4r0","1d4r1","1d4r2"};
    // vector<string> predictor_name_vec={"2d4r01","2d4r02","2d4r12"};
    // vector<string> predictor_name_vec={"1d6r0","1d6r1","1d6r2"};
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

    printf("计算平均BR和PSNR。。。。。。\n");
    // 访问方式是avg_br[rel_eb]，avg_psnr[rel_eb]
    unordered_map<double,double> avg_br,avg_psnr;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
        for (auto &predictor_name:predictor_name_vec)
        {
            if (csv_path.find(predictor_name)==string::npos)
                continue;
            avg_br[rel_eb]+=data[csv_path][rel_eb][t_vec]["BR"];
            avg_psnr[rel_eb]+=data[csv_path][rel_eb][t_vec]["PSNR"];
        }
    for (auto &rel_eb:rel_eb_vec)
    {
        avg_br[rel_eb]/=(t_vec_vec.size()*traversal_order_vec.size()*predictor_name_vec.size());
        avg_psnr[rel_eb]/=(t_vec_vec.size()*traversal_order_vec.size()*predictor_name_vec.size());
    }

    printf("计算平均斜率。。。。。。\n");
    // 访问方式是slope[rel_eb]
    unordered_map<double,double> slope;
    for (auto &rel_eb:rel_eb_vec)
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
        double delta_br=avg_br[right_rel_eb]-avg_br[left_rel_eb];
        double delta_psnr=avg_psnr[right_rel_eb]-avg_psnr[left_rel_eb];
        slope[rel_eb]=delta_psnr/delta_br;
        printf("rel_eb=%f, slope=%f\n",rel_eb,slope[rel_eb]);
    }

    printf("计算每个点相对于平均斜率的距离。。。。。。\n");
    // 访问方式是score[csv_path][rel_eb][t_vec]
    unordered_map<string,unordered_map<double,unordered_map<vector<double>,double>>> score;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
        for (auto &predictor_name:predictor_name_vec)
        {
            if (csv_path.find(predictor_name)==string::npos)
                continue;
            score[csv_path][rel_eb][t_vec]=-slope[rel_eb]*data[csv_path][rel_eb][t_vec]["BR"];
            score[csv_path][rel_eb][t_vec]+=data[csv_path][rel_eb][t_vec]["PSNR"];
            score[csv_path][rel_eb][t_vec]/=sqrt(slope[rel_eb]*slope[rel_eb]+1);
        }

    printf("寻找每个predictor_name和rel_eb下的最好情况。。。。。。\n");
    // 访问方式是xxx[predictor_name][rel_eb]
    unordered_map<string,unordered_map<double,string>> best_traversal_order;
    unordered_map<string,unordered_map<double,vector<double>>> best_t_vec;
    unordered_map<string,unordered_map<double,double>> best_score;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
    {
        string predictor_name,traversal_order;
        for (auto &temp_predictor_name:predictor_name_vec)
            if (csv_path.find(temp_predictor_name)!=string::npos)
                predictor_name=temp_predictor_name;
        for (auto &temp_traversal_order:traversal_order_vec)
            if (csv_path.find(temp_traversal_order)!=string::npos)
                traversal_order=temp_traversal_order;
        if (best_score[predictor_name][rel_eb]<score[csv_path][rel_eb][t_vec])
        {
            best_score[predictor_name][rel_eb]=score[csv_path][rel_eb][t_vec];
            best_traversal_order[predictor_name][rel_eb]=traversal_order;
            best_t_vec[predictor_name][rel_eb]=t_vec;
        }
    }
    for (auto &predictor_name:predictor_name_vec)
    for (auto &rel_eb:rel_eb_vec)
    {
        printf("predictor_name=%s, rel_eb=%f, best_traversal_order=%s, best_t_vec={",predictor_name.c_str(),rel_eb,best_traversal_order[predictor_name][rel_eb].c_str());
        for (auto &x:best_t_vec[predictor_name][rel_eb])
            printf("%f,",x);
        printf("}\n");
    }

    printf("输出结果。。。。。。\n");
    string score_path=repository_path+"/csv/"+data_name+"_each_sp_best_score.csv";
    string mse_path=repository_path+"/csv/"+data_name+"_each_sp_best_mse.csv";
    string mae_path=repository_path+"/csv/"+data_name+"_each_sp_best_mae.csv";
    create_csv_header(score_path,"rel_eb");
    create_csv_header(mse_path,"rel_eb");
    create_csv_header(mae_path,"rel_eb");
    for (auto &predictor_name:predictor_name_vec)
    for (auto &rel_eb:rel_eb_vec)
    {
        string csv_path;
        for (auto &temp_csv_path:csv_path_vec)
            if (temp_csv_path.find(predictor_name)!=string::npos)
            if (temp_csv_path.find(best_traversal_order[predictor_name][rel_eb])!=string::npos)
                csv_path=temp_csv_path;
        write_csv_item(score_path,rel_eb,predictor_name,score[csv_path][rel_eb][best_t_vec[predictor_name][rel_eb]]);
        write_csv_item(mse_path,rel_eb,predictor_name,data[csv_path][rel_eb][best_t_vec[predictor_name][rel_eb]]["MSE"]);
        write_csv_item(mae_path,rel_eb,predictor_name,data[csv_path][rel_eb][best_t_vec[predictor_name][rel_eb]]["MAE"]);
    }
}