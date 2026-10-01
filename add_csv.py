import os

def add_csv(method,csv_path,rel_eb,br,psnr):
    if os.path.exists(csv_path):
        with open(csv_path,"r") as f:
            lines=f.readlines()
            records=[]
            width=len(lines[0].strip().split(","))
            for line in lines:
                records.append(line.strip().split(","))
                if width<len(records[-1]):
                    raise ValueError(f"{csv_path}的第一行的长度小于后续行的长度")
                records[-1]+=[""]*(width-len(records[-1]))
        records[0][0]="REL_EB"
        row_index=0
        for i in range(1,len(records)+1):
            if i==len(records) or rel_eb>float(records[i][0])*1.001:
                records.insert(i,[""]*len(records[0]))
                records[i][0]=str(rel_eb)
                row_index=i
                break
            elif 0.999*float(records[i][0])<=rel_eb<=1.001*float(records[i][0]):
                row_index=i
                break
        column_index=0
        for i in range(1,len(records[0])+2,2):
            if i==len(records[0]) or method.upper()+"_BR">records[0][i]:
                records[0].insert(i,method.upper()+"_PSNR")
                records[0].insert(i,method.upper()+"_BR")
                for j in range(1,len(records)):
                    records[j].insert(i,"")
                    records[j].insert(i,"")
                column_index=i
                break
            elif method.upper()+"_BR"==records[0][i]:
                column_index=i
                break
        records[row_index][column_index]=str(br)
        records[row_index][column_index+1]=str(psnr)
        with open(csv_path,"w") as f:
            for record in records:
                f.write(",".join(record)+"\n")
    else:
        with open(csv_path,"w") as f:
            f.write(f"REL_EB,{method.upper()}_BR,{method.upper()}_PSNR\n")
            f.write(f"{rel_eb},{br},{psnr}\n")
