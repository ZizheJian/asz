#pragma once

using namespace std;

template<typename T>
string change_string_type(T value)
{
    if constexpr(is_same<T,float>::value || is_same<T,double>::value)
    {
        char buf[64];
        snprintf(buf,sizeof(buf),"%.15f",value);
        uint32_t pos_0=strlen(buf);
        uint32_t pos_dot=strlen(buf);
        for (int i=strlen(buf)-1;i>=0;i--)
        {
            if ((buf[i]=='0') and (pos_0==i+1))
                pos_0=i;
            else 
                if (buf[i]=='.')
                    if (pos_dot==strlen(buf))
                        pos_dot=i;
                    else
                        throw runtime_error("Multiple dots in change_string_type");
        }
        if (pos_dot!=strlen(buf))
            buf[pos_0]=0;
        return string(buf);
    }
    else if constexpr(is_same<T,const char *>::value)
        return string(value);
    else if constexpr(is_same<T,string>::value)
        return value;
    else
        throw runtime_error("Unsupported type in change_string_type");
}