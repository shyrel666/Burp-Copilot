package com.burpai.core;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.Arrays;
import java.util.Collections;
import org.junit.jupiter.api.Test;

class HighlightPaletteTest {

    @Test
    void highestSeverityWins() {
        assertEquals(HighlightPalette.RED, HighlightPalette.colorKeyFor(Arrays.asList("low", "critical", "info"), false));
        assertEquals(HighlightPalette.ORANGE, HighlightPalette.colorKeyFor(Arrays.asList("low", "high"), false));
        assertEquals(HighlightPalette.YELLOW, HighlightPalette.colorKeyFor(Arrays.asList("low", "medium"), false));
        assertEquals(HighlightPalette.BLUE, HighlightPalette.colorKeyFor(Collections.singletonList("low"), false));
        assertEquals(HighlightPalette.GRAY, HighlightPalette.colorKeyFor(Collections.singletonList("info"), false));
    }

    @Test
    void failedWithNoFindingsIsMagenta() {
        assertEquals(HighlightPalette.MAGENTA, HighlightPalette.colorKeyFor(Collections.emptyList(), true));
    }

    @Test
    void failedWithFindingsUsesSeverityColor() {
        assertEquals(HighlightPalette.RED, HighlightPalette.colorKeyFor(Collections.singletonList("critical"), true));
    }

    @Test
    void successWithNoFindingsIsGray() {
        assertEquals(HighlightPalette.GRAY, HighlightPalette.colorKeyFor(Collections.emptyList(), false));
    }
}
