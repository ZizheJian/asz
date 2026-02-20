import heapq
import numpy as np
from collections import Counter
from typing import List,Dict
from bitarray import bitarray

# 定义 Huffman 树的节点类
class HuffmanNode:
    def __init__(self,value,freq):
        self.value:int=value  # 整数值
        self.freq:int=freq    # 频率
        self.left:"HuffmanNode"=None    # 左子节点
        self.right:"HuffmanNode"=None   # 右子节点
    
    # 用于堆比较
    def __lt__(self,other):
        return self.freq<other.freq

# 构建 Huffman 树并返回根节点
def build_huffman_tree(freq_dict)->"HuffmanNode":
    heap:List["HuffmanNode"]=[]
    # 将每个整数及其频率加入最小堆
    for value,freq in freq_dict.items():
        heapq.heappush(heap,HuffmanNode(value,freq))
    
    # 合并节点直到只剩一个
    while len(heap)>1:
        left=heapq.heappop(heap)
        right=heapq.heappop(heap)
        parent=HuffmanNode(None,left.freq+right.freq)
        parent.left=left
        parent.right=right
        heapq.heappush(heap,parent)
    
    return heap[0]  # 返回根节点

# 压缩 Huffman 树到 bitarray
def compress_huffman_tree(root:"HuffmanNode",max_num:int,min_num:int)->bitarray:
    compressed=bitarray()
    if -(2**15)<=min_num and max_num<=(2**15-1):
        compressed.extend("00")
        ffff=0xFFFF
        format_string="016b"
    elif -(2**31)<=min_num and max_num<=(2**31-1):
        compressed.extend("01")
        ffff=0xFFFFFFFF
        format_string="032b"
    elif -(2**63)<=min_num and max_num<=(2**63-1):
        compressed.extend("10")
        ffff=0xFFFFFFFFFFFFFFFF
        format_string="064b"
    else:
        raise NotImplementedError("没有写qb超过2^63的情况")
    
    def preorder(node:"HuffmanNode"):
        if node is None:
            return
        if node.value is not None:  # 叶子节点
            compressed.extend(bitarray([1]))  # 1 表示叶子
            value_bits=bitarray(format(node.value&ffff,format_string))
            compressed.extend(value_bits)
        else:  # 内部节点
            compressed.extend(bitarray([0]))  # 0 表示内部节点
            preorder(node.left)
            preorder(node.right)
    
    preorder(root)
    return compressed

# 生成 Huffman 编码表
def build_huffman_codes(root:HuffmanNode,current_code="",codes=None)->Dict[int,str]:
    if codes is None:
        codes:dict[int,str]={}
    
    # 到达叶子节点，记录编码
    if root.value is not None:
        codes[root.value]=current_code or "0"  # 如果只有一个节点，默认给 "0"
        return codes
    
    # 递归遍历左子树（0）和右子树（1）
    if root.left:
        build_huffman_codes(root.left,current_code+"0",codes)
    if root.right:
        build_huffman_codes(root.right,current_code+"1",codes)
    
    return codes

# 编码函数
def huffman_encode(qb:np.ndarray)->bitarray:
    if type(qb) is not np.ndarray:
        raise NotImplementedError("只支持numpy数组")
    if qb.ndim!=1:
        raise NotImplementedError("只支持一维数组")
    if qb.size==0:
        raise NotImplementedError("qb长度为0")
    max_num=max(qb)
    min_num=min(qb)
    freq_dict=Counter(qb)
    root=build_huffman_tree(freq_dict)
    huffman_codes=build_huffman_codes(root)
    
    encoded_tree=compress_huffman_tree(root,max_num,min_num)
    encoded_main=bitarray()
    for num in qb:
        encoded_main.extend(huffman_codes[num])
    encoded_tree_bits=len(encoded_tree)
    encoded_main_bits=len(encoded_main)
    result=bitarray()
    if encoded_tree_bits>0xFFFFFFFF:
        raise NotImplementedError("Huffman树长度超过2^32")
    if encoded_main_bits>0xFFFFFFFF:
        raise NotImplementedError("Huffman编码长度超过2^32")
    result.extend(format(encoded_tree_bits&0xFFFFFFFF,'032b'))
    result.extend(encoded_tree)
    result.extend(format(encoded_main_bits&0xFFFFFFFF,'032b'))
    result.extend(encoded_main)
    return result