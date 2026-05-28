import { createContext, useContext } from 'react';
import { zh, type LocaleKeys } from './zh';
import { en } from './en';

export type Locale = 'zh' | 'en';

const messages: Record<Locale, Record<LocaleKeys, string>> = { zh, en };

export interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: LocaleKeys) => string;
}

export const LocaleContext = createContext<LocaleContextValue>({
  locale: 'zh',
  setLocale: () => {},
  t: (key) => zh[key],
});

export function useLocale() {
  return useContext(LocaleContext);
}

export function getMessages(locale: Locale) {
  return messages[locale];
}

export type { LocaleKeys };
