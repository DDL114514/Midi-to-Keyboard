# -*- coding: gb2312 -*-
import mido
from pynput.keyboard import Controller
from pynput import keyboard  # 修改导入方式
import time
from colorama import init, Fore
import json
import os
from pynput.keyboard import Key
import threading
from queue import Queue

# 初始化colorama
init()

# 加载配置文件
# 在文件顶部添加
import sys
import os

def load_config():
    # 获取当前可执行文件所在目录
    if getattr(sys, 'frozen', False):
        # 打包后的情况
        base_path = os.path.dirname(sys.executable)
    else:
        # 开发时的情况
        base_path = os.path.dirname(__file__)
    
    config_path = os.path.join(base_path, "config.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"未找到配置文件: {config_path}，请确保config.json与程序在同一目录下")
    
    with open(config_path, 'r', encoding='gb2312') as f:
        return json.load(f)

config = load_config()
NOTE_TO_KEY = config["key_mappings"]
CONTROL_KEYS = config["control_keys"]

import threading
from queue import Queue

# 全局控制变量
global_control = {
    'paused': False,
    'stopped': False,
    'speed_factor': 1.0
}

def midi_to_keyboard(midi_file_path, track_num=None, output_queue=None):
    keyboard_ctrl = Controller()
    start_playing = False
    paused = False
    should_stop = False
    should_restart = False
    restart_requested = False
    
    BASE_SPEED = 1.0/6
    speed_factor = 1.0

    def log(message):
        print(message)
        if output_queue:
            output_queue.put(message)

    def get_key_display(key):
        return config.get('key_display', {}).get(key, key)
    
    def on_press(key):
        nonlocal start_playing, paused, should_stop, should_restart, speed_factor, restart_requested
        try:
            key_char = key.char.lower() if hasattr(key, 'char') and key.char else None
            
            if key_char == CONTROL_KEYS["pause"]:
                if not start_playing:
                    start_playing = True
                    log("开始播放...")
                else:
                    paused = not paused
                    log("已暂停" if paused else "已继续")
            elif key_char == CONTROL_KEYS["stop"]:
                should_stop = True
                log("停止播放...")
                return False
            elif key_char == CONTROL_KEYS["restart"]:
                should_restart = True
                restart_requested = True
                log("重新开始播放...")
                return False
            elif key_char == CONTROL_KEYS["speed_down"]:
                speed_factor = max(0.1, speed_factor * 0.9)
                log(f"速度减慢({get_key_display(',')}): {speed_factor:.1f}x (实际速度: {BASE_SPEED * speed_factor:.1f}x)")
            elif key_char == CONTROL_KEYS["speed_up"]:
                speed_factor = min(10, speed_factor * 1.1)
                log(f"速度加快({get_key_display('.')}): {speed_factor:.1f}x (实际速度: {BASE_SPEED * speed_factor:.1f}x)")
                
        except Exception as e:
            log(f"按键处理错误: {e}")

    while True:
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        
        log("按下P键开始播放...")
        while not start_playing:
            if should_stop:
                listener.stop()
                return
            time.sleep(0.1)
        
        midi_file = mido.MidiFile(midi_file_path)
        start_time = time.time()
        active_notes = {}
        
        if track_num is None:
            messages = []
            for track in midi_file.tracks:
                current_time = 0
                for msg in track:
                    if hasattr(msg, 'time'):
                        current_time += msg.time
                        messages.append((current_time, msg))
            
            messages.sort(key=lambda x: x[0])
            last_time = 0
            
            for current_time, msg in messages:
                if should_stop:
                    listener.stop()
                    return
                if should_restart:
                    should_restart = False
                    break
                    
                while paused:
                    if should_stop:
                        listener.stop()
                        return
                    time.sleep(0.1)
                
                time_diff = (current_time - last_time) / 1000 * (1/(BASE_SPEED * speed_factor))
                if time_diff > 0:
                    time.sleep(time_diff)
                last_time = current_time
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    note_name = get_note_name(msg.note)
                    key = NOTE_TO_KEY.get(note_name, None)
                    if key:
                        keyboard_ctrl.press(key)
                        active_notes[msg.note] = (key, time.time())
                    elapsed = time.time() - start_time
                    log(f"[{elapsed:.2f}s] 按下: {key if key else '无映射'} (对应音符: {note_name})")
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_notes:
                        key, press_time = active_notes.pop(msg.note)
                        if key:
                            keyboard_ctrl.release(key)
                        elapsed = time.time() - start_time
                        log(f"[{elapsed:.2f}s] 释放: {key if key else '无映射'} (时长: {time.time()-press_time:.2f}s)")
        else:
            track = midi_file.tracks[track_num]
            for msg in track:
                if should_stop:
                    listener.stop()
                    return
                if should_restart:
                    should_restart = False
                    break
                    
                while paused:
                    if should_stop:
                        listener.stop()
                        return
                    time.sleep(0.1)
                    
                if hasattr(msg, 'time'):
                    time.sleep(msg.time / 1000 * (1/(BASE_SPEED * speed_factor)))
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    note_name = get_note_name(msg.note)
                    key = NOTE_TO_KEY.get(note_name, None)
                    if key:
                        keyboard_ctrl.press(key)
                        active_notes[msg.note] = (key, time.time())
                    elapsed = time.time() - start_time
                    log(f"[{elapsed:.2f}s] 按下: {key if key else '无映射'} (对应音符: {note_name})")
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_notes:
                        key, press_time = active_notes.pop(msg.note)
                        if key:
                            keyboard_ctrl.release(key)
                        elapsed = time.time() - start_time
                        log(f"[{elapsed:.2f}s] 释放: {key if key else '无映射'} (时长: {time.time()-press_time:.2f}s)")

        if not should_restart:
            break

    if restart_requested:
        midi_to_keyboard(midi_file_path, track_num, output_queue)

def get_note_name(note_number):
    """
    将MIDI音符编号转换为音符名称
    :param note_number: MIDI音符编号(0-127)
    :return: 音符名称(如"C4")
    """
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = note_number // 12 - 1
    note = notes[note_number % 12]
    return f"{note}{octave}"
# 在文件顶部添加
__all__ = ['midi_to_keyboard', 'CONTROL_KEYS', 'show_track_info']

def show_track_info(midi_file_path):
    """
    显示MIDI文件轨道信息
    :param midi_file_path: MIDI文件路径
    """
    midi_file = mido.MidiFile(midi_file_path)
    print(f"\nMIDI文件 '{midi_file_path}' 包含 {len(midi_file.tracks)} 个轨道:")
    
    all_unmapped_notes = set()  # 存储所有未映射的音符
    
    for i, track in enumerate(midi_file.tracks):
        note_count = mapped_count = unmapped_count = 0
        track_unmapped = set()
        
        for msg in track:
            if msg.type == 'note_on':
                note_count += 1
                note_name = get_note_name(msg.note)
                if NOTE_TO_KEY.get(note_name):
                    mapped_count += 1
                else:
                    unmapped_count += 1
                    track_unmapped.add(note_name)
                    all_unmapped_notes.add(note_name)
        
        print(f"\n轨道 {i}:")
        print(f"  总音符事件: {note_count}")
        print(f"  已映射按键: {mapped_count}")
        print(f"  未映射按键: {unmapped_count}")
        
        if track_unmapped:
            print(f"  未映射音高: {', '.join(sorted(track_unmapped))}")
    
    # 显示所有未映射的音高
    if all_unmapped_notes:
        print("\n=== 全局未映射音高 ===")
        print(", ".join(sorted(all_unmapped_notes)))

if __name__ == "__main__":
    import sys
    import re
    
    # 简化输入处理
    if len(sys.argv) == 1:
        # 无参数时显示帮助
        print("使用方法:")
        print("midi_to_keyboard <MIDI文件> [轨道编号] - 播放MIDI")
        print("midi_to_keyboard --info <MIDI文件> - 查看轨道信息")
        
        # 添加交互式输入
        while True:
            try:
                midi_file = input("请输入MIDI文件路径(直接拖放文件到窗口): ").strip()
                # 提取实际路径 - 处理Windows拖拽的特殊格式
                if midi_file.startswith('& '):
                    midi_file = midi_file[2:]  # 移除开头的'& '
                midi_file = midi_file.strip('\'"')  # 移除引号
                if os.path.exists(midi_file):
                    break
                print(f"文件不存在: {midi_file}，请重试")
            except Exception as e:
                print(f"输入错误: {e}")
        
        mode = input("输入模式(1=播放, 2=查看信息): ")
        
        try:
            if mode == "1":
                track_num = input("输入轨道编号(留空则播放全部): ")
                track_num = int(track_num) if track_num else None
                midi_to_keyboard(midi_file, track_num)
            elif mode == "2":
                show_track_info(midi_file)
            else:
                print("无效模式选择")
        except Exception as e:
            print(f"发生错误: {e}")
            print("请检查文件路径是否正确")
    else:
        # 保留原有命令行参数处理
        if sys.argv[1] == '--info':
            show_track_info(sys.argv[2])
        else:
            track_num = int(sys.argv[2]) if len(sys.argv) > 2 else None
            midi_to_keyboard(sys.argv[1], track_num)
