#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <quadmath.h>

#include "huffman.hpp"
#include "csv_tools/csv.hpp"
#include "third_party/zstd/lib/zstd.h"

using namespace std;

static __float128 simpson_step(__float128 fa,__float128 fm,__float128 fb,__float128 a,__float128 b)
{
    return (b-a)*(fa+4*fm+fb)/6;
}

template<typename F>
static __float128 adaptive_simpson_rec(F f,__float128 a,__float128 b,__float128 fa,__float128 fm,__float128 fb,__float128 whole,__float128 tol,int depth)
{
    __float128 m=(a+b)*0.5;
    __float128 lm=(a+m)*0.5;
    __float128 rm=(m+b)*0.5;
    __float128 flm=f(lm);
    __float128 frm=f(rm);
    __float128 left=simpson_step(fa,flm,fm,a,m);
    __float128 right=simpson_step(fm,frm,fb,m,b);
    __float128 delta=left+right-whole;
    if (depth<=0)
    {
        printf("Warning: maximum recursion depth reached in adaptive_simpson_rec, delta=%f, 15*tol=%f\n",(double)delta,(double)(15*tol));
        return left+right+delta/15;
    }
    if (labs(delta)<=15*tol)
        return left+right+delta/15;
    return adaptive_simpson_rec(f,a,m,fa,flm,fm,left,tol*0.5,depth-1)+adaptive_simpson_rec(f,m,b,fm,frm,fb,right,tol*0.5,depth-1);
}


template<typename F>
static __float128 adaptive_simpson(F f,__float128 a,__float128 b,__float128 tol,int max_depth=20)
{
    __float128 m=(a+b)*0.5;
    __float128 fa=f(a);
    __float128 fm=f(m);
    __float128 fb=f(b);
    __float128 whole=simpson_step(fa,fm,fb,a,b);
    return adaptive_simpson_rec(f,a,b,fa,fm,fb,whole,tol,max_depth);
}

vector<vector<__float128>> get_as(__float128 t2)
{
    vector<vector<__float128>> as(1,vector<__float128>(5));
    as[0][0]=0.25-t2;
    as[0][1]=0.25+t2;
    as[0][2]=-1;
    as[0][3]=0.25+t2;
    as[0][4]=0.25-t2;
    return as;
}

vector<vector<__float128>> get_aj(__float128 t2)
{
    vector<vector<__float128>> aj(2,vector<__float128>(7));
    aj[0][0]=0.25-t2;
    aj[0][1]=0.25+t2;
    aj[0][2]=-1;
    aj[0][3]=0.25+t2;
    aj[0][4]=0;
    aj[0][5]=0.25-t2;
    aj[0][6]=0;
    aj[1][0]=0;
    aj[1][1]=0.25-t2;
    aj[1][2]=0;
    aj[1][3]=0.25+t2;
    aj[1][4]=-1;
    aj[1][5]=0.25+t2;
    aj[1][6]=0.25-t2;
    return aj;
}

vector<vector<__float128>> get_dasdt2()
{
    vector<vector<__float128>> dasdt2(1,vector<__float128>(5));
    dasdt2[0][0]=-1;
    dasdt2[0][1]=1;
    dasdt2[0][2]=0;
    dasdt2[0][3]=1;
    dasdt2[0][4]=-1;
    return dasdt2;
}

vector<vector<__float128>> get_dajdt2()
{
    vector<vector<__float128>> dajdt2(2,vector<__float128>(7));
    dajdt2[0][0]=-1;
    dajdt2[0][1]=1;
    dajdt2[0][2]=0;
    dajdt2[0][3]=1;
    dajdt2[0][4]=0;
    dajdt2[0][5]=-1;
    dajdt2[0][6]=0;
    dajdt2[1][0]=0;
    dajdt2[1][1]=-1;
    dajdt2[1][2]=0;
    dajdt2[1][3]=1;
    dajdt2[1][4]=0;
    dajdt2[1][5]=1;
    dajdt2[1][6]=-1;
    return dajdt2;
}

vector<vector<__float128>> get_sigmas(vector<double> &cov)
{
    vector<vector<__float128>> sigmas(5,vector<__float128>(5));
    sigmas[0][0]=cov[0];    sigmas[0][1]=cov[2];    sigmas[0][2]=cov[3];    sigmas[0][3]=cov[4];    sigmas[0][4]=cov[6];
    sigmas[1][0]=cov[2];    sigmas[1][1]=cov[0];    sigmas[1][2]=cov[1];    sigmas[1][3]=cov[2];    sigmas[1][4]=cov[4];
    sigmas[2][0]=cov[3];    sigmas[2][1]=cov[1];    sigmas[2][2]=cov[0];    sigmas[2][3]=cov[1];    sigmas[2][4]=cov[3];
    sigmas[3][0]=cov[4];    sigmas[3][1]=cov[2];    sigmas[3][2]=cov[1];    sigmas[3][3]=cov[0];    sigmas[3][4]=cov[2];
    sigmas[4][0]=cov[6];    sigmas[4][1]=cov[4];    sigmas[4][2]=cov[3];    sigmas[4][3]=cov[2];    sigmas[4][4]=cov[0];
    return sigmas;
}

vector<vector<__float128>> get_sigmaj(vector<double> &cov)
{
    vector<vector<__float128>> sigmaj(7,vector<__float128>(7));
    sigmaj[0][0]=cov[0];    sigmaj[0][1]=cov[2];    sigmaj[0][2]=cov[3];    sigmaj[0][3]=cov[4];    sigmaj[0][4]=cov[5];    sigmaj[0][5]=cov[6];    sigmaj[0][6]=cov[8];
    sigmaj[1][0]=cov[2];    sigmaj[1][1]=cov[0];    sigmaj[1][2]=cov[1];    sigmaj[1][3]=cov[2];    sigmaj[1][4]=cov[3];    sigmaj[1][5]=cov[4];    sigmaj[1][6]=cov[6];
    sigmaj[2][0]=cov[3];    sigmaj[2][1]=cov[1];    sigmaj[2][2]=cov[0];    sigmaj[2][3]=cov[1];    sigmaj[2][4]=cov[2];    sigmaj[2][5]=cov[3];    sigmaj[2][6]=cov[5];
    sigmaj[3][0]=cov[4];    sigmaj[3][1]=cov[2];    sigmaj[3][2]=cov[1];    sigmaj[3][3]=cov[0];    sigmaj[3][4]=cov[1];    sigmaj[3][5]=cov[2];    sigmaj[3][6]=cov[4];
    sigmaj[4][0]=cov[5];    sigmaj[4][1]=cov[3];    sigmaj[4][2]=cov[2];    sigmaj[4][3]=cov[1];    sigmaj[4][4]=cov[0];    sigmaj[4][5]=cov[1];    sigmaj[4][6]=cov[3];
    sigmaj[5][0]=cov[6];    sigmaj[5][1]=cov[4];    sigmaj[5][2]=cov[3];    sigmaj[5][3]=cov[2];    sigmaj[5][4]=cov[1];    sigmaj[5][5]=cov[0];    sigmaj[5][6]=cov[2];
    sigmaj[6][0]=cov[8];    sigmaj[6][1]=cov[6];    sigmaj[6][2]=cov[5];    sigmaj[6][3]=cov[4];    sigmaj[6][4]=cov[3];    sigmaj[6][5]=cov[2];    sigmaj[6][6]=cov[0];
    return sigmaj;
}

vector<vector<__float128>> get_a_sigma_a(vector<vector<__float128>> &a,vector<vector<__float128>> &sigma)
{
    if ((a[0].size()!=sigma.size() || a[0].size()!=sigma[0].size()))
    {
        char buf[256];
        snprintf(buf,sizeof(buf),"get_a_sigma_a error: a.size()=(%lu,%lu), sigma.size()=(%lu,%lu)\n",a.size(),a[0].size(),sigma.size(),sigma[0].size());
        throw runtime_error(buf);
    }
    vector<vector<__float128>> ret(a.size(),vector<__float128>(a[0].size(),0));
    for (int i=0;i<a.size();i++)
        for (int j=0;j<a.size();j++)
            for (int k1=0;k1<sigma.size();k1++)
                for (int k2=0;k2<sigma.size();k2++)
                    ret[i][j]+=a[i][k1]*sigma[k1][k2]*a[j][k2];
    return ret;
}

vector<vector<__float128>> get_2a_sigma_a(vector<vector<__float128>> &a,vector<vector<__float128>> &sigma)
{
    vector<vector<__float128>> ret=get_a_sigma_a(a,sigma);
    for (int i=0;i<ret.size();i++)
        for (int j=0;j<ret[0].size();j++)
            ret[i][j]*=2;
    return ret;
}

__float128 f1_pdf(__float128 var,__float128 x)
{
    return expq(-x*x/(2*var))/sqrtq(2*M_PI*var);
}

__float128 f1_cdf(__float128 var,__float128 x)
{
    return 0.5*erfcq(-x/(sqrtq(2*var)));
}

int64_t find_is_by_pdf(__float128 var,__float128 eb,__float128 val)
{
    // return (int64_t)ceilq(sqrtq(2*var*logq(2*eb/(sqrtq(2*M_PI*var)*val)))/(2*eb));
    return (int64_t)ceilq(sqrtq(-2*var*logq(sqrtq(2*M_PI*var)*val))/(2*eb));
}

int64_t find_ij_by_pdf(vector<vector<__float128>> &varj,__float128 eb,__float128 val)
{
    __float128 det=varj[0][0]*varj[1][1]-varj[0][1]*varj[1][0];
    __float128 inv_varj00=varj[1][1]/det;
    // printf("sqrtq(4*M_PI*M_PI*det)*val=%f\n",(double)(sqrtq(4*M_PI*M_PI*det)*val));
    // printf("4*eb*eb=%f\n",(double)(4*eb*eb));
    // printf("logq(4*eb*eb/(sqrtq(4*M_PI*M_PI*det)*val))=%f\n",(double)logq(4*eb*eb/(sqrtq(4*M_PI*M_PI*det)*val)));
    // printf("sqrtq(2*logq(4*eb*eb/(sqrtq(4*M_PI*M_PI*det)*val)))=%f\n",(double)sqrtq(2*logq(4*eb*eb/(sqrtq(4*M_PI*M_PI*det)*val))));
    // printf("2*eb*sqrtq(inv_varj00)=%f\n",(double)(2*eb*sqrtq(inv_varj00)));
    printf("2*logq(2*M_PI*sqrtq(det)*val)=%f\n",(double)(2*logq(2*M_PI*sqrtq(det)*val)));
    return (int64_t)ceilq(sqrtq(-2*logq(2*M_PI*sqrtq(det)*val))/(2*eb*sqrtq(inv_varj00)));
}

__float128 get_ps(__float128 eb,__float128 var,int64_t i)
{
    return f1_cdf(var,(2*i+1)*eb)-f1_cdf(var,(2*i-1)*eb);
}

__float128 get_pj(__float128 eb,vector<vector<__float128>> &varj,int64_t i1,int64_t i2,__float128 tol)
{
    __float128 cond_var=varj[1][1]-varj[0][1]*varj[1][0]/varj[0][0];
    if(cond_var<=0)
        throw runtime_error("conditional variance Var(r2|r1) is non-positive");

    __float128 a1=(2*i1-1)*eb;
    __float128 b1=(2*i1+1)*eb;
    __float128 a2=(2*i2-1)*eb;
    __float128 b2=(2*i2+1)*eb;

    auto integrand=[&](__float128 x)->__float128{
        __float128 mux=varj[0][1]/varj[0][0]*x;
        __float128 py=f1_cdf(cond_var,b2-mux)-f1_cdf(cond_var,a2-mux);
        return f1_pdf(varj[0][0],x)*py;
    };

    return adaptive_simpson(integrand,a1,b1,tol);
}

__float128 get_mse(__float128 eb,__float128 var,int64_t i)
{
    __float128 r=2*i*eb;
    return (var+r*r)*(f1_cdf(var,r+eb)-f1_cdf(var,r-eb))+var*((r-eb)*f1_pdf(var,r+eb)-(r+eb)*f1_pdf(var,r-eb));
}

__float128 get_dpsdt2(__float128 eb,__float128 var,__float128 dvardt2,int64_t i)
{
    __float128 sigma=sqrtq(var);
    __float128 a=(2*i-1)*eb;
    __float128 b=(2*i+1)*eb;
    return -dvardt2*(expq(-(b*b)/(2*var))*b-expq(-(a*a)/(2*var))*a)/(2*sqrtq(2*M_PI)*sigma*sigma*sigma);
}

__float128 get_dpsddelta(__float128 eb,__float128 var,int64_t i)
{
    __float128 a=(2*i-1)*eb;
    __float128 b=(2*i+1)*eb;
    return (expq(-(b*b)/(2*var))*(2*i+1)-expq(-(a*a)/(2*var))*(2*i-1))/(2*sqrtq(2*M_PI*var));
}

int main()
{
    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    vector<uint64_t> data_shape={100,500,500};
    // vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,5.623e-5,3.162e-5,1.778e-5,1e-5,5.623e-6,3.162e-6,1.778e-6,1e-6,1e-7,1e-8};
    vector<double> rel_eb_vec={1e-6};
    // data_shape={1,1,7};

    uint64_t data_size=data_shape[0]*data_shape[1]*data_shape[2];
    vector<float> data;
    data.resize(data_size);
    ifstream data_file(data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    data_file.close();
    // data={10,3,10,0,9,6,8};
    uint64_t compressed_data_num=data_shape[0]*data_shape[1]*((data_shape[2]-5)/2);

    float min_val=*min_element(data.begin(),data.end());
    float max_val=*max_element(data.begin(),data.end());
    printf("min_val=%f\n",min_val);
    printf("max_val=%f\n",max_val);

    // vector<double> cov(11);
    // for (uint64_t i0=0;i0<data_shape[0];i0++)
    //     for (uint64_t i1=0;i1<data_shape[1];i1++)
    //     {
    //         float *line=data.data()+i0*data_shape[1]*data_shape[2]+i1*data_shape[2];
    //         double sigma_i_data=0,sigma_data=0;
    //         for (uint64_t i2=0;i2<data_shape[2];i2++)
    //         {
    //             sigma_i_data+=i2*line[i2];
    //             sigma_data+=line[i2];
    //         }
    //         double sigma_i=(data_shape[2]-1)*data_shape[2]/2;
    //         double sigma_i2=(data_shape[2]-1)*data_shape[2]*(2*data_shape[2]-1)/6;
    //         double a=(data_shape[2]*sigma_i_data-sigma_i*sigma_data)/(data_shape[2]*sigma_i2-sigma_i*sigma_i);
    //         double b=(sigma_i*sigma_i_data-sigma_i2*sigma_data)/(sigma_i*sigma_i-data_shape[2]*sigma_i2);
    //         vector<double> line2(data_shape[2]);
    //         for (uint64_t i2=0;i2<data_shape[2];i2++)
    //             line2[i2]=line[i2]-a*i2-b;
    //         for (uint64_t lag=0;lag<=10;lag++)
    //         {
    //             double local_cov=0;
    //             for (uint64_t i2=lag;i2<data_shape[2];i2++)
    //                 local_cov+=line2[i2]*line2[i2-lag];
    //             cov[lag]+=local_cov;
    //         }
    //     }
    // for (uint64_t lag=0;lag<=10;lag++)
    // {
    //     cov[lag]/=(data_shape[0]*data_shape[1]*(data_shape[2]-lag));
    //     printf("lag=%lu, cov=%f\n",lag,cov[lag]);
    // }

    vector<vector<double>> sigmas(5,vector<double>(5));
    for (uint64_t i0=0;i0<data_shape[0];i0++)
        for (uint64_t i1=0;i1<data_shape[1];i1++)
        {
            float *line=data.data()+i0*data_shape[1]*data_shape[2]+i1*data_shape[2];
            for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
            {
                sigmas[0][0]+=line[i2-3]*line[i2-3];
                sigmas[0][1]+=line[i2-3]*line[i2-1];
                sigmas[0][2]+=line[i2-3]*line[i2];
                sigmas[0][3]+=line[i2-3]*line[i2+1];
                sigmas[0][4]+=line[i2-3]*line[i2+3];
                sigmas[1][1]+=line[i2-1]*line[i2-1];
                sigmas[1][2]+=line[i2-1]*line[i2];
                sigmas[1][3]+=line[i2-1]*line[i2+1];
                sigmas[1][4]+=line[i2-1]*line[i2+3];
                sigmas[2][2]+=line[i2]*line[i2];
                sigmas[2][3]+=line[i2]*line[i2+1];
                sigmas[2][4]+=line[i2]*line[i2+3];
                sigmas[3][3]+=line[i2+1]*line[i2+1];
                sigmas[3][4]+=line[i2+1]*line[i2+3];
                sigmas[4][4]+=line[i2+3]*line[i2+3];
            }
        }
    for (uint64_t i=0;i<sigmas.size();i++)
        for (uint64_t j=i;j<sigmas[0].size();j++)
        {
            sigmas[i][j]/=(data_shape[0]*data_shape[1]*((data_shape[2]-5)/2));
            sigmas[j][i]=sigmas[i][j];
        }
    for (uint64_t i=0;i<sigmas.size();i++)
    {
        printf("{");
        for (uint64_t j=0;j<sigmas[0].size();j++)
        {
            printf("%f",sigmas[i][j]);
            if (j<sigmas[0].size()-1)
                printf(",");
        }
        printf("},\n");
    }
    
    vector<vector<double>> sigmaj(7,vector<double>(7));
    for (uint64_t i0=0;i0<data_shape[0];i0++)
        for (uint64_t i1=0;i1<data_shape[1];i1++)
        {
            float *line=data.data()+i0*data_shape[1]*data_shape[2]+i1*data_shape[2];
            for (uint64_t i2=3;i2+5<data_shape[2];i2+=2)
            {
                sigmaj[0][0]+=line[i2-3]*line[i2-3];
                sigmaj[0][1]+=line[i2-3]*line[i2-1];
                sigmaj[0][2]+=line[i2-3]*line[i2];
                sigmaj[0][3]+=line[i2-3]*line[i2+1];
                sigmaj[0][4]+=line[i2-3]*line[i2+2];
                sigmaj[0][5]+=line[i2-3]*line[i2+3];
                sigmaj[0][6]+=line[i2-3]*line[i2+5];
                sigmaj[1][1]+=line[i2-1]*line[i2-1];
                sigmaj[1][2]+=line[i2-1]*line[i2];
                sigmaj[1][3]+=line[i2-1]*line[i2+1];
                sigmaj[1][4]+=line[i2-1]*line[i2+2];
                sigmaj[1][5]+=line[i2-1]*line[i2+3];
                sigmaj[1][6]+=line[i2-1]*line[i2+5];
                sigmaj[2][2]+=line[i2]*line[i2];
                sigmaj[2][3]+=line[i2]*line[i2+1];
                sigmaj[2][4]+=line[i2]*line[i2+2];
                sigmaj[2][5]+=line[i2]*line[i2+3];
                sigmaj[2][6]+=line[i2]*line[i2+5];
                sigmaj[3][3]+=line[i2+1]*line[i2+1];
                sigmaj[3][4]+=line[i2+1]*line[i2+2];
                sigmaj[3][5]+=line[i2+1]*line[i2+3];
                sigmaj[3][6]+=line[i2+1]*line[i2+5];
                sigmaj[4][4]+=line[i2+2]*line[i2+2];
                sigmaj[4][5]+=line[i2+2]*line[i2+3];
                sigmaj[4][6]+=line[i2+2]*line[i2+5];
                sigmaj[5][5]+=line[i2+3]*line[i2+3];
                sigmaj[5][6]+=line[i2+3]*line[i2+5];
                sigmaj[6][6]+=line[i2+5]*line[i2+5];
            }
        }
    for (uint64_t i=0;i<sigmaj.size();i++)
        for (uint64_t j=i;j<sigmaj[0].size();j++)
        {
            sigmaj[i][j]/=(data_shape[0]*data_shape[1]*((data_shape[2]-7)/2));
            sigmaj[j][i]=sigmaj[i][j];
        }
    for (uint64_t i=0;i<sigmaj.size();i++)
    {
        printf("{");
        for (uint64_t j=0;j<sigmaj[0].size();j++)
        {
            printf("%f",sigmaj[i][j]);
            if (j<sigmaj[0].size()-1)
                printf(",");
        }
        printf("},\n");
    }
    exit(0);
    
    // 通过穷举t2并计算d来确定最优的t2
    // 计算d需要极端dH2dt2、dH2ddelta、dPSNRdt2、dPSNRddelta
    // 需要计算出很多Ps(r1,r2)、Pj(r1,r2)以及它们对t2和delta的导数
    // for (uint64_t lag=0;lag<=10;lag++)
    //     cov[lag]/=(max_val-min_val)*(max_val-min_val);
    // max_val=1;
    // min_val=0;
    // __float128 t2_min=0.2,t2_max=0.4,t2_gap=0.01;
    // __float128 t2_id_max=(t2_max-t2_min)/t2_gap;
    // vector<vector<__float128>> sigmas=get_sigmas(cov);
    // vector<vector<__float128>> sigmaj=get_sigmaj(cov);
    // for (int t2_id=0;t2_id<=t2_id_max;t2_id+=1)
    // {
    //     __float128 t2=t2_min+t2_gap*t2_id;
    //     vector<vector<__float128>> as=get_as(t2);
    //     vector<vector<__float128>> aj=get_aj(t2);
    //     vector<vector<__float128>> dasdt2=get_dasdt2();
    //     vector<vector<__float128>> dajdt2=get_dajdt2();
        
    //     vector<vector<__float128>> vars=get_a_sigma_a(as,sigmas);
    //     vector<vector<__float128>> varj=get_a_sigma_a(aj,sigmaj);
    //     vector<vector<__float128>> dvarsdt2=get_2a_sigma_a(dasdt2,sigmas);
    //     vector<vector<__float128>> dvarjdt2=get_2a_sigma_a(dajdt2,sigmaj);
    //     // for (__float128 eb:rel_eb_vec)
    //     for (__float128 eb=1e-3;eb>=1e-3;eb/=10)
    //     {
    //         __float128 tol=1e-8;
    //         // 先计算i的上限，使得ps(i)和pj(i,0)刚好小于tol
    //         int64_t ismax=find_is_by_pdf(vars[0][0],eb,tol);
    //         printf("ismax=%ld\n",t2,(double)eb,ismax);
    //         vector<__float128> ps(ismax+1);
    //         for (int i=0;i<=ismax;i++)
    //             ps[i]=get_ps(eb,vars[0][0],i);
    //         // print_float128(ps[ismax-1]);
    //         // print_float128(ps[ismax]);

    //         int64_t ijmax=find_ij_by_pdf(varj,eb,tol);
    //         printf("ijmax=%ld\n",ijmax);
    //         vector<vector<__float128>> pj(ijmax+1,vector<__float128>(ijmax+1));
    //         for (int i1=0;i1<=ijmax;i1++)
    //             for (int i2=0;i2<=ijmax;i2++)
    //                 pj[i1][i2]=get_pj(eb,varj,i1,i2,tol);
            
    //         // 然后计算mse
    //         vector<__float128> mse(ismax+1);
    //         for (int i=0;i<=ismax;i++)
    //             mse[i]=get_mse(eb,vars[0][0],i);

    //         // 计算H2和PSNR验证一下
    //         __float128 H2=0;
    //         for (int i1=0;i1<=ijmax;i1++)
    //             for (int i2=0;i2<=ijmax;i2++)
    //             {
    //                 __float128 temp_H2=-pj[i1][i2]*logq(pj[i1][i2]);
    //                 if (i1>0)
    //                     temp_H2*=2;
    //                 if (i2>0)
    //                     temp_H2*=2;
    //                 H2+=temp_H2;
    //             }
    //         for (int i=0;i<=ismax;i++)
    //         {
    //             __float128 temp_H2=ps[i]*logq(ps[i]);
    //             if (i>0)
    //                 temp_H2*=2;
    //             H2+=temp_H2;
    //         }
    //         __float128 PSNR=0;
    //         for (int i=0;i<=ismax;i++)
    //         {
    //             __float128 temp_PSNR=mse[i];
    //             if (i>0)
    //                 temp_PSNR*=2;
    //             PSNR+=temp_PSNR;
    //         }
    //         PSNR=10*logq((max_val-min_val)*(max_val-min_val)/PSNR)/logq(10);
    //         printf("t2=%f, eb=%f, H2=%f, PSNR=%f\n",(double)t2,(double)eb,(double)H2,(double)PSNR);
    //         getchar();

    //         // vector<__float128> dpsdt2(ismax+1);
    //         // vector<__float128> dpsddelta(ismax+1);
    //         // vector<vector<__float128>> dpjdt2(ijmax+1,vector<__float128>(ijmax+1));
    //         // vector<vector<__float128>> dpjddelta(ijmax+1,vector<__float128>(ijmax+1));
    //         // vector<__float128> dmse_dt2(ismax+1);
    //         // vector<__float128> dmse_ddelta(ismax+1);
    //         // for (int i=0;i<=ismax;i++)
    //         // {
    //         //     dpsdt2[i]=get_dpsdt2(eb,vars[0][0],dvarsdt2[0][0],i);
    //         //     dpsddelta[i]=get_dpsddelta(eb,vars[0][0],i);
    //         // }
    //     }
        
    // }
}