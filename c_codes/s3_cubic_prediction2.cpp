// 使用预测公式：
//      err=(0.25-t2)*data[-3]+(0.25+t2)*data[-1]-data[0]+(0.25+t2)*data[1]+(0.25-t2)*data[3]
// 分解为常数项（B）以及t2的一次方项（At2），统计出A和B的联合分布
// 随后代入不同的t2和rel_eb，计算出H1和PSNR

// 尝试是否可以采样
// stride=1时，tau=0.995238。stride=2,4,8时，tau没有减小
// stride=16时，tau=0.980952
// stride=32时，tau=0.976190
// stride=64时，tau=0.907143

// 尝试使用独立分布
// 无意义，因为AB_map.size()<<A_map.size()*B_map.size()

// 尝试截断A和B，排除A或B超出阈值的情况
// 阈值=1e-1*(max_val-min_val)时，tau=1.0
// 阈值=1e-2*(max_val-min_val)时，tau=0.995238
// 阈值=1e-3*(max_val-min_val)时，tau=0.995238
// 阈值=1e-4*(max_val-min_val)时，tau=0.990476
// 阈值=1e-5*(max_val-min_val)时，tau=0.990476
// 阈值=1e-6*(max_val-min_val)时，tau=0.342857
// 阈值可能和AB的分布有关，但统计整个AB非常耗时，所以只能靠经验设置
// 此外，阈值必须非常小才会明显地提速，但随后再小一点就会明显降低tau

// 尝试不均匀量化（暂时没试）

#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>

#include "huffman.hpp"
#include "get_H.hpp"
#include "csv_tools/csv.hpp"
#include "third_party/zstd/lib/zstd.h"

using namespace std;

int main()
{
    string data_path="/lcrc/project/SDR/zjian-in-SDR/Pf01.bin";
    vector<uint64_t> data_shape={100,500,500};
    vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,5.623e-5,3.162e-5,1.778e-5,1e-5,5.623e-6,3.162e-6,1.778e-6,1e-6,1e-7};
    string csv_path="/home/zjian/ASTZ_tests/csv/results_cubic_prediction_ISABEL_Pf01_2.csv";
    uint64_t stride=32;

    add_column(csv_path,"rel_eb");
    add_column(csv_path,"t2");
    add_column(csv_path,"H1");
    add_column(csv_path,"PSNR");
    uint64_t data_size=data_shape[0]*data_shape[1]*data_shape[2];
    vector<float> data;
    data.resize(data_size);
    ifstream data_file(data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    data_file.close();
    uint64_t compressed_data_num=(data_shape[0]+stride-1)/stride;
    compressed_data_num*=(data_shape[1]+stride-1)/stride;
    compressed_data_num*=(data_shape[2]+2*stride-7)/(2*stride);

    float min_val=*min_element(data.begin(),data.end());
    float max_val=*max_element(data.begin(),data.end());
    printf("min_val=%f\n",min_val);
    printf("max_val=%f\n",max_val);

    vector<double> t2_vec;
    for (int i=0;i<=20;i++)
        t2_vec.push_back(0.2+i*0.01);
    double stat_eb=*min_element(rel_eb_vec.begin(),rel_eb_vec.end())*(max_val-min_val)*0.1;
    double neg_2_stat_eb=1/(2*stat_eb);
    unordered_map<int64_t,int64_t> A_map,B_map;
    unordered_map<tuple<int64_t,int64_t>,int64_t> AB_map;
    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
        for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
            for (uint64_t i2=3;i2+3<data_shape[2];i2+=2*stride)
            {
                uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                double A=-data[pos-3]+data[pos-1]+data[pos+1]-data[pos+3];
                int64_t A_key=llround(A*neg_2_stat_eb);
                double B=0.25*(data[pos-3]+data[pos-1]+data[pos+1]+data[pos+3])-data[pos];
                int64_t B_key=llround(B*neg_2_stat_eb);
                // if ((abs(A)>(max_val-min_val)*1e-5) || (abs(B)>(max_val-min_val)*1e-5))
                //     continue;
                A_map[A_key]++;
                B_map[B_key]++;
                AB_map[{A_key,B_key}]++;
            }
    printf("A_map size=%lu\n",A_map.size());
    printf("B_map size=%lu\n",B_map.size());
    printf("AB_map size=%lu\n",AB_map.size());

    for (double rel_eb:rel_eb_vec)
    {
        double abs_eb=rel_eb*(max_val-min_val);
        double neg_2_eb=1/(2*abs_eb);
        for (double t2:t2_vec)
        {
            unordered_map<int64_t,int64_t> qb_map;
            double mse=0;
            for (const auto& [AB_key,count]:AB_map)
            {
                double A=get<0>(AB_key)*stat_eb*2;
                double B=get<1>(AB_key)*stat_eb*2;
                double err=A*t2+B;
                int64_t qb=llround(err*neg_2_eb);
                qb_map[qb]+=count;
                double decmp_err=err-qb*abs_eb*2;
                mse+=pow(decmp_err,2)*count;
            }
            double H1=0;
            for (auto &[qb,freq]:qb_map)
            {
                double p=(double)freq/compressed_data_num;
                H1-=p*log2(p);
            }
            mse/=compressed_data_num;
            double psnr=10*log10(pow(max_val-min_val,2)/mse);
            printf("rel_eb=%e, t2=%f, H1=%f, PSNR=%f\n",rel_eb,t2,H1,psnr);
            add_row(csv_path,rel_eb,t2);
            write_value(csv_path,rel_eb,t2,"H1",H1);
            write_value(csv_path,rel_eb,t2,"PSNR",psnr);
        }
    }
}