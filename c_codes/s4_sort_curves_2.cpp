// 从不同的文件中读取br-psnr和h1-psnr，排序并检验

#include <string>
#include <vector>
#include <map>
#include <unordered_set>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <unordered_map>

#include "csv_tools/csv.hpp"

using namespace std;

inline void hash_combine(uint64_t &v1,uint64_t v2) //输入需要std::hash产生的uint64_t
{
    v1^=v2+0x9e3779b97f4a7c15ULL+(v1<<6)+(v1>>2);
}

namespace std
{
    template<>
    struct hash<tuple<double,double>>
    {
        size_t operator()(const tuple<double,double> &t) const
        {
            auto[a,b]=t;
            uint64_t h=0;
            hash_combine(h,hash<double>{}(a));
            hash_combine(h,hash<double>{}(b));
            return h;
        }
    };
}

void compare_curves(vector<vector<int>> &win_table,unordered_map<tuple<double,double>,double> &br,unordered_map<tuple<double,double>,double> &psnr,
    vector<double> &rel_eb_vec,vector<double> &t2_vec)
{
    for (auto t2_base_it=t2_vec.begin();t2_base_it!=t2_vec.end();t2_base_it++)
        for (auto t2_cmp_it=t2_vec.begin();t2_cmp_it!=t2_vec.end();t2_cmp_it++)
        {
            double t2_base=*t2_base_it;
            double t2_cmp=*t2_cmp_it;
            if (t2_base==t2_cmp)
                continue;
            double dist=0;
            for (auto rel_eb_it=rel_eb_vec.begin();rel_eb_it!=rel_eb_vec.end();rel_eb_it++)
            {
                if (rel_eb_it==rel_eb_vec.begin() || rel_eb_it==rel_eb_vec.end()-1)
                    continue;
                double br_base_prev=br[{*(rel_eb_it-1),t2_base}];
                double psnr_base_prev=psnr[{*(rel_eb_it-1),t2_base}];
                double br_base_next=br[{*(rel_eb_it+1),t2_base}];
                double psnr_base_next=psnr[{*(rel_eb_it+1),t2_base}];
                if ((br_base_prev<=br_base_next) || (psnr_base_prev<=psnr_base_next))
                    continue;
                double k1=(psnr_base_next-psnr_base_prev)/(br_base_next-br_base_prev);
                double br_base=br[{*rel_eb_it,t2_base}];
                double psnr_base=psnr[{*rel_eb_it,t2_base}];
                double br_cmp=br[{*rel_eb_it,t2_cmp}];
                double psnr_cmp=psnr[{*rel_eb_it,t2_cmp}];
                dist+=(-k1*(br_cmp-br_base)+(psnr_cmp-psnr_base))/sqrt(k1*k1+1);
            }
            if (dist>0)
                win_table[t2_cmp_it-t2_vec.begin()][t2_base_it-t2_vec.begin()]=1;
             else if (dist<0)
                win_table[t2_cmp_it-t2_vec.begin()][t2_base_it-t2_vec.begin()]=-1;
        }
    vector<tuple<double,double>> rank_t2;
    for (auto t2_base_it=t2_vec.begin();t2_base_it!=t2_vec.end();t2_base_it++)
    {
        int win_count=0;
        int lose_count=0;
        for (auto t2_cmp_it=t2_vec.begin();t2_cmp_it!=t2_vec.end();t2_cmp_it++)
        {
            if (*t2_base_it==*t2_cmp_it)
                continue;
            if (win_table[t2_base_it-t2_vec.begin()][t2_cmp_it-t2_vec.begin()]==1)
                win_count++;
            else if (win_table[t2_base_it-t2_vec.begin()][t2_cmp_it-t2_vec.begin()]==-1)
                lose_count++;
        }
        rank_t2.emplace_back(*t2_base_it,(double)(win_count)/(win_count+lose_count));
    }
    sort(rank_t2.begin(),rank_t2.end(),[](const tuple<double,double> &a,const tuple<double,double> &b){return get<1>(a)>get<1>(b);});
    for (auto &t:rank_t2)
        printf("%f ",get<0>(t));
    printf("\n");
}

void compare_win_table(vector<vector<int>> &win_table_truth,vector<vector<int>> &win_table_h,string h_name)
{
    int tau=0;
    int n=win_table_truth.size();
    for (int i=0;i<n;i++)
        for (int j=0;j<n;j++)
        {
            if (i==j)
                continue;
            if (win_table_truth[i][j]==win_table_h[i][j])
                tau++;
        }
    printf("%s: tau= %f\n",h_name.c_str(),(double)tau/(n*(n-1)));
}

int main()
{
    string br_csv_path="/home/zjian/ASTZ_tests/csv/results_cubic_prediction_ISABEL_Pf01.csv";
    string h1_csv_path="/home/zjian/ASTZ_tests/csv/results_cubic_prediction_ISABEL_Pf01_2.csv";
    vector<double> rel_eb_vec;
    {
        vector<double> temp_vec1,temp_vec2;
        read_all_values_in_column(br_csv_path,"rel_eb",temp_vec1);
        read_all_values_in_column(h1_csv_path,"rel_eb",temp_vec2);
        for (auto &val1:temp_vec1)
            for (auto &val2:temp_vec2)
                if (val1==val2)
                    rel_eb_vec.push_back(val1);
    }
    vector<double> t2_vec;
    {
        vector<double> temp_vec1,temp_vec2;
        read_all_values_in_column(br_csv_path,"t2",temp_vec1);
        read_all_values_in_column(h1_csv_path,"t2",temp_vec2);
        for (auto &val1:temp_vec1)
            for (auto &val2:temp_vec2)
                if (val1==val2)
                    t2_vec.push_back(val1);
    }
    unordered_map<tuple<double,double>,double> br,br_psnr,h1,h1_psnr;
    for (auto &rel_eb:rel_eb_vec)
        for (auto &t2:t2_vec)
        {
            br[{rel_eb,t2}]=read_value(br_csv_path,rel_eb,t2,"BR");
            br_psnr[{rel_eb,t2}]=read_value(br_csv_path,rel_eb,t2,"PSNR");
            h1[{rel_eb,t2}]=read_value(h1_csv_path,rel_eb,t2,"H1");
            h1_psnr[{rel_eb,t2}]=read_value(h1_csv_path,rel_eb,t2,"PSNR");
        }

    vector<vector<int>> win_table_truth(t2_vec.size(),vector<int>(t2_vec.size(),0));
    vector<vector<int>> win_table_h1(t2_vec.size(),vector<int>(t2_vec.size(),0));
    compare_curves(win_table_truth,br,br_psnr,rel_eb_vec,t2_vec);
    compare_curves(win_table_h1,h1,h1_psnr,rel_eb_vec,t2_vec);
    compare_win_table(win_table_truth,win_table_h1,"H1");
}