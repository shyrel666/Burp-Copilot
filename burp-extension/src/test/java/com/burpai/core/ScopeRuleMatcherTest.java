package com.burpai.core;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ScopeRuleMatcherTest {

    @Test
    void singleWildcardMatchesWithinOneDomainSegment() {
        assertTrue(ScopeRuleMatcher.matches("*.target.com", "https://www.target.com/x"));
        assertFalse(ScopeRuleMatcher.matches("*.target.com", "https://a.b.target.com/x"));
    }

    @Test
    void doubleWildcardCrossesSegments() {
        assertTrue(ScopeRuleMatcher.matches("**.target.com", "https://a.b.target.com/x"));
    }

    @Test
    void schemeAgnosticWhenPatternHasNoScheme() {
        assertTrue(ScopeRuleMatcher.matches("api.example.com", "http://api.example.com/v1"));
        assertTrue(ScopeRuleMatcher.matches("api.example.com", "https://api.example.com/v1"));
    }

    @Test
    void schemeEnforcedWhenPatternHasScheme() {
        assertTrue(ScopeRuleMatcher.matches("https://api.example.com", "https://api.example.com/v1"));
        assertFalse(ScopeRuleMatcher.matches("https://api.example.com", "http://api.example.com/v1"));
    }

    @Test
    void hostMatchingIsCaseInsensitive() {
        assertTrue(ScopeRuleMatcher.matches("API.Example.com", "https://api.example.COM/v1"));
    }

    @Test
    void pathWildcardDoesNotCrossSlash() {
        assertTrue(ScopeRuleMatcher.matches("api.example.com/admin/*", "https://api.example.com/admin/users"));
        assertFalse(ScopeRuleMatcher.matches("api.example.com/admin/*", "https://api.example.com/admin/users/1"));
        assertTrue(ScopeRuleMatcher.matches("api.example.com/admin/**", "https://api.example.com/admin/users/1"));
    }

    @Test
    void hostOnlyPatternMatchesAnyPath() {
        assertTrue(ScopeRuleMatcher.matches("api.example.com", "https://api.example.com/any/deep/path"));
    }

    @Test
    void explicitPortInPatternMustMatchUrlPort() {
        assertTrue(ScopeRuleMatcher.matches("api.example.com:8080", "http://api.example.com:8080/v1"));
        assertFalse(ScopeRuleMatcher.matches("api.example.com:8080", "http://api.example.com:9090/v1"));
        assertFalse(ScopeRuleMatcher.matches("api.example.com:8080", "http://api.example.com/v1"));
    }

    @Test
    void portPatternCombinesWithWildcardHostAndPath() {
        assertTrue(ScopeRuleMatcher.matches("*.target.com:8443/admin/**",
                "https://shop.target.com:8443/admin/users/1"));
        assertFalse(ScopeRuleMatcher.matches("*.target.com:8443/admin/**",
                "https://shop.target.com:443/admin/users/1"));
    }

    @Test
    void hostOnlyPatternStillMatchesAnyPort() {
        assertTrue(ScopeRuleMatcher.matches("api.example.com", "http://api.example.com:8080/v1"));
    }

    @Test
    void noRulesMeansNothingInScope() {
        ScopeRuleStore store = new ScopeRuleStore(new MapStore());
        ScopeRuleMatcher matcher = new ScopeRuleMatcher(store);
        assertFalse(matcher.isInScope("https://api.example.com/v1"));
    }

    @Test
    void inScopeWhenAnyRuleMatches() throws Exception {
        ScopeRuleStore store = new ScopeRuleStore(new MapStore());
        store.addRule("*.target.com");
        ScopeRuleMatcher matcher = new ScopeRuleMatcher(store);
        assertTrue(matcher.isInScope("https://shop.target.com/cart"));
        assertFalse(matcher.isInScope("https://other.example.com/cart"));
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
