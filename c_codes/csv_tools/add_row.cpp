#pragma once

using namespace std;

template<typename T>
string change_string_type(T value);
void add_row2(string &csv_path,string row_name);

template<typename T>
void add_row(string &csv_path,T row_name)
{
    add_row2(csv_path,change_string_type(row_name));
}

template<typename T1,typename T2>
void add_row(string &csv_path,T1 row_name1,T2 row_name2)
{
    add_row2(csv_path,change_string_type(row_name1)+","+change_string_type(row_name2));
}

void add_row2(string &csv_path,string row_name)
{
    ifstream csv_file_in(csv_path);
    vector<string> lines;
    string line;
    if (!csv_file_in.is_open())
        throw runtime_error("CSV file does not exist, cannot add row");
    while (getline(csv_file_in, line))
        lines.push_back(line);
    csv_file_in.close();
    bool has_row_name=false;
    for (auto line=lines.begin()+1;line!=lines.end();line++)
        if (!line->empty() && line->size()>=row_name.size() && line->substr(0,row_name.size())==row_name)
        {
            has_row_name=true;
            break;
        }
    if (!has_row_name)
    {
        lines.push_back(row_name);
        ofstream csv_file_out(csv_path,ios::trunc);
        for (auto &l:lines)
            csv_file_out<<l<<"\n";
        csv_file_out.close();
    }
}