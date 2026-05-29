package com.burpai.core;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.core.Annotations;
import burp.api.montoya.core.HighlightColor;

/**
 * Applies a color highlight and a summary note to the captured {@link Annotations}
 * of an auto-analyzed message once its task completes.
 *
 * The annotations reference is captured when the message is first seen (proxy
 * response or Site Map entry) and mutated here; annotation/highlight failures are
 * non-fatal.
 */
public final class HighlightManager implements TaskPoller.HighlightSink {
    private final MontoyaApi api;

    public HighlightManager(MontoyaApi api) {
        this.api = api;
    }

    @Override
    public void apply(Object handle, String colorKey, String notes) {
        if (!(handle instanceof Annotations)) {
            return;
        }
        Annotations annotations = (Annotations) handle;
        try {
            annotations.setHighlightColor(toColor(colorKey));
        } catch (RuntimeException ex) {
            api.logging().logToError("应用高亮失败", ex);
        }
        if (notes != null && !notes.isEmpty()) {
            try {
                annotations.setNotes(notes);
            } catch (RuntimeException ignored) {
                // comment is best-effort
            }
        }
    }

    static HighlightColor toColor(String colorKey) {
        if (colorKey == null) {
            return HighlightColor.NONE;
        }
        switch (colorKey) {
            case HighlightPalette.RED: return HighlightColor.RED;
            case HighlightPalette.ORANGE: return HighlightColor.ORANGE;
            case HighlightPalette.YELLOW: return HighlightColor.YELLOW;
            case HighlightPalette.BLUE: return HighlightColor.BLUE;
            case HighlightPalette.MAGENTA: return HighlightColor.MAGENTA;
            case HighlightPalette.GRAY: return HighlightColor.GRAY;
            default: return HighlightColor.GRAY;
        }
    }
}
