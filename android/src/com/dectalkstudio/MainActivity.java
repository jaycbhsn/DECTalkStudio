package com.dectalkstudio;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.util.Base64;
import android.webkit.*;
import java.io.*;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final int REQ_OPEN = 1, REQ_SAVE = 2;
    private WebView web;
    private DecTalkEngine engine;
    private ValueCallback<Uri[]> fileCallback;
    private byte[] pendingBytes;
    private String pendingName;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.parseColor("#20242C"));
        getWindow().setNavigationBarColor(Color.parseColor("#171A20"));
        engine = new DecTalkEngine(this);
        new Thread(new Runnable() { public void run() { engine.ensureStarted(); } }).start();

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#171A20"));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setTextZoom(100);
        web.addJavascriptInterface(new Bridge(), "DTAndroid");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                return handle(req.getUrl());
            }
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return !HOST.equals(Uri.parse(url).getHost());
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = cb;
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                try {
                    startActivityForResult(Intent.createChooser(i, "Choose a file"), REQ_OPEN);
                } catch (ActivityNotFoundException e) {
                    fileCallback = null;
                    return false;
                }
                return true;
            }
        });
        setContentView(web);
        if (state != null) web.restoreState(state);
        else web.loadUrl("https://" + HOST + "/index.html");
    }

    private WebResourceResponse handle(Uri uri) {
        if (!HOST.equals(uri.getHost())) return null;
        String path = uri.getPath() == null ? "/" : uri.getPath();
        Map<String, String> headers = new HashMap<String, String>();
        headers.put("Cache-Control", "no-store");
        try {
            if (path.equals("/dt/ping")) {
                boolean ok = engine.ensureStarted();
                return new WebResourceResponse("text/plain", "utf-8", 200, "OK", headers,
                        new ByteArrayInputStream((ok ? "ok" : "fail").getBytes()));
            }
            if (path.equals("/dt/render")) {
                String q = uri.getQueryParameter("q");
                byte[] wav = q == null ? null : engine.render(q);
                if (wav == null)
                    return new WebResourceResponse("text/plain", "utf-8", 500, "Render failed", headers,
                            new ByteArrayInputStream(new byte[0]));
                return new WebResourceResponse("audio/wav", null, 200, "OK", headers, new ByteArrayInputStream(wav));
            }
            if (path.equals("/dt/phonemes")) {
                String q = uri.getQueryParameter("q");
                String log = q == null ? null : engine.phonemes(q);
                if (log == null)
                    return new WebResourceResponse("text/plain", "utf-8", 500, "Lookup failed", headers,
                            new ByteArrayInputStream(new byte[0]));
                return new WebResourceResponse("text/plain", "ISO-8859-1", 200, "OK", headers,
                        new ByteArrayInputStream(log.getBytes("ISO-8859-1")));
            }
            if (path.equals("/")) path = "/index.html";
            String mime = path.endsWith(".html") ? "text/html" : path.endsWith(".js") ? "application/javascript"
                    : path.endsWith(".css") ? "text/css" : "application/octet-stream";
            InputStream in = getAssets().open("web" + path);
            return new WebResourceResponse(mime, "utf-8", 200, "OK", headers, in);
        } catch (IOException e) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not found", headers,
                    new ByteArrayInputStream(new byte[0]));
        }
    }

    class Bridge {
        @JavascriptInterface
        public void saveFile(final String name, final String mime, String b64) {
            final byte[] bytes = Base64.decode(b64, Base64.DEFAULT);
            runOnUiThread(new Runnable() {
                public void run() {
                    pendingBytes = bytes;
                    pendingName = name;
                    Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    i.addCategory(Intent.CATEGORY_OPENABLE);
                    i.setType(mime);
                    i.putExtra(Intent.EXTRA_TITLE, name);
                    try {
                        startActivityForResult(i, REQ_SAVE);
                    } catch (ActivityNotFoundException e) {
                        notifySaved(false);
                    }
                }
            });
        }
    }

    private void notifySaved(boolean ok) {
        String n = pendingName == null ? "" : pendingName.replace("\\", "").replace("'", "\\'");
        web.evaluateJavascript("window.onSaved&&onSaved(" + ok + ",'" + n + "')", null);
        pendingBytes = null;
        pendingName = null;
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        Uri uri = (res == RESULT_OK && data != null) ? data.getData() : null;
        if (req == REQ_OPEN) {
            if (fileCallback != null) fileCallback.onReceiveValue(uri == null ? null : new Uri[]{uri});
            fileCallback = null;
        } else if (req == REQ_SAVE) {
            if (uri == null || pendingBytes == null) { notifySaved(false); return; }
            try {
                OutputStream out = getContentResolver().openOutputStream(uri, "w");
                out.write(pendingBytes);
                out.close();
                notifySaved(true);
            } catch (Exception e) {
                notifySaved(false);
            }
        }
    }

    @Override
    public void onBackPressed() {
        web.evaluateJavascript("window.onBack?onBack():false", new ValueCallback<String>() {
            public void onReceiveValue(String v) {
                if (!"true".equals(v)) MainActivity.super.onBackPressed();
            }
        });
    }

    @Override
    protected void onPause() {
        super.onPause();
        web.evaluateJavascript("window.pause&&pause()", null);
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    protected void onDestroy() {
        engine.stop();
        web.destroy();
        super.onDestroy();
    }
}
