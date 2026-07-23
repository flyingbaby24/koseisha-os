package com.jinnproject.jinnsp;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import androidx.media.app.NotificationCompat.MediaStyle;
import android.support.v4.media.MediaMetadataCompat;
import android.support.v4.media.session.MediaSessionCompat;
import android.support.v4.media.session.PlaybackStateCompat;

public final class MediaSessionHelper {
    private static final String CHANNEL_ID = "jinnsp_playback";
    private static final int NOTIFICATION_ID = 2424;
    private static MediaSessionCompat mediaSession;

    private MediaSessionHelper() {}

    public static void update(Context context, String title, String creator, boolean isPlaying) {
        ensureChannel(context);
        ensureSession(context);

        mediaSession.setMetadata(new MediaMetadataCompat.Builder()
            .putString(MediaMetadataCompat.METADATA_KEY_TITLE, title)
            .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, creator)
            .build());

        long actions = PlaybackStateCompat.ACTION_PLAY
            | PlaybackStateCompat.ACTION_PAUSE
            | PlaybackStateCompat.ACTION_SKIP_TO_NEXT
            | PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS;
        mediaSession.setPlaybackState(new PlaybackStateCompat.Builder()
            .setActions(actions)
            .setState(isPlaying ? PlaybackStateCompat.STATE_PLAYING : PlaybackStateCompat.STATE_PAUSED, 0, 1f)
            .build());
        mediaSession.setActive(true);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentTitle(title)
            .setContentText(creator)
            .setOngoing(isPlaying)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setStyle(new MediaStyle()
                .setMediaSession(mediaSession.getSessionToken())
                .setShowActionsInCompactView(0, 1, 2))
            .addAction(android.R.drawable.ic_media_previous, "Prev", actionIntent(context, "prev"))
            .addAction(
                isPlaying ? android.R.drawable.ic_media_pause : android.R.drawable.ic_media_play,
                isPlaying ? "Pause" : "Play",
                actionIntent(context, isPlaying ? "pause" : "play"))
            .addAction(android.R.drawable.ic_media_next, "Next", actionIntent(context, "next"));

        try {
            NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, builder.build());
        } catch (SecurityException ignored) {
            // Android 13+ notification permission may not be granted yet. Playback still works.
        }
    }

    private static void ensureSession(Context context) {
        if (mediaSession != null) return;
        mediaSession = new MediaSessionCompat(context, "JinnSP");
        mediaSession.setCallback(new MediaSessionCompat.Callback() {
            @Override public void onPlay() { sendAction(context, "play"); }
            @Override public void onPause() { sendAction(context, "pause"); }
            @Override public void onSkipToNext() { sendAction(context, "next"); }
            @Override public void onSkipToPrevious() { sendAction(context, "prev"); }
        });
    }

    private static PendingIntent actionIntent(Context context, String action) {
        Intent intent = new Intent(context, MainActivity.class);
        intent.setAction(MainActivity.ACTION_MEDIA_CONTROL);
        intent.putExtra(MainActivity.EXTRA_MEDIA_ACTION, action);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) flags |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getActivity(context, action.hashCode(), intent, flags);
    }

    private static void sendAction(Context context, String action) {
        try {
            actionIntent(context, action).send();
        } catch (PendingIntent.CanceledException ignored) {
        }
    }

    private static void ensureChannel(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null || manager.getNotificationChannel(CHANNEL_ID) != null) return;
        NotificationChannel channel = new NotificationChannel(CHANNEL_ID, "JinnSP Playback", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("JinnSP playback controls");
        manager.createNotificationChannel(channel);
    }
}
