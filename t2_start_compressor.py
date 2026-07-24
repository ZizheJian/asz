import os,subprocess,time
import numpy as np
from add_csv import add_csv

redbegin="\033[91m"
redend="\033[0m"
silent_build=False

def run_command(command,silent=False):
    import pty,errno,shlex
    command_list=shlex.split(command)
    if silent:
        result=subprocess.run(command_list,capture_output=True,text=True,encoding="utf-8")
        if result.returncode!=0:
            print(result.stdout)
            print(result.stderr)
            exit()
        return result.stdout+result.stderr
    else:
        master,slave=pty.openpty()
        proc=subprocess.Popen(command_list,stdout=slave,stderr=slave,text=True,bufsize=1)
        os.close(slave)
        lines=[]
        with os.fdopen(master) as proc_stdout:
            try:
                for line in proc_stdout:
                    print(line,end="")
                    lines.append(line)
            except OSError as e:
                if e.errno!=errno.EIO:
                    raise e
        proc.wait()
        output="".join(lines)
        if proc.returncode!=0:
            exit()
        return output

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/embeddings/videollava/embeds_0[(8, 257, 4096)].bin"
# data_shape=[8,257,4096] #32MB
# rel_eb_list=[1e-1,1e-2,1e-3,1e-4,1e-5]

data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_Kaz/xpcs-998x128x128.bin.f32"
data_shape=[998,128,128] #63MB
rel_eb_list=[1e-1,1e-2,1e-3,1e-4]

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin"
# data_shape=[100,500,500] #95MB
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/aramco/aramco-snapshot-1800.f32"
# data_shape=[449,449,235] #181MB
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/SCALE_LETKF/PRES-98x1200x1200.dat"
# data_shape=[98,1200,1200] #538MB
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat"
# data_shape=[26,1800,3600] #643MB
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/APSU_TestData_004/APSU_TestData_004.h5.f32"
# data_shape=[1024,1558,1813] #11GB
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/E017_CeramicGlass_L2Mq0_060C_att00_001/E017_CeramicGlass_L2Mq0_060C_att00_001_001.h5.f32"
# data_shape=[1024,1813,1558] #11GB
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5]

# compressor_list=["asz","sz3","qoz","sperr","zfp"]
compressor_list=["asz","sz3","qoz"]

for compressor in compressor_list:
    if compressor=="asz":
        os.makedirs("build",exist_ok=True)
        os.chdir("build")
        run_command(f"cmake -DCODE_NAME=s1_compress -DCMAKE_INSTALL_PREFIX=../install ../c_codes")
        run_command("make install",silent=silent_build)
        os.chdir("..")
        for rel_eb in rel_eb_list:
            command=f"./install/bin/s1_compress -f -i \"{data_path}\" -3 {data_shape[0]} {data_shape[1]} {data_shape[2]} -M REL {rel_eb}"
            result=run_command(command,silent=False)
            command=f"./install/bin/s1_decompress -f -i \"{data_path}\" -3 {data_shape[0]} {data_shape[1]} {data_shape[2]} -M REL {rel_eb}"
            result+=run_command(command,silent=False)
            br=cr=psnr=compress_time=decompress_time=None
            for line in reversed(result.splitlines()):
                if line.startswith("Decompression time: ") and decompress_time is None:
                    decompress_time=float(line.split("Decompression time: ")[1].split()[0])
                elif line.startswith("Compression time: ") and compress_time is None:
                    compress_time=float(line.split("Compression time: ")[1].split()[0])
                elif line.startswith("CR= ") and cr is None:
                    cr=float(line.split("CR= ")[1])
                elif line.startswith("BR= ") and br is None:
                    br=float(line.split("BR= ")[1])
                elif line.startswith("PSNR= ") and psnr is None:
                    psnr=float(line.split("PSNR= ")[1].split(",")[0])
            print(f"{rel_eb} {cr} {br} {psnr} {compress_time} {decompress_time}")
            add_csv("asz",f"{data_path}.csv",rel_eb,br,psnr)
    elif compressor=="sz3":
        os.makedirs("build/sz3_build",exist_ok=True)
        os.chdir("build/sz3_build")
        run_command("cmake -DCMAKE_INSTALL_PREFIX:PATH=../../install/sz3_install ../../c_codes/third_party/SZ3_master",silent=silent_build)
        run_command("make -j 4",silent=silent_build)
        run_command("make install",silent=silent_build)
        os.chdir("../..")
        for rel_eb in rel_eb_list:
            command=f"./install/sz3_install/bin/sz3 -f -i \"{data_path}\" -o \"{data_path}.sz3.bin\" -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -M REL {rel_eb} -a"
            result=run_command(command,silent=True)
            br=cr=psnr=compress_time=decompress_time=None
            for line in reversed(result.splitlines()):
                if line.startswith("decompression time = ") and decompress_time is None:
                    decompress_time=float(line.split("decompression time = ")[1].split()[0])
                elif line.startswith("compression ratio = ") and cr is None:
                    cr=float(line.split("compression ratio = ")[1])
                elif line.startswith("PSNR = ") and psnr is None:
                    psnr=float(line.split("PSNR = ")[1].split(",")[0])
                elif line.startswith("compression time = ") and compress_time is None:
                    compress_time=float(line.split("compression time = ")[1])
            br=32/cr
            print(f"{rel_eb} {cr} {br} {psnr} {compress_time} {decompress_time}")
            add_csv("sz3",f"{data_path}.csv",rel_eb,br,psnr)
    elif compressor=="qoz":
        os.makedirs("build/qoz_build",exist_ok=True)
        os.chdir("build/qoz_build")
        run_command("cmake -DCMAKE_INSTALL_PREFIX:PATH=../../install/qoz_install ../../c_codes/third_party/SZ3_QoZ",silent=silent_build)
        run_command("make -j 4",silent=silent_build)
        run_command("make install",silent=silent_build)
        os.chdir("../..")
        for rel_eb in rel_eb_list:
            command=f"./install/qoz_install/bin/sz3 -f -i \"{data_path}\" -o \"{data_path}.qoz.bin\" -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -M REL {rel_eb} -a -q 3"
            result=run_command(command,silent=True)
            br=cr=psnr=compress_time=decompress_time=None
            for line in reversed(result.splitlines()):
                if line.startswith("decompression time = ") and decompress_time is None:
                    decompress_time=float(line.split("decompression time = ")[1].split()[0])
                elif line.startswith("compression ratio = ") and cr is None:
                    cr=float(line.split("compression ratio = ")[1])
                elif line.startswith("PSNR = ") and psnr is None:
                    psnr=float(line.split("PSNR = ")[1].split(",")[0])
                elif line.startswith("compression time = ") and compress_time is None:
                    compress_time=float(line.split("compression time = ")[1])
            br=32/cr
            print(f"{rel_eb} {cr} {br} {psnr} {compress_time} {decompress_time}")
            add_csv("qoz",f"{data_path}.csv",rel_eb,br,psnr)
    elif compressor=="zfp":
        os.makedirs("build/zfp_build",exist_ok=True)
        os.chdir("build/zfp_build")
        run_command("cmake -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX:PATH=../../install/zfp_install ../../c_codes/third_party/zfp",silent=silent_build)
        run_command("make -j 4",silent=silent_build)
        run_command("make install",silent=silent_build)
        os.chdir("../..")
        data=np.fromfile(data_path,dtype=np.float32)
        value_range=data.max()-data.min()
        for rel_eb in rel_eb_list:
            abs_eb=rel_eb*value_range
            command1=f"./install/zfp_install/bin/zfp -f -i \"{data_path}\" -z \"{data_path}.zfp\" -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -a {abs_eb}"
            begin_time=time.time()
            result1=run_command(command1,silent=True)
            end_time=time.time()
            compress_time=end_time-begin_time
            command2=f"./install/zfp_install/bin/zfp -f -z \"{data_path}.zfp\" -o \"{data_path}.zfp.bin\" -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -a {abs_eb}"
            begin_time=time.time()
            result2=run_command(command2,silent=True)
            end_time=time.time()
            decompress_time=end_time-begin_time
            command3=f"./install/zfp_install/bin/zfp -f -i \"{data_path}\" -o \"{data_path}.zfp.bin\" -3 {data_shape[2]} {data_shape[1]} {data_shape[0]} -a {abs_eb} -s"
            result3=run_command(command3,silent=True)
            br=cr=psnr=None
            line=result3.splitlines()[0]
            for term in line.split(" "):
                if term.startswith("ratio=") and cr is None:
                    cr=float(term.split("ratio=")[1])
                elif term.startswith("rate=") and br is None:
                    br=float(term.split("rate=")[1])
                elif term.startswith("psnr=") and psnr is None:
                    psnr=float(term.split("psnr=")[1])
            print(f"{rel_eb} {cr} {br} {psnr} {compress_time} {decompress_time}")
            add_csv("zfp",f"{data_path}.csv",rel_eb,br,psnr)
    elif compressor=="sperr":
        os.makedirs("build/sperr_build",exist_ok=True)
        os.chdir("build/sperr_build")
        run_command("cmake -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX:PATH=../../install/sperr_install ../../c_codes/third_party/sperr",silent=silent_build)
        run_command("make -j 4",silent=silent_build)
        run_command("make install",silent=silent_build)
        os.chdir("../..")
        data=np.fromfile(data_path,dtype=np.float32)
        value_range=data.max()-data.min()
        for rel_eb in rel_eb_list:
            abs_eb=rel_eb*value_range
            command1=f"./install/sperr_install/bin/sperr3d \"{data_path}\" -c --ftype 32 --dims {data_shape[2]} {data_shape[1]} {data_shape[0]} --bitstream \"{data_path}.sperr\" --pwe {abs_eb}"
            begin_time=time.time()
            result1=run_command(command1,silent=True)
            end_time=time.time()
            compress_time=end_time-begin_time
            command2=f"./install/sperr_install/bin/sperr3d \"{data_path}.sperr\" -d --ftype 32 --dims {data_shape[2]} {data_shape[1]} {data_shape[0]} --decomp_f \"{data_path}.sperr.bin\" --pwe {abs_eb}"
            begin_time=time.time()
            result2=run_command(command2,silent=True)
            end_time=time.time()
            decompress_time=end_time-begin_time
            command3=f"./install/sperr_install/bin/sperr3d \"{data_path}\" -c --ftype 32 --dims {data_shape[2]} {data_shape[1]} {data_shape[0]} --decomp_f \"{data_path}.sperr.bin\" --print_stats --pwe {abs_eb}"
            result3=run_command(command3,silent=True)
            br=cr=psnr=None
            line=result3.splitlines()[-1]
            for term in line.split(", "):
                if term.startswith("Bitrate = ") and br is None:
                    br=float(term.split("Bitrate = ")[1])
                elif term.startswith("PSNR = ") and psnr is None:
                    psnr=float(term.split("PSNR = ")[1].split("dB")[0])
            cr=32/br
            print(f"{rel_eb} {cr} {br} {psnr} {compress_time} {decompress_time}")
            add_csv("sperr",f"{data_path}.csv",rel_eb,br,psnr)

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32"
# data_shape=[1024,1024,1024] #4096MB
# rel_eb_list=[1e-4,1e-5,1e-6,1e-7,1e-8]