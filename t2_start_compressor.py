import os,subprocess,sys

redbegin="\033[91m"
redend="\033[0m"
silent_build=True

def run_command(command,silent=False):
    import pty,errno,shlex
    command_list=shlex.split(command)
    if silent:
        result=subprocess.run(command_list,capture_output=True,text=True,encoding="utf-8")
        if result.returncode!=0:
            print(result.stdout)
            print(result.stderr)
            exit()
        return result.stdout
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
# data_shape=[8,257,4096]
# rel_eb_list=[1e-1,1e-2,1e-3,1e-4,1e-5]

# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin"
# data_shape=[100,500,500]
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# 好，有很多类似数据
# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat_center.bin"
# data_shape=[13,900,1800]
# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat"
# data_shape=[26,1800,3600]
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# 一般
# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32_center.bin"
# data_shape=[256,256,256]
# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32"
# data_shape=[1024,1024,1024]
# rel_eb_list=[1e-4,1e-5,1e-6,1e-7,1e-8]

# 好
data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/SCALE_LETKF/PRES-98x1200x1200.dat_center.bin"
data_shape=[49,600,600]
rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# 好，有4个类似数据
# param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/APSU_TestData_004/APSU_TestData_004.h5.f32_center.bin"
# param.data_shape={205,312,363}
# param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/APSU_TestData_004/APSU_TestData_004.h5.f32"
# param.data_shape={1024,1558,1813}

# 好，有3个类似数据
# param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/E017_CeramicGlass_L2Mq0_060C_att00_001/E017_CeramicGlass_L2Mq0_060C_att00_001_001.h5.f32_center.bin"
# param.data_shape={205,363,312}
# param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/E017_CeramicGlass_L2Mq0_060C_att00_001/E017_CeramicGlass_L2Mq0_060C_att00_001_001.h5.f32"
# param.data_shape={1024,1813,1558}

# 坏
data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/9-ID_CSSI_data/benchmarkdata/Avg_L0470_Double_exp_elong_siemens_1p00sampit_0p05inplane_patch1_of1_part0_001.h5.f32_center.bin"
data_shape=[150,454,390]
rel_eb_list=[1e-1,1e-2,1e-3,1e-4]

# 一般
# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Miranda/density.f32.dat"
# data_shape=[256,384,384]
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

# 略好
# data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/aramco/aramco-snapshot-1800.f32"
# data_shape=[449,449,235]
# rel_eb_list=[1e-2,1e-3,1e-4,1e-5,1e-6]

#asz or sz3 or qoz
compressor="asz"

if compressor=="asz":
    os.makedirs("build",exist_ok=True)
    os.chdir("build")
    run_command(f"cmake -DCODE_NAME=s1_compress -DCMAKE_INSTALL_PREFIX=../install ../c_codes")
    run_command("make install",silent=silent_build)
    os.chdir("..")
    for rel_eb in rel_eb_list:
        command=f"./install/bin/s1_compress -f -i \"{data_path}\" -3 {data_shape[0]} {data_shape[1]} {data_shape[2]} -M REL {rel_eb}"
        result=run_command(command,silent=True)
        command=f"./install/bin/s1_decompress -f -i \"{data_path}\" -3 {data_shape[0]} {data_shape[1]} {data_shape[2]} -M REL {rel_eb}"
        result+=run_command(command,silent=True)
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