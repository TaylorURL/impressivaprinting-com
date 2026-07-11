// Shared class-string tokens reused across views and components.

// Page gutter: centered, capped width, responsive horizontal padding.
export const CONTAINER = 'mx-auto max-w-[1400px] px-5 sm:px-8';

// Form field primitives — mono kicker label above an underlined transparent input.
export const FORM_LABEL = 'kicker mb-2 block text-paper-100/45';
export const FORM_INPUT =
  'w-full border-b border-paper-100/20 bg-transparent py-3 text-paper-100 placeholder:text-paper-100/30 outline-none transition-colors focus:border-flare';

// Upload status → text color, shared by the account and admin dashboards.
export const UPLOAD_STATUS_STYLE = {
  new: 'text-proc-c',
  'in-production': 'text-proc-y',
  ready: 'text-flare',
  archived: 'text-paper-100/40',
};
