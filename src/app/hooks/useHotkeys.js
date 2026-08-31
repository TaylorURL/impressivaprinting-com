import { useEffect } from 'react';

// The modifier as this keyboard carries it. A Mac shown Ctrl and a PC shown
// Command are each being told to press a key they do not have. `navigator.platform`
// is deprecated and reads empty in some browsers, so `userAgent` answers there.
//
// The trailing space is part of the value: `Ctrl` needs one before the letter
// and the command glyph does not, so every place a key is drawn writes
// `{MODIFIER}K` and one shortcut cannot be spelled two ways.
export const MODIFIER = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)
  ? '\u2318'
  : 'Ctrl ';

function isTyping(el) {
  return (
    el &&
    (el.tagName === 'INPUT' ||
      el.tagName === 'TEXTAREA' ||
      el.tagName === 'SELECT' ||
      el.isContentEditable)
  );
}

// One shortcut, the standard one: Cmd/Ctrl+K opens search. `/` works too,
// GitHub-style, when not typing in a field.
export function useHotkeys({ onPalette }) {
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onPalette();
        return;
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTyping(document.activeElement)) return;
      if (e.key === '/') {
        e.preventDefault();
        onPalette();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onPalette]);
}
