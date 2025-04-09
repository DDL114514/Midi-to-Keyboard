# -*- coding: gb2312 -*-
import os
import sys

# ��ȡ��ǰ����Ŀ¼��Ϊ·��
current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

block_cipher = None

a = Analysis(
    ['run_gui.py'],
    pathex=[current_dir],  # ʹ�ü���õ���·��
    binaries=[],
    datas=[],  # ȷ�������config.json
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['config.json', 'sample.mid'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='midi_to_keyboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # �൱��--noconsole
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # ���������������
    onefile=True,  # �൱��--onefile
    icon=None,  # �������ͼ��·��
)