package com.jinnproject.jinnsp;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.webkit.MimeTypeMap;

import androidx.documentfile.provider.DocumentFile;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONException;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

@CapacitorPlugin(name = "JinnSPNative")
public class JinnSPNativePlugin extends Plugin {
    private static final String[] AUDIO_EXTENSIONS = {
        ".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"
    };
    private String pendingBackupContent = "";

    @PluginMethod
    public void pickAudioFiles(PluginCall call) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("audio/*");
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(call, intent, "pickAudioFilesResult");
    }

    @ActivityCallback
    private void pickAudioFilesResult(PluginCall call, androidx.activity.result.ActivityResult result) {
        if (call == null) return;
        if (result.getResultCode() != Activity.RESULT_OK || result.getData() == null) {
            call.reject("No audio file selected.");
            return;
        }
        JSArray items = new JSArray();
        Intent data = result.getData();
        if (data.getClipData() != null) {
            for (int i = 0; i < data.getClipData().getItemCount(); i++) {
                Uri uri = data.getClipData().getItemAt(i).getUri();
                persistReadPermission(uri, data.getFlags());
                items.put(uriToTrack(uri));
            }
        } else if (data.getData() != null) {
            Uri uri = data.getData();
            persistReadPermission(uri, data.getFlags());
            items.put(uriToTrack(uri));
        }
        JSObject response = new JSObject();
        response.put("items", items);
        call.resolve(response);
    }

    @PluginMethod
    public void pickMusicFolder(PluginCall call) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
        startActivityForResult(call, intent, "pickMusicFolderResult");
    }

    @ActivityCallback
    private void pickMusicFolderResult(PluginCall call, androidx.activity.result.ActivityResult result) {
        if (call == null) return;
        if (result.getResultCode() != Activity.RESULT_OK || result.getData() == null || result.getData().getData() == null) {
            call.reject("No folder selected.");
            return;
        }
        Uri uri = result.getData().getData();
        persistReadPermission(uri, result.getData().getFlags());
        JSObject response = new JSObject();
        response.put("uri", uri.toString());
        response.put("name", displayName(uri));
        call.resolve(response);
    }

    @PluginMethod
    public void listFolderAudio(PluginCall call) {
        String uriValue = call.getString("uri", "");
        if (uriValue.isEmpty()) {
            call.reject("Folder URI is required.");
            return;
        }
        Uri uri = Uri.parse(uriValue);
        DocumentFile root = DocumentFile.fromTreeUri(getContext(), uri);
        if (root == null || !root.exists() || !root.canRead()) {
            call.reject("Folder access is not available.");
            return;
        }
        JSArray items = new JSArray();
        scanAudio(root, items);
        JSObject response = new JSObject();
        response.put("root", uriValue);
        response.put("items", items);
        call.resolve(response);
    }

    @PluginMethod
    public void saveBackup(PluginCall call) {
        String filename = call.getString("filename", "JinnSP_Backup.jinnsp");
        pendingBackupContent = call.getString("content", "");
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/octet-stream");
        intent.putExtra(Intent.EXTRA_TITLE, filename);
        startActivityForResult(call, intent, "saveBackupResult");
    }

    @ActivityCallback
    private void saveBackupResult(PluginCall call, androidx.activity.result.ActivityResult result) {
        if (call == null) return;
        if (result.getResultCode() != Activity.RESULT_OK || result.getData() == null || result.getData().getData() == null) {
            call.reject("Backup save canceled.");
            return;
        }
        try (OutputStream out = getContext().getContentResolver().openOutputStream(result.getData().getData())) {
            if (out == null) throw new IOException("Cannot open backup destination.");
            out.write(pendingBackupContent.getBytes(StandardCharsets.UTF_8));
            JSObject response = new JSObject();
            response.put("uri", result.getData().getData().toString());
            call.resolve(response);
        } catch (IOException error) {
            call.reject("Backup save failed: " + error.getMessage());
        } finally {
            pendingBackupContent = "";
        }
    }

    @PluginMethod
    public void openBackup(PluginCall call) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        String[] mimes = {"application/octet-stream", "application/json", "text/json", "*/*"};
        intent.putExtra(Intent.EXTRA_MIME_TYPES, mimes);
        startActivityForResult(call, intent, "openBackupResult");
    }

    @ActivityCallback
    private void openBackupResult(PluginCall call, androidx.activity.result.ActivityResult result) {
        if (call == null) return;
        if (result.getResultCode() != Activity.RESULT_OK || result.getData() == null || result.getData().getData() == null) {
            call.reject("Backup restore canceled.");
            return;
        }
        try {
            String content = readText(result.getData().getData());
            JSObject response = new JSObject();
            response.put("content", content);
            call.resolve(response);
        } catch (IOException error) {
            call.reject("Backup read failed: " + error.getMessage());
        }
    }

    @PluginMethod
    public void updateMediaSession(PluginCall call) {
        String title = call.getString("title", "JinnSP");
        String creator = call.getString("creator", "");
        boolean isPlaying = Boolean.TRUE.equals(call.getBoolean("isPlaying", false));
        MediaSessionHelper.update(getActivity(), title, creator, isPlaying);
        call.resolve();
    }

    private void scanAudio(DocumentFile file, JSArray items) {
        if (file.isDirectory()) {
            DocumentFile[] children = file.listFiles();
            for (DocumentFile child : children) scanAudio(child, items);
            return;
        }
        String name = file.getName();
        if (name == null || !isAudioName(name)) return;
        JSObject track = new JSObject();
        track.put("title", name.replaceFirst("\\.[^.]+$", ""));
        track.put("name", name);
        track.put("uri", file.getUri().toString());
        track.put("source", file.getUri().toString());
        track.put("source_type", "local");
        track.put("media_type", "audio");
        track.put("tags", "Android folder");
        items.put(track);
    }

    private boolean isAudioName(String name) {
        String lower = name.toLowerCase(Locale.ROOT);
        for (String ext : AUDIO_EXTENSIONS) {
            if (lower.endsWith(ext)) return true;
        }
        return false;
    }

    private JSObject uriToTrack(Uri uri) {
        String name = displayName(uri);
        JSObject track = new JSObject();
        track.put("title", name.replaceFirst("\\.[^.]+$", ""));
        track.put("name", name);
        track.put("uri", uri.toString());
        track.put("source", uri.toString());
        track.put("source_type", "local");
        track.put("media_type", "audio");
        track.put("tags", "Android");
        return track;
    }

    private void persistReadPermission(Uri uri, int flags) {
        int takeFlags = flags & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        try {
            getContext().getContentResolver().takePersistableUriPermission(uri, takeFlags);
        } catch (SecurityException ignored) {
            // Some providers grant temporary read access only. The UI marks lost access on rescan/play failure.
        }
    }

    private String displayName(Uri uri) {
        ContentResolver resolver = getContext().getContentResolver();
        try (Cursor cursor = resolver.query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) return cursor.getString(index);
            }
        } catch (Exception ignored) {
        }
        String tail = uri.getLastPathSegment();
        return tail == null ? "selected media" : tail;
    }

    private String readText(Uri uri) throws IOException {
        try (InputStream input = getContext().getContentResolver().openInputStream(uri)) {
            if (input == null) throw new IOException("Cannot open selected backup.");
            StringBuilder builder = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(input, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    builder.append(line).append('\n');
                }
            }
            return builder.toString();
        }
    }
}
