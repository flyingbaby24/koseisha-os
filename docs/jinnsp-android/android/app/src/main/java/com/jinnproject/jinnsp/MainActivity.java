package com.jinnproject.jinnsp;

import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    public static final String ACTION_MEDIA_CONTROL = "com.jinnproject.jinnsp.MEDIA_CONTROL";
    public static final String EXTRA_MEDIA_ACTION = "media_action";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(JinnSPNativePlugin.class);
        super.onCreate(savedInstanceState);
        requestNotificationPermission();
        handleMediaIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleMediaIntent(intent);
    }

    private void handleMediaIntent(Intent intent) {
        if (intent == null || !ACTION_MEDIA_CONTROL.equals(intent.getAction())) return;
        String action = intent.getStringExtra(EXTRA_MEDIA_ACTION);
        if (action == null || getBridge() == null || getBridge().getWebView() == null) return;
        getBridge().getWebView().post(() ->
            getBridge().getWebView().evaluateJavascript(
                "window.JinnSPMediaControls && window.JinnSPMediaControls['" + action + "'] && window.JinnSPMediaControls['" + action + "']()",
                null
            )
        );
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return;
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) return;
        ActivityCompat.requestPermissions(this, new String[] { android.Manifest.permission.POST_NOTIFICATIONS }, 2424);
    }
}
