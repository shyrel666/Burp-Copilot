package com.burpai.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ScopeRuleStoreTest {

    private ScopeRuleStore store() {
        return new ScopeRuleStore(new MapStore());
    }

    @Test
    void addAndRemoveRoundTrip() throws Exception {
        ScopeRuleStore store = store();
        store.addRule("*.target.com");
        store.addRule("api.example.com/**");
        store.removeRule("*.target.com");

        List<String> rules = store.getRules();
        assertEquals(1, rules.size());
        assertEquals("api.example.com/**", rules.get(0));
    }

    @Test
    void whitespaceAndEmptyPatternsAreRejected() {
        ScopeRuleStore store = store();
        assertThrows(ScopeRuleStore.ValidationException.class, () -> store.addRule(""));
        assertThrows(ScopeRuleStore.ValidationException.class, () -> store.addRule("   "));
        assertThrows(ScopeRuleStore.ValidationException.class, () -> store.addRule(null));
        assertTrue(store.getRules().isEmpty());
    }

    @Test
    void duplicateRulesAreNotAddedTwice() throws Exception {
        ScopeRuleStore store = store();
        store.addRule("*.target.com");
        store.addRule("*.target.com");
        assertEquals(1, store.getRules().size());
    }

    @Test
    void enabledFlagPersists() {
        ScopeRuleStore store = store();
        assertFalse(store.isEnabled());
        store.setEnabled(true);
        assertTrue(store.isEnabled());
        store.setEnabled(false);
        assertFalse(store.isEnabled());
    }

    @Test
    void encodeDecodePreservesSpecialCharacters() {
        List<String> input = List.of("a\"b", "c\\d", "*.x.com");
        String encoded = ScopeRuleStore.encodeArray(input);
        assertEquals(input, ScopeRuleStore.decodeArray(encoded));
    }

    static final class MapStore implements ScopeRuleStore.StringStore {
        private final Map<String, String> data = new HashMap<>();

        @Override
        public String getString(String key) {
            return data.get(key);
        }

        @Override
        public void setString(String key, String value) {
            data.put(key, value);
        }
    }
}
