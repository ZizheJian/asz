#pragma once

using namespace std;

template<typename T>
string change_string_type(T value)
{
    if constexpr(is_same<T,float>::value)
    {
        char buf[64];
        snprintf(buf,sizeof(buf),"%.10f",value);
        return string(buf);
    }
    else if constexpr(is_same<T,const char *>::value)
        return string(value);
    else if constexpr(is_same<T,string>::value)
        return value;
}