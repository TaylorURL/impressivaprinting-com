// The storefront's form treatment: a ruled underline rather than a box, in
// either tone. Defined once, so the contact sheet and the account pages keep
// the same control height and the same label-to-control rhythm.

const TONES = {
  ink: {
    label: 'text-paper-100/45',
    input: 'border-paper-100/20 text-paper-100 placeholder:text-paper-100/30',
  },
  paper: {
    label: 'text-ink-950/50',
    input: 'border-ink-950/20 text-ink-950 placeholder:text-ink-950/35',
  },
};

export const fieldLabel = (tone = 'ink') => `kicker mb-2 block ${TONES[tone].label}`;

export const fieldInput = (tone = 'ink') =>
  `control w-full border-b bg-transparent py-3 outline-none transition-colors focus:border-flare ${TONES[tone].input}`;
