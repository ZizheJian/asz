import os
import subprocess
import re

compressor="qoz"
data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32"
data_shape=[1024,1024,1024]
rel_eb_list=[1e-6]
q=3

results=[]
if compressor=="sz3":
    os.makedirs("build/sz3_build",exist_ok=True)
    os.chdir("build/sz3_build")
    os.system("cmake -DCMAKE_INSTALL_PREFIX:PATH=../../install/sz3_install ../../c_codes/third_party/SZ3_master")
    os.system("make -j 4")
    os.system("make install")
    os.chdir("../..")
    for rel_eb in rel_eb_list:
        command=f"./install/sz3_install/bin/sz3 -f -i \"{data_path}\" -o \"{data_path}.sz3.bin\" -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -M REL {rel_eb} -a"
        results.append(subprocess.run(command,shell=True,capture_output=True,text=True))
elif compressor=="qoz":
    os.makedirs("build/qoz_build",exist_ok=True)
    os.chdir("build/qoz_build")
    os.system("cmake -DCMAKE_INSTALL_PREFIX:PATH=../../install/qoz_install ../../c_codes/third_party/SZ3_QoZ")
    os.system("make -j 4")
    os.system("make install")
    os.chdir("../..")
    for rel_eb in rel_eb_list:
        command=f"./install/qoz_install/bin/sz3 -f -i \"{data_path}\" -o \"{data_path}.qoz.bin\" -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -M REL {rel_eb} -a -q {q}"
        results.append(subprocess.run(command,shell=True,capture_output=True,text=True))

for result in results:
    output=result.stdout
    print(output)

for result in results:
    output=result.stdout
    cr=float(re.search(r"compression ratio\s*=\s*([0-9.eE+-]+)",output).group(1))
    print(cr)

for result in results:
    output=result.stdout
    psnr=float(re.search(r"PSNR\s*=\s*([0-9.eE+-]+)",output).group(1))
    print(psnr)
