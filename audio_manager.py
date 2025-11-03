import os
import shutil
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

class AudioManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Audio File Manager")
        self.root.geometry("1000x1000")
        self.root.configure(bg='#2d2d2d')
        
        # สี theme เทา-ส้ม
        self.colors = {
            'bg': '#2d2d2d',
            'card': '#3d3d3d',
            'primary': '#ff6b35',
            'secondary': '#ff8c42',
            'text': '#ffffff',
            'text_secondary': '#cccccc',
            'accent': '#4a9eff'
        }
        
        # ตัวแปรสำหรับโหมดจัดระเบียบ
        self.selected_files = []
        self.preview_data = {}
        self.organized_base_dir = None  # เก็บตำแหน่งที่จัดระเบียบ
        
        # ตัวแปรสำหรับโหมดรวมเสียง
        self.selected_folders = []
        self.merge_preview_data = {}
        self.merged_files = []  # เก็บไฟล์ที่รวมแล้ว
        self.folder_cache = {}  # แคชข้อมูลโฟลเดอร์
        
        # ตัวแปรสำหรับโหมดลูปเสียง
        self.loop_files = []  # เก็บไฟล์เสียงที่จะนำมาลูป
        self.loop_preview_data = {}
        self.looped_files = []  # เก็บไฟล์ที่ลูปแล้ว
        
        # เก็บ path ของโฟลเดอร์ที่จัดระเบียบไว้
        self.organized_base_dir = None
        
        self.current_mode = 'organize'
        self.setup_ui()
        
    def setup_ui(self):
        # หัวข้อ
        title_frame = tk.Frame(self.root, bg=self.colors['bg'], pady=15)
        title_frame.pack(fill='x')
        
        title_label = tk.Label(
            title_frame,
            text="🎵 Audio File Manager",
            font=('Segoe UI', 20, 'bold'),
            fg=self.colors['primary'],
            bg=self.colors['bg']
        )
        title_label.pack()
        
        # แท็บสลับโหมด
        mode_frame = tk.Frame(title_frame, bg=self.colors['bg'])
        mode_frame.pack(pady=(10, 0))
        
        self.organize_mode_btn = tk.Button(
            mode_frame,
            text="📁 จัดระเบียบไฟล์",
            command=self.switch_to_organize,
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        self.organize_mode_btn.pack(side='left', padx=(0, 10))
        
        self.merge_mode_btn = tk.Button(
            mode_frame,
            text="🎧 รวมไฟล์เสียง",
            command=self.switch_to_merge,
            bg='#666666',
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        self.merge_mode_btn.pack(side='left', padx=(0, 10))
        
        self.loop_mode_btn = tk.Button(
            mode_frame,
            text="🔄 ลูปเสียง",
            command=self.switch_to_loop,
            bg='#666666',
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        self.loop_mode_btn.pack(side='left')
        
        # พื้นที่เนื้อหา
        self.content_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.content_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # สร้าง UI สำหรับแต่ละโหมด
        self.setup_organize_ui()
        self.setup_merge_ui()
        self.setup_loop_ui()
        
        # แสดงโหมดจัดระเบียบเป็นค่าเริ่มต้น
        self.switch_to_organize()
        
    def setup_organize_ui(self):
        # Frame สำหรับโหมดจัดระเบียบ
        self.organize_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        
        # ส่วนซ้าย - เลือกไฟล์
        left_frame = tk.Frame(self.organize_frame, bg=self.colors['card'], padx=20, pady=20)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # เลือกไฟล์
        files_label = tk.Label(
            left_frame,
            text="📂 เลือกไฟล์เสียง:",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        files_label.pack(anchor='w', pady=(0, 10))
        
        files_frame = tk.Frame(left_frame, bg=self.colors['card'])
        files_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Listbox พร้อม scrollbar
        listbox_frame = tk.Frame(files_frame, bg=self.colors['card'])
        listbox_frame.pack(fill='both', expand=True, side='left')
        
        self.files_listbox = tk.Listbox(
            listbox_frame,
            font=('Segoe UI', 9),
            bg='#4d4d4d',
            fg=self.colors['text'],
            bd=0,
            selectbackground=self.colors['primary'],
            activestyle='none'
        )
        
        files_scrollbar = ttk.Scrollbar(listbox_frame, orient='vertical')
        files_scrollbar.pack(side='right', fill='y')
        self.files_listbox.config(yscrollcommand=files_scrollbar.set)
        files_scrollbar.config(command=self.files_listbox.yview)
        self.files_listbox.pack(side='left', fill='both', expand=True)
        
        # ปุ่มควบคุม
        button_frame = tk.Frame(files_frame, bg=self.colors['card'])
        button_frame.pack(side='right', fill='y', padx=(10, 0))
        
        browse_btn = tk.Button(
            button_frame,
            text="📁 เลือกไฟล์",
            command=self.browse_files,
            bg=self.colors['secondary'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=15,
            pady=10,
            cursor='hand2'
        )
        browse_btn.pack(fill='x', pady=(0, 5))
        
        preview_btn = tk.Button(
            button_frame,
            text="👁️ ดูตัวอย่าง",
            command=self.generate_preview,
            bg=self.colors['accent'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=15,
            pady=10,
            cursor='hand2'
        )
        preview_btn.pack(fill='x', pady=(0, 5))
        
        clear_btn = tk.Button(
            button_frame,
            text="🗑️ ล้างรายการ",
            command=self.clear_files,
            bg='#666666',
            fg='white',
            font=('Segoe UI', 9),
            bd=0,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        clear_btn.pack(fill='x')
        
        # ส่วนขวา - แสดง Preview
        right_frame = tk.Frame(self.organize_frame, bg=self.colors['card'], padx=20, pady=20)
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        preview_label = tk.Label(
            right_frame,
            text="📋 ตัวอย่างโครงสร้างโฟลเดอร์:",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        preview_label.pack(anchor='w', pady=(0, 10))
        
        # TreeView สำหรับแสดง Preview
        tree_frame = tk.Frame(right_frame, bg=self.colors['card'])
        tree_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # สไตล์ TreeView
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Custom.Treeview", 
                       background='#4d4d4d',
                       foreground=self.colors['text'],
                       fieldbackground='#4d4d4d',
                       borderwidth=0)
        
        style.configure("Custom.Treeview.Heading",
                       background=self.colors['primary'],
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'))
        
        self.preview_tree = ttk.Treeview(
            tree_frame,
            style="Custom.Treeview",
            show='tree headings',
            columns=('count',),
            height=15
        )
        
        self.preview_tree.heading('#0', text='📁 โฟลเดอร์ / 🎵 ไฟล์')
        self.preview_tree.heading('count', text='จำนวน')
        self.preview_tree.column('#0', width=400)
        self.preview_tree.column('count', width=80, anchor='center')
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        tree_scrollbar.pack(side='right', fill='y')
        self.preview_tree.config(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.config(command=self.preview_tree.yview)
        self.preview_tree.pack(side='left', fill='both', expand=True)
        
        # ปุ่มดำเนินการ
        action_frame = tk.Frame(right_frame, bg=self.colors['card'])
        action_frame.pack(fill='x')
        
        
        self.organize_btn = tk.Button(
            action_frame,
            text="🚀 จัดระเบียบไฟล์",
            command=self.start_organize,
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 12, 'bold'),
            bd=0,
            padx=20,
            pady=15,
            cursor='hand2',
            state='disabled'
        )
        self.organize_btn.pack(fill='x', pady=(0, 10))
        
        
        # แถบความคืบหน้า
        self.progress = ttk.Progressbar(
            right_frame,
            style="Custom.Horizontal.TProgressbar"
        )
        
        style.configure(
            "Custom.Horizontal.TProgressbar",
            background=self.colors['primary'],
            troughcolor='#4d4d4d',
            borderwidth=0,
            lightcolor=self.colors['primary'],
            darkcolor=self.colors['primary']
        )
        
        # ข้อความสถานะ
        self.status_label = tk.Label(
            right_frame,
            text="",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        
    def setup_merge_ui(self):
        # Frame สำหรับโหมดรวมเสียง
        self.merge_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        
        # ตรวจสอบ pydub
        if not PYDUB_AVAILABLE:
            warning_frame = tk.Frame(self.merge_frame, bg=self.colors['card'], padx=20, pady=20)
            warning_frame.pack(fill='x', pady=(0, 20))
            
            warning_label = tk.Label(
                warning_frame,
                text="⚠️ ต้องติดตั้ง pydub และ ffmpeg เพื่อใช้ฟีเจอร์รวมเสียง\\n\\nติดตั้ง: pip install pydub",
                font=('Segoe UI', 12, 'bold'),
                fg='#ff6b35',
                bg=self.colors['card'],
                justify='center'
            )
            warning_label.pack()
            return
        
        # ส่วนซ้าย - เลือกโฟลเดอร์
        left_frame = tk.Frame(self.merge_frame, bg=self.colors['card'], padx=20, pady=20)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        folder_label = tk.Label(
            left_frame,
            text="📁 เลือกโฟลเดอร์ที่แยกไฟล์ไว้แล้ว:",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        folder_label.pack(anchor='w', pady=(0, 10))
        
        folder_frame = tk.Frame(left_frame, bg=self.colors['card'])
        folder_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Listbox สำหรับโฟลเดอร์
        listbox_frame = tk.Frame(folder_frame, bg=self.colors['card'])
        listbox_frame.pack(fill='both', expand=True, side='left')
        
        self.folders_listbox = tk.Listbox(
            listbox_frame,
            font=('Segoe UI', 9),
            bg='#4d4d4d',
            fg=self.colors['text'],
            bd=0,
            selectbackground=self.colors['primary'],
            activestyle='none'
        )
        
        folders_scrollbar = ttk.Scrollbar(listbox_frame, orient='vertical')
        folders_scrollbar.pack(side='right', fill='y')
        self.folders_listbox.config(yscrollcommand=folders_scrollbar.set)
        folders_scrollbar.config(command=self.folders_listbox.yview)
        self.folders_listbox.pack(side='left', fill='both', expand=True)
        
        # ปุ่มควบคุม
        folder_button_frame = tk.Frame(folder_frame, bg=self.colors['card'])
        folder_button_frame.pack(side='right', fill='y', padx=(10, 0))
        
        browse_folder_btn = tk.Button(
            folder_button_frame,
            text="📁 เลือกโฟลเดอร์หลัก",
            command=self.browse_parent_folder,
            bg=self.colors['secondary'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=15,
            pady=10,
            cursor='hand2'
        )
        browse_folder_btn.pack(fill='x', pady=(0, 5))
        
        browse_individual_btn = tk.Button(
            folder_button_frame,
            text="📂 เลือกทีละโฟลเดอร์",
            command=self.browse_folders,
            bg='#8c6239',
            fg='white',
            font=('Segoe UI', 9),
            bd=0,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        browse_individual_btn.pack(fill='x', pady=(0, 5))
        
        preview_selected_btn = tk.Button(
            folder_button_frame,
            text="👁️ ดูตัวอย่าง",
            command=self.preview_selected_folder,
            bg='#4a9eff',
            fg='white',
            font=('Segoe UI', 9),
            bd=0,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        preview_selected_btn.pack(fill='x', pady=(0, 5))
        
        preview_merge_btn = tk.Button(
            folder_button_frame,
            text="👁️ ดูตัวอย่างทั้งหมด",
            command=self.generate_merge_preview,
            bg=self.colors['accent'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=15,
            pady=10,
            cursor='hand2'
        )
        preview_merge_btn.pack(fill='x', pady=(0, 5))
        
        clear_folder_btn = tk.Button(
            folder_button_frame,
            text="🗑️ ล้างรายการ",
            command=self.clear_folders,
            bg='#666666',
            fg='white',
            font=('Segoe UI', 9),
            bd=0,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        clear_folder_btn.pack(fill='x')
        
        # ปุ่มโหลดข้อมูลจากโหมดจัดระเบียบ
        import_organized_btn = tk.Button(
            folder_button_frame,
            text="📋 ดึงข้อมูลที่จัดแล้ว",
            command=self.import_organized_data,
            bg='#673AB7',
            fg='white',
            font=('Segoe UI', 8),
            bd=0,
            padx=15,
            pady=6,
            cursor='hand2'
        )
        import_organized_btn.pack(fill='x', pady=(5, 0))
        
        # ส่วนขวา - แสดง Preview การรวมเสียง
        right_frame = tk.Frame(self.merge_frame, bg=self.colors['card'], padx=20, pady=20)
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        merge_preview_label = tk.Label(
            right_frame,
            text="🎧 ตัวอย่างการรวมเสียง:",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        merge_preview_label.pack(anchor='w', pady=(0, 5))
        
        # ปุ่มจัดลำดับ
        order_control_frame = tk.Frame(right_frame, bg=self.colors['card'])
        order_control_frame.pack(fill='x', pady=(0, 10))
        
        order_label = tk.Label(
            order_control_frame,
            text="🔄 จัดลำดับไฟล์:",
            font=('Segoe UI', 9, 'bold'),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        order_label.pack(side='left')
        
        move_up_btn = tk.Button(
            order_control_frame,
            text="⬆️",
            command=self.move_file_up,
            bg='#4CAF50',
            fg='white',
            font=('Segoe UI', 8, 'bold'),
            bd=0,
            width=3,
            height=1,
            cursor='hand2'
        )
        move_up_btn.pack(side='right', padx=(0, 2))
        
        move_down_btn = tk.Button(
            order_control_frame,
            text="⬇️",
            command=self.move_file_down,
            bg='#2196F3',
            fg='white',
            font=('Segoe UI', 8, 'bold'),
            bd=0,
            width=3,
            height=1,
            cursor='hand2'
        )
        move_down_btn.pack(side='right', padx=(0, 2))
        
        reset_order_btn = tk.Button(
            order_control_frame,
            text="🔄",
            command=self.reset_file_order,
            bg='#FF9800',
            fg='white',
            font=('Segoe UI', 8, 'bold'),
            bd=0,
            width=3,
            height=1,
            cursor='hand2'
        )
        reset_order_btn.pack(side='right')
        
        # TreeView สำหรับแสดง Preview การรวม
        merge_tree_frame = tk.Frame(right_frame, bg=self.colors['card'])
        merge_tree_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        self.merge_preview_tree = ttk.Treeview(
            merge_tree_frame,
            style="Custom.Treeview",
            show='tree headings',
            columns=('count', 'duration'),
            height=15
        )
        
        self.merge_preview_tree.heading('#0', text='📁 โฟลเดอร์ / 🎵 ไฟล์')
        self.merge_preview_tree.heading('count', text='จำนวน')
        self.merge_preview_tree.heading('duration', text='ระยะเวลา')
        self.merge_preview_tree.column('#0', width=300)
        self.merge_preview_tree.column('count', width=70, anchor='center')
        self.merge_preview_tree.column('duration', width=80, anchor='center')
        
        merge_tree_scrollbar = ttk.Scrollbar(merge_tree_frame, orient='vertical')
        merge_tree_scrollbar.pack(side='right', fill='y')
        self.merge_preview_tree.config(yscrollcommand=merge_tree_scrollbar.set)
        merge_tree_scrollbar.config(command=self.merge_preview_tree.yview)
        self.merge_preview_tree.pack(side='left', fill='both', expand=True)
        
        # Bind event สำหรับการคลิกบน treeview
        self.merge_preview_tree.bind('<ButtonRelease-1>', self.on_merge_tree_click)
        self.merge_preview_tree.bind('<Double-Button-1>', self.on_merge_tree_double_click)
        self.merge_preview_tree.bind('<Button-3>', self.on_merge_tree_right_click)  # Right click menu
        
        # การตั้งค่าการรวม
        settings_frame = tk.Frame(right_frame, bg=self.colors['card'])
        settings_frame.pack(fill='x', pady=(0, 15))
        
        settings_label = tk.Label(
            settings_frame,
            text="⚙️ การตั้งค่าการรวม:",
            font=('Segoe UI', 10, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        settings_label.pack(anchor='w', pady=(0, 5))
        
        # ตัวเลือกรูปแบบไฟล์ผลลัพธ์
        format_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        format_frame.pack(fill='x', pady=(0, 5))
        
        format_label = tk.Label(
            format_frame,
            text="รูปแบบไฟล์:",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        format_label.pack(side='left')
        
        self.output_format = tk.StringVar(value="wav")
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.output_format,
            values=["mp3", "wav", "flac", "m4a"],
            state="readonly",
            width=10
        )
        format_combo.pack(side='right')
        
        # ตัวเลือกคุณภาพ
        quality_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        quality_frame.pack(fill='x')
        
        quality_label = tk.Label(
            quality_frame,
            text="คุณภาพ (bitrate):",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        quality_label.pack(side='left')
        
        self.bitrate = tk.StringVar(value="320k")
        bitrate_combo = ttk.Combobox(
            quality_frame,
            textvariable=self.bitrate,
            values=["128k", "192k", "256k", "320k"],
            state="readonly",
            width=10
        )
        bitrate_combo.pack(side='right')
        
        # ตัวเลือกบิตเดธ
        bit_depth_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        bit_depth_frame.pack(fill='x', pady=(5, 0))
        
        bit_depth_label = tk.Label(
            bit_depth_frame,
            text="บิตเดธ (bit depth):",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        bit_depth_label.pack(side='left')
        
        self.bit_depth = tk.StringVar(value="24")
        bit_depth_combo = ttk.Combobox(
            bit_depth_frame,
            textvariable=self.bit_depth,
            values=["16", "24", "32"],
            state="readonly",
            width=10
        )
        bit_depth_combo.pack(side='right')
        
        # ตัวเลือกคอสเฟด
        crossfade_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        crossfade_frame.pack(fill='x', pady=(5, 0))
        
        crossfade_label = tk.Label(
            crossfade_frame,
            text="คอสเฟด (วินาที):",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        crossfade_label.pack(side='left')
        
        self.crossfade_duration = tk.StringVar(value="3")
        crossfade_combo = ttk.Combobox(
            crossfade_frame,
            textvariable=self.crossfade_duration,
            values=["0", "1", "2", "3", "4", "5", "10"],
            state="readonly",
            width=10
        )
        crossfade_combo.pack(side='right')
        
        # ปุ่มรวมเสียง
        merge_action_frame = tk.Frame(right_frame, bg=self.colors['card'])
        merge_action_frame.pack(fill='x')
        
        self.merge_btn = tk.Button(
            merge_action_frame,
            text="🎧 รวมไฟล์เสียง",
            command=self.start_merge_only,
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 12, 'bold'),
            bd=0,
            padx=20,
            pady=15,
            cursor='hand2',
            state='disabled'
        )
        self.merge_btn.pack(fill='x', pady=(0, 10))
        
        # ปุ่มโหลดไฟล์
        self.download_btn = tk.Button(
            merge_action_frame,
            text="💾 โหลดไฟล์รวม",
            command=self.download_merged_files,
            bg='#4CAF50',
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=20,
            pady=12,
            cursor='hand2',
            state='disabled'
        )
        self.download_btn.pack(fill='x')
        
        # แถบความคืบหน้าสำหรับรวมเสียง
        self.merge_progress = ttk.Progressbar(
            right_frame,
            style="Custom.Horizontal.TProgressbar"
        )
        
        # ข้อความสถานะสำหรับรวมเสียง
        self.merge_status_label = tk.Label(
            right_frame,
            text="",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
    
    def setup_loop_ui(self):
        # Frame สำหรับโหมดลูปเสียง
        self.loop_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        
        # ตรวจสอบ pydub
        if not PYDUB_AVAILABLE:
            warning_frame = tk.Frame(self.loop_frame, bg=self.colors['card'], padx=20, pady=20)
            warning_frame.pack(fill='x', pady=(0, 20))
            
            warning_label = tk.Label(
                warning_frame,
                text="⚠️ ต้องติดตั้ง pydub และ ffmpeg เพื่อใช้ฟีเจอร์ลูปเสียง\\n\\nติดตั้ง: pip install pydub",
                font=('Segoe UI', 12, 'bold'),
                fg='#ff6b35',
                bg=self.colors['card'],
                justify='center'
            )
            warning_label.pack()
            return
        
        # ส่วนซ้าย - เลือกไฟล์เสียง
        left_frame = tk.Frame(self.loop_frame, bg=self.colors['card'], padx=20, pady=20)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        audio_label = tk.Label(
            left_frame,
            text="🎵 เลือกไฟล์เสียงที่ต้องการลูป:",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        audio_label.pack(anchor='w', pady=(0, 10))
        
        audio_frame = tk.Frame(left_frame, bg=self.colors['card'])
        audio_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Listbox สำหรับไฟล์เสียง
        listbox_frame = tk.Frame(audio_frame, bg=self.colors['card'])
        listbox_frame.pack(fill='both', expand=True, side='left')
        
        self.loop_files_listbox = tk.Listbox(
            listbox_frame,
            font=('Segoe UI', 9),
            bg='#4d4d4d',
            fg=self.colors['text'],
            bd=0,
            selectbackground=self.colors['primary'],
            activestyle='none'
        )
        
        loop_scrollbar = ttk.Scrollbar(listbox_frame, orient='vertical')
        loop_scrollbar.pack(side='right', fill='y')
        self.loop_files_listbox.config(yscrollcommand=loop_scrollbar.set)
        loop_scrollbar.config(command=self.loop_files_listbox.yview)
        self.loop_files_listbox.pack(side='left', fill='both', expand=True)
        
        # ปุ่มควบคุม
        loop_button_frame = tk.Frame(audio_frame, bg=self.colors['card'])
        loop_button_frame.pack(side='right', fill='y', padx=(10, 0))
        
        browse_audio_btn = tk.Button(
            loop_button_frame,
            text="🎵 เลือกไฟล์เสียง",
            command=self.browse_audio_files,
            bg=self.colors['secondary'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=15,
            pady=10,
            cursor='hand2'
        )
        browse_audio_btn.pack(fill='x', pady=(0, 5))
        
        # ปุ่มดึงไฟล์จากโหมดรวมเสียง
        import_merged_btn = tk.Button(
            loop_button_frame,
            text="📥 ดึงไฟล์รวม",
            command=self.import_merged_files,
            bg='#9C27B0',
            fg='white',
            font=('Segoe UI', 9),
            bd=0,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        import_merged_btn.pack(fill='x', pady=(0, 5))
        
        preview_loop_btn = tk.Button(
            loop_button_frame,
            text="👁️ ดูตัวอย่าง",
            command=self.generate_loop_preview,
            bg=self.colors['accent'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=15,
            pady=10,
            cursor='hand2'
        )
        preview_loop_btn.pack(fill='x', pady=(0, 5))
        
        clear_loop_btn = tk.Button(
            loop_button_frame,
            text="🗑️ ล้างรายการ",
            command=self.clear_loop_files,
            bg='#666666',
            fg='white',
            font=('Segoe UI', 9),
            bd=0,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        clear_loop_btn.pack(fill='x')
        
        # ส่วนขวา - แสดง Preview และการตั้งค่า
        right_frame = tk.Frame(self.loop_frame, bg=self.colors['card'], padx=20, pady=20)
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        loop_preview_label = tk.Label(
            right_frame,
            text="🔄 ตัวอย่างการลูป:",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        loop_preview_label.pack(anchor='w', pady=(0, 10))
        
        # TreeView สำหรับแสดง Preview การลูป
        loop_tree_frame = tk.Frame(right_frame, bg=self.colors['card'])
        loop_tree_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        self.loop_preview_tree = ttk.Treeview(
            loop_tree_frame,
            style="Custom.Treeview",
            show='tree headings',
            columns=('duration', 'loops'),
            height=10
        )
        
        self.loop_preview_tree.heading('#0', text='🎵 ไฟล์เสียง')
        self.loop_preview_tree.heading('duration', text='ระยะเวลา')
        self.loop_preview_tree.heading('loops', text='จำนวนลูป')
        self.loop_preview_tree.column('#0', width=300)
        self.loop_preview_tree.column('duration', width=80, anchor='center')
        self.loop_preview_tree.column('loops', width=80, anchor='center')
        
        loop_tree_scrollbar = ttk.Scrollbar(loop_tree_frame, orient='vertical')
        loop_tree_scrollbar.pack(side='right', fill='y')
        self.loop_preview_tree.config(yscrollcommand=loop_tree_scrollbar.set)
        loop_tree_scrollbar.config(command=self.loop_preview_tree.yview)
        self.loop_preview_tree.pack(side='left', fill='both', expand=True)
        
        # การตั้งค่าการลูป
        loop_settings_frame = tk.Frame(right_frame, bg=self.colors['card'])
        loop_settings_frame.pack(fill='x', pady=(0, 15))
        
        loop_settings_label = tk.Label(
            loop_settings_frame,
            text="⚙️ การตั้งค่าการลูป:",
            font=('Segoe UI', 10, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        loop_settings_label.pack(anchor='w', pady=(0, 5))
        
        # จำนวนครั้งที่ลูป
        loop_count_frame = tk.Frame(loop_settings_frame, bg=self.colors['card'])
        loop_count_frame.pack(fill='x', pady=(0, 5))
        
        loop_count_label = tk.Label(
            loop_count_frame,
            text="จำนวนลูป:",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        loop_count_label.pack(side='left')
        
        self.loop_count = tk.StringVar(value="3")
        loop_count_combo = ttk.Combobox(
            loop_count_frame,
            textvariable=self.loop_count,
            values=["2", "3", "4", "5", "10", "20", "50"],
            state="readonly",
            width=10
        )
        loop_count_combo.pack(side='right')
        
        # ตัวเลือกรูปแบบไฟล์ผลลัพธ์
        loop_format_frame = tk.Frame(loop_settings_frame, bg=self.colors['card'])
        loop_format_frame.pack(fill='x', pady=(0, 5))
        
        loop_format_label = tk.Label(
            loop_format_frame,
            text="รูปแบบไฟล์:",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        loop_format_label.pack(side='left')
        
        self.loop_output_format = tk.StringVar(value="wav")
        loop_format_combo = ttk.Combobox(
            loop_format_frame,
            textvariable=self.loop_output_format,
            values=["mp3", "wav", "flac", "m4a"],
            state="readonly",
            width=10
        )
        loop_format_combo.pack(side='right')
        
        # ตัวเลือกคุณภาพ
        loop_quality_frame = tk.Frame(loop_settings_frame, bg=self.colors['card'])
        loop_quality_frame.pack(fill='x', pady=(0, 5))
        
        loop_quality_label = tk.Label(
            loop_quality_frame,
            text="คุณภาพ (bitrate):",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        loop_quality_label.pack(side='left')
        
        self.loop_bitrate = tk.StringVar(value="320k")
        loop_bitrate_combo = ttk.Combobox(
            loop_quality_frame,
            textvariable=self.loop_bitrate,
            values=["128k", "192k", "256k", "320k"],
            state="readonly",
            width=10
        )
        loop_bitrate_combo.pack(side='right')
        
        # ตัวเลือกบิตเดธ
        loop_bit_depth_frame = tk.Frame(loop_settings_frame, bg=self.colors['card'])
        loop_bit_depth_frame.pack(fill='x', pady=(0, 5))
        
        loop_bit_depth_label = tk.Label(
            loop_bit_depth_frame,
            text="บิตเดธ (bit depth):",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        loop_bit_depth_label.pack(side='left')
        
        self.loop_bit_depth = tk.StringVar(value="24")
        loop_bit_depth_combo = ttk.Combobox(
            loop_bit_depth_frame,
            textvariable=self.loop_bit_depth,
            values=["16", "24", "32"],
            state="readonly",
            width=10
        )
        loop_bit_depth_combo.pack(side='right')
        
        # ตัวเลือกคอสเฟด
        loop_crossfade_frame = tk.Frame(loop_settings_frame, bg=self.colors['card'])
        loop_crossfade_frame.pack(fill='x')
        
        loop_crossfade_label = tk.Label(
            loop_crossfade_frame,
            text="คอสเฟด (วินาที):",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        loop_crossfade_label.pack(side='left')
        
        self.loop_crossfade_duration = tk.StringVar(value="3")
        loop_crossfade_combo = ttk.Combobox(
            loop_crossfade_frame,
            textvariable=self.loop_crossfade_duration,
            values=["0", "1", "2", "3", "4", "5", "10"],
            state="readonly",
            width=10
        )
        loop_crossfade_combo.pack(side='right')
        
        # ปุ่มลูปเสียง
        loop_action_frame = tk.Frame(right_frame, bg=self.colors['card'])
        loop_action_frame.pack(fill='x')
        
        self.loop_btn = tk.Button(
            loop_action_frame,
            text="🔄 ลูปไฟล์เสียง",
            command=self.start_loop_only,
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 12, 'bold'),
            bd=0,
            padx=20,
            pady=15,
            cursor='hand2',
            state='disabled'
        )
        self.loop_btn.pack(fill='x', pady=(0, 10))
        
        # ปุ่มโหลดไฟล์ลูป
        self.download_loop_btn = tk.Button(
            loop_action_frame,
            text="💾 โหลดไฟล์ลูป",
            command=self.download_looped_files,
            bg='#4CAF50',
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            bd=0,
            padx=20,
            pady=12,
            cursor='hand2',
            state='disabled'
        )
        self.download_loop_btn.pack(fill='x')
        
        # แถบความคืบหน้าสำหรับลูปเสียง
        self.loop_progress = ttk.Progressbar(
            right_frame,
            style="Custom.Horizontal.TProgressbar"
        )
        
        # ข้อความสถานะสำหรับลูปเสียง
        self.loop_status_label = tk.Label(
            right_frame,
            text="",
            font=('Segoe UI', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['card']
        )
        
    def switch_to_organize(self):
        self.current_mode = 'organize'
        self.organize_mode_btn.configure(bg=self.colors['primary'])
        self.merge_mode_btn.configure(bg='#666666')
        self.loop_mode_btn.configure(bg='#666666')
        
        # ซ่อนโหมดอื่น
        if hasattr(self, 'merge_frame'):
            self.merge_frame.pack_forget()
        if hasattr(self, 'loop_frame'):
            self.loop_frame.pack_forget()
        
        # แสดงโหมดจัดระเบียบ
        self.organize_frame.pack(fill='both', expand=True)
        
    def switch_to_merge(self):
        if not PYDUB_AVAILABLE:
            messagebox.showerror("ข้อผิดพลาด", "ต้องติดตั้ง pydub เพื่อใช้ฟีเจอร์รวมเสียง\\n\\nติดตั้ง: pip install pydub")
            return
            
        self.current_mode = 'merge'
        self.merge_mode_btn.configure(bg=self.colors['primary'])
        self.organize_mode_btn.configure(bg='#666666')
        self.loop_mode_btn.configure(bg='#666666')
        
        # ซ่อนโหมดอื่น
        self.organize_frame.pack_forget()
        if hasattr(self, 'loop_frame'):
            self.loop_frame.pack_forget()
        
        # แสดงโหมดรวมเสียง
        self.merge_frame.pack(fill='both', expand=True)
    
    def switch_to_loop(self):
        if not PYDUB_AVAILABLE:
            messagebox.showerror("ข้อผิดพลาด", "ต้องติดตั้ง pydub เพื่อใช้ฟีเจอร์ลูปเสียง\\n\\nติดตั้ง: pip install pydub")
            return
            
        self.current_mode = 'loop'
        self.loop_mode_btn.configure(bg=self.colors['primary'])
        self.organize_mode_btn.configure(bg='#666666')
        self.merge_mode_btn.configure(bg='#666666')
        
        # ซ่อนโหมดอื่น
        self.organize_frame.pack_forget()
        if hasattr(self, 'merge_frame'):
            self.merge_frame.pack_forget()
        
        # แสดงโหมดลูปเสียง
        self.loop_frame.pack(fill='both', expand=True)
    
    # ========== ฟังก์ชันสำหรับโหมดจัดระเบียบ ==========
    
    def browse_files(self):
        filetypes = [
            ('ไฟล์เสียง', '*.mp3;*.wav;*.flac;*.m4a;*.aac;*.ogg;*.wma'),
            ('MP3', '*.mp3'),
            ('WAV', '*.wav'),
            ('FLAC', '*.flac'),
            ('M4A', '*.m4a'),
            ('AAC', '*.aac'),
            ('OGG', '*.ogg'),
            ('WMA', '*.wma'),
            ('ทุกไฟล์', '*.*')
        ]
        
        files = filedialog.askopenfilenames(
            title="เลือกไฟล์เสียง",
            filetypes=filetypes
        )
        
        if files:
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    filename = Path(file).name
                    self.files_listbox.insert(tk.END, filename)
    
    def clear_files(self):
        self.selected_files = []
        self.files_listbox.delete(0, tk.END)
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.organize_btn.configure(state='disabled')
        self.preview_data = {}
    
    def generate_preview(self):
        if not self.selected_files:
            messagebox.showwarning("คำเตือน", "กรุณาเลือกไฟล์เสียงก่อน")
            return
        
        # ล้างข้อมูลเก่า
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.preview_data = defaultdict(list)
        
        # จัดกลุ่มไฟล์ตามตัวเลข
        no_number_files = []
        
        for file_path_str in self.selected_files:
            file_path = Path(file_path_str)
            # หาตัวเลขท้ายชื่อไฟล์ (อาจมีช่องว่างก่อนนามสกุล)
            filename_without_ext = file_path.stem
            match = re.search(r'(\d+)\s*$', filename_without_ext)
            
            if match:
                number = match.group(1)
                self.preview_data[number].append(file_path.name)
            else:
                no_number_files.append(file_path.name)
        
        # แสดงโครงสร้างใน TreeView
        total_organized = 0
        
        for number in sorted(self.preview_data.keys(), key=int):
            files = self.preview_data[number]
            folder_item = self.preview_tree.insert(
                '', 'end', 
                text=f"📁 โฟลเดอร์ {number}",
                values=(len(files),),
                open=False
            )
            
            for file_name in sorted(files):
                self.preview_tree.insert(
                    folder_item, 'end',
                    text=f"  🎵 {file_name}",
                    values=('',)
                )
            
            total_organized += len(files)
        
        # แสดงไฟล์ที่ไม่มีตัวเลข
        if no_number_files:
            no_number_item = self.preview_tree.insert(
                '', 'end',
                text="⚠️ ไฟล์ที่ไม่สามารถจัดระเบียบได้",
                values=(len(no_number_files),),
                open=False
            )
            
            for file_name in sorted(no_number_files):
                self.preview_tree.insert(
                    no_number_item, 'end',
                    text=f"  ❌ {file_name}",
                    values=('',)
                )
        
        # สรุปผล
        summary_item = self.preview_tree.insert(
            '', 'end',
            text=f"📊 สรุป: จัดระเบียบได้ {total_organized}/{len(self.selected_files)} ไฟล์",
            values=('',),
            open=True
        )
        
        # เปิดใช้งานปุ่มต่างๆ
        if total_organized > 0:
            self.organize_btn.configure(state='normal')
        
        # ปิด items ทั้งหมด (ให้ผู้ใช้กดเปิดเอง)
        for item in self.preview_tree.get_children():
            self.preview_tree.item(item, open=False)
    
    def start_organize(self):
        if not self.preview_data:
            messagebox.showwarning("คำเตือน", "กรุณากดดูตัวอย่างก่อน")
            return
        
        # ยืนยันการทำงาน
        total_files = sum(len(files) for files in self.preview_data.values())
        if not messagebox.askyesno(
            "ยืนยัน", 
            f"ต้องการจัดระเบียบ {total_files} ไฟล์ใช่หรือไม่?\\n\\nการดำเนินการนี้จะย้ายไฟล์ไปยังโฟลเดอร์ใหม่"
        ):
            return
        
        # เริ่มการทำงาน
        self.progress.pack(fill='x', pady=(20, 10))
        self.status_label.pack(anchor='w')
        self.progress.configure(mode='indeterminate')
        self.progress.start()
        
        self.organize_btn.configure(state='disabled', text="กำลังจัดระเบียบ...")
        self.status_label.configure(text="กำลังย้ายไฟล์...")
        
        # รันในเธรดแยก
        thread = threading.Thread(target=self.organize_files)
        thread.daemon = True
        thread.start()
    
    def organize_files(self):
        try:
            if not self.selected_files:
                self.root.after(0, lambda: self.finish_organize_with_message("ไม่มีไฟล์ที่เลือก"))
                return
            
            # ใช้ตำแหน่งของไฟล์แรกเป็นฐาน
            base_dir = Path(self.selected_files[0]).parent
            
            moved_files = 0
            total_files = sum(len(files) for files in self.preview_data.values())
            
            # จัดระเบียบไฟล์ตาม preview_data
            for number, file_names in self.preview_data.items():
                target_dir = base_dir / number
                target_dir.mkdir(exist_ok=True)
                
                for file_name in file_names:
                    # หาไฟล์ต้นฉบับ
                    source_file = None
                    for file_path_str in self.selected_files:
                        if Path(file_path_str).name == file_name:
                            source_file = Path(file_path_str)
                            break
                    
                    if source_file and source_file.exists():
                        target_path = target_dir / file_name
                        
                        # จัดการไฟล์ชื่อซ้ำ
                        counter = 1
                        original_target = target_path
                        while target_path.exists():
                            stem = original_target.stem
                            suffix = original_target.suffix
                            target_path = original_target.parent / f"{stem}_{counter}{suffix}"
                            counter += 1
                        
                        shutil.move(str(source_file), str(target_path))
                        moved_files += 1
                        
                        # อัพเดทสถานะ
                        status_text = f"ย้ายแล้ว {moved_files}/{total_files} ไฟล์"
                        self.root.after(0, lambda text=status_text: self.status_label.configure(text=text))
            
            # บันทึกตำแหน่งที่จัดระเบียบสำหรับดึงข้อมูลภายหลัง
            self.organized_base_dir = str(base_dir)
            
            # ล้างข้อมูลไฟล์หลังเสร็จ
            self.root.after(0, self.clear_files)
            
            success_msg = f"🎉 เสร็จสิ้น!\\n\\nจัดระเบียบ {moved_files} ไฟล์แล้ว\\nสร้าง {len(self.preview_data)} โฟลเดอร์"
            self.root.after(0, lambda: self.finish_organize_with_message(success_msg, True))
            
        except Exception as e:
            self.root.after(0, lambda: self.finish_organize_with_message(f"เกิดข้อผิดพลาด: {str(e)}"))
    
    
    def send_to_merge_mode(self):
        """ส่งข้อมูลโฟลเดอร์ที่จัดระเบียบไปโหมดรวมเสียง"""
        if not self.organized_base_dir:
            messagebox.showwarning("คำเตือน", "กรุณาจัดระเบียบไฟล์ก่อน")
            return
        
        # สลับไปโหมดรวมเสียง
        self.switch_to_merge()
        
        # เคลียร์รายการโฟลเดอร์เดิม
        self.selected_folders = []
        self.folders_listbox.delete(0, tk.END)
        
        # หาโฟลเดอร์ที่จัดระเบียบแล้วในตำแหน่งที่กำหนด
        base_path = Path(self.organized_base_dir)
        audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
        
        # หาโฟลเดอร์ย่อยที่มีไฟล์เสียง
        for item in base_path.iterdir():
            if item.is_dir():
                # ตรวจสอบว่ามีไฟล์เสียงหรือไม่
                has_audio = any(f.suffix.lower() in audio_extensions 
                              for f in item.iterdir() if f.is_file())
                if has_audio:
                    self.selected_folders.append(str(item))
                    self.folders_listbox.insert(tk.END, f"📁 {item.name}")
        
        # แสดงข้อความสำเร็จ
        if self.selected_folders:
            messagebox.showinfo(
                "สำเร็จ", 
                f"ส่งข้อมูล {len(self.selected_folders)} โฟลเดอร์ไปโหมดรวมเสียงแล้ว!\n\nกด 'ดูตัวอย่าง' เพื่อดูรายละเอียดการรวมเสียง"
            )
        else:
            messagebox.showwarning(
                "ไม่พบโฟลเดอร์",
                "ไม่พบโฟลเดอร์ที่มีไฟล์เสียงในตำแหน่งที่จัดระเบียบ"
            )
    
    def finish_organize_with_message(self, message, show_send_button=False):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label.pack_forget()
        self.organize_btn.configure(state='disabled', text="🚀 จัดระเบียบไฟล์")
        
        
        messagebox.showinfo("ผลลัพธ์", message)
    
    # ========== ฟังก์ชันสำหรับโหมดรวมเสียง ==========
    
    def browse_parent_folder(self):
        """เลือกโฟลเดอร์หลักที่มีโฟลเดอร์ย่อย (โฟลเดอร์ที่จัดระเบียบไว้แล้ว)"""
        parent_folder = filedialog.askdirectory(title="เลือกโฟลเดอร์หลักที่มีโฟลเดอร์ย่อย")
        if parent_folder:
            # หาโฟลเดอร์ย่อยที่มีไฟล์เสียง
            parent_path = Path(parent_folder)
            audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
            
            found_folders = []
            for item in parent_path.iterdir():
                if item.is_dir():
                    # ตรวจสอบว่าโฟลเดอร์นี้มีไฟล์เสียงหรือไม่
                    has_audio = any(f.suffix.lower() in audio_extensions 
                                  for f in item.iterdir() if f.is_file())
                    if has_audio:
                        found_folders.append(str(item))
            
            if found_folders:
                # เคลียร์รายการเก่า
                self.selected_folders = []
                self.folders_listbox.delete(0, tk.END)
                
                # เพิ่มโฟลเดอร์ที่พบ
                for folder_path in sorted(found_folders, key=lambda x: Path(x).name):
                    self.selected_folders.append(folder_path)
                    folder_name = Path(folder_path).name
                    self.folders_listbox.insert(tk.END, f"📁 {folder_name}")
                
                messagebox.showinfo("สำเร็จ", f"พบ {len(found_folders)} โฟลเดอร์ที่มีไฟล์เสียง")
            else:
                messagebox.showwarning("ไม่พบโฟลเดอร์", "ไม่พบโฟลเดอร์ย่อยที่มีไฟล์เสียงในโฟลเดอร์ที่เลือก")
    
    def browse_folders(self):
        """เลือกโฟลเดอร์ทีละโฟลเดอร์"""
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่มีไฟล์เสียง")
        if folder and folder not in self.selected_folders:
            self.selected_folders.append(folder)
            folder_name = Path(folder).name
            self.folders_listbox.insert(tk.END, f"📁 {folder_name}")
    
    def clear_folders(self):
        self.selected_folders = []
        self.folders_listbox.delete(0, tk.END)
        self.merge_preview_tree.delete(*self.merge_preview_tree.get_children())
        self.merge_btn.configure(state='disabled')
        self.download_btn.configure(state='disabled')
        self.merge_preview_data = {}
        self.merged_files = []  # ล้างไฟล์ที่รวมแล้วด้วย
        # ไม่ลบแคชเพื่อความเร็วในการโหลดครั้งถัดไป
    
    def preview_selected_folder(self):
        """ดูตัวอย่างเฉพาะโฟลเดอร์ที่เลือกใน listbox"""
        selected_indices = self.folders_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("คำเตือน", "กรุณาเลือกโฟลเดอร์ที่ต้องการดูตัวอย่างใน listbox")
            return
        
        # เอาเฉพาะโฟลเดอร์ที่เลือก
        selected_folders = []
        for index in selected_indices:
            selected_folders.append(self.selected_folders[index])
        
        # ล้างข้อมูลเก่า
        self.merge_preview_tree.delete(*self.merge_preview_tree.get_children())
        preview_data = {}
        
        audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
        total_files = 0
        
        for folder_path in selected_folders:
            folder = Path(folder_path)
            audio_files = []
            total_duration = 0
            
            for file_path in folder.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                    audio_files.append(file_path.name)
                    # พยายามหาระยะเวลาไฟล์ (ถ้าเป็นไปได้)
                    try:
                        if PYDUB_AVAILABLE:
                            audio = AudioSegment.from_file(str(file_path))
                            total_duration += len(audio) / 1000  # แปลงเป็นวินาที
                    except:
                        total_duration = 0  # ไม่สามารถอ่านได้
            
            if audio_files:
                # เรียงลำดับไฟล์ตามตัวเลขในชื่อไฟล์
                def natural_sort_key(filename):
                    import re
                    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', filename)]
                
                audio_files_sorted = sorted(audio_files, key=natural_sort_key)
                
                preview_data[folder.name] = {
                    'path': folder_path,
                    'files': audio_files_sorted,
                    'original_files': audio_files_sorted.copy(),  # เก็บลำดับเดิมไว้
                    'duration': total_duration
                }
                
                duration_text = f"{int(total_duration//60):02d}:{int(total_duration%60):02d}" if total_duration > 0 else "N/A"
                
                folder_item = self.merge_preview_tree.insert(
                    '', 'end',
                    text=f"📁 {folder.name}",
                    values=(len(audio_files), duration_text),
                    open=True
                )
                
                for file_name in audio_files:
                    child_item = self.merge_preview_tree.insert(
                        folder_item, 'end',
                        text=f"  🎵 {file_name}",
                        values=('', '')
                    )
                    print(f"Added child item: {child_item} with text: 🎵 {file_name}")  # debug
                
                total_files += len(audio_files)
        
        # สรุปผล
        if preview_data:
            total_duration = sum(data['duration'] for data in preview_data.values())
            duration_text = f"{int(total_duration//60):02d}:{int(total_duration%60):02d}" if total_duration > 0 else "N/A"
            
            self.merge_preview_tree.insert(
                '', 'end',
                text=f"📊 สรุป: {len(preview_data)} โฟลเดอร์ที่เลือก, {total_files} ไฟล์",
                values=('', duration_text)
            )
    
    def generate_merge_preview(self):
        if not self.selected_folders:
            messagebox.showwarning("คำเตือน", "กรุณาเลือกโฟลเดอร์ก่อน")
            return
        
        # แสดง progress bar
        self.merge_progress.pack(fill='x', pady=(20, 10))
        self.merge_status_label.pack(anchor='w')
        self.merge_progress.configure(mode='indeterminate')
        self.merge_progress.start()
        self.merge_status_label.configure(text="กำลังโหลดข้อมูลไฟล์...")
        
        # รันในเธรดแยกเพื่อไม่ให้ UI แฮง
        thread = threading.Thread(target=self.generate_merge_preview_thread)
        thread.daemon = True
        thread.start()
    
    def generate_merge_preview_thread(self):
        try:
            # ล้างข้อมูลเก่า
            self.root.after(0, lambda: self.merge_preview_tree.delete(*self.merge_preview_tree.get_children()))
            self.merge_preview_data = {}
            
            audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
            total_files = 0
            processed = 0
            total_folders = len(self.selected_folders)
            
            for folder_path in self.selected_folders:
                folder = Path(folder_path)
                processed += 1
                
                # อัพเดทสถานะ
                status_text = f"กำลังสแกนโฟลเดอร์ {processed}/{total_folders}: {folder.name}"
                self.root.after(0, lambda text=status_text: self.merge_status_label.configure(text=text))
                
                # ตรวจสอบแคช
                cache_key = str(folder_path)
                if cache_key in self.folder_cache:
                    cached_data = self.folder_cache[cache_key]
                    # ตรวจสอบว่าโฟลเดอร์ยังไม่เปลี่ยนแปลง
                    try:
                        folder_mtime = folder.stat().st_mtime
                        if cached_data['mtime'] == folder_mtime:
                            # ใช้ข้อมูลจากแคช
                            audio_files_sorted = cached_data['files']
                            total_duration = 0  # ข้ามการคำนวณระยะเวลาเพื่อความเร็ว
                            
                            self.merge_preview_data[folder.name] = {
                                'path': folder_path,
                                'files': audio_files_sorted,
                                'original_files': audio_files_sorted.copy(),
                                'duration': total_duration
                            }
                            
                            # เพิ่มใน UI
                            self.root.after(0, lambda f=folder, files=audio_files_sorted: self.add_folder_to_tree(f, files, 0))
                            total_files += len(audio_files_sorted)
                            continue
                    except:
                        pass  # ถ้าตรวจสอบแคชไม่ได้ ให้โหลดใหม่
                
                # สแกนไฟล์ในโฟลเดอร์
                audio_files = []
                try:
                    for file_path in folder.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                            audio_files.append(file_path.name)
                except:
                    continue  # ข้ามโฟลเดอร์ที่อ่านไม่ได้
                
                if audio_files:
                    # เรียงลำดับไฟล์ตามตัวเลขในชื่อไฟล์
                    def natural_sort_key(filename):
                        import re
                        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', filename)]
                    
                    audio_files_sorted = sorted(audio_files, key=natural_sort_key)
                    total_duration = 0  # ข้ามการคำนวณระยะเวลาเพื่อความเร็ว
                    
                    # บันทึกลงแคช
                    try:
                        folder_mtime = folder.stat().st_mtime
                        self.folder_cache[cache_key] = {
                            'files': audio_files_sorted,
                            'mtime': folder_mtime
                        }
                    except:
                        pass
                    
                    self.merge_preview_data[folder.name] = {
                        'path': folder_path,
                        'files': audio_files_sorted,
                        'original_files': audio_files_sorted.copy(),
                        'duration': total_duration
                    }
                    
                    # เพิ่มใน UI
                    self.root.after(0, lambda f=folder, files=audio_files_sorted: self.add_folder_to_tree(f, files, 0))
                    total_files += len(audio_files_sorted)
            
            # สรุปผล
            if self.merge_preview_data:
                summary_text = f"📊 สรุป: {len(self.merge_preview_data)} โฟลเดอร์, {total_files} ไฟล์"
                self.root.after(0, lambda: self.merge_preview_tree.insert('', 'end', text=summary_text, values=('', 'พร้อมใช้งาน')))
                self.root.after(0, lambda: self.merge_btn.configure(state='normal'))
            
            # ซ่อน progress bar
            self.root.after(0, self.hide_merge_progress)
            
        except Exception as e:
            self.root.after(0, lambda: self.merge_status_label.configure(text=f"เกิดข้อผิดพลาด: {str(e)}"))
            self.root.after(0, self.hide_merge_progress)
    
    def add_folder_to_tree(self, folder, files, duration):
        """เพิ่มโฟลเดอร์ลง treeview"""
        duration_text = "N/A"  # ไม่คำนวณระยะเวลาเพื่อความเร็ว
        
        folder_item = self.merge_preview_tree.insert(
            '', 'end',
            text=f"📁 {folder.name}",
            values=(len(files), duration_text),
            open=True
        )
        
        for file_name in files:
            self.merge_preview_tree.insert(
                folder_item, 'end',
                text=f"  🎵 {file_name}",
                values=('', '')
            )
    
    def hide_merge_progress(self):
        """ซ่อน progress bar"""
        self.merge_progress.stop()
        self.merge_progress.pack_forget()
        self.merge_status_label.pack_forget()
    
    def import_organized_data(self):
        """ดึงข้อมูลจากโฟลเดอร์ที่จัดระเบียบไว้ก่อนหน้า"""
        if not self.organized_base_dir:
            messagebox.showwarning(
                "ไม่มีข้อมูล", 
                "ยังไม่มีข้อมูลโฟลเดอร์ที่จัดระเบียบแล้ว\n\nกรุณาไปโหมดจัดระเบียบและจัดระเบียบไฟล์ก่อน"
            )
            return
        
        # ตรวจสอบว่าโฟลเดอร์ยังอยู่หรือไม่
        base_path = Path(self.organized_base_dir)
        if not base_path.exists():
            messagebox.showerror(
                "ไม่พบโฟลเดอร์",
                f"ไม่พบโฟลเดอร์ที่จัดระเบียบไว้\n\nตำแหน่ง: {self.organized_base_dir}\n\nอาจถูกย้ายหรือลบไปแล้ว"
            )
            return
        
        # เคลียร์รายการโฟลเดอร์เดิม
        self.selected_folders = []
        self.folders_listbox.delete(0, tk.END)
        
        # หาโฟลเดอร์ย่อยที่มีไฟล์เสียง
        audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
        
        found_count = 0
        for item in base_path.iterdir():
            if item.is_dir():
                # ตรวจสอบว่ามีไฟล์เสียงหรือไม่
                has_audio = any(f.suffix.lower() in audio_extensions 
                              for f in item.iterdir() if f.is_file())
                if has_audio:
                    self.selected_folders.append(str(item))
                    self.folders_listbox.insert(tk.END, f"📁 {item.name}")
                    found_count += 1
        
        if found_count > 0:
            messagebox.showinfo(
                "ดึงข้อมูลสำเร็จ", 
                f"🎉 ดึงข้อมูล {found_count} โฟลเดอร์จากโฟลเดอร์ที่จัดระเบียบไว้!\n\nกด 'ดูตัวอย่างทั้งหมด' เพื่อดูรายละเอียด"
            )
        else:
            messagebox.showwarning(
                "ไม่พบโฟลเดอร์",
                "ไม่พบโฟลเดอร์ย่อยที่มีไฟล์เสียงในโฟลเดอร์ที่จัดระเบียบไว้\n\nอาจไฟล์ถูกย้ายหรือลบไปแล้ว"
            )
    
    def on_merge_tree_click(self, event):
        """จัดการการคลิกบน merge preview tree"""
        # หาตำแหน่งที่คลิก
        item = self.merge_preview_tree.identify_row(event.y)
        if item:
            # เลือก item นั้น
            self.merge_preview_tree.selection_set(item)
            # ตรวจสอบว่าเป็นโฟลเดอร์หรือไม่ (parent items)
            item_text = self.merge_preview_tree.item(item, "text")
            print(f"Clicked item: {item_text}")  # debug
            
            if item_text.startswith("📁") and not item_text.startswith("📊"):
                # สลับการเปิด/ปิดโฟลเดอร์
                is_open = self.merge_preview_tree.item(item, "open")
                print(f"Item is currently open: {is_open}")  # debug
                self.merge_preview_tree.item(item, open=not is_open)
                print(f"Set item open to: {not is_open}")  # debug
                
                # ตรวจสอบว่ามี children หรือไม่
                children = self.merge_preview_tree.get_children(item)
                print(f"Item has {len(children)} children: {children}")  # debug
    
    def on_merge_tree_double_click(self, event):
        """จัดการการดับเบิลคลิกบน merge preview tree"""
        item = self.merge_preview_tree.identify_row(event.y)
        if item:
            print(f"Double-clicked item: {self.merge_preview_tree.item(item, 'text')}")  # debug
            item_text = self.merge_preview_tree.item(item, "text")
            
            if item_text.startswith("📁") and not item_text.startswith("📊"):
                # สลับการเปิด/ปิดโฟลเดอร์
                is_open = self.merge_preview_tree.item(item, "open")
                self.merge_preview_tree.item(item, open=not is_open)
                print(f"Double-click toggled folder to: {not is_open}")  # debug
    
    def on_merge_tree_right_click(self, event):
        """จัดการการคลิกขวาบน merge preview tree"""
        item = self.merge_preview_tree.identify_row(event.y)
        if item:
            self.merge_preview_tree.selection_set(item)
            item_text = self.merge_preview_tree.item(item, "text")
            
            # สร้าง context menu สำหรับไฟล์เพลง
            if item_text.strip().startswith("🎵"):
                self.show_file_context_menu(event, item)
    
    def show_file_context_menu(self, event, item):
        """แสดง context menu สำหรับไฟล์เพลง"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="⬆️ ย้ายขึ้น", command=lambda: self.move_selected_file_up(item))
        context_menu.add_command(label="⬇️ ย้ายลง", command=lambda: self.move_selected_file_down(item))
        context_menu.add_separator()
        context_menu.add_command(label="ยกเลิก", command=lambda: context_menu.destroy())
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def move_file_up(self):
        """ย้ายไฟล์ที่เลือกขึ้น"""
        selected = self.merge_preview_tree.selection()
        if selected:
            item = selected[0]
            self.move_selected_file_up(item)
    
    def move_file_down(self):
        """ย้ายไฟล์ที่เลือกลง"""
        selected = self.merge_preview_tree.selection()
        if selected:
            item = selected[0]
            self.move_selected_file_down(item)
    
    def move_selected_file_up(self, item):
        """ย้ายไฟล์ที่เลือกขึ้น"""
        item_text = self.merge_preview_tree.item(item, "text")
        if not item_text.strip().startswith("🎵"):
            return
            
        parent = self.merge_preview_tree.parent(item)
        if not parent:
            return
        
        # หาโฟลเดอร์ที่ไฟล์นี้อยู่
        parent_text = self.merge_preview_tree.item(parent, "text")
        folder_name = parent_text.replace("📁 ", "")
        
        if folder_name not in self.merge_preview_data:
            return
        
        # หาไฟล์ในรายการ
        file_name = item_text.replace("  🎵 ", "")
        files = self.merge_preview_data[folder_name]['files']
        
        if file_name in files:
            current_index = files.index(file_name)
            if current_index > 0:
                # สลับตำแหน่ง
                files[current_index], files[current_index-1] = files[current_index-1], files[current_index]
                self.refresh_folder_preview(folder_name)
    
    def move_selected_file_down(self, item):
        """ย้ายไฟล์ที่เลือกลง"""
        item_text = self.merge_preview_tree.item(item, "text")
        if not item_text.strip().startswith("🎵"):
            return
            
        parent = self.merge_preview_tree.parent(item)
        if not parent:
            return
        
        # หาโฟลเดอร์ที่ไฟล์นี้อยู่
        parent_text = self.merge_preview_tree.item(parent, "text")
        folder_name = parent_text.replace("📁 ", "")
        
        if folder_name not in self.merge_preview_data:
            return
        
        # หาไฟล์ในรายการ
        file_name = item_text.replace("  🎵 ", "")
        files = self.merge_preview_data[folder_name]['files']
        
        if file_name in files:
            current_index = files.index(file_name)
            if current_index < len(files) - 1:
                # สลับตำแหน่ง
                files[current_index], files[current_index+1] = files[current_index+1], files[current_index]
                self.refresh_folder_preview(folder_name)
    
    def reset_file_order(self):
        """รีเซ็ตลำดับไฟล์กลับเป็นเดิม"""
        selected = self.merge_preview_tree.selection()
        if selected:
            item = selected[0]
            parent = self.merge_preview_tree.parent(item)
            
            # หาโฟลเดอร์
            if parent:  # ถ้าเลือกไฟล์
                target_item = parent
            else:  # ถ้าเลือกโฟลเดอร์
                target_item = item
            
            parent_text = self.merge_preview_tree.item(target_item, "text")
            folder_name = parent_text.replace("📁 ", "")
            
            if folder_name in self.merge_preview_data and 'original_files' in self.merge_preview_data[folder_name]:
                # รีเซ็ตกลับเป็นลำดับเดิม
                self.merge_preview_data[folder_name]['files'] = self.merge_preview_data[folder_name]['original_files'].copy()
                self.refresh_folder_preview(folder_name)
                messagebox.showinfo("รีเซ็ต", f"รีเซ็ตลำดับไฟล์ในโฟลเดอร์ '{folder_name}' เรียบร้อยแล้ว")
    
    def refresh_folder_preview(self, folder_name):
        """รีเฟรชการแสดงผลโฟลเดอร์ที่กำหนด"""
        if folder_name not in self.merge_preview_data:
            return
        
        # หาโฟลเดอร์ใน treeview
        folder_item = None
        for item in self.merge_preview_tree.get_children():
            item_text = self.merge_preview_tree.item(item, "text")
            if item_text == f"📁 {folder_name}":
                folder_item = item
                break
        
        if not folder_item:
            return
        
        # ลบไฟล์เก่าออกจากโฟลเดอร์
        for child in self.merge_preview_tree.get_children(folder_item):
            self.merge_preview_tree.delete(child)
        
        # เพิ่มไฟล์ใหม่ตามลำดับที่ปรับแล้ว
        files = self.merge_preview_data[folder_name]['files']
        for file_name in files:
            self.merge_preview_tree.insert(
                folder_item, 'end',
                text=f"  🎵 {file_name}",
                values=('', '')
            )
    
    def start_merge_only(self):
        """รวมไฟล์เสียงแต่ยังไม่โหลด เก็บไว้ใน memory"""
        if not self.merge_preview_data:
            messagebox.showwarning("คำเตือน", "กรุณากดดูตัวอย่างก่อน")
            return
        
        # ยืนยันการทำงาน
        total_folders = len(self.merge_preview_data)
        if not messagebox.askyesno(
            "ยืนยัน", 
            f"ต้องการรวมไฟล์เสียงจาก {total_folders} โฟลเดอร์ใช่หรือไม่?\n\nจะรวมไฟล์แต่ยังไม่บันทึก"
        ):
            return
        
        # เริ่มการทำงาน
        self.merge_progress.pack(fill='x', pady=(20, 10))
        self.merge_status_label.pack(anchor='w')
        self.merge_progress.configure(mode='indeterminate')
        self.merge_progress.start()
        
        self.merge_btn.configure(state='disabled', text="กำลังรวมเสียง...")
        self.merge_status_label.configure(text="กำลังรวมไฟล์เสียง...")
        
        # รันในเธรดแยก
        thread = threading.Thread(target=self.merge_audio_in_memory)
        thread.daemon = True
        thread.start()
    
    def process_single_folder(self, folder_info):
        """ประมวลผลโฟลเดอร์เดียว สำหรับ parallel processing"""
        folder_name, data = folder_info
        folder_path = Path(data['path'])
        audio_files = data['files']
        
        if not audio_files:
            return None
        
        try:
            # รวมไฟล์เสียงในโฟลเดอร์พร้อมคอสเฟด
            combined = AudioSegment.empty()
            crossfade_ms = int(self.crossfade_duration.get()) * 1000
            
            for i, file_name in enumerate(audio_files):
                file_path = folder_path / file_name
                try:
                    audio = AudioSegment.from_file(str(file_path))
                    
                    if i == 0:
                        combined = audio
                    else:
                        if crossfade_ms > 0 and len(combined) > crossfade_ms and len(audio) > crossfade_ms:
                            combined = combined.append(audio, crossfade=crossfade_ms)
                        else:
                            combined += audio
                except Exception as e:
                    print(f"ไม่สามารถอ่านไฟล์ {file_name}: {e}")
                    continue
            
            if len(combined) > 0:
                output_format = self.output_format.get()
                return {
                    'name': f"{folder_name}_merged.{output_format}",
                    'audio': combined,
                    'folder_name': folder_name
                }
        except Exception as e:
            print(f"ไม่สามารถประมวลผลโฟลเดอร์ {folder_name}: {e}")
        
        return None

    def merge_audio_in_memory(self):
        """รวมไฟล์เสียงเก็บใน memory แบบ parallel"""
        try:
            total_folders = len(self.merge_preview_data)
            self.merged_files = []
            
            # ใช้ parallel processing สำหรับการรวมไฟล์
            max_workers = min(multiprocessing.cpu_count(), 4)  # จำกัดไม่เกิน 4 threads
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # เตรียม tasks
                folder_items = list(self.merge_preview_data.items())
                
                # ส่ง tasks ไปประมวลผล
                future_to_folder = {
                    executor.submit(self.process_single_folder, folder_info): folder_info[0] 
                    for folder_info in folder_items
                }
                
                merged_count = 0
                for future in as_completed(future_to_folder):
                    folder_name = future_to_folder[future]
                    try:
                        result = future.result()
                        if result:
                            self.merged_files.append(result)
                            merged_count += 1
                            
                            # อัพเดทสถานะใน UI thread
                            progress_text = f"รวมเสร็จแล้ว {merged_count}/{total_folders} โฟลเดอร์"
                            self.root.after(0, lambda text=progress_text: self.merge_status_label.configure(text=text))
                    except Exception as e:
                        print(f"ข้อผิดพลาดในการประมวลผลโฟลเดอร์ {folder_name}: {e}")
            
            success_msg = f"🎉 เสร็จสิ้น!\n\nรวมไฟล์เสียงจาก {merged_count} โฟลเดอร์แล้ว\nกด 'โหลดไฟล์รวม' เพื่อบันทึกไฟล์"
            self.root.after(0, lambda: self.finish_merge_only_with_message(success_msg))
            
        except Exception as e:
            self.root.after(0, lambda: self.finish_merge_only_with_message(f"เกิดข้อผิดพลาด: {str(e)}"))
    
    def finish_merge_only_with_message(self, message):
        """เสร็จสิ้นการรวมไฟล์ (ยังไม่บันทึก)"""
        self.merge_progress.stop()
        self.merge_progress.pack_forget()
        self.merge_status_label.pack_forget()
        self.merge_btn.configure(state='normal', text="🎧 รวมไฟล์เสียง")
        
        # เปิดปุ่มโหลดถ้ามีไฟล์รวมแล้ว
        if self.merged_files:
            self.download_btn.configure(state='normal')
        
        messagebox.showinfo("ผลลัพธ์", message)
    
    def download_merged_files(self):
        """โหลดไฟล์ที่รวมแล้ว"""
        if not self.merged_files:
            messagebox.showwarning("คำเตือน", "ยังไม่มีไฟล์ที่รวมแล้ว กรุณารวมไฟล์ก่อน")
            return
        
        # เลือกโฟลเดอร์สำหรับบันทึกผลลัพธ์
        output_dir = filedialog.askdirectory(title="เลือกโฟลเดอร์สำหรับบันทึกไฟล์รวม")
        if not output_dir:
            return
        
        try:
            output_path = Path(output_dir)
            saved_count = 0
            
            for file_data in self.merged_files:
                output_format = self.output_format.get()
                bitrate = self.bitrate.get()
                bit_depth = int(self.bit_depth.get())
                
                output_file = output_path / file_data['name']
                
                # ป้องกันชื่อไฟล์ซ้ำ
                counter = 1
                original_output = output_file
                while output_file.exists():
                    stem = original_output.stem
                    suffix = original_output.suffix
                    output_file = original_output.parent / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                # Export ตามรูปแบบที่เลือก
                combined = file_data['audio']
                if output_format == "mp3":
                    combined.export(str(output_file), format="mp3", bitrate=bitrate)
                elif output_format == "wav":
                    combined.export(str(output_file), format="wav", 
                                  parameters=["-acodec", f"pcm_s{bit_depth}le"])
                elif output_format == "flac":
                    combined.export(str(output_file), format="flac",
                                  parameters=["-sample_fmt", f"s{bit_depth}"])
                elif output_format == "m4a":
                    combined.export(str(output_file), format="mp4", bitrate=bitrate)
                
                saved_count += 1
            
            # ล้างไฟล์ที่รวมแล้วออกจาก memory
            self.merged_files = []
            self.download_btn.configure(state='disabled')
            
            messagebox.showinfo(
                "สำเร็จ", 
                f"🎉 โหลดเสร็จสิ้น!\n\nบันทึก {saved_count} ไฟล์แล้ว\nที่ตำแหน่ง: {output_dir}"
            )
            
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการบันทึกไฟล์: {str(e)}")
    
    def start_merge(self):
        if not self.merge_preview_data:
            messagebox.showwarning("คำเตือน", "กรุณากดดูตัวอย่างก่อน")
            return
        
        # ยืนยันการทำงาน
        total_folders = len(self.merge_preview_data)
        if not messagebox.askyesno(
            "ยืนยัน", 
            f"ต้องการรวมไฟล์เสียงจาก {total_folders} โฟลเดอร์ใช่หรือไม่?\\n\\nจะสร้างไฟล์รวมในแต่ละโฟลเดอร์"
        ):
            return
        
        # เลือกโฟลเดอร์สำหรับบันทึกผลลัพธ์
        output_dir = filedialog.askdirectory(title="เลือกโฟลเดอร์สำหรับบันทึกไฟล์รวม")
        if not output_dir:
            return
        
        # เริ่มการทำงาน
        self.merge_progress.pack(fill='x', pady=(20, 10))
        self.merge_status_label.pack(anchor='w')
        self.merge_progress.configure(mode='indeterminate')
        self.merge_progress.start()
        
        self.merge_btn.configure(state='disabled', text="กำลังรวมเสียง...")
        self.merge_status_label.configure(text="กำลังรวมไฟล์เสียง...")
        
        # รันในเธรดแยก
        thread = threading.Thread(target=self.merge_audio_files, args=(output_dir,))
        thread.daemon = True
        thread.start()
    
    def merge_audio_files(self, output_dir):
        try:
            output_path = Path(output_dir)
            merged_count = 0
            total_folders = len(self.merge_preview_data)
            
            for folder_name, data in self.merge_preview_data.items():
                folder_path = Path(data['path'])
                audio_files = data['files']
                
                if not audio_files:
                    continue
                
                # อัพเดทสถานะ
                status_text = f"กำลังรวมโฟลเดอร์ {folder_name}..."
                self.root.after(0, lambda text=status_text: self.merge_status_label.configure(text=text))
                
                # รวมไฟล์เสียงในโฟลเดอร์พร้อมคอสเฟด
                combined = AudioSegment.empty()
                crossfade_ms = int(self.crossfade_duration.get()) * 1000  # แปลงเป็น milliseconds
                
                for i, file_name in enumerate(audio_files):
                    file_path = folder_path / file_name
                    try:
                        audio = AudioSegment.from_file(str(file_path))
                        
                        if i == 0:
                            # ไฟล์แรก - เพิ่มเข้าไปโดยตรง
                            combined = audio
                        else:
                            # ไฟล์ต่อๆ มา - ใช้คอสเฟด
                            if crossfade_ms > 0 and len(combined) > crossfade_ms and len(audio) > crossfade_ms:
                                combined = combined.append(audio, crossfade=crossfade_ms)
                            else:
                                # ถ้าไฟล์สั้นเกินไปสำหรับคอสเฟด ให้รวมแบบปกติ
                                combined += audio
                    except Exception as e:
                        print(f"ไม่สามารถอ่านไฟล์ {file_name}: {e}")
                        continue
                
                if len(combined) > 0:
                    # บันทึกไฟล์รวม
                    output_format = self.output_format.get()
                    bitrate = self.bitrate.get()
                    bit_depth = int(self.bit_depth.get())
                    output_file = output_path / f"{folder_name}_merged.{output_format}"
                    
                    # ป้องกันชื่อไฟล์ซ้ำ
                    counter = 1
                    while output_file.exists():
                        output_file = output_path / f"{folder_name}_merged_{counter}.{output_format}"
                        counter += 1
                    
                    # Export ตามรูปแบบที่เลือก
                    if output_format == "mp3":
                        combined.export(str(output_file), format="mp3", bitrate=bitrate)
                    elif output_format == "wav":
                        combined.export(str(output_file), format="wav", 
                                      parameters=["-acodec", f"pcm_s{bit_depth}le"])
                    elif output_format == "flac":
                        combined.export(str(output_file), format="flac",
                                      parameters=["-sample_fmt", f"s{bit_depth}"])
                    elif output_format == "m4a":
                        combined.export(str(output_file), format="mp4", bitrate=bitrate)
                    
                    merged_count += 1
                
                # อัพเดทความคืบหน้า
                progress_text = f"รวมเสร็จแล้ว {merged_count}/{total_folders} โฟลเดอร์"
                self.root.after(0, lambda text=progress_text: self.merge_status_label.configure(text=text))
            
            # ล้างข้อมูลหลังเสร็จ
            self.root.after(0, self.clear_folders)
            
            success_msg = f"🎉 เสร็จสิ้น!\\n\\nรวมไฟล์เสียงจาก {merged_count} โฟลเดอร์แล้ว\\nไฟล์ถูกบันทึกที่: {output_dir}"
            self.root.after(0, lambda: self.finish_merge_with_message(success_msg))
            
        except Exception as e:
            self.root.after(0, lambda: self.finish_merge_with_message(f"เกิดข้อผิดพลาด: {str(e)}"))
    
    def finish_merge_with_message(self, message):
        self.merge_progress.stop()
        self.merge_progress.pack_forget()
        self.merge_status_label.pack_forget()
        self.merge_btn.configure(state='disabled', text="🎧 เริ่มรวมไฟล์เสียง")
        messagebox.showinfo("ผลลัพธ์", message)
    
    # ========== ฟังก์ชันสำหรับโหมดลูปเสียง ==========
    
    def browse_audio_files(self):
        """เลือกไฟล์เสียงสำหรับลูป"""
        filetypes = [
            ('ไฟล์เสียง', '*.mp3;*.wav;*.flac;*.m4a;*.aac;*.ogg;*.wma'),
            ('MP3', '*.mp3'),
            ('WAV', '*.wav'),
            ('FLAC', '*.flac'),
            ('M4A', '*.m4a'),
            ('AAC', '*.aac'),
            ('OGG', '*.ogg'),
            ('WMA', '*.wma'),
            ('ทุกไฟล์', '*.*')
        ]
        
        files = filedialog.askopenfilenames(
            title="เลือกไฟล์เสียงสำหรับลูป",
            filetypes=filetypes
        )
        
        if files:
            for file in files:
                if file not in self.loop_files:
                    self.loop_files.append(file)
                    filename = Path(file).name
                    self.loop_files_listbox.insert(tk.END, filename)
    
    def import_merged_files(self):
        """ดึงไฟล์ที่รวมแล้วจากโหมดรวมเสียงมาโหมดลูป"""
        if not self.merged_files:
            messagebox.showwarning(
                "ไม่มีไฟล์ที่รวม", 
                "ไม่มีไฟล์ที่รวมแล้วในโหมดรวมเสียง\n\nกรุณาไปโหมดรวมเสียงและรวมไฟล์ก่อน"
            )
            return
        
        imported_count = 0
        
        for merged_file in self.merged_files:
            # สร้างไฟล์ชั่วคราวเพื่อเก็บข้อมูลเสียง
            import tempfile
            import os
            
            try:
                # สร้างไฟล์ชั่วคราว
                temp_dir = tempfile.gettempdir()
                temp_filename = f"temp_merged_{merged_file['folder_name']}.wav"
                temp_path = os.path.join(temp_dir, temp_filename)
                
                # Export ไฟล์เสียงไปยังไฟล์ชั่วคราว
                merged_file['audio'].export(temp_path, format="wav")
                
                # เพิ่มลงในรายการไฟล์ลูป
                if temp_path not in self.loop_files:
                    self.loop_files.append(temp_path)
                    display_name = f"🎧 {merged_file['folder_name']}_merged.wav (จากโหมดรวมเสียง)"
                    self.loop_files_listbox.insert(tk.END, display_name)
                    imported_count += 1
                    
            except Exception as e:
                print(f"ไม่สามารถนำเข้าไฟล์ {merged_file['folder_name']}: {e}")
                continue
        
        if imported_count > 0:
            messagebox.showinfo(
                "นำเข้าสำเร็จ",
                f"🎉 นำเข้าไฟล์รวม {imported_count} ไฟล์แล้ว!\n\nไฟล์เหล่านี้พร้อมสำหรับการลูป\nกด 'ดูตัวอย่าง' เพื่อดูรายละเอียด"
            )
        else:
            messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถนำเข้าไฟล์ได้")
    
    def clear_loop_files(self):
        """ล้างรายการไฟล์เสียง"""
        # ล้างไฟล์ชั่วคราวที่สร้างจากโหมดรวมเสียง
        import tempfile
        import os
        
        temp_dir = tempfile.gettempdir()
        for file_path in self.loop_files:
            if file_path.startswith(temp_dir) and "temp_merged_" in file_path:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass  # ไม่แสดง error ถ้าลบไม่ได้
        
        self.loop_files = []
        self.loop_files_listbox.delete(0, tk.END)
        self.loop_preview_tree.delete(*self.loop_preview_tree.get_children())
        self.loop_btn.configure(state='disabled')
        self.download_loop_btn.configure(state='disabled')
        self.loop_preview_data = {}
        self.looped_files = []
    
    def generate_loop_preview(self):
        """สร้างตัวอย่างการลูป"""
        if not self.loop_files:
            messagebox.showwarning("คำเตือน", "กรุณาเลือกไฟล์เสียงก่อน")
            return
        
        # ล้างข้อมูลเก่า
        self.loop_preview_tree.delete(*self.loop_preview_tree.get_children())
        self.loop_preview_data = {}
        
        loop_count = int(self.loop_count.get())
        
        for file_path_str in self.loop_files:
            file_path = Path(file_path_str)
            filename = file_path.name
            
            # พยายามหาระยะเวลาไฟล์
            duration = 0
            try:
                if PYDUB_AVAILABLE:
                    audio = AudioSegment.from_file(file_path_str)
                    duration = len(audio) / 1000  # แปลงเป็นวินาที
            except:
                duration = 0
            
            self.loop_preview_data[filename] = {
                'path': file_path_str,
                'duration': duration,
                'loop_count': loop_count
            }
            
            duration_text = f"{int(duration//60):02d}:{int(duration%60):02d}" if duration > 0 else "N/A"
            total_duration = duration * loop_count
            total_duration_text = f"{int(total_duration//60):02d}:{int(total_duration%60):02d}" if total_duration > 0 else "N/A"
            
            # เพิ่ม item หลัก
            main_item = self.loop_preview_tree.insert(
                '', 'end',
                text=f"🎵 {filename}",
                values=(duration_text, f"{loop_count}x"),
                open=True
            )
            
            # เพิ่ม sub items สำหรับแต่ละลูป
            for i in range(loop_count):
                self.loop_preview_tree.insert(
                    main_item, 'end',
                    text=f"  🔄 ลูปที่ {i+1}",
                    values=(duration_text, ""),
                )
            
            # เพิ่มสรุปรวม
            self.loop_preview_tree.insert(
                main_item, 'end',
                text=f"  📊 รวม",
                values=(total_duration_text, f"{loop_count}x"),
            )
        
        # สรุปรวมทั้งหมด
        if self.loop_preview_data:
            total_files = len(self.loop_preview_data)
            total_duration = sum(data['duration'] * data['loop_count'] for data in self.loop_preview_data.values())
            total_duration_text = f"{int(total_duration//60):02d}:{int(total_duration%60):02d}" if total_duration > 0 else "N/A"
            
            self.loop_preview_tree.insert(
                '', 'end',
                text=f"📊 สรุปทั้งหมด: {total_files} ไฟล์",
                values=(total_duration_text, f"{loop_count}x")
            )
            
            self.loop_btn.configure(state='normal')
    
    def start_loop_only(self):
        """ลูปไฟล์เสียงแต่ยังไม่โหลด เก็บไว้ใน memory"""
        if not self.loop_preview_data:
            messagebox.showwarning("คำเตือน", "กรุณากดดูตัวอย่างก่อน")
            return
        
        # ยืนยันการทำงาน
        total_files = len(self.loop_preview_data)
        loop_count = int(self.loop_count.get())
        if not messagebox.askyesno(
            "ยืนยัน", 
            f"ต้องการลูปไฟล์เสียง {total_files} ไฟล์ อย่างละ {loop_count} ครั้ง ใช่หรือไม่?\\n\\nจะลูปไฟล์แต่ยังไม่บันทึก"
        ):
            return
        
        # เริ่มการทำงาน
        self.loop_progress.pack(fill='x', pady=(20, 10))
        self.loop_status_label.pack(anchor='w')
        self.loop_progress.configure(mode='indeterminate')
        self.loop_progress.start()
        
        self.loop_btn.configure(state='disabled', text="กำลังลูปเสียง...")
        self.loop_status_label.configure(text="กำลังลูปไฟล์เสียง...")
        
        # รันในเธรดแยก
        thread = threading.Thread(target=self.loop_audio_in_memory)
        thread.daemon = True
        thread.start()
    
    def process_single_loop(self, file_info):
        """ประมวลผลการลูปไฟล์เดียว สำหรับ parallel processing"""
        filename, data = file_info
        file_path = data['path']
        loop_count = data['loop_count']
        
        try:
            # โหลดไฟล์เสียง
            audio = AudioSegment.from_file(file_path)
            
            # สร้างไฟล์ลูป
            looped_audio = audio
            crossfade_ms = int(self.loop_crossfade_duration.get()) * 1000
            
            for i in range(1, loop_count):
                if crossfade_ms > 0 and len(looped_audio) > crossfade_ms and len(audio) > crossfade_ms:
                    looped_audio = looped_audio.append(audio, crossfade=crossfade_ms)
                else:
                    looped_audio += audio
            
            # เตรียมชื่อไฟล์
            output_format = self.loop_output_format.get()
            file_stem = Path(filename).stem
            
            # แก้ไขชื่อไฟล์สำหรับไฟล์ temp_merged ให้ใช้แค่เลขท้าย
            if file_stem.startswith('temp_merged_'):
                display_name = file_stem.replace('temp_merged_', '')
            else:
                display_name = file_stem
            
            return {
                'name': f"{display_name}.{output_format}",
                'audio': looped_audio,
                'original_name': filename
            }
        except Exception as e:
            print(f"ไม่สามารถลูปไฟล์ {filename}: {e}")
            return None

    def loop_audio_in_memory(self):
        """ลูปไฟล์เสียงเก็บใน memory แบบ parallel"""
        try:
            total_files = len(self.loop_preview_data)
            self.looped_files = []
            
            # ใช้ parallel processing สำหรับการลูปไฟล์
            max_workers = min(multiprocessing.cpu_count(), 4)  # จำกัดไม่เกิน 4 threads
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # เตรียม tasks
                file_items = list(self.loop_preview_data.items())
                
                # ส่ง tasks ไปประมวลผล
                future_to_file = {
                    executor.submit(self.process_single_loop, file_info): file_info[0] 
                    for file_info in file_items
                }
                
                looped_count = 0
                for future in as_completed(future_to_file):
                    filename = future_to_file[future]
                    try:
                        result = future.result()
                        if result:
                            self.looped_files.append(result)
                            looped_count += 1
                            
                            # อัพเดทสถานะใน UI thread
                            progress_text = f"ลูปเสร็จแล้ว {looped_count}/{total_files} ไฟล์"
                            self.root.after(0, lambda text=progress_text: self.loop_status_label.configure(text=text))
                    except Exception as e:
                        print(f"ข้อผิดพลาดในการลูปไฟล์ {filename}: {e}")
            
            success_msg = f"🎉 เสร็จสิ้น!\n\nลูปไฟล์เสียง {looped_count} ไฟล์แล้ว\nกด 'โหลดไฟล์ลูป' เพื่อบันทึกไฟล์"
            self.root.after(0, lambda: self.finish_loop_only_with_message(success_msg))
            
        except Exception as e:
            self.root.after(0, lambda: self.finish_loop_only_with_message(f"เกิดข้อผิดพลาด: {str(e)}"))
    
    def finish_loop_only_with_message(self, message):
        """เสร็จสิ้นการลูปไฟล์ (ยังไม่บันทึก)"""
        self.loop_progress.stop()
        self.loop_progress.pack_forget()
        self.loop_status_label.pack_forget()
        self.loop_btn.configure(state='normal', text="🔄 ลูปไฟล์เสียง")
        
        # เปิดปุ่มโหลดถ้ามีไฟล์ลูปแล้ว
        if self.looped_files:
            self.download_loop_btn.configure(state='normal')
        
        messagebox.showinfo("ผลลัพธ์", message)
    
    def download_looped_files(self):
        """โหลดไฟล์ที่ลูปแล้ว"""
        if not self.looped_files:
            messagebox.showwarning("คำเตือน", "ยังไม่มีไฟล์ที่ลูปแล้ว กรุณาลูปไฟล์ก่อน")
            return
        
        # เลือกโฟลเดอร์สำหรับบันทึกผลลัพธ์
        output_dir = filedialog.askdirectory(title="เลือกโฟลเดอร์สำหรับบันทึกไฟล์ลูป")
        if not output_dir:
            return
        
        try:
            output_path = Path(output_dir)
            saved_count = 0
            
            for file_data in self.looped_files:
                output_format = self.loop_output_format.get()
                bitrate = self.loop_bitrate.get()
                bit_depth = int(self.loop_bit_depth.get())
                
                output_file = output_path / file_data['name']
                
                # ป้องกันชื่อไฟล์ซ้ำ
                counter = 1
                original_output = output_file
                while output_file.exists():
                    stem = original_output.stem
                    suffix = original_output.suffix
                    output_file = original_output.parent / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                # Export ตามรูปแบบที่เลือก
                looped_audio = file_data['audio']
                if output_format == "mp3":
                    looped_audio.export(str(output_file), format="mp3", bitrate=bitrate)
                elif output_format == "wav":
                    looped_audio.export(str(output_file), format="wav", 
                                      parameters=["-acodec", f"pcm_s{bit_depth}le"])
                elif output_format == "flac":
                    looped_audio.export(str(output_file), format="flac",
                                      parameters=["-sample_fmt", f"s{bit_depth}"])
                elif output_format == "m4a":
                    looped_audio.export(str(output_file), format="mp4", bitrate=bitrate)
                
                saved_count += 1
            
            # ล้างไฟล์ที่ลูปแล้วออกจาก memory
            self.looped_files = []
            self.download_loop_btn.configure(state='disabled')
            
            messagebox.showinfo(
                "สำเร็จ", 
                f"🎉 โหลดเสร็จสิ้น!\\n\\nบันทึก {saved_count} ไฟล์แล้ว\\nที่ตำแหน่ง: {output_dir}"
            )
            
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการบันทึกไฟล์: {str(e)}")

def main():
    root = tk.Tk()
    app = AudioManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()