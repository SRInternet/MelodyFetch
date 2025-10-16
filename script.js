document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const welcomeScreen = document.getElementById('welcomeScreen');
    const searchResultsArea = document.getElementById('searchResultsArea');
    const searchContainer = document.getElementById('searchContainer');
    const floatingSearchContainer = document.getElementById('floatingSearchContainer');
    const searchInput = document.getElementById('searchInput');
    const floatingSearchInput = document.getElementById('floatingSearchInput');
    const searchButton = document.getElementById('searchButton');
    const floatingSearchButton = document.getElementById('floatingSearchButton');
    const progressContainer = document.getElementById('progressContainer');
    const resultsContainer = document.getElementById('resultsContainer');
    const songDetailPage = document.getElementById('songDetailPage');
    const detailCard = document.getElementById('detailCard');
    const closeDetailButton = document.getElementById('closeDetailButton');
    const songCover = document.getElementById('songCover');
    const songName = document.getElementById('detailSongName');
    const artist = document.getElementById('detailArtist');
    const album = document.getElementById('detailAlbum');
    const duration = document.getElementById('detailDuration');
    const downloadButton = document.getElementById('downloadButton');
    const openInBrowserButton = document.getElementById('openInBrowserButton');
    const playPreview = document.getElementById('playPreview');
    // 新增元素
    const notification = document.getElementById('notification');
    const notificationIcon = document.getElementById('notificationIcon');
    const notificationMessage = document.getElementById('notificationMessage');
    const backButton = document.getElementById('backButton');
    
    // 当前选中的歌曲
    let currentSong = null;
    let audioPlayer = null;
    let isPlaying = false;
    
    // 初始化主题
    function initializeTheme() {
        const savedTheme = getThemePreference();
        if (savedTheme) {
            setTheme(savedTheme);
        } else {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            setTheme(prefersDark ? 'dark' : 'light');
        }
    }
    
    function getThemePreference() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'theme') {
                return value;
            }
        }
        return null;
    }
    
    function setTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            themeIcon.className = 'fa fa-sun-o';
        } else {
            document.documentElement.classList.remove('dark');
            themeIcon.className = 'fa fa-moon-o';
        }
        document.cookie = `theme=${theme}; max-age=${30 * 24 * 60 * 60}; path=/`;
    }
    
    // 主题切换
    themeToggle.addEventListener('click', function() {
        const isDark = document.documentElement.classList.contains('dark');
        setTheme(isDark ? 'light' : 'dark');
    });
    
    // 搜索音乐
    async function searchMusic(keyword) {
        if (!keyword.trim()) {
            log('错误: 请输入歌曲名或歌手名');
            showNotification('请输入歌曲名或歌手名', 'warning');
            return;
        }
        
        // 禁用搜索按钮，防止重复点击
        searchButton.disabled = true;
        floatingSearchButton.disabled = true;
        searchButton.classList.add('opacity-70', 'cursor-not-allowed');
        floatingSearchButton.classList.add('opacity-70', 'cursor-not-allowed');
        
        // 同步搜索框文本
        floatingSearchInput.value = keyword;
        
        // 显示搜索结果区域和进度条
        welcomeScreen.classList.add('opacity-0');
        setTimeout(() => {
            welcomeScreen.classList.add('hidden');
            searchResultsArea.classList.remove('hidden');
            progressContainer.classList.remove('hidden');
        }, 500);
        
        // 清空之前的搜索结果
        resultsContainer.innerHTML = '';
        
        try {
            // 调用API搜索音乐
            log(`开始搜索歌曲: ${keyword}`);
            const results = await fetchSongs(keyword);
            
            if (results && results.length > 0) {
                log(`搜索成功，找到 ${results.length} 首歌曲`);
                // 显示搜索结果
                displayResults(results);
            } else {
                log('未找到相关歌曲');
                // 显示无结果提示
                displayNoResults();
            }
        } catch (error) {
            log(`搜索音乐时出错: ${error.message}`);
            console.error('搜索音乐时出错:', error);
            displayNoResults('网络错误，请稍后重试');
        } finally {
            // 确保进度条隐藏，即使在错误情况下
            setTimeout(() => {
                progressContainer.classList.add('hidden');
                // 重新启用搜索按钮
                searchButton.disabled = false;
                floatingSearchButton.disabled = false;
                searchButton.classList.remove('opacity-70', 'cursor-not-allowed');
                floatingSearchButton.classList.remove('opacity-70', 'cursor-not-allowed');
            }, 300);
        }
    }
    
    // 调用API搜索音乐 - 复用MelodyFetch_GUI.py的搜索方法
    async function fetchSongs(keyword) {
        log(`[DEBUG] 开始搜索歌曲: ${keyword}`);
        const encodedKeyword = encodeURIComponent(keyword);
        const url = `https://api.vkeys.cn/v2/music/netease?word=${encodedKeyword}&page=1&num=10`;
        log(`[DEBUG] 搜索URL: ${url}`);
        
        const headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive'
        };
        
        // 实现重试机制 - 复用MelodyFetch_GUI.py的逻辑
        const maxRetries = 3;
        let retryCount = 0;
        let response;
        
        while (retryCount < maxRetries) {
            try {
                log(`[DEBUG] 尝试 ${retryCount + 1}/${maxRetries}，发送请求...`);
                response = await fetch(url, { headers });
                log(`[DEBUG] 响应状态码: ${response.status}`);
                
                if (response.status === 200) {
                    const data = await response.json();
                    log(`[DEBUG] API响应: ${JSON.stringify(data)}`);
                    
                    if (data.code === 200 && data.data) {
                        log(`[DEBUG] 搜索成功，找到 ${data.data.length} 首歌曲`);
                        return data.data;
                    } else {
                        log(`[DEBUG] API返回错误码: ${data.code}, 消息: ${data.msg}`);
                        // 准备重试
                        retryCount++;
                        if (retryCount < maxRetries) {
                            const waitTime = Math.floor(Math.random() * 5) + 1;
                            log(`[DEBUG] 准备重试，等待 ${waitTime} 秒`);
                            await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
                            continue;
                        }
                        throw new Error(`API返回错误: ${data.msg || '未知错误'}`);
                    }
                } else {
                    log(`[DEBUG] HTTP错误: 状态码 ${response.status}`);
                    // 准备重试
                    retryCount++;
                    if (retryCount < maxRetries) {
                        const waitTime = Math.floor(Math.random() * 5) + 1;
                        log(`[DEBUG] 准备重试，等待 ${waitTime} 秒`);
                        await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
                        continue;
                    }
                    throw new Error(`HTTP错误: 状态码 ${response.status}`);
                }
            } catch (error) {
                log(`[DEBUG] 请求异常: ${error.message}`);
                retryCount++;
                if (retryCount >= maxRetries) {
                    log(`[DEBUG] 达到最大重试次数，搜索失败`);
                    throw error;
                }
                // 等待一段时间后重试
                const waitTime = Math.floor(Math.random() * 5) + 1;
                log(`[DEBUG] 准备重试，等待 ${waitTime} 秒`);
                await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
            }
        }
    }
    
    // 显示搜索结果
    function displayResults(songs) {
        songs.forEach(song => {
            const songItem = document.createElement('div');
            songItem.className = 'song-item';
            songItem.dataset.songId = song.id;
            
            // 格式化时长
            const formattedDuration = formatDuration(song.interval || '');
            
            songItem.innerHTML = `
                <img src="${song.cover || 'https://via.placeholder.com/64/cccccc/999999?text=No+Cover'}" alt="${song.song}" class="song-cover">
                <div class="song-info">
                    <div class="song-name">${song.song}</div>
                    <div class="song-artist">${song.singer}</div>
                </div>
                <div class="song-duration">${formattedDuration}</div>
            `;
            
            songItem.addEventListener('click', () => {
                showSongDetail(song.id);
            });
            
            // 添加动画延迟
            songItem.style.opacity = '0';
            songItem.style.transform = 'translateY(20px)';
            
            resultsContainer.appendChild(songItem);
            
            // 触发动画
            setTimeout(() => {
                songItem.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                songItem.style.opacity = '1';
                songItem.style.transform = 'translateY(0)';
            }, 50);
        });
    }
    
    // 格式化时长
    function formatDuration(seconds) {
        if (!seconds || isNaN(seconds)) return '--:--';
        
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    // 显示无结果提示
    function displayNoResults(message = '未找到相关歌曲') {
        resultsContainer.innerHTML = `
            <div class="no-results">
                <i class="fa fa-music text-5xl mb-4 opacity-20"></i>
                <p class="text-xl">${message}</p>
            </div>
        `;
    }
    
    // 显示歌曲详情
    async function showSongDetail(songId) {
        try {
            log(`显示歌曲详情: ID = ${songId}`);
            const songData = await getSongById(songId);
            if (songData) {
                currentSong = songData;
                updateDetailPanel(songData);
                
                // 显示详情页
                songDetailPage.classList.remove('hidden');
                // 添加动画
                setTimeout(() => {
                    detailCard.classList.add('detail-card-enter');
                }, 10);
            }
        } catch (error) {
            log(`获取歌曲详情时出错: ${error.message}`);
            console.error('获取歌曲详情时出错:', error);
            alert('获取歌曲详情失败，请稍后重试');
        }
    }
    
    // 通过ID获取歌曲详情 - 复用MelodyFetch_GUI.py的逻辑
    async function getSongById(songId) {
        log(`[DEBUG] 开始获取歌曲详情: ID = ${songId}`);
        const url = `https://api.vkeys.cn/v2/music/netease?id=${songId}`;
        log(`[DEBUG] 请求URL: ${url}`);
        
        const headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive'
        };
        
        // 实现重试机制
        const maxRetries = 3;
        let retryCount = 0;
        let response;
        
        while (retryCount <= maxRetries) {
            try {
                log(`[DEBUG] 重试次数: ${retryCount}/${maxRetries}`);
                response = await fetch(url, { headers });
                log(`[DEBUG] 响应状态码: ${response.status}`);
                
                if (response.status === 200) {
                    const data = await response.json();
                    log(`[DEBUG] API响应: ${JSON.stringify(data)}`);
                    
                    // 检查是否为503错误，如果是则重试
                    if (data.code === 503) {
                        log(`[DEBUG] 遇到503错误，准备重试`);
                        retryCount++;
                        if (retryCount <= maxRetries) {
                            log(`[DEBUG] 等待1秒后重试...`);
                            await new Promise(resolve => setTimeout(resolve, 1000));
                            continue;
                        } else {
                            log(`[DEBUG] 达到最大重试次数，获取失败`);
                            throw new Error('达到最大重试次数，获取失败');
                        }
                    }
                    
                    if (data.code === 200 && data.data) {
                        log(`[DEBUG] 获取歌曲详情成功`);
                        return data.data;
                    } else {
                        log(`[DEBUG] API返回错误码: ${data.code}, 消息: ${data.msg}`);
                        throw new Error(`API返回错误: ${data.msg || '未知错误'}`);
                    }
                } else {
                    log(`[DEBUG] HTTP错误: 状态码 ${response.status}`);
                    throw new Error(`HTTP错误: 状态码 ${response.status}`);
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    throw error;
                }
                log(`[DEBUG] 请求异常: ${error.message}`);
                retryCount++;
                if (retryCount <= maxRetries) {
                    log(`[DEBUG] 等待1秒后重试...`);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    continue;
                } else {
                    log(`[DEBUG] 达到最大重试次数，获取失败`);
                    throw error;
                }
            }
        }
    }
    
    // 更新详情面板，添加音乐进度条
    function updateDetailPanel(songData) {
        songCover.src = songData.cover || 'https://via.placeholder.com/300/cccccc/999999?text=No+Cover';
        songCover.alt = songData.song;
        // 更新详情页的各个信息元素
        document.getElementById('detailSongName').textContent = songData.song;
        document.getElementById('detailArtist').textContent = `歌手: ${songData.singer}`;
        document.getElementById('detailAlbum').textContent = `专辑: ${songData.album || '未知'}`;
        document.getElementById('detailDuration').textContent = `时长: ${formatDuration(songData.interval || 0)}`;
        
        // 初始化进度条
        initProgressBar();
    }
    
    // 关闭详情页
    function closeDetailPage() {
        detailCard.classList.remove('detail-card-enter');
        setTimeout(() => {
            songDetailPage.classList.add('hidden');
            // 停止播放
            if (audioPlayer) {
                audioPlayer.pause();
                audioPlayer = null;
                isPlaying = false;
                playPreview.querySelector('i').className = 'fa fa-play text-purple-600 text-xl';
            }
        }, 300);
    }
    
    // 初始化进度条
    function initProgressBar() {
        // 检查是否已经有进度条，如果有则移除
        const existingProgressBar = document.getElementById('progressContainerWrapper');
        if (existingProgressBar) {
            existingProgressBar.remove();
        }
        
        // 创建进度条容器
        const progressWrapper = document.createElement('div');
        progressWrapper.id = 'progressContainerWrapper';
        progressWrapper.className = 'mt-4';
        
        // 创建进度条HTML结构
        progressWrapper.innerHTML = `
            <div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 mb-1">
                <span id="currentTime">00:00</span>
                <span id="totalTime">${formatDuration(currentSong.interval || 0)}</span>
            </div>
            <div class="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div id="progressFill" class="absolute top-0 left-0 h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full" style="width: 0%"></div>
                <div id="progressHandle" class="absolute w-4 h-4 bg-white dark:bg-gray-300 rounded-full shadow-md -mt-1 cursor-pointer" style="left: 0%"></div>
            </div>
        `;
        
        // 插入到详情卡片中
        const detailCardContent = document.querySelector('#detailCard .p-6');
        const actionButtons = detailCardContent.querySelector('.flex.flex-wrap.gap-3');
        actionButtons.parentNode.insertBefore(progressWrapper, actionButtons.nextSibling);
        
        // 添加进度条事件监听
        const progressBar = document.querySelector('#progressContainerWrapper .relative');
        const progressFill = document.getElementById('progressFill');
        const progressHandle = document.getElementById('progressHandle');
        const currentTimeDisplay = document.getElementById('currentTime');
        
        // 点击进度条跳转
        progressBar.addEventListener('click', function(e) {
            if (!audioPlayer) return;
            
            const rect = progressBar.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            const seekTime = pos * audioPlayer.duration;
            
            audioPlayer.currentTime = seekTime;
            updateProgressBar();
        });
        
        // 拖动进度条
        let isDragging = false;
        progressHandle.addEventListener('mousedown', function() {
            isDragging = true;
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging || !audioPlayer) return;
            
            const rect = progressBar.getBoundingClientRect();
            let pos = (e.clientX - rect.left) / rect.width;
            pos = Math.max(0, Math.min(1, pos)); // 限制在0-1之间
            
            // 更新进度条UI，但不立即更新音频.currentTime
            progressFill.style.width = `${pos * 100}%`;
            progressHandle.style.left = `${pos * 100}%`;
            
            const seekTime = pos * audioPlayer.duration;
            currentTimeDisplay.textContent = formatDuration(seekTime || 0);
        });
        
        document.addEventListener('mouseup', function() {
            if (!isDragging || !audioPlayer) {
                isDragging = false;
                return;
            }
            
            const rect = progressBar.getBoundingClientRect();
            let pos = (event.clientX - rect.left) / rect.width;
            pos = Math.max(0, Math.min(1, pos)); // 限制在0-1之间
            
            const seekTime = pos * audioPlayer.duration;
            audioPlayer.currentTime = seekTime;
            updateProgressBar();
            
            isDragging = false;
        });
    }
    
    // 更新进度条
    function updateProgressBar() {
        if (!audioPlayer) return;
        
        const progressFill = document.getElementById('progressFill');
        const progressHandle = document.getElementById('progressHandle');
        const currentTimeDisplay = document.getElementById('currentTime');
        const totalTimeDisplay = document.getElementById('totalTime');
        
        if (!progressFill || !progressHandle || !currentTimeDisplay || !totalTimeDisplay) return;
        
        // 确保音频有有效的时长
        if (isNaN(audioPlayer.duration) || audioPlayer.duration === Infinity) {
            // 如果无法获取准确时长，使用歌曲数据中的时长
            const songDuration = currentSong && currentSong.interval ? currentSong.interval : 0;
            totalTimeDisplay.textContent = formatDuration(songDuration);
            
            // 显示加载中的进度条状态
            progressFill.style.width = '0%';
            progressHandle.style.left = '0%';
            currentTimeDisplay.textContent = '00:00';
            return;
        }
        
        // 更新总时长显示
        totalTimeDisplay.textContent = formatDuration(audioPlayer.duration);
        
        // 更新当前时间和进度
        const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
        progressFill.style.width = `${progress}%`;
        progressHandle.style.left = `${progress}%`;
        currentTimeDisplay.textContent = formatDuration(audioPlayer.currentTime || 0);
    }
    
    // 在线试听，支持进度条
    function togglePreview() {
        if (!currentSong || !currentSong.url) {
            alert('暂无试听资源');
            return;
        }
        
        if (isPlaying && audioPlayer) {
            // 停止播放
            log(`停止播放: ${currentSong.song}`);
            audioPlayer.pause();
            audioPlayer = null;
            isPlaying = false;
            playPreview.querySelector('i').className = 'fa fa-play text-purple-600 text-xl';
            
            // 清除进度条更新间隔
            if (window.progressInterval) {
                clearInterval(window.progressInterval);
                window.progressInterval = null;
            }
        } else {
            // 开始播放
            log(`开始播放: ${currentSong.song}`);
            
            // 使用预加载模式确保能获取准确时长
            audioPlayer = new Audio();
            audioPlayer.src = currentSong.url;
            audioPlayer.preload = 'metadata';
            
            // 监听元数据加载完成
            audioPlayer.onloadedmetadata = function() {
                log(`音频元数据加载完成，时长: ${audioPlayer.duration}秒`);
                updateProgressBar(); // 更新进度条显示准确时长
            };
            
            // 监听可播放事件再开始播放
            audioPlayer.oncanplay = function() {
                audioPlayer.play().catch(error => {
                    log(`播放失败: ${error.message}`);
                    console.error('播放失败:', error);
                    showNotification('播放失败，请稍后重试', 'error');
                });
            };
            
            isPlaying = true;
            playPreview.querySelector('i').className = 'fa fa-pause text-purple-600 text-xl';
            
            // 监听播放结束
            audioPlayer.onended = function() {
                log(`播放结束: ${currentSong.song}`);
                isPlaying = false;
                playPreview.querySelector('i').className = 'fa fa-play text-purple-600 text-xl';
                
                // 清除进度条更新间隔
                if (window.progressInterval) {
                    clearInterval(window.progressInterval);
                    window.progressInterval = null;
                }
                
                // 重置进度条
                updateProgressBar();
            };
            
            // 定期更新进度条
            if (window.progressInterval) {
                clearInterval(window.progressInterval);
            }
            window.progressInterval = setInterval(updateProgressBar, 500);
        }
    }
    
    // // 下载音乐
    // function downloadMusic() {
    //     if (!currentSong || !currentSong.url) {
    //         showNotification('暂无下载资源', 'warning');
    //         log('下载失败: currentSong或currentSong.url不存在');
    //         return;
    //     }
        
    //     // 检查URL有效性
    //     try {
    //         new URL(currentSong.url);
    //     } catch (e) {
    //         showNotification('下载链接无效', 'error');
    //         log(`下载失败: 无效的URL - ${currentSong.url}`);
    //         console.error('无效的URL:', currentSong.url);
    //         return;
    //     }
        
    //     log(`准备下载: ${currentSong.song} - ${currentSong.singer} (URL: ${currentSong.url})`);
        
    //     // 显示正在获取下载链接的提示
    //     showNotification(`正在获取下载链接，请稍候...`, 'info');
        
    //     // 使用fetch来获取文件然后创建BlobURL
    //     fetch(currentSong.url, {
    //         mode: 'cors',
    //         headers: {
    //             'Accept': 'audio/*'
    //         }
    //     })
    //         .then(response => {
    //             if (!response.ok) {
    //                 const errorMsg = `HTTP错误: ${response.status} ${response.statusText}`;
    //                 log(`下载失败: ${errorMsg}`);
    //                 console.error('下载失败:', errorMsg, response);
    //                 throw new Error(errorMsg);
    //             }
    //             return response.blob();
    //         })
    //         .then(blob => {
    //             // 创建Blob URL
    //             const blobUrl = URL.createObjectURL(blob);
    //             log('下载成功，创建Blob URL');
                
    //             // 创建下载链接
    //             const downloadLink = document.createElement('a');
    //             downloadLink.href = blobUrl;
    //             downloadLink.download = `${currentSong.song} - ${currentSong.singer}.mp3`;
                
    //             // 触发下载
    //             document.body.appendChild(downloadLink);
    //             downloadLink.click();
    //             document.body.removeChild(downloadLink);
                
    //             // 清理Blob URL
    //             setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
                
    //             // 下载成功提示
    //             showNotification(`开始下载: ${currentSong.song} - ${currentSong.singer}`, 'success');
    //         })
    //         .catch(error => {
    //             log(`下载失败: ${error.message}`);
    //             console.error('下载失败:', error);
    //             showNotification(`下载失败: ${error.message}\n请尝试"在浏览器中打开"后手动下载`, 'error');
    //         });
    // }

    // 下载音乐 - 使用CORS代理
    // function downloadMusic() {
    //     if (!currentSong || !currentSong.url) {
    //         showNotification('暂无下载资源', 'warning');
    //         log('下载失败: currentSong或currentSong.url不存在');
    //         return;
    //     }

    //     log(`准备下载: ${currentSong.song} - ${currentSong.singer} (URL: ${currentSong.url})`);
    //     showNotification(`正在获取下载链接，请稍候...`, 'info');

    //     // 使用CORS代理
    //     const proxyUrl = 'https://crossorigin.me/'; // 公共CORS代理
        
    //     const targetUrl = currentSong.url;
    //     const finalUrl = proxyUrl + targetUrl;

    //     fetch(finalUrl, {
    //         mode: 'cors',
    //         headers: {
    //             'Accept': 'audio/*',
    //             'Origin': window.location.origin
    //         }
    //     })
    //     .then(response => {
    //         if (!response.ok) {
    //             throw new Error(`HTTP错误: ${response.status}`);
    //         }
    //         return response.blob();
    //     })
    //     .then(blob => {
    //         const blobUrl = URL.createObjectURL(blob);
    //         const downloadLink = document.createElement('a');
    //         downloadLink.href = blobUrl;
    //         downloadLink.download = `${currentSong.song} - ${currentSong.singer}.mp3`;
            
    //         document.body.appendChild(downloadLink);
    //         downloadLink.click();
    //         document.body.removeChild(downloadLink);
            
    //         setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
    //         showNotification(`开始下载: ${currentSong.song}`, 'success');
    //     })
    //     .catch(error => {
    //         log(`下载失败: ${error.message}`);
    //         console.error('下载失败:', error);
            
    //         // 备用方案：直接打开链接
    //         showNotification(`下载失败，尝试直接打开链接...`, 'warning');
    //         setTimeout(() => {
    //             window.open(currentSong.url, '_blank');
    //         }, 1000);
    //     });
    // }

   // 最简单的解决方案 - 避免CORS问题
    function downloadMusic() {
        if (!currentSong || !currentSong.url) {
            showNotification('暂无下载资源', 'warning');
            return;
        }

        // 直接创建下载链接，让浏览器处理
        const link = document.createElement('a');
        link.href = currentSong.url;
        link.download = `${currentSong.song} - ${currentSong.singer}.mp3`;
        link.target = '_blank';
        
        // 添加到DOM并触发点击
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification('下载已开始，如未自动下载请右键另存为', 'info');
    }
    
    // 在浏览器中打开歌曲
    function openInBrowser() {
        if (!currentSong || !currentSong.id) {
            showNotification('无法打开此歌曲', 'error');
            return;
        }
        
        const musicUrl = `https://music.163.com/song?id=${currentSong.id}`;
        log(`在浏览器中打开歌曲: ${currentSong.song}, URL: ${musicUrl}`);
        window.open(musicUrl, '_blank');
    }
    
    // 日志输出函数
    function log(message) {
        // 在控制台输出日志
        console.log(`[MelodyFetch] ${new Date().toLocaleTimeString()} - ${message}`);
        
        // 可以在这里添加更多的日志处理逻辑，比如保存到本地存储等
    }
    
    // 事件监听
    searchButton.addEventListener('click', () => searchMusic(searchInput.value));
    floatingSearchButton.addEventListener('click', () => searchMusic(floatingSearchInput.value));
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchMusic(searchInput.value);
    });
    floatingSearchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchMusic(floatingSearchInput.value);
    });
    closeDetailButton.addEventListener('click', closeDetailPage);
    downloadButton.addEventListener('click', downloadMusic);
    openInBrowserButton.addEventListener('click', openInBrowser);
    playPreview.addEventListener('click', togglePreview);
    // 返回按钮事件
    backButton.addEventListener('click', function() {
        log('返回首页');
        searchResultsArea.classList.add('hidden');
        welcomeScreen.classList.remove('hidden');
        // 重置欢迎界面的样式
        setTimeout(() => {
            welcomeScreen.classList.remove('opacity-0');
        }, 10);
    });
    
    // 点击详情页外部关闭
    songDetailPage.addEventListener('click', (e) => {
        if (e.target === songDetailPage) {
            closeDetailPage();
        }
    });
    
    // 初始化主题
    initializeTheme();
    
    // 显示初始化完成的通知
    showNotification('MelodyFetch 无损音乐解析工具已初始化完成', 'success', 3000);
    
    log('MelodyFetch WebUI 已初始化完成');
    
    // 显示通知函数
    function showNotification(message, type = 'info', duration = 3000) {
        // 设置通知内容
        notificationMessage.textContent = message;
        
        // 根据类型设置图标和颜色
        switch (type) {
            case 'success':
                notificationIcon.className = 'fa fa-check-circle text-green-500 mr-3';
                break;
            case 'error':
                notificationIcon.className = 'fa fa-exclamation-circle text-red-500 mr-3';
                break;
            case 'warning':
                notificationIcon.className = 'fa fa-exclamation-triangle text-yellow-500 mr-3';
                break;
            default:
                notificationIcon.className = 'fa fa-info-circle text-purple-500 mr-3';
        }
        
        // 显示通知
        notification.classList.remove('-translate-y-full');
        
        // 设置定时器，在指定时间后隐藏通知
        setTimeout(() => {
            notification.classList.add('-translate-y-full');
        }, duration);
    }
});