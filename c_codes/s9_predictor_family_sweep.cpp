#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <set>
#include <string>
#include <vector>
#include "asz_core/huffman.hpp"
#include "../third_party/zstd/lib/zstd.h"

using namespace std;
using point_t=array<uint64_t,3>;

struct candidate_c
{
    string family,orientation;
    int axis1,axis2;
    double t,a,b;
};

double prediction(const candidate_c &candidate,double near1,double middle1,double far1,double near2)
{
    if(candidate.family=="1D4R")
        return (0.25+candidate.t)*near1+(0.25-candidate.t)*middle1;
    if(candidate.family=="2D4R")
        return (0.25+candidate.t)*near1+(0.25-candidate.t)*near2;
    return (0.5-candidate.a-candidate.b)*near1+candidate.b*middle1+candidate.a*far1;
}

vector<candidate_c> make_candidates()
{
    vector<candidate_c> candidates;
    for(int axis=0;axis<3;axis++)
    {
        for(int tick=0;tick<=12;tick++)
            candidates.push_back({"1D4R",to_string(axis),axis,-1,tick/32.0,0,0});
        set<pair<double,double>> weights;
        for(int outer=-4;outer<=4;outer++)
            for(int middle=-8;middle<=8;middle++)
                weights.emplace(outer/64.0,middle/32.0);
        for(int outer=-4;outer<=4;outer++)
            for(int middle=-4;middle<=4;middle++)
                weights.emplace(3.0/256+outer/512.0,-25.0/256+middle/256.0);
        for(int tick=0;tick<=12;tick++)
            weights.emplace(0,0.25-tick/32.0);
        for(auto [a,b]:weights)
            candidates.push_back({"1D6R",to_string(axis),axis,-1,0,a,b});
    }
    for(int axis1=0;axis1<3;axis1++)
        for(int axis2=axis1+1;axis2<3;axis2++)
            for(int tick=-12;tick<=12;tick++)
                candidates.push_back({"2D4R",to_string(axis1)+to_string(axis2),axis1,axis2,tick/32.0,0,0});
    return candidates;
}

void self_test()
{
    auto polynomial=[](double x){return 3+2*x-x*x+0.5*x*x*x+0.125*pow(x,4)-0.03125*pow(x,5);};
    for(double center:{-1.0,0.0,2.0})
    {
        auto pair_sum=[&](double distance){return polynomial(center-distance)+polynomial(center+distance);};
        candidate_c quintic={"1D6R","0",0,-1,0,3.0/256,-25.0/256};
        if(abs(prediction(quintic,pair_sum(1),pair_sum(3),pair_sum(5),0)-polynomial(center))>1e-10)
            throw runtime_error("quintic polynomial reproduction failed");
    }
    for(int tick=0;tick<=12;tick++)
    {
        double t=tick/32.0;
        candidate_c four={"1D4R","0",0,-1,t,0,0};
        candidate_c six={"1D6R","0",0,-1,0,0,0.25-t};
        if(abs(prediction(four,7,11,13,0)-prediction(six,7,11,13,0))>1e-12)
            throw runtime_error("1D6R must contain every 1D4R grid candidate");
    }
    cout<<"PASS: quintic reproduction and nested coefficient grids\n";
}

int main(int argc,char **argv)
{
    try
    {
        if(argc==2&&string(argv[1])=="--self-test")
        {
            self_test();
            return 0;
        }
        if(argc!=8)
            throw runtime_error("usage: sweep input dim0 dim1 dim2 output.csv blocks edge");
        auto started=chrono::steady_clock::now();
        string input_path=argv[1],output_path=argv[5];
        point_t shape={stoull(argv[2]),stoull(argv[3]),stoull(argv[4])};
        uint64_t blocks=stoull(argv[6]),edge=stoull(argv[7]);
        if(!blocks||!edge||filesystem::exists(output_path))
            throw runtime_error("nonzero sampling sizes and a new output path are required");
        uint64_t count=1;
        for(auto dimension:shape)
        {
            if(dimension<edge+10||count>numeric_limits<uint64_t>::max()/dimension)
                throw runtime_error("invalid dimensions");
            count*=dimension;
        }
        if(filesystem::file_size(input_path)!=count*sizeof(float))
            throw runtime_error("input size does not match float32 shape");
        vector<float> data(count);
        ifstream input(input_path,ios::binary);
        input.read(reinterpret_cast<char *>(data.data()),count*sizeof(float));
        if(!input)
            throw runtime_error("input read failed");
        double minimum=numeric_limits<double>::infinity(),maximum=-minimum;
        for(float value:data)
        {
            if(!isfinite(value))
                throw runtime_error("input has nonfinite values");
            minimum=min(minimum,(double)value);
            maximum=max(maximum,(double)value);
        }
        double range=maximum-minimum;
        if(!(range>0))
            throw runtime_error("constant input");
        mt19937_64 random_generator(20261010);
        set<point_t> anchors;
        uint64_t available_anchors=1;
        for(auto dimension:shape)
            available_anchors*=dimension-edge-9;
        if(blocks>available_anchors)
            throw runtime_error("too many distinct sample blocks");
        while(anchors.size()<blocks)
        {
            point_t anchor;
            for(int axis=0;axis<3;axis++)
                anchor[axis]=5+random_generator()%(shape[axis]-edge-9);
            anchors.insert(anchor);
        }
        vector<uint64_t> positions;
        for(auto anchor:anchors)
            for(uint64_t x=anchor[0];x<anchor[0]+edge;x++)
                for(uint64_t y=anchor[1];y<anchor[1]+edge;y++)
                    for(uint64_t z=anchor[2];z<anchor[2]+edge;z++)
                        positions.push_back((x*shape[1]+y)*shape[2]+z);
        sort(positions.begin(),positions.end());
        positions.erase(unique(positions.begin(),positions.end()),positions.end());
        array<int64_t,3> strides={(int64_t)(shape[1]*shape[2]),(int64_t)shape[2],1};
        vector<array<double,10>> features(positions.size());
        for(uint64_t sample=0;sample<positions.size();sample++)
        {
            int64_t pos=positions[sample];
            features[sample][0]=data[pos];
            for(int axis=0;axis<3;axis++)
                for(int pair=0;pair<3;pair++)
                {
                    int64_t offset=(2*pair+1)*strides[axis];
                    features[sample][1+3*axis+pair]=(double)data[pos-offset]+data[pos+offset];
                }
        }
        data.clear();
        data.shrink_to_fit();
        auto loaded=chrono::steady_clock::now();
        cout<<"input="<<input_path<<", samples="<<features.size()<<", zstd="<<ZSTD_versionString()<<", load_seconds="<<chrono::duration<double>(loaded-started).count()<<endl;
        ofstream output(output_path);
        if(!output)
            throw runtime_error("cannot create output");
        output<<"family,orientation,t,a,b,t1,t2,rel_eb,BR,PSNR,PRED_MSE,SAMPLES,ENCODE_SECONDS\n"<<setprecision(17);
        uint64_t evaluated=0;
        for(auto candidate:make_candidates())
        {
            vector<double> residuals(features.size());
            long double squared_error=0;
            for(uint64_t sample=0;sample<features.size();sample++)
            {
                const auto &f=features[sample];
                int index=1+3*candidate.axis1;
                residuals[sample]=prediction(candidate,f[index],f[index+1],f[index+2],candidate.axis2<0?0:f[1+3*candidate.axis2])-f[0];
                squared_error+=(long double)residuals[sample]*residuals[sample];
            }
            for(int eb_tick=0;eb_tick<=16;eb_tick++)
            {
                auto encoded_start=chrono::steady_clock::now();
                double rel_eb=pow(10.0,-1-eb_tick/4.0);
                double interval=2*range*rel_eb;
                vector<int64_t> symbols(residuals.size());
                long double quantization_error=0;
                for(uint64_t sample=0;sample<residuals.size();sample++)
                {
                    double bin=residuals[sample]/interval;
                    if(!isfinite(bin)||abs(bin)>9e18)
                        throw runtime_error("quantization index overflow");
                    symbols[sample]=llround(bin);
                    double error=residuals[sample]-interval*symbols[sample];
                    quantization_error+=(long double)error*error;
                }
                vector<unsigned char> huffman_bytes(symbols.size()*16+65536);
                unsigned char *cursor=huffman_bytes.data();
                huffman_encoder_class<int64_t> encoder;
                encoder.preprocess_encode(symbols.data(),symbols.size());
                encoder.save(cursor);
                encoder.encode(symbols.data(),symbols.size(),cursor);
                size_t encoded_size=cursor-huffman_bytes.data();
                vector<unsigned char> zstd_bytes(ZSTD_compressBound(encoded_size));
                size_t compressed_size=ZSTD_compress(zstd_bytes.data(),zstd_bytes.size(),huffman_bytes.data(),encoded_size,3);
                if(ZSTD_isError(compressed_size))
                    throw runtime_error(ZSTD_getErrorName(compressed_size));
                double mse=(double)(quantization_error/symbols.size());
                double psnr=mse>0?10*log10(range*range/mse):numeric_limits<double>::infinity();
                double elapsed=chrono::duration<double>(chrono::steady_clock::now()-encoded_start).count();
                output<<candidate.family<<','<<candidate.orientation<<','<<candidate.t<<','<<candidate.a<<','<<candidate.b<<','<<(1.0/6-candidate.a)<<','<<(1.0/6-candidate.b)<<','<<rel_eb<<','<<8.0*compressed_size/symbols.size()<<','<<psnr<<','<<(double)(squared_error/symbols.size())<<','<<symbols.size()<<','<<elapsed<<'\n';
            }
            if(++evaluated%100==0)
                cout<<"candidates="<<evaluated<<", evaluation_seconds="<<chrono::duration<double>(chrono::steady_clock::now()-loaded).count()<<endl;
        }
        output.close();
        if(!output)
            throw runtime_error("output write failed");
        cout<<"complete candidates="<<evaluated<<", total_seconds="<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<endl;
    }
    catch(const exception &error)
    {
        cerr<<error.what()<<'\n';
        return 1;
    }
}
