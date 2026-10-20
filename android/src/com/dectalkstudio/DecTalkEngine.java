package com.dectalkstudio;

import android.content.Context;
import android.content.res.AssetManager;
import android.util.Log;
import java.io.*;

/** Runs the bundled DECtalk render server (libdtserver.so) as a child process. */
public class DecTalkEngine {
    private static final String TAG = "DECtalk";
    private final Context ctx;
    private final File workDir;
    private final File outWav;
    private Process proc;
    private BufferedReader reader;
    private OutputStream writer;

    public DecTalkEngine(Context ctx) {
        this.ctx = ctx.getApplicationContext();
        this.workDir = new File(this.ctx.getFilesDir(), "dectalk");
        this.outWav = new File(this.ctx.getCacheDir(), "render.wav");
    }

    private void copyAsset(AssetManager am, String name, File dest) throws IOException {
        dest.getParentFile().mkdirs();
        InputStream in = am.open(name);
        File tmp = new File(dest.getPath() + ".tmp");
        OutputStream out = new FileOutputStream(tmp);
        byte[] buf = new byte[65536];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        out.close();
        in.close();
        tmp.renameTo(dest);
    }

    private boolean alive() {
        if (proc == null) return false;
        try { proc.exitValue(); return false; } catch (IllegalThreadStateException e) { return true; }
    }

    public synchronized boolean ensureStarted() {
        if (alive()) return true;
        try {
            AssetManager am = ctx.getAssets();
            File stamp = new File(workDir, "version");
            String ver = "1";
            boolean fresh = !stamp.exists();
            if (!fresh) {
                BufferedReader r = new BufferedReader(new FileReader(stamp));
                fresh = !ver.equals(r.readLine());
                r.close();
            }
            if (fresh) {
                copyAsset(am, "dectalk/DECtalk.conf", new File(workDir, "DECtalk.conf"));
                copyAsset(am, "dectalk/dic/dtalk_us.dic", new File(workDir, "dic/dtalk_us.dic"));
                FileWriter w = new FileWriter(stamp);
                w.write(ver);
                w.close();
            }
            File exe = new File(ctx.getApplicationInfo().nativeLibraryDir, "libdtserver.so");
            ProcessBuilder pb = new ProcessBuilder(exe.getAbsolutePath());
            pb.directory(workDir);
            proc = pb.start();
            final InputStream err = proc.getErrorStream();
            Thread drain = new Thread(new Runnable() {
                public void run() {
                    try { byte[] b = new byte[4096]; while (err.read(b) >= 0) { } } catch (IOException ignored) { }
                }
            });
            drain.setDaemon(true);
            drain.start();
            reader = new BufferedReader(new InputStreamReader(proc.getInputStream(), "UTF-8"));
            writer = proc.getOutputStream();
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.startsWith("READY")) return true;
                if (line.startsWith("FAIL")) break;
            }
            Log.e(TAG, "engine did not start: " + line);
        } catch (Exception e) {
            Log.e(TAG, "engine start failed", e);
        }
        stop();
        return false;
    }

    /** Renders DECtalk text to a WAV file and returns its bytes, or null on failure. */
    public synchronized byte[] render(String text) {
        for (int attempt = 0; attempt < 2; attempt++) {
            if (!ensureStarted()) return null;
            try {
                outWav.delete();
                String clean = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ');
                writer.write((outWav.getAbsolutePath() + "\t" + clean + "\n").getBytes("UTF-8"));
                writer.flush();
                String reply = reader.readLine();
                if (reply == null) { stop(); continue; }
                if (!reply.startsWith("OK")) return null;
                return readAll(outWav);
            } catch (IOException e) {
                Log.e(TAG, "render failed", e);
                stop();
            }
        }
        return null;
    }

    /** Returns DECtalk's pronunciation log (phonemes + syllable marks) for plain text, or null. */
    public synchronized String phonemes(String text) {
        File logFile = new File(ctx.getCacheDir(), "phonemes.log");
        for (int attempt = 0; attempt < 2; attempt++) {
            if (!ensureStarted()) return null;
            try {
                logFile.delete();
                String clean = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
                        .replace('[', ' ').replace(']', ' ');
                writer.write(("PHON\t" + logFile.getAbsolutePath() + "\t18\t" + clean + "\n").getBytes("UTF-8"));
                writer.flush();
                String reply = reader.readLine();
                if (reply == null) { stop(); continue; }
                if (!reply.startsWith("OK") || !logFile.exists()) return null;
                return new String(readAll(logFile), "ISO-8859-1");
            } catch (IOException e) {
                Log.e(TAG, "phoneme lookup failed", e);
                stop();
            }
        }
        return null;
    }

    private static byte[] readAll(File f) throws IOException {
        FileInputStream in = new FileInputStream(f);
        ByteArrayOutputStream out = new ByteArrayOutputStream((int) f.length());
        byte[] buf = new byte[65536];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        in.close();
        return out.toByteArray();
    }

    public synchronized void stop() {
        if (proc != null) {
            try { writer.write("QUIT\n".getBytes()); writer.flush(); } catch (Exception ignored) { }
            proc.destroy();
            proc = null;
        }
    }
}
