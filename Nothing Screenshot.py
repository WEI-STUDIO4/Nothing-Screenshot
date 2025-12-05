import os
import sys
import threading
import time
import json
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import keyboard
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item
import win32api
import win32con
import win32gui
import win32ui

# 配置文件路径
CONFIG_FILE = "nothing_screenshot_config.json"

class ScreenshotApp:
    def __init__(self):
        # 默认配置
        self.config = {
            "hotkey": "ctrl+shift+s",
            "save_path": str(Path.home() / "Pictures" / "NothingScreenshots"),
            "start_minimized": True,
            "flash_screen": True
        }
        
        # 加载配置
        self.load_config()
        
        # 创建保存目录
        Path(self.config["save_path"]).mkdir(parents=True, exist_ok=True)
        
        # 初始化主窗口
        self.root = tk.Tk()
        self.setup_window()
        
        # 初始化系统托盘
        self.setup_tray()
        
        # 注册全局快捷键
        self.register_hotkey()
        
        # 截图计数
        self.screenshot_count = 0
        
    def setup_window(self):
        """设置主窗口"""
        self.root.title("Nothing Screenshot")
        self.root.geometry("500x400")  # 减小高度，移除了通知选项
        self.root.resizable(False, False)
        
        # 设置窗口图标
        try:
            self.root.iconbitmap(self.get_icon_path())
        except:
            pass
        
        # 设置扁平化主题
        self.setup_style()
        
        # 创建UI组件
        self.create_widgets()
        
        # 窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
    def setup_style(self):
        """设置扁平化主题"""
        style = ttk.Style()
        
        # 定义颜色 - 使用更简洁的颜色方案
        self.primary_color = "#333333"  # 深灰色
        self.secondary_color = "#666666"  # 中灰色
        self.bg_color = "#F5F5F5"  # 浅灰背景
        self.text_color = "#333333"  # 深灰文字
        self.accent_color = "#999999"  # 浅灰色强调色
        
        # 配置样式
        self.root.configure(bg=self.bg_color)
        style.theme_use('clam')
        
        # 配置标签样式
        style.configure('Custom.TLabel', 
                       background=self.bg_color,
                       foreground=self.text_color,
                       font=('Segoe UI', 10))
        
        # 配置按钮样式
        style.configure('Accent.TButton',
                       background=self.primary_color,
                       foreground="white",
                       borderwidth=0,
                       focusthickness=0,
                       focuscolor='none',
                       font=('Segoe UI', 10, 'bold'))
        
        style.map('Accent.TButton',
                 background=[('active', self.secondary_color)],
                 relief=[('pressed', 'sunken'), ('!pressed', 'flat')])
        
        # 配置框架样式
        style.configure('Custom.TFrame', background=self.bg_color)
        
        # 配置输入框样式
        style.configure('Custom.TEntry',
                       fieldbackground="white",
                       borderwidth=1,
                       relief="solid")
        
    def create_widgets(self):
        """创建UI组件"""
        # 标题栏
        title_frame = ttk.Frame(self.root, style='Custom.TFrame')
        title_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        title_label = ttk.Label(title_frame, 
                               text="Nothing Screenshot", 
                               style='Custom.TLabel',
                               font=('Segoe UI', 18, 'bold'),
                               foreground=self.primary_color)
        title_label.pack(side='left')
        
        # 状态标签
        self.status_label = ttk.Label(title_frame, 
                                     text="已就绪", 
                                     style='Custom.TLabel')
        self.status_label.pack(side='right')
        
        # 分隔线
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', padx=20, pady=10)
        
        # 设置区域
        settings_frame = ttk.Frame(self.root, style='Custom.TFrame')
        settings_frame.pack(fill='both', padx=20, pady=10, expand=True)
        
        # 快捷键设置
        hotkey_frame = ttk.Frame(settings_frame, style='Custom.TFrame')
        hotkey_frame.pack(fill='x', pady=10)
        
        hotkey_label = ttk.Label(hotkey_frame, 
                                text="截图快捷键:", 
                                style='Custom.TLabel',
                                width=15,
                                anchor='w')
        hotkey_label.pack(side='left')
        
        self.hotkey_var = tk.StringVar(value=self.config["hotkey"])
        hotkey_entry = ttk.Entry(hotkey_frame, 
                                textvariable=self.hotkey_var,
                                style='Custom.TEntry',
                                width=30)
        hotkey_entry.pack(side='left', padx=(10, 0))
        
        test_hotkey_btn = ttk.Button(hotkey_frame,
                                    text="测试快捷键",
                                    style='Accent.TButton',
                                    command=self.test_hotkey)
        test_hotkey_btn.pack(side='left', padx=(10, 0))
        
        # 保存路径设置
        path_frame = ttk.Frame(settings_frame, style='Custom.TFrame')
        path_frame.pack(fill='x', pady=10)
        
        path_label = ttk.Label(path_frame, 
                              text="保存路径:", 
                              style='Custom.TLabel',
                              width=15,
                              anchor='w')
        path_label.pack(side='left')
        
        self.path_var = tk.StringVar(value=self.config["save_path"])
        path_entry = ttk.Entry(path_frame, 
                              textvariable=self.path_var,
                              style='Custom.TEntry',
                              width=30)
        path_entry.pack(side='left', padx=(10, 0))
        
        browse_btn = ttk.Button(path_frame,
                               text="浏览",
                               style='Accent.TButton',
                               command=self.browse_path)
        browse_btn.pack(side='left', padx=(10, 0))
        
        # 其他选项
        options_frame = ttk.Frame(settings_frame, style='Custom.TFrame')
        options_frame.pack(fill='x', pady=10)
        
        self.flash_var = tk.BooleanVar(value=self.config["flash_screen"])
        flash_check = ttk.Checkbutton(options_frame,
                                     text="截图后100ms屏幕闪白",
                                     variable=self.flash_var,
                                     style='Custom.TLabel')
        flash_check.pack(anchor='w')
        
        self.minimize_var = tk.BooleanVar(value=self.config["start_minimized"])
        minimize_check = ttk.Checkbutton(options_frame,
                                        text="启动时最小化到托盘",
                                        variable=self.minimize_var,
                                        style='Custom.TLabel')
        minimize_check.pack(anchor='w', pady=(5, 0))
        
        # 按钮区域
        button_frame = ttk.Frame(self.root, style='Custom.TFrame')
        button_frame.pack(fill='x', padx=20, pady=20)
        
        # 左侧按钮
        left_btn_frame = ttk.Frame(button_frame, style='Custom.TFrame')
        left_btn_frame.pack(side='left')
        
        test_screenshot_btn = ttk.Button(left_btn_frame,
                                        text="测试截图",
                                        style='Accent.TButton',
                                        command=self.test_screenshot)
        test_screenshot_btn.pack(side='left', padx=(0, 10))
        
        open_folder_btn = ttk.Button(left_btn_frame,
                                    text="打开截图文件夹",
                                    command=self.open_screenshot_folder)
        open_folder_btn.pack(side='left')
        
        # 右侧按钮
        right_btn_frame = ttk.Frame(button_frame, style='Custom.TFrame')
        right_btn_frame.pack(side='right')
        
        save_btn = ttk.Button(right_btn_frame,
                             text="保存设置",
                             style='Accent.TButton',
                             command=self.save_config)
        save_btn.pack(side='right', padx=(10, 0))
        
        quit_btn = ttk.Button(right_btn_frame,
                             text="退出程序",
                             command=self.quit_app)
        quit_btn.pack(side='right')
        
    def setup_tray(self):
        """设置系统托盘图标"""
        # 创建托盘图标 - 使用🈚字符
        image = Image.new('RGB', (64, 64), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        try:
            # 尝试使用系统字体显示🈚字符
            font = ImageFont.truetype("seguisym.ttf", 40)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()
        
        # 绘制🈚字符
        text = "🈚"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (64 - text_width) // 2
        y = (64 - text_height) // 2
        
        draw.text((x, y), text, font=font, fill=self.primary_color)
        
        # 创建托盘菜单
        menu = (
            item('显示主窗口', self.show_window),
            item('截图', self.take_screenshot),
            item('退出', self.quit_app)
        )
        
        # 创建托盘图标
        self.tray_icon = pystray.Icon("nothing_screenshot", image, "Nothing Screenshot", menu)
        
        # 在单独的线程中运行托盘图标
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()
        
    def register_hotkey(self):
        """注册全局快捷键"""
        try:
            # 注销之前的快捷键
            keyboard.unhook_all_hotkeys()
            
            # 注册新的快捷键
            keyboard.add_hotkey(self.config["hotkey"], self.take_screenshot)
            self.update_status(f"快捷键已注册: {self.config['hotkey']}")
        except Exception as e:
            self.update_status(f"快捷键注册失败: {str(e)}")
            
    def take_screenshot(self):
        """执行截图操作 - 无通知版本"""
        try:
            # 先截图
            screenshot = pyautogui.screenshot()
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = Path(self.config["save_path"]) / filename
            
            # 保存图片
            screenshot.save(filepath)
            
            # 更新计数但不显示通知
            self.screenshot_count += 1
            
            # 截图完成后100ms再执行闪屏效果
            if self.config["flash_screen"]:
                self.root.after(100, self.flash_screen)
            
            return filepath
            
        except Exception as e:
            # 只在调试时显示错误
            if not self.config["start_minimized"]:
                self.update_status(f"截图失败: {str(e)}")
            return None
            
    def flash_screen(self):
        """屏幕闪白效果"""
        try:
            # 创建全屏白色窗口
            flash_window = tk.Toplevel(self.root)
            flash_window.attributes('-fullscreen', True)
            flash_window.attributes('-topmost', True)
            flash_window.attributes('-alpha', 0.7)  # 70%透明度
            flash_window.configure(bg='white')
            flash_window.overrideredirect(True)
            
            # 显示窗口
            flash_window.update()
            
            # 短暂显示后关闭
            self.root.after(50, flash_window.destroy)
            
        except Exception as e:
            pass  # 静默失败
            
    def test_screenshot(self):
        """测试截图功能"""
        filepath = self.take_screenshot()
        if filepath:
            # 只在测试时显示一次通知
            self.update_status(f"测试截图完成: {filepath.name}")
            
    def test_hotkey(self):
        """测试快捷键"""
        hotkey = self.hotkey_var.get()
        self.update_status(f"请按下: {hotkey}")
        
        # 临时注册快捷键进行测试
        def on_test():
            self.update_status("快捷键测试成功!")
            messagebox.showinfo("测试成功", f"快捷键 {hotkey} 测试成功!")
            
        keyboard.add_hotkey(hotkey, on_test, suppress=True)
        
        # 10秒后清除测试快捷键
        def clear_test():
            keyboard.unhook_all_hotkeys()
            self.register_hotkey()
            
        self.root.after(10000, clear_test)
        
    def browse_path(self):
        """浏览选择保存路径"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
            
    def open_screenshot_folder(self):
        """打开截图文件夹"""
        path = Path(self.config["save_path"])
        if path.exists():
            os.startfile(path)
        else:
            messagebox.showerror("错误", "截图文件夹不存在")
            
    def update_status(self, message):
        """更新状态标签"""
        if hasattr(self, 'status_label') and not self.config["start_minimized"]:
            self.status_label.config(text=message)
            self.root.update_idletasks()
            
    def save_config(self):
        """保存配置"""
        self.config["hotkey"] = self.hotkey_var.get()
        self.config["save_path"] = self.path_var.get()
        self.config["flash_screen"] = self.flash_var.get()
        self.config["start_minimized"] = self.minimize_var.get()
        
        # 保存到文件
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
            
        # 重新注册快捷键
        self.register_hotkey()
        
        # 更新状态
        self.update_status("设置已保存")
        messagebox.showinfo("成功", "设置已保存!")
        
    def load_config(self):
        """加载配置"""
        try:
            if Path(CONFIG_FILE).exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
        except Exception as e:
            print(f"加载配置失败: {e}")
            
    def show_window(self, icon=None, item=None):
        """显示主窗口"""
        self.root.after(0, self.root.deiconify)
        
    def minimize_to_tray(self):
        """最小化到托盘"""
        self.root.withdraw()
        
    def quit_app(self):
        """退出程序"""
        # 停止托盘图标
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
            
        # 注销快捷键
        try:
            keyboard.unhook_all_hotkeys()
        except:
            pass
            
        # 退出程序
        self.root.quit()
        self.root.destroy()
        
    def get_icon_path(self):
        """获取图标路径"""
        # 尝试查找图标文件
        icon_path = "nothing_screenshot.ico"
        
        # 如果不存在，创建一个带🈚字符的图标
        if not Path(icon_path).exists():
            try:
                img = Image.new('RGBA', (64, 64), (255, 255, 255, 255))
                draw = ImageDraw.Draw(img)
                
                try:
                    # 尝试使用系统字体
                    font = ImageFont.truetype("seguisym.ttf", 48)
                except:
                    try:
                        font = ImageFont.truetype("arial.ttf", 48)
                    except:
                        font = ImageFont.load_default()
                
                # 绘制🈚字符
                text = "🈚"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (64 - text_width) // 2
                y = (64 - text_height) // 2
                
                draw.text((x, y), text, font=font, fill=self.primary_color)
                
                # 保存为ICO
                img.save(icon_path, format='ICO')
            except:
                pass
                
        return icon_path
        
    def run(self):
        """运行应用程序"""
        # 如果配置为启动时最小化，则隐藏窗口
        if self.config["start_minimized"]:
            self.root.withdraw()
        else:
            self.root.deiconify()
            
        # 运行主循环
        self.root.mainloop()

def main():
    """主函数"""
    app = ScreenshotApp()
    app.run()

if __name__ == "__main__":
    # 检查依赖库
    try:
        import pyautogui
        import keyboard
        from PIL import Image, ImageDraw, ImageFont
        import pystray
    except ImportError as e:
        print(f"缺少依赖库: {e}")
        print("请安装以下库:")
        print("pip install pyautogui keyboard pillow pystray pywin32")
        input("按Enter键退出...")
        sys.exit(1)
        
    main()