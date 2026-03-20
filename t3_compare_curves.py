import numpy as np
import math

with open("results_cubic_prediction2.csv","r") as f:
    lines=f.readlines()
    lines=[line.strip().split(",") for line in lines]
    eb_set=set()
    t2_set=set()
    for line in lines[1:]:
        eb_set.add(float(line[0].strip()))
        t2_set.add(float(line[1].strip()))
    eb_list=sorted(eb_set,reverse=True)
    t2_list=sorted(t2_set)
    data=np.zeros((len(eb_list),len(t2_list),3))
    for line in lines[1:]:
        eb=float(line[0].strip())
        t2=float(line[1].strip())
        eb_index=eb_list.index(eb)
        t2_index=t2_list.index(t2)
        for i in range(1,len(line)):
            data[eb_index][t2_index][0]=float(line[2].strip())
            data[eb_index][t2_index][1]=float(line[3].strip())
            data[eb_index][t2_index][2]=float(line[4].strip())

score=[0]*21
for t2_base_id,t2_base in enumerate(t2_list):
    for t2_oppo_id,t2_oppo in enumerate(t2_list):
        if t2_base==t2_oppo:
            continue
        dist=0
        for eb_id,eb in enumerate(eb_list):
            if eb_id==0 or eb_id==len(eb_list)-1:
                continue
            br_base_prev=data[eb_id-1][t2_base_id][0]
            psnr_base_prev=data[eb_id-1][t2_base_id][2]
            br_base_next=data[eb_id+1][t2_base_id][0]
            psnr_base_next=data[eb_id+1][t2_base_id][2]
            k1=(psnr_base_next-psnr_base_prev)/(br_base_next-br_base_prev)
            if k1<=0:
                continue
            br_base=data[eb_id][t2_base_id][0]
            psnr_base=data[eb_id][t2_base_id][2]
            br_oppo=data[eb_id][t2_oppo_id][0]
            psnr_oppo=data[eb_id][t2_oppo_id][2]
            dist+=(-k1*(br_oppo-br_base)+(psnr_oppo-psnr_base))/math.sqrt(k1*k1+1)
        if dist>0:
            score[t2_oppo_id]+=1
for t2_id,t2 in enumerate(t2_list):
    print(f"t2={t2:.6f}, score={score[t2_id]}")

score_pred=[0]*21
for t2_base_id,t2_base in enumerate(t2_list):
    for t2_oppo_id,t2_oppo in enumerate(t2_list):
        if t2_base==t2_oppo:
            continue
        dist=0
        for eb_id,eb in enumerate(eb_list):
            if eb_id==0 or eb_id==len(eb_list)-1:
                continue
            h2_base_prev=data[eb_id-1][t2_base_id][1]
            psnr_base_prev=data[eb_id-1][t2_base_id][2]
            h2_base_next=data[eb_id+1][t2_base_id][1]
            psnr_base_next=data[eb_id+1][t2_base_id][2]
            k1=(psnr_base_next-psnr_base_prev)/(h2_base_next-h2_base_prev)
            if k1<=0:
                continue
            h2_base=data[eb_id][t2_base_id][1]
            psnr_base=data[eb_id][t2_base_id][2]
            h2_oppo=data[eb_id][t2_oppo_id][1]
            psnr_oppo=data[eb_id][t2_oppo_id][2]
            dist+=(-k1*(h2_oppo-h2_base)+(psnr_oppo-psnr_base))/math.sqrt(k1*k1+1)
        if dist>0:
            score_pred[t2_oppo_id]+=1
for t2_id,t2 in enumerate(t2_list):
    print(f"t2={t2:.6f}, score={score_pred[t2_id]}")