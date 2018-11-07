#!/usr/bin/env python
# encoding: utf-8
# https://jingyan.baidu.com/article/cb5d6105c148b9005c2fe00d.html

import cheat_engine
import threading
import os

"""
市场雇佣人数：  0x008E0F38  2Byte
市场第一项资源：0x008e0F4C  2Byte
市场标识： 0x008E0F38 值 0x00xx000000000005 后8Byte 值为 0x0000xx00000000xx 地址以 0x8 结尾

                                                人数
02  00  00  00  00  00  00  00  00  00  00  00  08  00  00  00
00  00  0C  00  05  00  00  00  00  4F  00  00  00  00  00  00
资源
D0  07  D1  07  D2  07  D3  07  D4  07  D5  07  D6  07  D7  07

06  00  00  00  00  00  00  00  00  00  00  00  05  00  00  00
00  00  02  00  00  00  00  00  00  5D  00  00  00  00  00  00
5C  05  08  07  A4  06  A4  06  A4  06  06  07  D1  06  17  07



房屋已住人口：   0x008DF616     0x008DF916      0x008DFA16      0x008DFE16
房屋还能住人口： 0x008DF618
房屋第一项资源： 0x008DF64A
                        已住人口
1B  00  00  00  00  00 |24  00||64  00| 23  00  24  00  00  00
00  00  00  00  00  00  00  00  00  00  00  00  00  01  00  00
00  00  00  00  00  00  00  00  00  00  FF  00  00  00  00  00
                                        资源1
00  00  00  00  00  18  00  00  00  00 |CD  00  00  00  00  00
00  00  00  00  00  00  00  00  00  00| 00  00  00  00  00  00
00  00  00  00  00  00  00  00  00  00  00  00  00  01  00  00


粮仓雇佣人数：  0x008E0EB8
粮仓可容纳量：  0x008E0ECC
粮仓第一项资源：0x008E0ECE  2Byte
粮仓标识： 0x008E0EB8 值 0x00xx000100010006 地址以 0x8 结尾

雇佣人数
06  00| 01  00  01  00  03  00  00  00  00  00  00  00  00  00
                可容纳量 谷     蔬菜    水果
00  00  00  00  58  1B||00  00  00  00  00  00  00  00  00  00
鱼
00  00  00  00  00  00  00  00  00  00  00  00  00  00  00  00
"""

ALL_MARKET_ADDRESSES = []
ALL_GRANARY_ADDRESSES = []
TIMER_INTERVAL = 5

CITY_MONEY_ADDRESS = 0x00505160         # 城市的金钱
PERSON_MONEY_ADDRESS = 0x00509424       # 个人的金钱
RATING_ITEMS = [0x005092DC, 0x005092E0, 0x005092E4, 0x005092E8]     # 四项评比指标： 文化，繁荣，和平，支持度

TIMER = None


def list_market_and_granary(hProcess, sysinfo):
    """
    查找所有的市场与粮仓
    """
    # current_address = sysinfo['start_addr']
    # end_address = sysinfo['end_addr']
    current_address = 0x008d0008
    end_address = 0x009FFFFF

    result = { 'market': [], 'granary': [] }

    debug_addrs = []
    while current_address < end_address:
        addr = current_address
        mem_info = cheat_engine.query_virtual(hProcess, addr)
        if mem_info['protect'] and mem_info['state']:
            try:
                value = cheat_engine.read_process(hProcess, addr, 8)
            except Exception:
                continue

            if addr in debug_addrs:
                print '-----------debug', hex(addr), hex(value)
            if (value & 0xff00ffffffffffff) == 0x0000000100010006:     # 雇佣6人的粮仓
                total_volume = cheat_engine.read_process(hProcess, addr + 0x14, 2)
                value_num = 8
                i = 0
                values = []
                while i < value_num:
                    values.append(cheat_engine.read_process(hProcess, addr + 0x16 + 2 * i , 2))
                    i += 1
                if (sum(values) + total_volume) == 2400:                # 粮仓总容量为 2400
                    result['granary'].append(addr)
            elif (value & 0xff00ffffffffffff) == 0x0000000000000005:    # 雇佣5人的市场
                try:
                    next_value = cheat_engine.read_process(hProcess, addr+8, 8)
                except Exception:
                    continue
                if (next_value & 0xffff000000000000) == 0 and (next_value & 0x0000ff0000000000) != 0:
                    # 最高2个字节为0；再下一个字节不为0
                    print hex(addr), hex(value)
                    result['market'].append(addr)

        current_address += 0x10

    global ALL_MARKET_ADDRESSES
    global ALL_GRANARY_ADDRESSES
    ALL_MARKET_ADDRESSES = result['market']
    ALL_GRANARY_ADDRESSES = result['granary']
    ALL_MARKET_ADDRESSES.sort()
    ALL_GRANARY_ADDRESSES.sort()

    print u'所有市场：', map(lambda x: hex(x), ALL_MARKET_ADDRESSES)
    print u'所有粮仓：', map(lambda x: hex(x), ALL_GRANARY_ADDRESSES)

    return result


def update_market(hProcess, base_addr, sysinfo):
    """
    修改市场8项资源
    """
    i = 0

    mem_info = cheat_engine.query_virtual(hProcess, base_addr)
    if not mem_info:
        os._exit(1)

    while i < 8:
        addr = base_addr + (i * 2)
        if addr < sysinfo['start_addr'] or addr >= sysinfo['end_addr']:
            print hex(addr), u'超出内存范围'
            return


        if mem_info['protect'] and mem_info['state']:
            cheat_engine.write_process(hProcess, addr, 9000 + i, 2)

        i += 1


def update_granary(hProcess, base_addr, sysinfo):
    """
    修改粮仓4项资源
    """
    addr = base_addr
    if addr < sysinfo['start_addr'] or addr >= sysinfo['end_addr']:
        print hex(addr), u'超出内存范围'
        return

    mem_info = cheat_engine.query_virtual(hProcess, addr)
    if not mem_info:
        os._exit(1)
    cheat_engine.write_process(hProcess, addr+0, 50, 2)
    # cheat_engine.write_process(hProcess, addr+2, 50, 2)
    # cheat_engine.write_process(hProcess, addr+4, 50, 2)
    # cheat_engine.write_process(hProcess, addr+10, 50, 2)


def freeze_mem(hProcess, info):
    """
    锁定内存：定时修改内存的值
    """
    # print 'freeze_mem......'
    for addr in ALL_MARKET_ADDRESSES:
        update_market(hProcess, addr+0x14, info)

    # for addr in ALL_GRANARY_ADDRESSES:
        # update_granary(hProcess, addr+0x16, info)

    TIMER = threading.Timer(TIMER_INTERVAL, freeze_mem, [hProcess, info])
    TIMER.start()


def print_help():
    print 'c - Clear'
    print 'q - Quit'
    print 's - Scan'
    print 'h - Help'


def main():
    # 获取凯撒大帝3的游戏进程
    processes = cheat_engine.list_process()
    pid = processes.get('c3.exe')

    if not pid:
        print u'游戏没有启动'
        os._exit(1)

    info = cheat_engine.get_system_info()
    if not info:
        return

    print u'当前游戏进程：', pid

    hProcess = cheat_engine.inject_process(pid)
    if not hProcess:
        return

    TIMER = threading.Timer(TIMER_INTERVAL, freeze_mem, [hProcess, info])
    TIMER.start()

    global ALL_MARKET_ADDRESSES
    global ALL_GRANARY_ADDRESSES

    print_help()
    while True:
        print(u'请输入指令：')
        op = raw_input()
        if op == 'q':
            cheat_engine.close_process(hProcess)
            os._exit(1)
        elif op == 'c':
            ALL_MARKET_ADDRESSES = []
            ALL_GRANARY_ADDRESSES = []
        elif op == 's':
            list_market_and_granary(hProcess, info)
        elif op == 'h':
            print_help()

    cheat_engine.close_process(hProcess)


if __name__ == '__main__':
    main()
