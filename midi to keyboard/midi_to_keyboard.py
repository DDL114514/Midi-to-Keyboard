# -*- coding: gb2312 -*-
import mido
from pynput.keyboard import Controller
from pynput import keyboard  # �޸ĵ��뷽ʽ
import time
from colorama import init, Fore
import json
import os
from pynput.keyboard import Key
import threading
from queue import Queue

# ��ʼ��colorama
init()

# ���������ļ�
# ���ļ��������
import sys
import os

def load_config():
    # ��ȡ��ǰ��ִ���ļ�����Ŀ¼
    if getattr(sys, 'frozen', False):
        # ���������
        base_path = os.path.dirname(sys.executable)
    else:
        # ����ʱ�����
        base_path = os.path.dirname(__file__)
    
    config_path = os.path.join(base_path, "config.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"δ�ҵ������ļ�: {config_path}����ȷ��config.json�������ͬһĿ¼��")
    
    with open(config_path, 'r', encoding='gb2312') as f:
        return json.load(f)

config = load_config()
NOTE_TO_KEY = config["key_mappings"]
CONTROL_KEYS = config["control_keys"]

import threading
from queue import Queue

# ȫ�ֿ��Ʊ���
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
                    log("��ʼ����...")
                else:
                    paused = not paused
                    log("����ͣ" if paused else "�Ѽ���")
            elif key_char == CONTROL_KEYS["stop"]:
                should_stop = True
                log("ֹͣ����...")
                return False
            elif key_char == CONTROL_KEYS["restart"]:
                should_restart = True
                restart_requested = True
                log("���¿�ʼ����...")
                return False
            elif key_char == CONTROL_KEYS["speed_down"]:
                speed_factor = max(0.1, speed_factor * 0.9)
                log(f"�ٶȼ���({get_key_display(',')}): {speed_factor:.1f}x (ʵ���ٶ�: {BASE_SPEED * speed_factor:.1f}x)")
            elif key_char == CONTROL_KEYS["speed_up"]:
                speed_factor = min(10, speed_factor * 1.1)
                log(f"�ٶȼӿ�({get_key_display('.')}): {speed_factor:.1f}x (ʵ���ٶ�: {BASE_SPEED * speed_factor:.1f}x)")
                
        except Exception as e:
            log(f"�����������: {e}")

    while True:
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        
        log("����P����ʼ����...")
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
                    log(f"[{elapsed:.2f}s] ����: {key if key else '��ӳ��'} (��Ӧ����: {note_name})")
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_notes:
                        key, press_time = active_notes.pop(msg.note)
                        if key:
                            keyboard_ctrl.release(key)
                        elapsed = time.time() - start_time
                        log(f"[{elapsed:.2f}s] �ͷ�: {key if key else '��ӳ��'} (ʱ��: {time.time()-press_time:.2f}s)")
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
                    log(f"[{elapsed:.2f}s] ����: {key if key else '��ӳ��'} (��Ӧ����: {note_name})")
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_notes:
                        key, press_time = active_notes.pop(msg.note)
                        if key:
                            keyboard_ctrl.release(key)
                        elapsed = time.time() - start_time
                        log(f"[{elapsed:.2f}s] �ͷ�: {key if key else '��ӳ��'} (ʱ��: {time.time()-press_time:.2f}s)")

        if not should_restart:
            break

    if restart_requested:
        midi_to_keyboard(midi_file_path, track_num, output_queue)

def get_note_name(note_number):
    """
    ��MIDI�������ת��Ϊ��������
    :param note_number: MIDI�������(0-127)
    :return: ��������(��"C4")
    """
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = note_number // 12 - 1
    note = notes[note_number % 12]
    return f"{note}{octave}"
# ���ļ��������
__all__ = ['midi_to_keyboard', 'CONTROL_KEYS', 'show_track_info']

def show_track_info(midi_file_path):
    """
    ��ʾMIDI�ļ������Ϣ
    :param midi_file_path: MIDI�ļ�·��
    """
    midi_file = mido.MidiFile(midi_file_path)
    print(f"\nMIDI�ļ� '{midi_file_path}' ���� {len(midi_file.tracks)} �����:")
    
    all_unmapped_notes = set()  # �洢����δӳ�������
    
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
        
        print(f"\n��� {i}:")
        print(f"  �������¼�: {note_count}")
        print(f"  ��ӳ�䰴��: {mapped_count}")
        print(f"  δӳ�䰴��: {unmapped_count}")
        
        if track_unmapped:
            print(f"  δӳ������: {', '.join(sorted(track_unmapped))}")
    
    # ��ʾ����δӳ�������
    if all_unmapped_notes:
        print("\n=== ȫ��δӳ������ ===")
        print(", ".join(sorted(all_unmapped_notes)))

if __name__ == "__main__":
    import sys
    import re
    
    # �����봦��
    if len(sys.argv) == 1:
        # �޲���ʱ��ʾ����
        print("ʹ�÷���:")
        print("midi_to_keyboard <MIDI�ļ�> [������] - ����MIDI")
        print("midi_to_keyboard --info <MIDI�ļ�> - �鿴�����Ϣ")
        
        # ��ӽ���ʽ����
        while True:
            try:
                midi_file = input("������MIDI�ļ�·��(ֱ���Ϸ��ļ�������): ").strip()
                # ��ȡʵ��·�� - ����Windows��ק�������ʽ
                if midi_file.startswith('& '):
                    midi_file = midi_file[2:]  # �Ƴ���ͷ��'& '
                midi_file = midi_file.strip('\'"')  # �Ƴ�����
                if os.path.exists(midi_file):
                    break
                print(f"�ļ�������: {midi_file}��������")
            except Exception as e:
                print(f"�������: {e}")
        
        mode = input("����ģʽ(1=����, 2=�鿴��Ϣ): ")
        
        try:
            if mode == "1":
                track_num = input("���������(�����򲥷�ȫ��): ")
                track_num = int(track_num) if track_num else None
                midi_to_keyboard(midi_file, track_num)
            elif mode == "2":
                show_track_info(midi_file)
            else:
                print("��Чģʽѡ��")
        except Exception as e:
            print(f"��������: {e}")
            print("�����ļ�·���Ƿ���ȷ")
    else:
        # ����ԭ�������в�������
        if sys.argv[1] == '--info':
            show_track_info(sys.argv[2])
        else:
            track_num = int(sys.argv[2]) if len(sys.argv) > 2 else None
            midi_to_keyboard(sys.argv[1], track_num)
