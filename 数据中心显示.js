// ==UserScript==
// @name         Cloudflare CDN检测脚本
// @version      1.0
// @author       PoppyGuy
// @description  根据网页标头中的CF-Ray字段提取Cloudflare数据中心，并在页面右上角显示相应内容，方便用于IP优选站点识别。
// @match        *://*/*
// @grant        GM_setClipboard
// @icon         https://www.cloudflare-cn.com/favicon.ico
// @license MIT
// @namespace https://greasyfork.org/users/1304869
// @downloadURL https://update.greasyfork.org/scripts/495659/Cloudflare%20CDN%E6%A3%80%E6%B5%8B%E8%84%9A%E6%9C%AC.user.js
// @updateURL https://update.greasyfork.org/scripts/495659/Cloudflare%20CDN%E6%A3%80%E6%B5%8B%E8%84%9A%E6%9C%AC.meta.js
// ==/UserScript==

(function() {
    'use strict';

    let headersCache = {}; // 缓存标头信息

    function checkCDNStatus() {
        if (headersCache[window.location.href]) {
            processCFRayHeader(headersCache[window.location.href]);
        } else {
            let xhr = new XMLHttpRequest();
            xhr.open('HEAD', window.location.href, true);
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4) {
                    headersCache[window.location.href] = xhr.getAllResponseHeaders();
                    processCFRayHeader(headersCache[window.location.href]);
                }
            };
            xhr.send();
        }
    }

    function processCFRayHeader(headers) {
        let cfRayHeader = headers.match(/cf-ray: (.*)/i);
        if (cfRayHeader) {
            // 提取数据中心代码，格式通常是 "xxxxxxxxxx-XXX"，我们需要最后的 XXX 部分
            let cfRayValue = cfRayHeader[1].trim();
            let dataCenterCode = cfRayValue.split('-').pop();
            
            if (dataCenterCode) {
                showDataCenter(dataCenterCode);
            }
        }
    }

    function showDataCenter(dataCenterCode) {
        removeDataCenterDisplay(); // 清除之前的显示

        let containerDiv = document.createElement('div');
        containerDiv.className = 'cf-datacenter-container';
        containerDiv.style.cssText = "position: fixed; top: 50px; right: 20px; padding: 10px 15px; border-radius: 8px; font-weight: bold; z-index: 999999; font-size: 22px; text-align: center; color: #fff; background: linear-gradient(45deg, #00FF42, #74F3D4, #045DE9); box-shadow: 0 2px 10px rgba(0,0,0,0.2); display: flex; align-items: center;";
        
        let textSpan = document.createElement('span');
        textSpan.textContent = dataCenterCode;
        textSpan.style.cssText = "margin-right: 10px; cursor: pointer; letter-spacing: 1px; -webkit-text-stroke: 1px #000; text-shadow: 0 0 8px rgba(0,0,0,0.7), 0 0 3px #000; font-family: Arial, sans-serif;";
        containerDiv.appendChild(textSpan);
        
        // 添加关闭按钮
        let closeButton = document.createElement('span');
        closeButton.textContent = '×';
        closeButton.style.cssText = "cursor: pointer; font-size: 20px; width: 20px; height: 20px; line-height: 18px; text-align: center; border-radius: 50%; background-color: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center;";
        closeButton.addEventListener('click', function(e) {
            e.stopPropagation(); // 阻止事件冒泡
            containerDiv.remove();
        });
        containerDiv.appendChild(closeButton);
        
        // 点击文本部分复制主机名
        textSpan.addEventListener('click', function() {
            GM_setClipboard(window.location.hostname);
            textSpan.style.color = 'gold';
            setTimeout(() => {
                textSpan.style.color = '#fff';
            }, 500);
        });

        document.body.appendChild(containerDiv);
    }

    function removeDataCenterDisplay() {
        let existingDisplay = document.querySelector('.cf-datacenter-container');
        if (existingDisplay) {
            existingDisplay.remove();
        }
    }

    checkCDNStatus();
})();
