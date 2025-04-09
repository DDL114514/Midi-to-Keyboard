# -*- coding: gb2312 -*-
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import queue
from midi_to_keyboard import midi_to_keyboard, CONTROL_KEYS, show_track_info  # ���show_track_info����

class MidiPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDIӳ����̽ű� By DDL")
        self.output_queue = queue.Queue()
        self.setup_ui()
        self.update_output()
        
    def setup_ui(self):
        # ��ݼ���ʾ����
        shortcut_frame = ttk.LabelFrame(self.root, text="��ݼ�")
        shortcut_frame.pack(padx=10, pady=5, fill=tk.X)
        
        # �������ļ����ذ�����ʾӳ��
        from midi_to_keyboard import config
        key_display = config.get('key_display', {})
        
        shortcuts = [
            f"��ʼ/��ͣ: {CONTROL_KEYS['pause']}",
            f"ֹͣ: {CONTROL_KEYS['stop']}",
            f"���¿�ʼ: {CONTROL_KEYS['restart']}",
            f"����: {key_display.get(CONTROL_KEYS['speed_down'], CONTROL_KEYS['speed_down'])}",
            f"����: {key_display.get(CONTROL_KEYS['speed_up'], CONTROL_KEYS['speed_up'])}"
        ]
        ttk.Label(shortcut_frame, text=" | ".join(shortcuts)).pack()

        # �ļ�ѡ������
        file_frame = ttk.LabelFrame(self.root, text="MIDI�ļ�")
        file_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(file_frame, text="���", command=self.browse_file).pack(side=tk.RIGHT, padx=5)
        ttk.Button(file_frame, text="��ѯmidi��Ϣ", command=self.query_midi_info).pack(side=tk.RIGHT, padx=5)

        # ���ѡ�������ƶ����ٶ������Ϸ���
        track_frame = ttk.LabelFrame(self.root, text="���ѡ��")
        track_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.track_var = tk.StringVar(value="ȫ�����")
        ttk.Label(track_frame, text="ѡ����:").pack(side=tk.LEFT, padx=5)
        self.track_combobox = ttk.Combobox(track_frame, textvariable=self.track_var, state="readonly")
        self.track_combobox.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # �ٶ���ʾ����
        speed_frame = ttk.LabelFrame(self.root, text="��ǰ�ٶ�")
        speed_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.pack()

        # �����ʾ����
        output_frame = ttk.LabelFrame(self.root, text="�������")
        output_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ��ʼ��ť
        start_frame = ttk.Frame(self.root)
        start_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.start_btn = ttk.Button(start_frame, text="��ʼ����", command=self.start_playback)
        self.start_btn.pack(fill=tk.X)
        
        # ɾ���ļ�ĩβ�ظ��Ĺ��ѡ��������
    def browse_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("MIDI�ļ�", "*.mid *.midi")])
        if filepath:
            self.file_path.set(filepath)
            # �Զ����¹���б�
            self.update_track_list()
    def start_playback(self):
        filepath = self.file_path.get()
        if not filepath:
            self.append_output("����ѡ��MIDI�ļ�")
            return
            
        # ��ȡѡ��Ĺ��
        track_selection = self.track_var.get()
        track_num = None if track_selection == "ȫ�����" else int(track_selection.split()[-1])
            
        self.start_btn.config(state=tk.DISABLED)
        
        # �����߳�������MIDI����
        threading.Thread(
            target=self.run_midi_playback,
            args=(filepath, track_num),  # ���������
            daemon=True
        ).start()
        
    def run_midi_playback(self, filepath, track_num=None):
        try:
            midi_to_keyboard(filepath, track_num=track_num, output_queue=self.output_queue)
        except Exception as e:
            self.output_queue.put(f"���Ŵ���: {str(e)}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            
    def append_output(self, text):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
        
    def update_output(self):
        while not self.output_queue.empty():
            text = self.output_queue.get_nowait()
            self.append_output(text)
            
            # �����ٶ���ʾ
            if "�ٶ�" in text:
                self.speed_label.config(text=text.split(":")[1].strip())
                
        self.root.after(100, self.update_output)

    def query_midi_info(self):
        """��ѯMIDI�ļ���Ϣ"""
        filepath = self.file_path.get()
        if not filepath:
            self.append_output("����ѡ��MIDI�ļ�")
            return
            
        try:
            # �ض����׼����Բ�����Ϣ
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()
            
            from midi_to_keyboard import show_track_info
            show_track_info(filepath)
            
            sys.stdout = old_stdout
            output = mystdout.getvalue()
            
            # ��ʾ��GUI��
            self.append_output(output)
            
        except Exception as e:
            self.append_output(f"��ѯ����: {str(e)}")

    def update_track_list(self):
        filepath = self.file_path.get()
        if not filepath:
            self.append_output("����ѡ��MIDI�ļ�")
            return
            
        try:
            # �ض����׼����Բ�������Ϣ
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()
            
            show_track_info(filepath)  # ���ú�˷���
            
            sys.stdout = old_stdout
            output = mystdout.getvalue()
            
            # �����������
            import re
            track_count = len(re.findall(r'��� \d+:', output))
            tracks = ["ȫ�����"] + [f"��� {i}" for i in range(track_count)]
            self.track_combobox['values'] = tracks
            self.append_output(f"�Ѽ��� {track_count} �����")
        except Exception as e:
            self.append_output(f"���¹���б����: {str(e)}")