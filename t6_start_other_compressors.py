import os

compressor="sz3"
data_path="/lcrc/project/ECP-EZ/aramco/aramco-snapshot-1800.f32"
data_shape=[449,449,235]
rel_eb=1e-1
q=3

if compressor=="sz3":
    command=f"./install/sz3_install/bin/sz3 -f -i {data_path} -o {data_path}.sz3.bin -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -M REL {rel_eb} -a"
    os.system(command)
elif compressor=="qoz":
    command=f"./install/qoz_install/bin/sz3 -f -i {data_path} -o {data_path}.qoz.bin -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -M REL {rel_eb} -a -q {q}"
    os.system(command)