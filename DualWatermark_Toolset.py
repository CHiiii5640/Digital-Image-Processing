import cv2
import numpy as np
from tkinter import *
from tkinter import filedialog, colorchooser, messagebox, ttk
from PIL import Image, ImageTk, ImageFont, ImageDraw
from pathlib import Path
import base64
import io
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import qrcode
import logging
import os
from datetime import datetime

SENTINEL = '1111111111111110'

class WatermarkApp:
    def apply_all_watermarks(self):
        if self.image is None:
            self.log_action("套用全部浮水印", "失敗", "未載入圖片")
            return messagebox.showwarning("警告", "請先載入圖片")

        try:
            # 取得參數
            fs, a, x, y = map(lambda e: int(e.get()), [self.font_size, self.alpha, self.pos_x, self.pos_y])
        except Exception as e:
            self.log_action("套用全部浮水印", "失敗", f"參數解析錯誤: {str(e)}")
            return messagebox.showwarning("格式錯誤", "請輸入數字")
            
        text = self.text_entry.get().strip()
        base = Image.fromarray(self.image).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        try:
            font = ImageFont.truetype(self.font_path, fs) if self.font_path and Path(self.font_path).exists() else ImageFont.load_default()
        except Exception as e:
            self.log_action("套用全部浮水印", "警告", f"字型載入失敗: {str(e)}")
            font = ImageFont.load_default()
            
        # 套用文字浮水印
        if text:
            draw.text((x, y), text, font=font, fill=self.color + (a,))
            self.log_action("套用全部浮水印", "成功", "已套用文字浮水印")

        # 套用圖片浮水印
        if self.wm_image_path:
            try:
                wm = Image.open(self.wm_image_path).convert("RGBA")
                
                # 智能縮放浮水印圖片
                base_w, base_h = base.size
                wm_w, wm_h = wm.size
                
                # 限制浮水印大小不超過主圖的 1/4
                max_w = base_w / 4
                max_h = base_h / 4
                
                if wm_w > max_w or wm_h > max_h:
                    scale = min(max_w / wm_w, max_h / wm_h)
                    wm = wm.resize((int(wm_w * scale), int(wm_h * scale)), Image.LANCZOS)
                
                # 調整透明度
                if a < 255:
                    r, g, b, alpha = wm.split()
                    alpha = alpha.point(lambda i: int(i * (a / 255)))
                    wm.putalpha(alpha)
                    
                # 圖片位置偏移，避免與文字重疊
                wm_pos = (x + 50, y + 50)
                overlay.paste(wm, wm_pos, wm)
                self.log_action("套用全部浮水印", "成功", "已套用圖片浮水印")
            except Exception as e:
                self.log_action("套用全部浮水印", "警告", f"圖片浮水印處理失敗: {str(e)}")

        # 套用 QR code
        if text:
            try:
                qr = qrcode.make(text)
                qr = qr.convert("RGBA").resize((fs * 3, fs * 3), Image.LANCZOS)
                
                # 調整透明度
                if a < 255:
                    r, g, b, alpha = qr.split()
                    alpha = alpha.point(lambda i: int(i * (a / 255)))
                    qr.putalpha(alpha)
                    
                # 放在右下角
                base_w, base_h = base.size
                qr_pos = (base_w - qr.width - 20, base_h - qr.height - 20)
                overlay.paste(qr, qr_pos, qr)
                self.log_action("套用全部浮水印", "成功", "已套用QR碼浮水印")
            except Exception as e:
                self.log_action("套用全部浮水印", "警告", f"QR碼處理失敗: {str(e)}")

        # 合併所有浮水印
        merged = Image.alpha_composite(base, overlay)
        self.preview_image = np.array(merged.convert("RGB"))
        self.display_image()
        self.log_action("套用全部浮水印", "成功", "已完成所有浮水印套用")
        
        # 顯示成功提示
        messagebox.showinfo("完成", "已套用全部浮水印")
    def __init__(self, root):
        self.root, self.image, self.preview_image = root, None, None
        self.image_path, self.wm_image_path = "", ""
        self.font_path = str(Path(__file__).parent / "NotoSansCJK-Regular.ttf")
        self.color = (0, 0, 0)
        self.original_image = None  # 保存原始圖像以便重置
        
        root.title("影像處理期末專題 - 浮水印工具")

        # 主要佈局
        main_frame = Frame(root)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 左側面板 - 圖像顯示區
        left_panel = Frame(main_frame)
        left_panel.pack(side=LEFT, fill=BOTH, expand=True)
        
        self.canvas = Canvas(left_panel, width=600, height=400, bg='gray')
        self.canvas.pack(fill=BOTH, expand=True)
        
        # 路徑顯示
        self.path_display = Frame(left_panel)
        self.path_display.pack(fill=X)
        
        Label(self.path_display, text="主圖路徑: ").grid(row=0, column=0, sticky=W)
        self.main_image_path_label = Label(self.path_display, text="未載入", fg="gray")
        self.main_image_path_label.grid(row=0, column=1, sticky=W)
        
        Label(self.path_display, text="浮水印圖路徑: ").grid(row=1, column=0, sticky=W)
        self.wm_image_path_label = Label(self.path_display, text="未載入", fg="gray")
        self.wm_image_path_label.grid(row=1, column=1, sticky=W)
        
        # 右側面板 - 控制區
        right_panel = Frame(main_frame)
        right_panel.pack(side=RIGHT, fill=Y, padx=10)
        
        # 控制區
        ctrl = LabelFrame(right_panel, text="控制面板")
        ctrl.pack(fill=BOTH, expand=True)

        # Entries grouped
        Label(ctrl, text="浮水印文字").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.text_entry = Entry(ctrl, width=20); self.text_entry.grid(row=0, column=1, padx=5, pady=2)
        Label(ctrl, text="字體大小").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.font_size = Entry(ctrl, width=20); self.font_size.insert(0, "36"); self.font_size.grid(row=1, column=1, padx=5, pady=2)
        Label(ctrl, text="透明度").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.alpha = Entry(ctrl, width=20); self.alpha.insert(0, "128"); self.alpha.grid(row=2, column=1, padx=5, pady=2)
        Label(ctrl, text="X 位置").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.pos_x = Entry(ctrl, width=20); self.pos_x.insert(0, "50"); self.pos_x.grid(row=3, column=1, padx=5, pady=2)
        Label(ctrl, text="Y 位置").grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self.pos_y = Entry(ctrl, width=20); self.pos_y.insert(0, "50"); self.pos_y.grid(row=4, column=1, padx=5, pady=2)
        Label(ctrl, text="不可見浮水印文字").grid(row=5, column=0, sticky="e", padx=5, pady=2)
        self.hidden_text = Entry(ctrl, width=20); self.hidden_text.grid(row=5, column=1, padx=5, pady=2)
        
        # 顏色選擇和顯示
        color_frame = Frame(ctrl)
        color_frame.grid(row=1, column=2, padx=5, pady=2)
        Button(color_frame, text="選擇顏色", command=self.choose_color).pack(side=LEFT)
        self.color_preview = Canvas(color_frame, width=20, height=20, bg='black')
        self.color_preview.pack(side=LEFT, padx=5)
        self.color_value_label = Label(color_frame, text="RGB(0,0,0)")
        self.color_value_label.pack(side=LEFT)
        
        # 字型選擇和預覽
        font_frame = Frame(ctrl)
        font_frame.grid(row=5, column=2, padx=5, pady=2, columnspan=1)
        Button(font_frame, text="選擇字型檔", command=self.choose_font).pack(fill=X)
        self.font_preview = Label(font_frame, text="字型預覽 Aa 中文", height=2)
        self.font_preview.pack(fill=X, pady=2)
        self._update_font_preview()  # 初始化字型預覽

        Label(ctrl, text="加密密鑰(16字)").grid(row=6, column=0, sticky="e", padx=5, pady=2)
        self.aes_key_entry = Entry(ctrl, width=20); self.aes_key_entry.grid(row=6, column=1, padx=5, pady=2)
        
        # LSB 容量預測
        self.lsb_capacity_frame = Frame(ctrl)
        self.lsb_capacity_frame.grid(row=6, column=2, padx=5, pady=2)
        self.lsb_capacity_label = Label(self.lsb_capacity_frame, text="LSB 容量: 0 bytes")
        self.lsb_capacity_label.pack()

        # 文件操作按鈕區
        file_frame = LabelFrame(right_panel, text="檔案操作")
        file_frame.pack(fill=X, pady=5)
        
        Button(file_frame, text="載入圖片", command=self.load_image).grid(row=0, column=0, padx=5, pady=2, sticky="ew")
        Button(file_frame, text="載入浮水印圖", command=self.load_wm_image).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        Button(file_frame, text="儲存圖片", command=self.save_image).grid(row=0, column=2, padx=5, pady=2, sticky="ew")
        Button(file_frame, text="重置圖片", command=self.reset_image).grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        # 浮水印操作按鈕區
        watermark_frame = LabelFrame(right_panel, text="浮水印操作")
        watermark_frame.pack(fill=X, pady=5)
        
        Button(watermark_frame, text="套用文字浮水印", command=self.apply_text_watermark).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        Button(watermark_frame, text="套用圖片浮水印", command=self.apply_image_watermark).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        Button(watermark_frame, text="套用QR碼浮水印", command=self.apply_qrcode_watermark).grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        Button(watermark_frame, text="套用全部浮水印", command=self.apply_all_watermarks).grid(row=0, column=3, padx=2, pady=2, sticky="ew")
        
        # LSB 操作按鈕區
        lsb_frame = LabelFrame(right_panel, text="LSB 隱寫操作")
        lsb_frame.pack(fill=X, pady=5)
        
        Button(lsb_frame, text="嵌入文字LSB", command=self.embed_lsb_text).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        Button(lsb_frame, text="讀取LSB", command=self.extract_lsb).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        Button(lsb_frame, text="嵌入圖片LSB", command=self.embed_lsb_image).grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        Button(lsb_frame, text="讀出圖片LSB", command=self.extract_lsb_image).grid(row=0, column=3, padx=2, pady=2, sticky="ew")
        Button(lsb_frame, text="顯示LSB差異", command=self.show_lsb_difference).grid(row=1, column=0, columnspan=2, padx=2, pady=2, sticky="ew")
        Button(lsb_frame, text="批次浮水印", command=self.batch_apply_watermarks).grid(row=1, column=2, columnspan=2, padx=2, pady=2, sticky="ew")
        
        # 狀態列
        self.status_bar = Label(root, text="就緒", bd=1, relief=SUNKEN, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X)
        
        # 建立日誌紀錄器
        self.setup_logger()

    def setup_logger(self):
        """設置日誌紀錄系統"""
        self.logger = logging.getLogger('watermark_app')
        self.logger.setLevel(logging.INFO)
        
        # 檢查是否已有處理器，避免重複
        if not self.logger.handlers:
            # 建立日誌目錄
            log_dir = Path('./logs')
            log_dir.mkdir(exist_ok=True)
            
            # 建立當日日誌檔案
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = log_dir / f'watermark_log_{today}.txt'
            
            # 檔案處理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 格式化
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            
            self.logger.info('=== 應用程式啟動 ===')
    
    def log_action(self, action, status, details=""):
        """紀錄用戶操作"""
        if not hasattr(self, 'logger'):
            return
            
        log_msg = f'【{action}】{status}: {details}'
        self.logger.info(log_msg)
        
        # 更新狀態列
        if status == "成功":
            self.status_bar.config(text=f'✓ {action} 完成', fg="green")
        elif status == "警告":
            self.status_bar.config(text=f'⚠ {action}: {details}', fg="orange")
        elif status == "失敗":
            self.status_bar.config(text=f'✗ {action} 失敗: {details}', fg="red")
        else:
            self.status_bar.config(text=f'{action}: {details}', fg="black")

    def apply_text_watermark(self):
        if self.image is None: 
            self.log_action("套用文字浮水印", "失敗", "未載入圖片")
            return messagebox.showwarning("警告", "請先載入圖片")
        
        try:
            fs, a, x, y = map(lambda e: int(e.get()), [self.font_size, self.alpha, self.pos_x, self.pos_y])
        except Exception as e:
            self.log_action("套用文字浮水印", "失敗", f"參數解析錯誤: {str(e)}")
            return messagebox.showwarning("格式錯誤", "請輸入數字")

        img_pil = Image.fromarray(self.image).convert("RGBA")
        overlay = Image.new("RGBA", img_pil.size, (255,255,255,0))
        draw = ImageDraw.Draw(overlay)
        text = self.text_entry.get()
        
        try:
            font = ImageFont.truetype(self.font_path, fs) if self.font_path and Path(self.font_path).exists() else ImageFont.load_default()
        except Exception as e:
            self.log_action("套用文字浮水印", "警告", f"字型載入失敗: {str(e)}")
            font = ImageFont.load_default()
        
        draw.text((x, y), text, font=font, fill=self.color + (a,))
        self.preview_image = np.array(Image.alpha_composite(img_pil, overlay).convert("RGB"))
        self.display_image()
        self.log_action("套用文字浮水印", "成功", f"文字: {text}, 位置: ({x}, {y}), 大小: {fs}")

    def apply_qrcode_watermark(self):
        if self.image is None:
            self.log_action("套用QR碼浮水印", "失敗", "未載入圖片")
            return messagebox.showwarning("警告", "請先載入圖片")
        
        text = self.text_entry.get().strip()
        if not text:
            self.log_action("套用QR碼浮水印", "失敗", "未輸入文字")
            return messagebox.showwarning("警告", "請輸入文字來產生 QR code")
        
        try:
            fs, a, x, y = map(lambda e: int(e.get()), [self.font_size, self.alpha, self.pos_x, self.pos_y])
        except Exception as e:
            self.log_action("套用QR碼浮水印", "失敗", f"參數解析錯誤: {str(e)}")
            return messagebox.showwarning("格式錯誤", "請輸入數字")
        
        try:
            qr = qrcode.make(text)
            qr = qr.convert("RGBA").resize((fs * 3, fs * 3), Image.LANCZOS)
            if a < 255:
                r, g, b, alpha = qr.split()
                alpha = alpha.point(lambda i: int(i * (a / 255)))
                qr.putalpha(alpha)
            base = Image.fromarray(self.image).convert("RGBA")
            base_w, base_h = base.size
            qr_pos = (base_w - qr.width - 20, base_h - qr.height - 20)
            base.paste(qr, qr_pos, qr)
            self.preview_image = np.array(base.convert("RGB"))
            self.display_image()
            self.log_action("套用QR碼浮水印", "成功", f"QR內容: {text}, 位置: 右下角")
        except Exception as e:
            self.log_action("套用QR碼浮水印", "失敗", f"處理錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"QR碼處理錯誤: {str(e)}")

    def _add_entry(self, frame, label, row, default=""):
        Label(frame, text=label).grid(row=row, column=0)
        entry = Entry(frame, width=20); entry.grid(row=row, column=1)
        entry.insert(0, default)
        return entry

    def load_image(self):
        path = filedialog.askopenfilename()
        if path:
            self.image_path = path
            img = cv2.imread(path)
            if img is None:
                self.log_action("載入圖片", "失敗", f"無法載入 {path}")
                # 即使載入失敗，仍更新 LSB 容量顯示為 0
                self.image = None
                self.update_lsb_capacity()
                return messagebox.showerror("錯誤", "無法載入圖片")
            
            self.image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self.original_image = self.image.copy()  # 保存原始圖像
            self.preview_image = self.image.copy()
            self.display_image()
            
            # 更新路徑顯示
            self.main_image_path_label.config(text=str(Path(path).name), fg="blue")
            
            # 更新 LSB 容量預測
            self.update_lsb_capacity()
            
            self.log_action("載入圖片", "成功", path)

    def update_lsb_capacity(self):
        """更新 LSB 容量顯示標籤"""
        if self.image is not None:
            if hasattr(self.image, "shape"):
                height, width, channels = self.image.shape
                total_bits = height * width * channels
                total_bytes = total_bits // 8
                self.lsb_capacity_label.config(text=f"LSB 容量: {total_bytes} bytes")
            else:
                self.lsb_capacity_label.config(text="LSB 容量: 0 bytes")
        else:
            self.lsb_capacity_label.config(text="LSB 容量: 0 bytes")
    
    def reset_image(self):
        """重置圖片到原始狀態"""
        if hasattr(self, 'original_image') and self.original_image is not None:
            self.preview_image = self.original_image.copy()
            self.display_image()
            self.log_action("重置圖片", "成功", "已重置為原始圖片")
        else:
            self.log_action("重置圖片", "失敗", "沒有原始圖片可供重置")
            messagebox.showwarning("警告", "請先載入圖片")

    def load_wm_image(self):
        path = filedialog.askopenfilename()
        if path:
            self.wm_image_path = path
            # 更新路徑顯示
            self.wm_image_path_label.config(text=str(Path(path).name), fg="blue")
            self.log_action("載入浮水印圖片", "成功", path)
            messagebox.showinfo("已載入", f"浮水印圖片：{path}")

    def display_image(self):
        """顯示預覽圖像"""
        if self.preview_image is None:
            return
            
        try:
            # 獲取畫布大小
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 確保畫布尺寸有效
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 600
                canvas_height = 400
            
            # 創建PIL圖像
            img = Image.fromarray(self.preview_image)
            
            # 計算縮放比例，保持原始比例
            img_width, img_height = img.size
            scale = min(canvas_width / img_width, canvas_height / img_height)
            
            # 計算新尺寸
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # 縮放圖像
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 計算居中位置
            x_offset = (canvas_width - new_width) // 2
            y_offset = (canvas_height - new_height) // 2
            
            # 顯示圖像
            self.canvas.delete("all")  # 清除現有內容
            self.canvas.imgtk = ImageTk.PhotoImage(img)
            self.canvas.create_image(x_offset, y_offset, anchor=NW, image=self.canvas.imgtk)
            
            # 更新狀態欄
            img_info = f"圖片尺寸: {img_width} × {img_height} 像素"
            self.status_bar.config(text=img_info)
        except Exception as e:
            self.log_action("顯示圖片", "失敗", str(e))
            self.status_bar.config(text=f"顯示圖片錯誤: {str(e)}")

    def choose_color(self):
        color_result = colorchooser.askcolor(title="選擇文字顏色")
        if color_result[0]:  # color_result is ((r,g,b), '#rrggbb')
            self.color = tuple(map(int, color_result[0]))
            # 更新顏色預覽
            rgb_str = f"RGB({self.color[0]},{self.color[1]},{self.color[2]})"
            self.color_value_label.config(text=rgb_str)
            self.color_preview.config(bg=color_result[1])
            self.log_action("選擇顏色", "成功", rgb_str)

    def choose_font(self):
        path = filedialog.askopenfilename(filetypes=[("Font files", "*.ttf")])
        if not path:
            return
        self.font_path = path
        self._update_font_preview()
        self.log_action("選擇字型", "成功", path)
        messagebox.showinfo("已選擇字型", path)

    def _update_font_preview(self):
        """更新字型預覽"""
        try:
            if self.font_path and Path(self.font_path).exists():
                # 建立臨時圖像以顯示字型
                img = Image.new('RGB', (200, 50), color=(255, 255, 255))
                draw = ImageDraw.Draw(img)
                font = ImageFont.truetype(self.font_path, 18)
                draw.text((10, 10), "字型預覽 Aa 中文", font=font, fill=(0, 0, 0))
                img_tk = ImageTk.PhotoImage(img)
                self.font_preview.config(image=img_tk, text="")
                self.font_preview.image = img_tk  # 保持引用以防垃圾回收
            else:
                self.font_preview.config(text="字型預覽 Aa 中文", image="")
        except Exception as e:
            self.log_action("更新字型預覽", "失敗", str(e))
            self.font_preview.config(text="字型預覽 Aa 中文", image="")

    def apply_image_watermark(self):
        if self.image is None or not self.wm_image_path: 
            self.log_action("套用圖片浮水印", "失敗", "未載入圖片或浮水印圖")
            return messagebox.showwarning("警告", "請先載入主圖與浮水印圖")
        
        try:
            alpha = int(self.alpha.get())
            x, y = int(self.pos_x.get()), int(self.pos_y.get())
        except:
            self.log_action("套用圖片浮水印", "失敗", "輸入參數格式錯誤")
            return messagebox.showwarning("格式錯誤", "請輸入數字")

        base = Image.fromarray(self.image).convert("RGBA")

        try:
            wm = Image.open(self.wm_image_path).convert("RGBA")
        except Exception as e:
            self.log_action("套用圖片浮水印", "失敗", f"無法載入浮水印圖: {str(e)}")
            return messagebox.showerror("錯誤", "無法載入浮水印圖")

        base_w, base_h = base.size
        wm_w, wm_h = wm.size

        # 改進縮放算法：根據主圖尺寸智能調整浮水印大小
        if x + wm_w > base_w or y + wm_h > base_h:
            max_w = base_w - x
            max_h = base_h - y
            
            # 如果浮水印太大，限制最大尺寸為主圖的 1/3
            max_allowed_w = base_w / 3
            max_allowed_h = base_h / 3
            
            max_w = min(max_w, max_allowed_w)
            max_h = min(max_h, max_allowed_h)
            
            # 保持縱橫比縮放
            scale = min(max_w / wm_w, max_h / wm_h, 1.0)
            
            # 確保高解析度圖片不會縮放太小
            min_scale = 0.1  # 確保不會小於原始尺寸的 10
            scale = max(scale, min_scale)
            
            wm = wm.resize((int(wm_w * scale), int(wm_h * scale)), Image.LANCZOS)
            self.log_action("圖片浮水印縮放", "成功", f"縮放比例: {scale:.2f}")

        if alpha < 255:
            r, g, b, a = wm.split()
            a = a.point(lambda i: int(i * (alpha / 255)))
            wm.putalpha(a)

        base.paste(wm, (x, y), wm)
        self.preview_image = np.array(base.convert("RGB"))
        self.display_image()
        self.log_action("套用圖片浮水印", "成功", f"位置: ({x}, {y}), 透明度: {alpha}")

    def save_image(self):
        """儲存處理後的圖像"""
        if self.preview_image is None:
            self.log_action("儲存圖片", "失敗", "未載入圖片")
            return messagebox.showwarning("警告", "沒有可儲存的圖片")
            
        try:
            # 取得原始檔名做為預設值
            default_name = "watermarked_image.png"
            if self.image_path:
                orig_name = Path(self.image_path).stem
                default_name = f"{orig_name}_watermarked.png"
                
            # 顯示儲存對話框
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG 圖片", "*.png"),
                    ("JPEG 圖片", "*.jpg;*.jpeg"),
                    ("所有檔案", "*.*")
                ],
                initialfile=default_name
            )
            
            if path:
                # 儲存圖片
                cv2.imwrite(path, cv2.cvtColor(self.preview_image, cv2.COLOR_RGB2BGR))
                self.log_action("儲存圖片", "成功", path)
                messagebox.showinfo("完成", f"圖片已儲存：{path}")
        except Exception as e:
            self.log_action("儲存圖片", "失敗", str(e))
            messagebox.showerror("錯誤", f"儲存圖片時發生錯誤：{str(e)}")

    def text_to_bin(self, text):
        return ''.join(format(b, '08b') for b in text.encode('utf-8'))

    def bin_to_text(self, binary):
        bytes_arr = bytearray(int(binary[i:i+8], 2) for i in range(0, len(binary), 8))
        return bytes_arr.decode('utf-8', errors='ignore')

    def embed_lsb_text(self):
        if not self.image_path: 
            self.log_action("嵌入文字LSB", "失敗", "未載入圖片")
            return messagebox.showwarning("警告", "請先載入圖片")
        
        key = self.aes_key_entry.get()
        if len(key) != 16:
            self.log_action("嵌入文字LSB", "失敗", "密鑰長度不為16")
            return messagebox.showerror("錯誤", "請輸入長度為16的加密密鑰")
        
        hidden_text = self.hidden_text.get()
        if not hidden_text:
            self.log_action("嵌入文字LSB", "失敗", "未輸入隱藏文字")
            return messagebox.showerror("錯誤", "請輸入要隱藏的文字")
            
        try:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
            padded = pad(hidden_text.encode('utf-8'), AES.block_size)
            msg = base64.b64encode(cipher.encrypt(padded)).decode('utf-8')
        except Exception as e:
            self.log_action("嵌入文字LSB", "失敗", f"加密錯誤: {str(e)}")
            return messagebox.showerror("錯誤", f"加密過程出錯: {str(e)}")

        try:
            img = cv2.imread(self.image_path)
            max_bits = img.size  # total pixels * channels
            max_bytes = (max_bits - len(SENTINEL)) // 8
            encrypted_size = len(base64.b64decode(msg.encode('utf-8')))
            
            if encrypted_size > max_bytes:
                self.log_action("嵌入文字LSB", "失敗", f"訊息過長 ({encrypted_size}/{max_bytes} bytes)")
                return messagebox.showerror("錯誤", f"訊息過長，最大可嵌入約 {max_bytes} bytes，目前需要 {encrypted_size} bytes")

            bin_msg = self.text_to_bin(msg) + SENTINEL
            h, w, _ = img.shape; idx = 0

            for r in range(h):
                for c in range(w):
                    for ch in range(3):
                        if idx < len(bin_msg):
                            img[r,c,ch] = (img[r,c,ch] & 254) | int(bin_msg[idx])
                            idx += 1

            path = filedialog.asksaveasfilename(defaultextension=".png")
            if path:
                cv2.imwrite(path, img)
                self.log_action("嵌入文字LSB", "成功", f"儲存至 {path}, 大小: {encrypted_size}/{max_bytes} bytes")
                messagebox.showinfo("完成", f"✅ LSB 文字嵌入完成：{path}\n使用容量: {encrypted_size}/{max_bytes} bytes")
                self.preview_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self.display_image()
        except Exception as e:
            self.log_action("嵌入文字LSB", "失敗", f"處理錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"LSB處理錯誤: {str(e)}")

    def embed_lsb_image(self):
        if not self.image_path or not self.wm_image_path:
            self.log_action("嵌入圖片LSB", "失敗", "未載入主圖或浮水印圖")
            return messagebox.showwarning("警告", "請先載入主圖與浮水印圖")
        
        try:
            img = cv2.imread(self.image_path)
            wm_img = cv2.imread(self.wm_image_path)
            
            # 檢查浮水印圖片大小
            h, w, _ = img.shape
            wm_h, wm_w, _ = wm_img.shape
            
            # 如果浮水印圖片太大，提供縮放選項
            if wm_img.size * 8 > img.size - len(SENTINEL):
                result = messagebox.askyesno("浮水印過大", 
                    "浮水印圖片太大，無法完整嵌入。要自動縮放浮水印圖片嗎？\n" + 
                    f"主圖容量: {(img.size - len(SENTINEL))//8} bytes\n" +
                    f"浮水印需要: {wm_img.size} bytes")
                
                if result:
                    # 計算需要的縮放比例
                    target_size = (img.size - len(SENTINEL)) // 10  # 預留空間，只使用90%容量
                    scale_factor = (target_size / wm_img.size) ** 0.5  # 平方根，因為縮放同時影響寬高
                    
                    new_width = int(wm_w * scale_factor)
                    new_height = int(wm_h * scale_factor)
                    
                    if new_width < 10 or new_height < 10:
                        self.log_action("嵌入圖片LSB", "失敗", "縮放後圖片太小")
                        return messagebox.showerror("錯誤", "縮放後浮水印太小，無法使用")
                    
                    wm_img = cv2.resize(wm_img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                    self.log_action("嵌入圖片LSB", "警告", f"浮水印已縮放至 {new_width}x{new_height}")
                else:
                    self.log_action("嵌入圖片LSB", "取消", "使用者取消縮放")
                    return
            
            # 編碼圖片
            _, buffer = cv2.imencode('.png', wm_img)
            encoded_str = base64.b64encode(buffer).decode('utf-8')
            bin_data = self.text_to_bin(encoded_str) + SENTINEL
            
            # 再次檢查容量
            if len(bin_data) > img.size:
                self.log_action("嵌入圖片LSB", "失敗", "編碼後數據仍然過大")
                return messagebox.showerror("錯誤", "即使縮放後，浮水印仍然太大")
            
            h, w, _ = img.shape; idx = 0
            for r in range(h):
                for c in range(w):
                    for ch in range(3):
                        if idx < len(bin_data):
                            img[r, c, ch] = (img[r, c, ch] & 254) | int(bin_data[idx])
                            idx += 1
            
            path = filedialog.asksaveasfilename(defaultextension=".png")
            if path:
                cv2.imwrite(path, img)
                self.log_action("嵌入圖片LSB", "成功", f"使用容量: {len(bin_data)/8}/{img.size/8} bytes")
                messagebox.showinfo("完成", f"✅ 圖片已嵌入圖片 LSB 中\n使用容量: {len(bin_data)/8:.0f}/{img.size/8:.0f} bytes")
        except Exception as e:
            self.log_action("嵌入圖片LSB", "失敗", f"處理錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"處理錯誤: {str(e)}")

    def extract_lsb(self):
        path = filedialog.askopenfilename(title="選擇含LSB的圖片")
        if not path: return
    
        key = self.aes_key_entry.get()
        if len(key) != 16:
            self.log_action("讀取LSB", "失敗", "密鑰長度不為16")
            return messagebox.showerror("錯誤", "請輸入長度為16的加密密鑰")
            
        try:
            img = cv2.imread(path)
            if img is None:
                self.log_action("讀取LSB", "失敗", f"無法載入圖片 {path}")
                return messagebox.showerror("錯誤", "無法載入圖片")
                
            # 顯示進度對話框
            progress = Toplevel(self.root)
            progress.title("正在提取LSB")
            progress.geometry("300x100")
            progress_label = Label(progress, text="正在分析圖片中的LSB數據...", pady=10)
            progress_label.pack()
            progress_bar = ttk.Progressbar(progress, orient="horizontal", length=250, mode="determinate")
            progress_bar.pack(pady=10)
            progress.update()
            
            # 提取數據
            h, w, c = img.shape
            total_pixels = h * w
            bin_msg = []
            found_sentinel = False
            
            for r in range(h):
                if found_sentinel: break
                for c in range(w):
                    if found_sentinel: break
                    
                    # 更新進度條
                    if (r * w + c) % 10000 == 0:  # 每10000像素更新一次
                        progress_percent = (r * w + c) / total_pixels * 100
                        progress_bar["value"] = progress_percent
                        progress.update()
                    
                    for ch in range(3):
                        bin_msg.append(str(img[r, c, ch] & 1))
                        
                        # 檢查是否已有足夠的位元來檢查SENTINEL
                        if len(bin_msg) >= len(SENTINEL):
                            # 檢查最後的位元是否匹配SENTINEL
                            last_bits = ''.join(bin_msg[-len(SENTINEL):])
                            if last_bits == SENTINEL:
                                found_sentinel = True
                                break
            
            progress.destroy()
            
            if found_sentinel:
                # 提取出SENTINEL之前的數據
                extracted_bits = ''.join(bin_msg[:-len(SENTINEL)])
                # 轉換為文字
                try:
                    msg = self.bin_to_text(extracted_bits)
                    # 解密
                    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
                    decrypted = unpad(cipher.decrypt(base64.b64decode(msg)), AES.block_size).decode('utf-8')
                    
                    # 顯示結果
                    result_window = Toplevel(self.root)
                    result_window.title("LSB提取結果")
                    result_window.geometry("400x300")
                    
                    Label(result_window, text="成功提取隱藏訊息", font=("Arial", 12, "bold")).pack(pady=10)
                    
                    text_frame = Frame(result_window)
                    text_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
                    
                    text_widget = Text(text_frame, wrap=WORD, height=10)
                    text_widget.pack(side=LEFT, fill=BOTH, expand=True)
                    
                    scrollbar = Scrollbar(text_frame, command=text_widget.yview)
                    scrollbar.pack(side=RIGHT, fill=Y)
                    text_widget.config(yscrollcommand=scrollbar.set)
                    
                    text_widget.insert(END, decrypted)
                    text_widget.config(state=DISABLED)
                    
                    Button(result_window, text="複製到剪貼簿", command=lambda: self.copy_to_clipboard(decrypted)).pack(pady=5)
                    Button(result_window, text="關閉", command=result_window.destroy).pack(pady=5)
                    
                    self.log_action("讀取LSB", "成功", f"從 {path} 提取")
                except Exception as e:
                    self.log_action("讀取LSB", "失敗", f"解密錯誤: {str(e)}")
                    messagebox.showerror("錯誤", f"解密失敗，請確認密鑰正確: {str(e)}")
            else:
                self.log_action("讀取LSB", "失敗", "未找到LSB終止標記")
                messagebox.showerror("錯誤", "在圖片中未找到有效的LSB隱寫數據")
        except Exception as e:
            self.log_action("讀取LSB", "失敗", f"處理錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"處理錯誤: {str(e)}")

    def extract_lsb_image(self):
        path = filedialog.askopenfilename(title="選擇含圖片LSB的圖片")
        if not path: return
        
        try:
            img = cv2.imread(path)
            if img is None:
                self.log_action("讀出圖片LSB", "失敗", f"無法載入圖片 {path}")
                return messagebox.showerror("錯誤", "無法載入圖片")
                
            # 顯示進度對話框
            progress = Toplevel(self.root)
            progress.title("正在提取圖片LSB")
            progress.geometry("300x100")
            progress_label = Label(progress, text="正在分析圖片中的LSB數據...", pady=10)
            progress_label.pack()
            progress_bar = ttk.Progressbar(progress, orient="horizontal", length=250, mode="determinate")
            progress_bar.pack(pady=10)
            progress.update()
            
            # 提取數據
            h, w, c = img.shape
            total_pixels = h * w
            bin_msg = []
            found_sentinel = False
            
            for r in range(h):
                if found_sentinel: break
                for c in range(w):
                    if found_sentinel: break
                    
                    # 更新進度條
                    if (r * w + c) % 10000 == 0:  # 每10000像素更新一次
                        progress_percent = (r * w + c) / total_pixels * 100
                        progress_bar["value"] = progress_percent
                        progress.update()
                    
                    for ch in range(3):
                        bin_msg.append(str(img[r, c, ch] & 1))
                        
                        # 檢查是否已有足夠的位元來檢查SENTINEL
                        if len(bin_msg) >= len(SENTINEL):
                            # 檢查最後的位元是否匹配SENTINEL
                            last_bits = ''.join(bin_msg[-len(SENTINEL):])
                            if last_bits == SENTINEL:
                                found_sentinel = True
                                break
            
            progress.destroy()
            
            if found_sentinel:
                # 提取出SENTINEL之前的數據
                extracted_bits = ''.join(bin_msg[:-len(SENTINEL)])
                # 轉換為文字
                try:
                    content = self.bin_to_text(extracted_bits)
                    decoded = base64.b64decode(content.encode('utf-8'))
                    
                    # 顯示預覽視窗
                    preview_window = Toplevel(self.root)
                    preview_window.title("提取的圖片預覽")
                    preview_window.geometry("600x500")
                    
                    # 解碼並顯示圖片
                    np_arr = np.frombuffer(decoded, np.uint8)
                    extracted_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    extracted_img_rgb = cv2.cvtColor(extracted_img, cv2.COLOR_BGR2RGB)
                    
                    h, w, _ = extracted_img.shape
                    info_text = f"提取的圖片尺寸: {w} x {h}"
                    
                    Label(preview_window, text="成功提取隱藏圖片", font=("Arial", 12, "bold")).pack(pady=5)
                    Label(preview_window, text=info_text).pack(pady=5)
                    
                    # 預覽圖片
                    preview_img = Image.fromarray(extracted_img_rgb)
                    
                    # 調整大小以適應視窗
                    preview_w, preview_h = preview_img.size
                    max_size = 400
                    if preview_w > max_size or preview_h > max_size:
                        scale = min(max_size / preview_w, max_size / preview_h)
                        preview_img = preview_img.resize((int(preview_w * scale), int(preview_h * scale)), Image.LANCZOS)
                    
                    photo = ImageTk.PhotoImage(preview_img)
                    img_label = Label(preview_window, image=photo)
                    img_label.image = photo  # 保持引用
                    img_label.pack(pady=10)
                    
                    # 儲存按鈕
                    def save_extracted_image():
                        save_path = filedialog.asksaveasfilename(defaultextension=".png")
                        if save_path:
                            with open(save_path, "wb") as f:
                                f.write(decoded)
                            self.log_action("讀出圖片LSB", "儲存", f"儲存至 {save_path}")
                            messagebox.showinfo("成功", f"已提取圖片，儲存為 {save_path}")
                            preview_window.destroy()
                    
                    Button(preview_window, text="儲存圖片", command=save_extracted_image).pack(pady=5)
                    Button(preview_window, text="關閉", command=preview_window.destroy).pack(pady=5)
                    
                    self.log_action("讀出圖片LSB", "成功", f"從 {path} 提取")
                except Exception as e:
                    self.log_action("讀出圖片LSB", "失敗", f"解碼錯誤: {str(e)}")
                    messagebox.showerror("失敗", f"無法解碼圖片資料: {str(e)}")
            else:
                self.log_action("讀出圖片LSB", "失敗", "未找到LSB終止標記")
                messagebox.showerror("錯誤", "在圖片中未找到有效的LSB圖片數據")
        except Exception as e:
            self.log_action("讀出圖片LSB", "失敗", f"處理錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"處理錯誤: {str(e)}")

    def copy_to_clipboard(self, text):
        """複製文字到剪貼簿"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("已複製", "文字已複製到剪貼簿")

    def batch_apply_watermarks(self):
        """批次處理多個圖片添加浮水印"""
        if not messagebox.askyesno("確認", "是否要進行批次浮水印處理？這將在多張圖片上應用相同的浮水印設定。"):
            return
            
        # 選擇輸入目錄
        input_dir = filedialog.askdirectory(title="選擇包含圖片的目錄")
        if not input_dir:
            return
            
        # 選擇輸出目錄
        output_dir = filedialog.askdirectory(title="選擇浮水印圖片的儲存目錄")
        if not output_dir:
            return
            
        # 獲取所有支援的圖片文件
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        image_files = []
        for ext in supported_formats:
            image_files.extend(list(Path(input_dir).glob(f'*{ext}')))
            image_files.extend(list(Path(input_dir).glob(f'*{ext.upper()}')))
            
        if not image_files:
            self.log_action("批次浮水印", "失敗", "未找到支援的圖片文件")
            return messagebox.showwarning("警告", "所選目錄中未找到支援的圖片文件")
            
        try:
            # 取得參數
            fs, a, x, y = map(lambda e: int(e.get()), [self.font_size, self.alpha, self.pos_x, self.pos_y])
        except Exception as e:
            self.log_action("批次浮水印", "失敗", f"參數解析錯誤: {str(e)}")
            return messagebox.showwarning("格式錯誤", "請輸入數字")
            
        text = self.text_entry.get().strip()
        
        # 是否需要加載字體
        try:
            font = ImageFont.truetype(self.font_path, fs) if self.font_path and Path(self.font_path).exists() else ImageFont.load_default()
        except Exception as e:
            self.log_action("批次浮水印", "警告", f"字型載入失敗: {str(e)}")
            font = ImageFont.load_default()
            
        # 加載浮水印圖片（如果有）
        wm_image = None
        if self.wm_image_path:
            try:
                wm_image = Image.open(self.wm_image_path).convert("RGBA")
            except Exception as e:
                self.log_action("批次浮水印", "警告", f"浮水印圖片載入失敗: {str(e)}")
                
        # 創建進度窗口
        progress_window = Toplevel(self.root)
        progress_window.title("批次處理進度")
        progress_window.geometry("400x150")
        
        progress_label = Label(progress_window, text="正在處理圖片...")
        progress_label.pack(pady=10)
        
        progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=350, mode="determinate")
        progress_bar.pack(pady=10)
        
        status_label = Label(progress_window, text="0/{} 已完成".format(len(image_files)))
        status_label.pack(pady=5)
        
        progress_window.update()
        
        # 批次處理所有圖片
        processed_count = 0
        success_count = 0
        
        for img_path in image_files:
            try:
                # 更新進度
                progress_label.config(text=f"正在處理: {img_path.name}")
                progress_window.update()
                
                # 開啟圖片
                img = Image.open(img_path).convert("RGBA")
                
                # 創建疊加層
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                
                # 套用文字浮水印
                if text:
                    draw.text((x, y), text, font=font, fill=self.color + (a,))
                
                # 套用圖片浮水印
                if wm_image:
                    # 調整浮水印圖片大小
                    wm_width, wm_height = wm_image.size
                    img_width, img_height = img.size
                    
                    # 確保浮水印不會超過原圖大小的1/4
                    max_wm_width = img_width // 4
                    max_wm_height = img_height // 4
                    
                    if wm_width > max_wm_width or wm_height > max_wm_height:
                        scale = min(max_wm_width / wm_width, max_wm_height / wm_height)
                        new_size = (int(wm_width * scale), int(wm_height * scale))
                        resized_wm = wm_image.resize(new_size, Image.LANCZOS)
                    else:
                        resized_wm = wm_image
                    
                    # 計算貼上位置（右下角）
                    paste_x = img_width - resized_wm.width - x
                    paste_y = img_height - resized_wm.height - y
                    
                    # 確保不會超出圖片範圍
                    paste_x = max(0, min(paste_x, img_width - resized_wm.width))
                    paste_y = max(0, min(paste_y, img_height - resized_wm.height))
                    
                    # 使用 alpha 混合浮水印圖片
                    alpha_resized = Image.new("RGBA", resized_wm.size, (0, 0, 0, 0))
                    alpha_draw = ImageDraw.Draw(alpha_resized)
                    
                    for i in range(resized_wm.width):
                        for j in range(resized_wm.height):
                            p = resized_wm.getpixel((i, j))
                            if p[3] > 0:  # 有透明度
                                alpha_resized.putpixel((i, j), (p[0], p[1], p[2], min(p[3], a)))
                    
                    overlay.paste(alpha_resized, (paste_x, paste_y), alpha_resized)
                
                # 合併原圖和浮水印層
                result = Image.alpha_composite(img, overlay).convert("RGB")
                
                # 儲存結果
                output_path = Path(output_dir) / img_path.name
                result.save(output_path)
                
                success_count += 1
                self.log_action("批次浮水印", "成功", f"已處理 {img_path.name}")
                
            except Exception as e:
                self.log_action("批次浮水印", "失敗", f"處理 {img_path.name} 時出錯: {str(e)}")
            
            # 更新進度條
            processed_count += 1
            progress_bar["value"] = (processed_count / len(image_files)) * 100
            status_label.config(text=f"{processed_count}/{len(image_files)} 已完成")
            progress_window.update()
        
        # 處理完成
        progress_window.destroy()
        
        # 顯示結果
        self.log_action("批次浮水印", "完成", f"已處理 {processed_count} 張圖片，成功 {success_count} 張")
        messagebox.showinfo("完成", f"批次處理完成！\n已處理 {processed_count} 張圖片，成功 {success_count} 張。\n輸出目錄: {output_dir}")

    def show_lsb_difference(self):
        """顯示原圖和LSB修改後的圖片差異"""
        # 選擇原始圖片
        original_path = filedialog.askopenfilename(title="選擇原始圖片")
        if not original_path: 
            return
            
        # 選擇LSB處理後的圖片
        lsb_path = filedialog.askopenfilename(title="選擇LSB處理後的圖片")
        if not lsb_path: 
            return
            
        try:
            # 讀取兩張圖片
            original_img = cv2.imread(original_path)
            lsb_img = cv2.imread(lsb_path)
            
            if original_img is None or lsb_img is None:
                self.log_action("顯示LSB差異", "失敗", "無法載入圖片")
                return messagebox.showerror("錯誤", "無法載入圖片")
                
            # 確保兩張圖片大小相同
            if original_img.shape != lsb_img.shape:
                self.log_action("顯示LSB差異", "失敗", "兩張圖片尺寸不同")
                return messagebox.showerror("錯誤", "兩張圖片尺寸不同，無法比較")
                
            # 計算差異圖
            diff = cv2.absdiff(original_img, lsb_img)
            
            # 增強差異以便觀察
            enhanced_diff = diff * 20
            
            # 創建一個視窗顯示差異
            result = Toplevel(self.root)
            result.title("LSB差異分析")
            
            # 使用 PIL 處理圖像
            original_pil = Image.fromarray(cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB))
            lsb_pil = Image.fromarray(cv2.cvtColor(lsb_img, cv2.COLOR_BGR2RGB))
            diff_pil = Image.fromarray(cv2.cvtColor(enhanced_diff, cv2.COLOR_BGR2RGB))
            
            # 縮放圖像以適應窗口
            max_width = 300
            width_percent = max_width/float(original_pil.size[0])
            new_height = int(float(original_pil.size[1])*float(width_percent))
            
            original_pil = original_pil.resize((max_width, new_height), Image.LANCZOS)
            lsb_pil = lsb_pil.resize((max_width, new_height), Image.LANCZOS)
            diff_pil = diff_pil.resize((max_width, new_height), Image.LANCZOS)
            
            # 轉換為 ImageTk 格式
            original_tk = ImageTk.PhotoImage(original_pil)
            lsb_tk = ImageTk.PhotoImage(lsb_pil)
            diff_tk = ImageTk.PhotoImage(diff_pil)
            
            # 創建標籤顯示圖像
            frame = Frame(result)
            frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
            
            # 原圖
            original_frame = LabelFrame(frame, text="原始圖片")
            original_frame.grid(row=0, column=0, padx=5, pady=5)
            original_label = Label(original_frame, image=original_tk)
            original_label.image = original_tk  # 保持引用
            original_label.pack(padx=5, pady=5)
            
            # LSB圖
            lsb_frame = LabelFrame(frame, text="LSB圖片")
            lsb_frame.grid(row=0, column=1, padx=5, pady=5)
            lsb_label = Label(lsb_frame, image=lsb_tk)
            lsb_label.image = lsb_tk  # 保持引用
            lsb_label.pack(padx=5, pady=5)
            
            # 差異圖
            diff_frame = LabelFrame(frame, text="差異 (x20)")
            diff_frame.grid(row=0, column=2, padx=5, pady=5)
            diff_label = Label(diff_frame, image=diff_tk)
            diff_label.image = diff_tk  # 保持引用
            diff_label.pack(padx=5, pady=5)
            
            # 差異統計
            non_zero = np.count_nonzero(diff)
            total_pixels = diff.shape[0] * diff.shape[1] * diff.shape[2]
            change_percent = (non_zero / total_pixels) * 100
            
            stats_frame = LabelFrame(result, text="差異統計")
            stats_frame.pack(fill=X, padx=10, pady=10)
            
            stats_text = f"總像素數: {total_pixels}\n" \
                         f"變更像素數: {non_zero}\n" \
                         f"變更百分比: {change_percent:.5f}%"
            
            stats_label = Label(stats_frame, text=stats_text, justify=LEFT, padx=10, pady=10)
            stats_label.pack()
            
            self.log_action("顯示LSB差異", "成功", f"差異像素: {non_zero}/{total_pixels} ({change_percent:.5f}%)")
            
        except Exception as e:
            self.log_action("顯示LSB差異", "失敗", f"處理時出錯: {str(e)}")
            messagebox.showerror("錯誤", f"處理LSB差異時出錯: {str(e)}")


# 程式入口點
if __name__ == "__main__":
    root = Tk()
    root.title("影像處理期末專題 - 浮水印工具")
    root.geometry("1200x800")  # 設置合適的視窗大小
    app = WatermarkApp(root)
    root.mainloop()
