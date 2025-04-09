# -*- coding: gb2312 -*-
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import queue
from midi_to_keyboard import midi_to_keyboard, CONTROL_KEYS, show_track_info  # 添加show_track_info导入

class MidiPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDI映射键盘脚本 By DDL")
        self.output_queue = queue.Queue()
        self.setup_ui()
        self.update_output()
        
    def setup_ui(self):
        # 快捷键提示区域
        shortcut_frame = ttk.LabelFrame(self.root, text="快捷键")
        shortcut_frame.pack(padx=10, pady=5, fill=tk.X)
        
        # 从配置文件加载按键显示映射
        from midi_to_keyboard import config
        key_display = config.get('key_display', {})
        
        shortcuts = [
            f"开始/暂停: {CONTROL_KEYS['pause']}",
            f"停止: {CONTROL_KEYS['stop']}",
            f"重新开始: {CONTROL_KEYS['restart']}",
            f"减速: {key_display.get(CONTROL_KEYS['speed_down'], CONTROL_KEYS['speed_down'])}",
            f"加速: {key_display.get(CONTROL_KEYS['speed_up'], CONTROL_KEYS['speed_up'])}"
        ]
        ttk.Label(shortcut_frame, text=" | ".join(shortcuts)).pack()

        # 文件选择区域
        file_frame = ttk.LabelFrame(self.root, text="MIDI文件")
        file_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_file).pack(side=tk.RIGHT, padx=5)
        ttk.Button(file_frame, text="查询midi信息", command=self.query_midi_info).pack(side=tk.RIGHT, padx=5)

        # 轨道选择区域
        track_frame = ttk.LabelFrame(self.root, text="轨道选择")
        track_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.track_var = tk.StringVar(value="全部轨道")
        ttk.Label(track_frame, text="选择轨道:").pack(side=tk.LEFT, padx=5)
        self.track_combobox = ttk.Combobox(track_frame, textvariable=self.track_var, state="readonly")
        self.track_combobox.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # 速度显示区域
        speed_frame = ttk.LabelFrame(self.root, text="当前速度")
        speed_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.pack()

        # 输出显示区域
        output_frame = ttk.LabelFrame(self.root, text="播放输出")
        output_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 开始按钮
        start_frame = ttk.Frame(self.root)
        start_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.start_btn = ttk.Button(start_frame, text="开始程序", command=self.start_playback)
        self.start_btn.pack(fill=tk.X)
        
        # 删除文件末尾重复的轨道选择区域定义
    def browse_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("MIDI文件", "*.mid *.midi")])
        if filepath:
            self.file_path.set(filepath)
            # 自动更新轨道列表
            self.update_track_list()
    def start_playback(self):
        filepath = self.file_path.get()
        if not filepath:
            self.append_output("请先选择MIDI文件")
            return
            
        # 获取选择的轨道
        track_selection = self.track_var.get()
        track_num = None if track_selection == "全部轨道" else int(track_selection.split()[-1])
            
        self.start_btn.config(state=tk.DISABLED)
        
        # 在新线程中运行MIDI播放
        threading.Thread(
            target=self.run_midi_playback,
            args=(filepath, track_num),  # 传入轨道编号
            daemon=True
        ).start()
        
    def run_midi_playback(self, filepath, track_num=None):
        try:
            midi_to_keyboard(filepath, track_num=track_num, output_queue=self.output_queue)
        except Exception as e:
            self.output_queue.put(f"播放错误: {str(e)}")
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
            
            # 更新速度显示
            if "速度" in text:
                self.speed_label.config(text=text.split(":")[1].strip())
                
        self.root.after(100, self.update_output)

    def query_midi_info(self):
        """查询MIDI文件信息"""
        filepath = self.file_path.get()
        if not filepath:
            self.append_output("请先选择MIDI文件")
            return
            
        try:
            # 重定向标准输出以捕获信息
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()
            
            from midi_to_keyboard import show_track_info
            show_track_info(filepath)
            
            sys.stdout = old_stdout
            output = mystdout.getvalue()
            
            # 显示在GUI中
            self.append_output(output)
            
        except Exception as e:
            self.append_output(f"查询错误: {str(e)}")

    def update_track_list(self):
        filepath = self.file_path.get()
        if not filepath:
            self.append_output("请先选择MIDI文件")
            return
            
        try:
            # 重定向标准输出以捕获轨道信息
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()
            
            show_track_info(filepath)  # 调用后端方法
            
            sys.stdout = old_stdout
            output = mystdout.getvalue()
            
            # 解析轨道数量
            import re
            track_count = len(re.findall(r'轨道 \d+:', output))
            tracks = ["全部轨道"] + [f"轨道 {i}" for i in range(track_count)]
            self.track_combobox['values'] = tracks
            self.append_output(f"已加载 {track_count} 个轨道")
        except Exception as e:
            self.append_output(f"更新轨道列表错误: {str(e)}")
