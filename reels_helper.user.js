// ==UserScript==
// @name         Reels Auto-Transcription Webhook Helper
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Sends a webhook to local Python script when scrolling/changing Reels (Instagram/YouTube/TikTok) to automate transcription and extract metadata.
// @author       Antigravity
// @match        https://www.instagram.com/reels/*
// @match        https://www.instagram.com/p/*
// @match        https://www.youtube.com/shorts/*
// @match        https://www.tiktok.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// ==/UserScript==

(function() {
    'use strict';

    let lastUrl = location.href;

    function notifyReelChange() {
        console.log("[Reels Helper] Reel changed, extracting metadata...");
        
        let title = document.title || "Reel";
        let author = "";
        
        // Site-specific selectors to scrape uploader/author names
        if (location.host.includes("instagram.com")) {
            // Instagram Reels author name
            let authorEl = document.querySelector('header a, a[href*="/reels/"], span._ap3a._aaco._aacw._aacx._aad7._aade');
            if (authorEl) author = authorEl.innerText.trim();
        } else if (location.host.includes("youtube.com")) {
            // YouTube Shorts channel name
            let authorEl = document.querySelector('#channel-name a, #text-container a, .ytd-channel-name');
            if (authorEl) author = authorEl.innerText.trim();
        } else if (location.host.includes("tiktok.com")) {
            // TikTok creator name
            let authorEl = document.querySelector('h3[data-e2e="user-title"], h3[class*="UniqueId"]');
            if (authorEl) author = authorEl.innerText.trim();
        }

        GM_xmlhttpRequest({
            method: "POST",
            url: "http://127.0.0.1:8080",
            data: JSON.stringify({
                url: location.href,
                title: title,
                author: author
            }),
            headers: {
                "Content-Type": "application/json"
            },
            onload: function(response) {
                console.log("[Reels Helper] Local webhook sent successfully!", response.responseText);
            },
            onerror: function(err) {
                console.error("[Reels Helper] Webhook failed. Is transcribe_audio.py running?", err);
            }
        });
    }

    // Monitor URL changes (which happen when scrolling between reels)
    setInterval(() => {
        if (location.href !== lastUrl) {
            lastUrl = location.href;
            notifyReelChange();
        }
    }, 500);

    // Run once at startup
    setTimeout(notifyReelChange, 2000);
})();
