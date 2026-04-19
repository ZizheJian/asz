#pragma once

using namespace std;

template<typename T>
string change_string_type(T value);
void add_row2(string &csv_path,string row_index);

template<typename T>
void add_row(string &csv_path,T row_index)
{
    add_row2(csv_path,{change_string_type(row_index)});
}

template<typename T1,typename T2>
void add_row(string &csv_path,T1 row_index1,T2 row_index2)
{
    add_row2(csv_path,change_string_type(row_index1)+","+change_string_type(row_index2));
}

void add_row2(string &csv_path,string row_index)
{
    ifstream csv_file_in(csv_path);
    vector<string> lines;
    string line;
    if (!csv_file_in.is_open())
        throw runtime_error("CSV file does not exist, cannot add row");
    while (getline(csv_file_in,line))
        lines.push_back(line);
    csv_file_in.close();
    bool found_row_index=false;
    for (auto line=lines.begin()+1;line!=lines.end();line++)
        if (!line->empty() && line->size()>=row_index.size() && line->substr(0,row_index.size())==row_index)
        {
            found_row_index=true;
            break;
        }
    if (!found_row_index)
    {
        lines.push_back(row_index);
        ofstream csv_file_out(csv_path,ios::trunc);
        for (auto &l:lines)
        {
            csv_file_out.write(l.data(),l.size());
            csv_file_out.write("\n",1);
        }
        csv_file_out.close();
    }
}