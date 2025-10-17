# -*- coding: utf-8 -*-
import sys
import os
import asyncio
import aiohttp
import re
from urllib.parse import quote
import webbrowser
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
    QProgressBar, QMessageBox, QGroupBox, QTextEdit, QHeaderView,
    QStyleFactory, QFileDialog, QSplitter, QDialog, QAction
)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QColor
from PyQt5.QtCore import Qt, QUrl, QSize, QObject, pyqtSignal
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

class AsyncTaskManager(QObject):
    """异步任务管理器"""
    # 定义信号，用于在异步任务完成时通知主线程
    search_result_ready = pyqtSignal(object)
    song_detail_ready = pyqtSignal(object)
    download_info_ready = pyqtSignal(object, str, str)
    
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
    
    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def run_coroutine(self, coro, signal=None, callback=None):
        """在事件循环中运行协程"""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        if signal:
            future.add_done_callback(lambda f: self._on_signal_done(f, signal))
        elif callback:
            future.add_done_callback(lambda f: self._on_callback_done(f, callback))
        return future
    
    def _on_signal_done(self, future, signal):
        """当协程完成时调用，发射相应的信号"""
        try:
            result = future.result()
            # 使用Qt的信号机制在主线程中处理结果
            signal.emit(result)
        except Exception as e:
            print(f"协程执行出错: {e}")
            signal.emit(None)
    
    def _on_callback_done(self, future, callback):
        """当协程完成时调用，执行回调函数"""
        try:
            result = future.result()
            # 直接执行回调函数
            callback(result)
        except Exception as e:
            print(f"协程执行出错: {e}")
            callback(None)
    
    def stop(self):
        """停止事件循环"""
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=1.0)
    
    def search_songs(self, keyword):
        """搜索歌曲并发射结果信号"""
        self.run_coroutine(self._search_songs_impl(keyword), self.search_result_ready)
    
    def get_song_by_id(self, song_id, for_download=False, song_info=None):
        """获取歌曲详情并发射结果信号"""
        if for_download and song_info:
            # 为下载操作准备
            self.run_coroutine(
                self._get_song_by_id_impl(song_id), 
                callback=lambda result: self.download_info_ready.emit(result, song_info['name'], song_info['singer'])
            )
        else:
            # 为获取详情准备
            self.run_coroutine(self._get_song_by_id_impl(song_id), signal=self.song_detail_ready)
    
    async def _search_songs_impl(self, keyword):
        """异步搜索歌曲的实现 - 复用MelodyFetch.py的逻辑，添加3次自动重试"""
        import random  # 导入random模块用于生成随机间隔
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            print(f"[DEBUG] 开始搜索歌曲: {keyword} (尝试 {retry_count + 1}/{max_retries})")
            try:
                encoded_keyword = quote(keyword)
                url = f"https://api.vkeys.cn/v2/music/netease?word={encoded_keyword}&page=1&num=10"
                print(f"[DEBUG] 搜索URL: {url}")
                
                # 添加浏览器头信息
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Connection': 'keep-alive'
                }
                
                async with aiohttp.ClientSession() as session:
                    try:
                        print(f"[DEBUG] 发送请求...")
                        async with session.get(url, headers=headers, timeout=10) as response:
                            print(f"[DEBUG] 响应状态码: {response.status}")
                            
                            if response.status == 200:
                                data = await response.json()
                                print(f"[DEBUG] API响应: {data}")
                                
                                if data.get("code") == 200 and data.get("data"):
                                    print(f"[DEBUG] 搜索成功，找到 {len(data['data'])} 首歌曲")
                                    return data["data"]
                                else:
                                    print(f"[DEBUG] API返回错误码: {data.get('code')}, 消息: {data.get('msg')}")
                                    # 准备重试
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        wait_time = random.randint(1, 5)
                                        print(f"[DEBUG] 准备重试，等待 {wait_time} 秒")
                                        await asyncio.sleep(wait_time)
                                        continue
                                    return None
                            else:
                                print(f"[DEBUG] HTTP错误: 状态码 {response.status}")
                                # 准备重试
                                retry_count += 1
                                if retry_count < max_retries:
                                    wait_time = random.randint(1, 5)
                                    print(f"[DEBUG] 准备重试，等待 {wait_time} 秒")
                                    await asyncio.sleep(wait_time)
                                    continue
                                return None
                    except asyncio.TimeoutError:
                        print(f"[DEBUG] 搜索超时")
                        # 准备重试
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = random.randint(1, 5)
                            print(f"[DEBUG] 准备重试，等待 {wait_time} 秒")
                            await asyncio.sleep(wait_time)
                            continue
                        return None
                    except Exception as e:
                        print(f"[DEBUG] 请求异常: {e}")
                        # 准备重试
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = random.randint(1, 5)
                            print(f"[DEBUG] 准备重试，等待 {wait_time} 秒")
                            await asyncio.sleep(wait_time)
                            continue
                        return None
            except Exception as e:
                print(f"[DEBUG] 搜索歌曲时出错: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = random.randint(1, 5)
                    print(f"[DEBUG] 准备重试，等待 {wait_time} 秒")
                    await asyncio.sleep(wait_time)
                    continue
                return None
        
        return None
    
    async def _get_song_by_id_impl(self, song_id):
        """异步通过ID获取歌曲详情的实现 - 复用MelodyFetch.py的逻辑"""
        print(f"[DEBUG] 开始获取歌曲详情: ID = {song_id}")
        try:
            url = f"https://api.vkeys.cn/v2/music/netease?id={song_id}"
            print(f"[DEBUG] 请求URL: {url}")
            
            # 添加重试机制
            max_retries = 3
            retry_count = 0
            
            # 添加浏览器头信息
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Connection': 'keep-alive'
            }
            
            while retry_count <= max_retries:
                print(f"[DEBUG] 重试次数: {retry_count}/{max_retries}")
                async with aiohttp.ClientSession() as session:
                    try:
                        print(f"[DEBUG] 发送请求...")
                        async with session.get(url, headers=headers, timeout=15) as response:
                            print(f"[DEBUG] 响应状态码: {response.status}")
                            
                            if response.status == 200:
                                data = await response.json()
                                print(f"[DEBUG] API响应: {data}")
                                
                                # 检查是否为503错误，如果是则重试
                                if data.get("code") == 503:
                                    print(f"[DEBUG] 遇到503错误，准备重试")
                                    retry_count += 1
                                    if retry_count <= max_retries:
                                        print(f"[DEBUG] 等待1秒后重试...")
                                        await asyncio.sleep(1)  # 等待1秒后重试
                                        continue
                                    else:
                                        print(f"[DEBUG] 达到最大重试次数，获取失败")
                                        return None
                                
                                if data.get("code") == 200 and data.get("data"):
                                    print(f"[DEBUG] 获取歌曲详情成功")
                                    return data["data"]
                                else:
                                    print(f"[DEBUG] API返回错误码: {data.get('code')}, 消息: {data.get('msg')}")
                            else:
                                print(f"[DEBUG] HTTP错误: 状态码 {response.status}")
                            break  # 成功获取数据或非503错误，退出循环
                    except asyncio.TimeoutError:
                        print(f"[DEBUG] 请求超时")
                        retry_count += 1
                        if retry_count <= max_retries:
                            print(f"[DEBUG] 等待1秒后重试...")
                            await asyncio.sleep(1)
                            continue
                        break
                    except Exception as e:
                        print(f"[DEBUG] 请求异常: {e}")
                        retry_count += 1
                        if retry_count <= max_retries:
                            print(f"[DEBUG] 等待1秒后重试...")
                            await asyncio.sleep(1)
                            continue
                        break
        except Exception as e:
            print(f"[DEBUG] 获取歌曲信息时出错: {e}")
        return None

class AboutDialog(QDialog):
    """关于对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 MelodyFetch")
        self.setWindowIcon(QIcon("MelodyFetchIcon.png"))
        self.setGeometry(400, 300, 400, 300)
        
        # 设置全局样式
        self.setStyleSheet(readQss("qss/DefaultMix.qss"))
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建图标
        icon_label = QLabel()
        icon_pixmap = QPixmap("MelodyFetchIcon.png")
        scaled_pixmap = icon_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(scaled_pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(icon_label)
        
        # 创建应用信息
        info_label = QLabel()
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setTextFormat(Qt.RichText)
        info_label.setText("<h3>MelodyFetch 音乐无损解析工具</h3><p>版本: 1.0.0</p><p>作者: SRInternet</p><p>一款简单易用的音乐搜索和下载工具</p>")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # 创建捐赠按钮
        # donate_button = QPushButton(" 支持作者 ")
        # donate_button.clicked.connect(self.open_donate_page)
        # donate_layout = QHBoxLayout()
        # donate_layout.addStretch()
        # donate_layout.addWidget(donate_button)
        # donate_layout.addStretch()
        # main_layout.addLayout(donate_layout)
        
        # 添加底部间距
        main_layout.addStretch()
        
    def open_donate_page(self):
        """打开捐赠页面"""
        webbrowser.open("https://afdian.com/a/srinternet")

class MelodyFetchGUI(QMainWindow):
    """MelodyFetch图形界面应用"""
    def __init__(self):
        super().__init__()
        # 设置中文字体支持
        self.font = QFont()
        self.font.setFamily("Microsoft YaHei")
        self.setFont(self.font)
        
        # 初始化异步任务管理器
        self.async_manager = AsyncTaskManager()
        # 连接信号和槽
        self.async_manager.search_result_ready.connect(self.handle_search_result)
        self.async_manager.song_detail_ready.connect(self.handle_get_song_result)
        self.async_manager.download_info_ready.connect(self.handle_download_song)
        
        # 当前选中的歌曲信息
        self.current_song = None
        
        # 设置窗口属性
        self.setWindowIcon(QIcon("MelodyFetchIcon.png"))
        self.setWindowTitle("MelodyFetch 音乐无损解析工具")
        self.setGeometry(100, 100, 1000, 700)
        
        # 设置全局样式
        self.setStyleSheet(readQss("qss/DefaultMix.qss"))
        
        # 创建菜单
        self.create_menu()
        
        # 创建主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建顶部搜索栏
        self.create_search_bar()
        
        # 创建主分割器
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.main_splitter)
        
        # 创建搜索结果表格
        self.create_result_table()
        
        # 创建歌曲详情面板
        self.create_detail_panel()
        
        # 将表格和详情面板添加到分割器
        self.main_splitter.addWidget(self.result_table_group)
        self.main_splitter.addWidget(self.detail_panel_group)
        
        # 设置分割器初始比例
        self.main_splitter.setSizes([300, 400])
        
        # 创建状态栏进度条
        self.create_status_bar()
        
        # 创建临时目录
        self.temp_dir = "temp_music"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def create_menu(self):
        """创建菜单栏"""
        # 获取菜单栏
        menu_bar = self.menuBar()
        
        # 创建帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        # 创建关于菜单项
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
    def show_about_dialog(self):
        """显示关于对话框"""
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def create_search_bar(self):
        """创建搜索栏"""
        search_group = QGroupBox("音乐搜索")
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入歌曲名或ID")
        self.search_input.returnPressed.connect(self.search_music)
        
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.search_music)
        self.search_button.setFixedHeight(30)
        
        search_layout.addWidget(self.search_input, 4)
        search_layout.addWidget(self.search_button, 1)
        
        search_group.setLayout(search_layout)
        self.main_layout.addWidget(search_group)
    
    def create_result_table(self):
        """创建搜索结果表格"""
        self.result_table_group = QGroupBox("搜索结果")
        table_layout = QVBoxLayout()
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["序号", "歌曲名", "歌手"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.cellDoubleClicked.connect(self.on_table_item_double_clicked)
        self.result_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        # 设置表格为不可编辑模式，避免用户双击修改文字
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        table_layout.addWidget(self.result_table)
        self.result_table_group.setLayout(table_layout)
    
    def create_detail_panel(self):
        """创建歌曲详情面板"""
        self.detail_panel_group = QGroupBox("歌曲详情")
        detail_layout = QVBoxLayout()
        
        # 封面和基本信息布局
        info_layout = QHBoxLayout()
        
        # 封面图
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(150, 150)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setText("封面图片")
        self.cover_label.setObjectName("coverLabel")  # 使用QSS中定义的样式
        
        # 基本信息
        basic_info_layout = QVBoxLayout()
        
        self.song_name_label = QLabel("歌曲名: -")
        self.song_name_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        
        self.singer_label = QLabel("歌手: -")
        self.album_label = QLabel("专辑: -")
        self.duration_label = QLabel("时长: -")
        self.size_label = QLabel("大小: -")
        
        basic_info_layout.addWidget(self.song_name_label)
        basic_info_layout.addWidget(self.singer_label)
        basic_info_layout.addWidget(self.album_label)
        basic_info_layout.addWidget(self.duration_label)
        basic_info_layout.addWidget(self.size_label)
        basic_info_layout.addStretch()
        
        info_layout.addWidget(self.cover_label)
        info_layout.addLayout(basic_info_layout)
        
        # 操作按钮布局
        actions_layout = QHBoxLayout()
        
        self.open_browser_button = QPushButton("在浏览器中打开")
        self.open_browser_button.clicked.connect(self.open_in_browser)
        self.open_browser_button.setEnabled(False)
        
        self.download_button = QPushButton("下载音频")
        self.download_button.clicked.connect(self.download_audio)
        self.download_button.setEnabled(False)
        
        actions_layout.addWidget(self.open_browser_button)
        actions_layout.addWidget(self.download_button)
        
        # 添加所有布局到详情面板
        detail_layout.addLayout(info_layout)
        detail_layout.addLayout(actions_layout)
        
        # 歌曲信息详情文本框
        self.song_info_text = QTextEdit()
        self.song_info_text.setReadOnly(True)
        self.song_info_text.setHtml("<p style='color: #666;'>请选择一首歌曲查看详情</p>")
        
        detail_layout.addWidget(self.song_info_text)
        
        self.detail_panel_group.setLayout(detail_layout)
    
    def create_status_bar(self):
        """创建状态栏进度条"""
        self.statusBar().showMessage("就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)
    
    def search_music(self):
        """搜索音乐"""
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "警告", "请输入歌曲名或ID")
            return
        
        # 禁用搜索按钮和输入框，防止连续点击
        self.search_button.setEnabled(False)
        self.search_input.setEnabled(False)
        
        self.statusBar().showMessage(f"正在搜索: {keyword}")
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        
        # 清空表格
        self.result_table.setRowCount(0)
        self.current_song = None
        self.reset_detail_panel()
        
        # 判断是搜索歌曲还是通过ID获取
        if keyword.isdigit():
            # 通过ID获取歌曲
            self.async_manager.get_song_by_id(keyword)
        else:
            # 搜索歌曲
            self.async_manager.search_songs(keyword)
    
    def on_table_item_double_clicked(self, row, column):
        """双击表格项时触发"""
        song_id = self.result_table.item(row, 0).data(Qt.UserRole)
        song_name = self.result_table.item(row, 1).text()
        
        # 更新状态栏并显示不确定的进度条
        self.statusBar().showMessage(f"正在获取歌曲 '{song_name}' 的详情...")
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        
        self.async_manager.get_song_by_id(song_id)
    
    def on_table_selection_changed(self):
        """表格选择项变化时触发"""
        selected_items = self.result_table.selectedItems()
        if selected_items:
            # 启用操作按钮
            self.open_browser_button.setEnabled(True)
            self.download_button.setEnabled(True)
        else:
            # 禁用操作按钮
            self.open_browser_button.setEnabled(False)
            self.download_button.setEnabled(False)
    
    def open_in_browser(self):
        """在浏览器中打开选中的歌曲"""
        selected_rows = set(item.row() for item in self.result_table.selectedItems())
        if not selected_rows:
            return
        
        row = list(selected_rows)[0]
        song_id = self.result_table.item(row, 0).data(Qt.UserRole)
        
        # 构建网易云音乐链接
        music_url = f"https://music.163.com/song?id={song_id}"
        webbrowser.open(music_url)
    
    def download_audio(self):
        """下载音频文件"""
        selected_rows = set(item.row() for item in self.result_table.selectedItems())
        if not selected_rows:
            return
        
        row = list(selected_rows)[0]
        song_id = self.result_table.item(row, 0).data(Qt.UserRole)
        song_name = self.result_table.item(row, 1).text()
        singer = self.result_table.item(row, 2).text()
        
        # 获取歌曲详情并下载
        self.statusBar().showMessage(f"正在获取歌曲 '{song_name}' 的下载链接...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        self.async_manager.get_song_by_id(song_id, True, {'name': song_name, 'singer': singer})
    
    def reset_detail_panel(self):
        """重置详情面板"""
        self.cover_label.clear()
        self.cover_label.setText("封面图片")
        # self.cover_label.setStyleSheet("background-color: #f0f0f0; border-radius: 5px;")
        
        self.song_name_label.setText("歌曲名: -")
        self.singer_label.setText("歌手: -")
        self.album_label.setText("专辑: -")
        self.duration_label.setText("时长: -")
        self.size_label.setText("大小: -")
        
        self.song_info_text.setHtml("<p style='color: #666;'>请选择一首歌曲查看详情</p>")
        
        self.open_browser_button.setEnabled(False)
        self.download_button.setEnabled(False)
    
    def handle_search_result(self, result):
        """处理搜索结果"""
        self.progress_bar.hide()
        self.progress_bar.setRange(0, 100)  # 恢复为正常模式
        
        # 重新启用搜索按钮和输入框
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)
        
        if result is None:
            self.statusBar().showMessage("服务器繁忙，请稍后重试")
            return
        
        if result:
            self.statusBar().showMessage(f"找到 {len(result)} 首歌曲")
            self.populate_result_table(result)
        else:
            self.statusBar().showMessage("未找到相关歌曲")
            QMessageBox.information(self, "提示", "未找到相关歌曲")
    
    def handle_get_song_result(self, result):
        """处理获取歌曲详情结果"""
        self.progress_bar.hide()
        
        if result is None:
            self.statusBar().showMessage("获取歌曲详情失败")
            return
        
        self.current_song = result
        self.update_detail_panel(result)
        self.statusBar().showMessage(f"已加载歌曲: {result['song']}")
    
    def handle_download_song(self, result, song_name, singer):
        """处理下载歌曲结果"""
        if result is None:
            self.statusBar().showMessage("获取下载链接失败")
            QMessageBox.warning(self, "警告", "获取下载链接失败")
            return
        
        # 获取下载链接
        download_url = result.get("url")
        if not download_url:
            self.statusBar().showMessage("未找到下载链接")
            QMessageBox.warning(self, "警告", "未找到下载链接")
            return
        
        # 选择保存路径
        default_filename = f"{song_name} - {singer}.mp3"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存音频文件", default_filename, "MP3 Files (*.mp3);;All Files (*)")
        
        if not save_path:
            self.statusBar().showMessage("已取消下载")
            self.progress_bar.hide()  # 取消下载时隐藏进度条
            return
        
        # 开始下载 - 禁用搜索和选择其他歌曲功能
        self.statusBar().showMessage(f"正在下载: {song_name}")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        # 禁用搜索和选择功能
        self.search_input.setEnabled(False)
        self.search_button.setEnabled(False)
        self.result_table.setEnabled(False)
        
        # 使用PyQt5的QNetworkAccessManager进行下载
        self.download_manager = QNetworkAccessManager()
        self.download_manager.finished.connect(lambda reply: self.on_download_finished(reply, save_path, song_name))
        self.download_reply = self.download_manager.get(QNetworkRequest(QUrl(download_url)))
        self.download_reply.downloadProgress.connect(self.on_download_progress)
    
    def on_download_progress(self, received, total):
        """下载进度回调"""
        if total > 0:
            progress = int(received * 100 / total)
            self.progress_bar.setValue(progress)
    
    def on_download_finished(self, reply, save_path, song_name):
        """下载完成回调"""
        self.progress_bar.hide()
        
        # 重新启用搜索和选择功能
        self.search_input.setEnabled(True)
        self.search_button.setEnabled(True)
        self.result_table.setEnabled(True)
        
        if reply.error() == QNetworkReply.NoError:
            # 保存文件
            try:
                with open(save_path, 'wb') as f:
                    f.write(reply.readAll())
                
                self.statusBar().showMessage(f"下载完成: {song_name}")
                QMessageBox.information(self, "提示", f"歌曲已成功下载到:\n{save_path}")
                
                # 询问是否打开文件
                if QMessageBox.question(self, "询问", "是否打开已下载的文件？") == QMessageBox.Yes:
                    os.startfile(save_path)
            except Exception as e:
                self.statusBar().showMessage(f"保存文件失败: {str(e)}")
                QMessageBox.warning(self, "警告", f"保存文件失败: {str(e)}")
        else:
            self.statusBar().showMessage(f"下载失败: {reply.errorString()}")
            QMessageBox.warning(self, "警告", f"下载失败: {reply.errorString()}")
        
        # 清理
        reply.deleteLater()
    
    def populate_result_table(self, songs):
        """填充结果表格"""
        self.result_table.setRowCount(len(songs))
        
        for row, song in enumerate(songs):
            # 序号列（存储ID在用户数据中）
            id_item = QTableWidgetItem(str(row + 1))
            id_item.setData(Qt.UserRole, song["id"])
            id_item.setTextAlignment(Qt.AlignCenter)
            
            # 歌曲名列
            song_item = QTableWidgetItem(song["song"])
            
            # 歌手列
            singer_item = QTableWidgetItem(song["singer"])
            
            # 设置表格项
            self.result_table.setItem(row, 0, id_item)
            self.result_table.setItem(row, 1, song_item)
            self.result_table.setItem(row, 2, singer_item)
    
    def update_detail_panel(self, song_data):
        """更新详情面板"""
        # 更新基本信息
        self.song_name_label.setText(f"歌曲名: {song_data['song']}")
        self.singer_label.setText(f"歌手: {song_data['singer']}")
        self.album_label.setText(f"专辑: {song_data['album']}")
        self.duration_label.setText(f"时长: {song_data.get('interval', '未知')}")
        self.size_label.setText(f"大小: {song_data.get('size', '未知')}")
        
        # 下载并显示封面图片
        if song_data.get('cover'):
            self.cover_manager = QNetworkAccessManager()
            self.cover_manager.finished.connect(lambda reply: self.on_cover_downloaded(reply))
            self.cover_manager.get(QNetworkRequest(QUrl(song_data['cover'])))
        
        # 更新详细信息文本框
        url = song_data.get('url', '无')
        html_content = f"""
        <h3>歌曲信息</h3>
        <p><strong>歌曲名:</strong> {song_data['song']}</p>
        <p><strong>歌手:</strong> {song_data['singer']}</p>
        <p><strong>专辑:</strong> {song_data['album']}</p>
        <p><strong>时长:</strong> {song_data.get('interval', '未知')}</p>
        <p><strong>大小:</strong> {song_data.get('size', '未知')}</p>
        <p><strong>下载链接:</strong> <a href="{url}">{url}</a></p>
        """
        
        self.song_info_text.setHtml(html_content)
        
        # 启用操作按钮
        self.open_browser_button.setEnabled(True)
        self.download_button.setEnabled(True)
    
    def on_cover_downloaded(self, reply):
        """封面图片下载完成回调"""
        if reply.error() == QNetworkReply.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            
            # 调整图片大小以适应标签
            scaled_pixmap = pixmap.scaled(
                self.cover_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            self.cover_label.setPixmap(scaled_pixmap)
            # self.cover_label.setStyleSheet("")  # 移除背景色
        
        # 清理
        reply.deleteLater()
    

    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止异步任务管理器
        self.async_manager.stop()
        
        # 清理临时目录
        if os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                try:
                    os.remove(os.path.join(self.temp_dir, file))
                except:
                    pass
            try:
                os.rmdir(self.temp_dir)
            except:
                pass
        
        event.accept()


def readQss(style):
    with open(style, 'r', encoding='utf-8') as f:
        return f.read()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置应用程序样式为Fusion，提供更好的暗色主题支持
    app.setStyle("Fusion")
    # 设置全局样式
    app.setStyleSheet(readQss("qss/DefaultMix.qss"))
    # 设置全局字体
    font = QFont("Microsoft YaHei")
    app.setFont(font)
    
    window = MelodyFetchGUI()
    window.show()
    sys.exit(app.exec_())