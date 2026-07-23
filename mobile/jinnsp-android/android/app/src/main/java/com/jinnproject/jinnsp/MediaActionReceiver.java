package com.jinnproject.jinnsp;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class MediaActionReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        Intent activityIntent = new Intent(context, MainActivity.class);
        activityIntent.setAction(MainActivity.ACTION_MEDIA_CONTROL);
        activityIntent.putExtra(MainActivity.EXTRA_MEDIA_ACTION, intent.getStringExtra(MainActivity.EXTRA_MEDIA_ACTION));
        activityIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        context.startActivity(activityIntent);
    }
}
